"""EuRoC-adapted upstream TLIO and AirIO networks with causal inertial filters."""
import importlib.util,json,logging,sys,time,types
from types import SimpleNamespace
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from torch.utils.data import Dataset,DataLoader
from common import ROOT,PROJECT,UPSTREAM,PROTOCOL,OUT,MODELS,seed_all,save_json,save_csv,metrics

P=PROTOCOL['io'];DEST=OUT/'IO';DEST.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'datasets/EuRoC/processed_learning'
sys.path.insert(0,str(UPSTREAM/'TLIO/src'))
# The upstream package initializer imports GUI and training CLIs that this harness does not use.
network_package=types.ModuleType('network')
network_package.__path__=[str(UPSTREAM/'TLIO/src/network')]
sys.modules['network']=network_package
from network.model_resnet import BasicBlock1D,ResNet1D
from network.losses import get_loss
from tracker.scekf import ImuMSCKF
from utils.math_utils import hat
from utils.dotdict import dotdict
from utils.logging import logging as tlio_logging
tlio_logging.getLogger().setLevel(logging.ERROR)
spec=importlib.util.spec_from_file_location('airio_architecture',UPSTREAM/'AirIO/model/code.py')
air=importlib.util.module_from_spec(spec);spec.loader.exec_module(air)

def load(seq):
    return dict(np.load(DATA/seq/'inputs.npz')),dict(np.load(DATA/seq/'reference.npz'))

def model(method):
    if method=='TLIO':return ResNet1D(BasicBlock1D,6,3,[2,2,2,2],200//32+1)
    return air.CodeNetMotionwithRot(SimpleNamespace(propcov=True))

class Windows(Dataset):
    def __init__(self,sequences,method,augment=False):
        self.method=method;self.window=200 if method=='TLIO' else 1000;self.augment=augment;self.seq=[];self.index=[]
        for name in sequences:
            d,g=load(name);r=Rotation.from_quat(g['quaternion']);R=r.as_matrix()
            acc=d['acc'].astype(float)-g['acc_bias'][0];gyro=d['gyro'].astype(float)-g['gyro_bias'][0]
            vbody=np.einsum('nji,nj->ni',R,g['velocity'])
            globalimu=np.column_stack([np.einsum('nij,nj->ni',R,gyro),np.einsum('nij,nj->ni',R,acc)])
            idx=len(self.seq);self.seq.append(dict(acc=acc.astype('float32'),gyro=gyro.astype('float32'),rot=r.as_rotvec().astype('float32'),globalimu=globalimu,position=g['position'],velocity=vbody.astype('float32'),yaw=r.as_euler('xyz')[:,2]))
            self.index.extend((idx,i) for i in range(0,len(acc)-self.window,self.window))
        assert self.index
    def __len__(self):return len(self.index)
    def __getitem__(self,index):
        s,i=self.index[index];d=self.seq[s];j=i+self.window
        if self.method=='TLIO':
            angle=-d['yaw'][i]+(np.random.uniform(-np.pi,np.pi) if self.augment else 0.)
            c,s=np.cos(angle),np.sin(angle);rz=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
            x=d['globalimu'][i:j].copy();x[:,:3]=x[:,:3]@rz.T;x[:,3:]=x[:,3:]@rz.T
            y=(d['position'][j]-d['position'][i])@rz.T
            return torch.tensor(x.T,dtype=torch.float32),torch.tensor(y,dtype=torch.float32)
        return {'acc':torch.from_numpy(d['acc'][i:j]),'gyro':torch.from_numpy(d['gyro'][i:j]),'rot':torch.from_numpy(d['rot'][i:j])},torch.from_numpy(d['velocity'][i:j+1])

def train_loss(net,batch,method,epoch):
    x,y=batch
    if method=='TLIO':
        pred,logstd=net(x);loss=get_loss(pred,logstd,y,epoch).mean()
        val=(pred-y).square().sum(-1).mean()
    else:
        out=net(x,x['rot']);target=net.get_label(y);error=out['net_vel']-target
        cov=out['cov'].clamp_min(1e-7)
        loss=100*(torch.nn.functional.huber_loss(error,torch.zeros_like(error),delta=.005)+1e-4*(error.square()/cov+cov.log()).mean())
        val=error.square().sum(-1).mean()
    return loss,val

def train_models():
    for method in ['TLIO','AirIO']:
        train=Windows(P['train'],method,augment=True);val=Windows(P['validation'],method)
        save_json(DEST/f'{method}_window_counts.json',{'training_windows':len(train),'validation_windows':len(val),'window_samples':train.window,'training_stride_samples':train.window})
        for seed in PROTOCOL['seeds']:
            path=MODELS/'IO'/method/f'seed_{seed}'/'best.pt';path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():continue
            seed_all(seed);net=model(method);opt=torch.optim.Adam(net.parameters(),lr=P['learning_rate'],weight_decay=1e-4)
            loader=DataLoader(train,batch_size=P['batch_size'],shuffle=True,num_workers=0)
            vl=DataLoader(val,batch_size=P['batch_size'],shuffle=False,num_workers=0)
            best=float('inf');wait=0;hist=[];start=time.perf_counter()
            for epoch in range(P['epochs']):
                net.train();losses=[]
                for batch in loader:
                    loss,_=train_loss(net,batch,method,epoch)
                    assert torch.isfinite(loss),'Nonfinite training loss'
                    opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),10);opt.step();losses.append(loss.item())
                net.eval();vals=[]
                with torch.no_grad():
                    for batch in vl:
                        _,v=train_loss(net,batch,method,epoch);vals.append((float(v),len(batch[1])))
                error=float(np.sqrt(sum(v*n for v,n in vals)/sum(n for _,n in vals)))
                hist.append(dict(epoch=epoch+1,train_loss=float(np.mean(losses)),validation_network_error=error))
                # Let the TLIO covariance head receive training before checkpoint selection.
                eligible=method!='TLIO' or epoch>=10
                if eligible and error<best:
                    best=error;wait=0;torch.save(net.state_dict(),path)
                    save_json(path.with_suffix('.json'),dict(best_epoch=epoch+1,validation_network_error=error,validation_error_unit='m' if method=='TLIO' else 'm/s'))
                elif eligible:wait+=1
                if epoch%5==0:print(method,seed,epoch+1,'validation',round(error,4),'seconds',round(time.perf_counter()-start,1),flush=True)
                if wait>=P['patience']:break
            save_csv(DEST/f'training_{method}_{seed}.csv',hist)
            save_json(DEST/f'training_{method}_{seed}.json',dict(wall_s=time.perf_counter()-start,epochs=len(hist),validation_error=best))
            if method=='TLIO':
                net.load_state_dict(torch.load(path,weights_only=True));net.eval()
                traced=torch.jit.trace(net,torch.zeros(1,6,200));traced.save(str(path.with_suffix('.torchscript.pt')))

