"""Controlled TDL-GNSS head ablations using the upstream network and GNSS terms."""
import importlib.util,sys,time
from pathlib import Path
import numpy as np
import torch
from common import ROOT,PROJECT,UPSTREAM,PROTOCOL,OUT,MODELS,seed_all,save_json,save_csv,metrics

spec=importlib.util.spec_from_file_location('tdl_model',UPSTREAM/'TDL-GNSS/model/model.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
Net=module.HybridShareSysNet
P=PROTOCOL['gnss'];DEST=OUT/'GNSS';DEST.mkdir(parents=True,exist_ok=True)

def load(names):
    raw=[dict(np.load(ROOT/'datasets/UrbanNav/learning_processed'/(n+'.npz'))) for n in names]
    m=max(a['mask'].shape[1] for a in raw)
    for a in raw:
        for k in ['mask','res','feat','sat','clock']:
            a[k]=np.pad(a[k],[(0,0),(0,m-a[k].shape[1])]+([(0,0)] if a[k].ndim==3 else []))
    return {k:torch.tensor(np.concatenate([a[k] for a in raw]),dtype=torch.float64) for k in raw[0]}

def subset(d,i):return {k:v[i] for k,v in d.items()}

def solve(d,w,b):
    mask=d['mask'];w=w.clamp_min(.001)*mask
    dp=torch.zeros_like(d['pos']);dc=torch.zeros_like(d['cb'])
    base_range=torch.linalg.vector_norm(d['sat']-d['pos'][:,None,:],dim=-1)
    active=(d['clock'].sum(1)>0).double()
    unused=torch.cat([torch.zeros_like(dp),1-active],dim=1)
    for _ in range(4):
        diff=d['pos'][:,None,:]+dp[:,None,:]-d['sat']
        distance=torch.linalg.vector_norm(diff,dim=-1).clamp_min(1)
        H=torch.cat([diff/distance[:,:,None],d['clock']],dim=-1)*mask[:,:,None]
        residual=(d['res']-b-(distance-base_range)-(d['clock']@dc[:,:,None]).squeeze(-1))*mask
        A=H*w[:,:,None];z=residual*w
        step=torch.linalg.solve(A.transpose(1,2)@A+torch.diag_embed(unused),(A.transpose(1,2)@z[:,:,None])).squeeze(-1)
        dp=dp+step[:,:3];dc=dc+step[:,3:]
    return d['pos']+dp

def forward(net,d,method):
    sh=d['mask'].shape
    w,b=net(d['feat'].reshape(-1,9));w=w.reshape(sh);b=b.reshape(sh)
    if method=='TDL-W':b=torch.zeros_like(b)
    if method=='TDL-B':w=torch.ones_like(w)
    return solve(d,w,b)

def validate_solver(d):
    q=subset(d,slice(0,3));w=torch.ones_like(q['mask']);b=torch.zeros_like(w)
    p=solve(q,w,b)
    assert torch.max(abs(p-q['pos']))<.002, 'Baseline parity failed'
    b.requires_grad_();loss=solve(q,w,b).square().sum();g=torch.autograd.grad(loss,b)[0]
    assert torch.isfinite(g).all() and g.abs().sum()>0
    # Compare a nonuniform-weight, nonzero-bias epoch against upstream nonlinear WLS.
    import tasgnss as tas
    r=ROOT/'datasets/KLT/0610_KLT'
    obs,nav,_=tas.read_obs(str(r/'COM38_210610_025603.obs'),str(r/'sta/hksc161d.21*'))
    o=tas.filter_obs(tas.split_obs(obs),float(q['time'][0]),float(q['time'][0])+1)[0]
    ret=tas.wls_pnt_pos(o,nav,w=1,return_residual=True)
    n=len(ret['data']);ws=np.linspace(.2,1,n);bs=np.linspace(0,3,n)
    ref=tas.wls_pnt_pos(o,nav,w=ws,b=bs)['pos']
    w=torch.ones_like(q['mask'][:1]);w[0,:n]=torch.tensor(ws)
    b=torch.zeros_like(w);b[0,:n]=torch.tensor(bs)
    ours=solve(subset(q,slice(0,1)),w,b)[0].detach().numpy()
    gap=float(np.linalg.norm(ref-ours));assert gap<.005,(gap,ref,ours)
    save_json(DEST/'solver_check.json',{'upstream_position_difference_m':gap,'baseline_tolerance_m':.002,'gradient_finite':True})

def main():
    train=load(P['train']);val=load(P['validation']);validate_solver(train)
    x=train['feat'][train['mask'].bool()];mean=x.mean(0);std=x.std(0);mean[4:]=0;std[4:]=1
    assert (std>0).all()
    for method in P['methods'][1:]:
        for seed in PROTOCOL['seeds']:
            modelpath=MODELS/'GNSS'/method/f'seed_{seed}'/'best.pt';modelpath.parent.mkdir(parents=True,exist_ok=True)
            if modelpath.exists():continue
            seed_all(seed);net=Net(mean.clone(),std.clone()).double()
            # Keep the upstream ReLU bias head active at initialization.
            with torch.no_grad():net.seq[-1].bias[1]=1.
            opt=torch.optim.Adam(net.parameters(),lr=P['learning_rate'])
            best=float('inf');wait=0;hist=[];start=time.perf_counter()
            for epoch in range(P['epochs']):
                net.train();losses=[]
                for inds in torch.randperm(len(train['time'])).split(P['batch_size']):
                    d=subset(train,inds);pred=forward(net,d,method)
                    loss=torch.linalg.vector_norm(pred-d['gt'],dim=1).mean()
                    assert torch.isfinite(loss)
                    opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),100);opt.step();losses.append(loss.item())
                net.eval()
                with torch.no_grad():vl=float(torch.linalg.vector_norm(forward(net,val,method)-val['gt'],dim=1).mean())
                hist.append(dict(epoch=epoch+1,train_mean_position_loss_m=float(np.mean(losses)),validation_mean_position_error_m=vl))
                if vl<best:
                    best=vl;wait=0;torch.save(net.state_dict(),modelpath)
                    save_json(modelpath.with_suffix('.json'),dict(best_epoch=epoch+1,validation_mean_position_error_m=vl,seed=seed))
                else:wait+=1
                if epoch%10==0:print(method,seed,epoch+1,'validation',round(vl,3),flush=True)
                if wait>=P['patience']:break
            save_csv(DEST/f'training_{method}_{seed}.csv',hist)
            save_json(DEST/f'training_{method}_{seed}.json',dict(wall_s=time.perf_counter()-start,epochs=len(hist),best_validation_m=best))
    rows=[]
    for name in P['test']:
        d=load([name]);t=d['time'].numpy();gt=d['gt'].numpy()
        import pymap3d as pm
        lat,lon,h=pm.ecef2geodetic(*gt[0]);ref=np.array(pm.ecef2enu(*gt.T,lat,lon,h)).T
        pred_all={'WLS':d['pos'].numpy()}
        for method in P['methods']:
            seeds=[0] if method=='WLS' else PROTOCOL['seeds']
            for seed in seeds:
                start=time.perf_counter()
                if method=='WLS':pos=d['pos'].numpy()
                else:
                    net=Net(mean.clone(),std.clone()).double();net.load_state_dict(torch.load(MODELS/'GNSS'/method/f'seed_{seed}'/'best.pt',weights_only=True));net.eval()
                    with torch.no_grad():pos=forward(net,d,method).numpy()
                wall=time.perf_counter()-start
                enu=np.array(pm.ecef2enu(*pos.T,lat,lon,h)).T
                row=dict(sequence=name,method=method,seed=seed,**metrics(enu,ref,t),wall_s=wall)
                rows.append(row);np.savez_compressed(DEST/f'{name}_{method}_{seed}.npz',time=t,position=enu,reference=ref,reference_quality=d['quality'].numpy())
                print('TEST',name,method,seed,row['rmse_3d_m'],flush=True)
    save_csv(DEST/'metrics.csv',rows)
    save_json(DEST/'status.json',{'status':'complete','methods':P['methods'],'seeds':PROTOCOL['seeds']})

if __name__=='__main__':main()