def tuning():
    return dotdict(dict(g_norm=9.81007,sigma_na=np.sqrt(1e-3),sigma_ng=np.sqrt(1e-4),ita_ba=1e-4,ita_bg=1e-6,init_attitude_sigma=np.deg2rad(1),init_yaw_sigma=np.deg2rad(.1),init_vel_sigma=1.,init_pos_sigma=.001,init_bg_sigma=.0001,init_ba_sigma=.02,meascov_scale=10.,mahalanobis_fail_scale=0,use_const_cov=False,add_sim_meas_noise=False))

def velocity_update(f,measurement,cov,t):
    s=f.state;R=s.s_R;v=s.s_v
    H=np.zeros((3,15));H[:,:3]=R.T@hat(v);H[:,3:6]=R.T
    noise=np.diag(np.maximum(np.asarray(cov),.01))*10
    error=measurement.reshape(3,1)-R.T@v;S=H@f.Sigma@H.T+noise
    nis=float((error.T@np.linalg.solve(S,error)).item())
    if t>15 and nis>11.345:return False
    K=np.linalg.solve(S,H@f.Sigma).T
    f.state.apply_correction(K@error)
    A=np.eye(15)-K@H
    f.Sigma=A@f.Sigma@A.T+K@noise@K.T;f.Sigma=(f.Sigma+f.Sigma.T)/2;f.Sigma15=f.Sigma
    return True

def validate_velocity_jacobian():
    R=Rotation.from_rotvec([.2,-.1,.3]).as_matrix();v=np.array([[.8],[1.2],[-.4]])
    H=np.column_stack([R.T@hat(v),R.T])
    numeric=[]
    for j in range(6):
        d=np.eye(6)[j]*1e-6
        plus=(Rotation.from_rotvec(d[:3]).as_matrix()@R).T@(v+d[3:,None])
        minus=(Rotation.from_rotvec(-d[:3]).as_matrix()@R).T@(v-d[3:,None])
        numeric.append(((plus-minus)/2e-6).ravel())
    gap=float(np.max(abs(H-np.array(numeric).T)));assert gap<1e-7
    save_json(DEST/'velocity_update_check.json',{'max_jacobian_error':gap,'reference_orientation_during_inference':False})

def causal_inference(d,initial,method,net=None,torchscript=None):
    # Only this single initial reference state is accepted by the inference function.
    r0,v0,p0,bg0,ba0=initial
    t=d['time'];acc=d['acc'].astype(float)-ba0;gyro=d['gyro'].astype(float)-bg0
    count=len(t);position=np.empty((count,3));rotation=np.empty((count,3,3));position[0]=p0;rotation[0]=r0
    vel=np.empty((count,3));vel[0]=v0;attempts=accepted=0
    if method=='TLIO':
        from tracker import meas_source_torchscript as source
        class CPUOnlySource(source.MeasSourceTorchScript):
            def __init__(self,model_path,force_cpu=False):
                self.device=torch.device('cpu');self.net=torch.jit.load(str(model_path),map_location='cpu');self.net.eval()
        # Constructor-only compatibility adjustment; upstream inference and EKF remain unchanged.
        import tracker.imu_tracker as tracker_module
        tracker_module.MeasSourceTorchScript=CPUOnlySource
        param=DEST/'tlio_network_parameters.json'
        save_json(param,dict(imu_freq=200.,past_time=0.,window_time=1.,arch='resnet'))
        tr=tracker_module.ImuTracker(str(torchscript),str(param),5.,tuning(),None,force_cpu=True)
        tr.init_with_state_at_time(0,r0,v0[:,None],p0[:,None],gyro[0,:,None],acc[0,:,None]);f=tr.filter
    else:
        f=ImuMSCKF(tuning());f.initialize_with_state(0,r0,v0[:,None],p0[:,None],np.zeros((3,1)),np.zeros((3,1)))
    start=time.perf_counter()
    for i in range(1,count):
        us=int(round(t[i]*1e6))
        if method=='TLIO':
            did=tr.on_imu_measurement(us,gyro[i,:,None],acc[i,:,None]);attempts+=int(did)
        else:
            f.propagate(acc[i,:,None],gyro[i,:,None],us)
            if method=='AirIO' and i>=1000 and i%40==0:
                ids=slice(i-1000,i)
                data={'acc':torch.tensor(acc[ids],dtype=torch.float32)[None],'gyro':torch.tensor(gyro[ids],dtype=torch.float32)[None]}
                ori=Rotation.from_matrix(rotation[ids]).as_rotvec()
                with torch.no_grad():out=net(data,torch.tensor(ori,dtype=torch.float32)[None])
                measurement=out['net_vel'][0,-1].numpy();cov=out['cov'][0,-1].numpy()
                attempts+=1;accepted+=int(velocity_update(f,measurement,cov,float(t[i])))
        position[i]=f.state.s_p.ravel();rotation[i]=f.state.s_R;vel[i]=f.state.s_v.ravel()
        assert np.isfinite(position[i]).all()
    wall=time.perf_counter()-start
    return position,vel,rotation,wall,attempts,(None if method=='TLIO' else accepted)

def main():
    validate_velocity_jacobian();train_models();rows=[]
    for seq in P['test']:
        d,g=load(seq);initial=(Rotation.from_quat(g['quaternion'][0]).as_matrix(),g['velocity'][0],g['position'][0],g['gyro_bias'][0],g['acc_bias'][0])
        grid=np.arange(5,float(d['time'][-1]),.1)
        gt=np.column_stack([np.interp(grid,d['time'],g['position'][:,j]) for j in range(3)])
        for method in P['methods']:
            for seed in ([0] if method=='IMU' else PROTOCOL['seeds']):
                target=DEST/f'{seq}_{method}_{seed}.npz'
                if target.exists():
                    result=dict(np.load(target));rows.append(json.loads(target.with_suffix('.json').read_text()));continue
                net=None;script=None
                if method!='IMU':
                    path=MODELS/'IO'/method/f'seed_{seed}'/'best.pt'
                    if method=='AirIO':net=model(method);net.load_state_dict(torch.load(path,weights_only=True));net.eval()
                    else:script=path.with_suffix('.torchscript.pt')
                pos,v,r,wall,attempted,accepted=causal_inference(d,initial,method,net,script)
                pred=np.column_stack([np.interp(grid,d['time'],pos[:,j]) for j in range(3)])
                row=dict(sequence=seq,method=method,seed=seed,**metrics(pred,gt,grid),wall_s=wall,updates=attempted,accepted_updates=accepted)
                rows.append(row);np.savez_compressed(target,time=grid,position=pred,reference=gt)
                save_json(target.with_suffix('.json'),row)
                print('TEST',seq,method,seed,'RMSE',round(row['rmse_3d_m'],3),'wall_s',round(wall,1),flush=True)
    save_csv(DEST/'metrics.csv',rows);save_json(DEST/'status.json',{'status':'complete','methods':P['methods'],'seeds':PROTOCOL['seeds']})

if __name__=='__main__':main()
