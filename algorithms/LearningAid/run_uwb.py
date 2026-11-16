"""UTIL ESKF with controlled robust and learned signed-bias updates."""
import importlib.util,sys,time
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation,Slerp
from pyquaternion import Quaternion
import torch
from common import ROOT,PROJECT,UPSTREAM,PROTOCOL,OUT,MODELS,seed_all,save_json,save_csv,metrics

sys.path.insert(0,str(UPSTREAM/'UTIL/scripts/estimation'))
from eskf_class import ESKF
P=PROTOCOL['uwb'];D=ROOT/'datasets/UTIL/dataset/flight-dataset';DEST=OUT/'UWB';DEST.mkdir(parents=True,exist_ok=True)
ARM=np.array([-.01245,.00127,.0908])

def records(const):
    if const=='const4':
        return [D/f'csv-data/{const}/{const}-trial{trial}-tdoa2-traj{trajectory}.csv' for trial in [1,2,3] for trajectory in [1,2,3]]
    return [D/f'csv-data/{const}/{const}-trial{trial}-tdoa2.csv' for trial in [1,2,3]]

def data(path):
    df=pd.read_csv(path)
    def cols(names):
        a=df[names].dropna().to_numpy();return a[np.argsort(a[:,0],kind='stable')]
    gt=cols(['t_pose','pose_x','pose_y','pose_z','pose_qx','pose_qy','pose_qz','pose_qw'])
    acc=cols(['t_acc','acc_x','acc_y','acc_z']);gyro=cols(['t_gyro','gyro_x','gyro_y','gyro_z'])
    uwb=cols(['t_tdoa','idA','idB','tdoa_meas'])
    # Last available gyro sample makes synchronization causal.
    gi=np.clip(np.searchsorted(gyro[:,0],acc[:,0],side='right')-1,0,len(gyro)-1)
    imu=np.column_stack([acc,gyro[gi,1:]])[::8]
    pairs=[uwb[(uwb[:,1]==i)&(uwb[:,2]==((i+1)%8))][::8] for i in range(8)]
    uwb=np.concatenate(pairs);uwb=uwb[np.argsort(uwb[:,0],kind='stable')]
    anchor=np.load(D/f'survey-results/anchor_{path.parent.name}.npz')['an_pos']
    assert np.isfinite(imu).all() and np.isfinite(uwb).all() and len(uwb)>100
    return imu,uwb,gt,anchor

def features(pos,rot,anchors,ids):
    pos=np.atleast_2d(pos);rot=np.asarray(rot).reshape(-1,3,3);ids=np.asarray(ids,dtype=int).reshape(-1,2)
    tag=pos+np.einsum('nij,j->ni',rot,ARM)
    a=anchors[ids[:,0]]-tag;b=anchors[ids[:,1]]-tag
    a=np.einsum('nji,nj->ni',rot,a);b=np.einsum('nji,nj->ni',rot,b)
    def angle(v):return np.column_stack([np.arctan2(v[:,1],v[:,0]),np.arctan2(v[:,2],np.linalg.norm(v[:,:2],axis=1))])
    return np.column_stack([a,b,angle(a),angle(b)])

def examples(consts):
    xs=[];ys=[];counts={}
    for const in consts:
        for path in records(const):
            _,u,g,a=data(path);u=u[(u[:,0]>=g[0,0])&(u[:,0]<=g[-1,0])]
            pos=np.column_stack([np.interp(u[:,0],g[:,0],g[:,j]) for j in [1,2,3]])
            rot=Slerp(g[:,0],Rotation.from_quat(g[:,4:8]))(u[:,0]).as_matrix()
            x=features(pos,rot,a,u[:,1:3]);tag=pos+np.einsum('nij,j->ni',rot,ARM)
            y=u[:,3]-(np.linalg.norm(tag-a[u[:,2].astype(int)],axis=1)-np.linalg.norm(tag-a[u[:,1].astype(int)],axis=1))
            xs.append(x);ys.append(y);counts[path.stem]=len(y)
    return np.concatenate(xs),np.concatenate(ys),counts

class BiasNet(torch.nn.Module):
    def __init__(self,mean,std):
        super().__init__();self.register_buffer('mean',torch.as_tensor(mean,dtype=torch.float32));self.register_buffer('std',torch.as_tensor(std,dtype=torch.float32))
        self.net=torch.nn.Sequential(torch.nn.Linear(10,64),torch.nn.ReLU(),torch.nn.Linear(64,64),torch.nn.ReLU(),torch.nn.Linear(64,1))
    def forward(self,x):return self.net((x-self.mean)/self.std).squeeze(-1)

class LearnedESKF(ESKF):
    def __init__(self,*args,net=None,robust=False,**kwargs):
        super().__init__(*args,**kwargs);self.net=net;self.robust=robust;self.attempts=0;self.accepted=0;self.bias=[]
    def UWB_correct(self,uwb,anchor_position,k):
        self.attempts+=1
        q=Quaternion(self.q_list[k]);rot=q.rotation_matrix;p=self.Xpr[k,:3];tag=p+rot@ARM
        a,b=anchor_position[uwb[:2].astype(int)]
        predicted=np.linalg.norm(tag-b)-np.linalg.norm(tag-a)
        bias=0.
        if self.net is not None:
            x=features(p,rot,anchor_position,uwb[:2])
            with torch.no_grad():bias=float(self.net(torch.tensor(x,dtype=torch.float32)).item())
            bias=float(np.clip(bias,-2,2))
        self.bias.append(bias)
        err=float(uwb[2]-bias-predicted)
        G=self.computeG_grad(a,b,self.t_uv,p,self.q_list[k]);Q=self.std_uwb_tdoa**2
        M=float((G@self.Ppr[k]@G.T).item()+Q)
        z=abs(err)/np.sqrt(M)
        if z>=5:return
        if self.robust:
            weight=min(1.,1.345/max(z,1e-12));Q/=weight;M=float((G@self.Ppr[k]@G.T).item()+Q)
        gain=self.Ppr[k]@G.T/M
        self.Ppo[k]=(np.eye(9)-gain@G)@self.Ppr[k]
        self.Ppo[k]=(self.Ppo[k]+self.Ppo[k].T)/2
        dx=(gain*err).ravel();self.Xpo[k]=self.Xpr[k]+dx[:6]
        dq=Quaternion(self.zeta(dx[6:]));qn=q*dq
        self.q_list[k]=[qn.w,qn.x,qn.y,qn.z];self.accepted+=1

def run(path,net,robust,base=False):
    imu,u,g,a=data(path)
    times=np.unique(np.r_[imu[:,0],u[:,0]])
    X0=np.zeros((6,1));X0[:3,0]=[1.25,0,.07];q0=Quaternion([1,0,0,0]);P0=np.eye(9)*.01
    if base:ekf=ESKF(X0,q0,P0,len(times))
    else:ekf=LearnedESKF(X0,q0,P0,len(times),net=net,robust=robust)
    ui={float(t):i for i,t in enumerate(u[:,0])};ii={float(t):i for i,t in enumerate(imu[:,0])}
    start=time.perf_counter()
    for k in range(1,len(times)):
        old=float(times[k-1]);idx=ii.get(old)
        ekf.predict(imu[idx if idx is not None else 0,1:],float(times[k]-old),idx is not None,k)
        if old in ui:ekf.UWB_correct(u[ui[old],1:],a,k)
    wall=time.perf_counter()-start
    # Evaluate at a common 10 Hz grid, excluding the same initial five seconds.
    t=np.arange(max(times[0]+5,g[0,0]),min(times[-1],g[-1,0]),.1)
    pos=np.column_stack([np.interp(t,times,ekf.Xpo[:,j]) for j in range(3)])
    ref=np.column_stack([np.interp(t,g[:,0],g[:,j]) for j in [1,2,3]])
    return t,pos,ref,wall,ekf

def check():
    a=np.array([[0.,0.,0.],[3.,2.,1.]])
    p=np.array([1.,.8,.6]);r=Rotation.from_rotvec([.1,-.2,.3]).as_matrix();q=Quaternion(matrix=r)
    ekf=ESKF(np.zeros((6,1)),Quaternion(),np.eye(9),2)
    G=ekf.computeG_grad(a[0],a[1],ARM[:,None],p,[q.w,q.x,q.y,q.z]).ravel()
    def h(x):
        v=x+r@ARM;return np.linalg.norm(v-a[1])-np.linalg.norm(v-a[0])
    numeric=np.array([(h(p+np.eye(3)[j]*1e-5)-h(p-np.eye(3)[j]*1e-5))/2e-5 for j in range(3)])
    assert np.max(abs(G[:3]-numeric))<1e-7
    path=records('const1')[0]
    t,p,ref,_,_=run(path,None,False)
    t2,p2,_,_,_=run(path,None,False,base=True)
    gap=float(np.max(abs(p-p2)));assert gap<1e-7,gap
    save_json(DEST/'backend_check.json',{'position_jacobian_max_abs_error':float(np.max(abs(G[:3]-numeric))),'upstream_baseline_max_position_difference_m':gap})

def main():
    if not (DEST/'backend_check.json').exists():check()
    x,y,counts=examples(P['train']);vx,vy,vc=examples(P['validation'])
    save_json(DEST/'training_samples.json',{'train':counts,'validation':vc})
    mean=x.mean(0);std=np.maximum(x.std(0),1e-6)
    tx=torch.tensor(x,dtype=torch.float32);ty=torch.tensor(y,dtype=torch.float32);vx=torch.tensor(vx,dtype=torch.float32);vy=torch.tensor(vy,dtype=torch.float32)
    for seed in PROTOCOL['seeds']:
        path=MODELS/'UWB'/f'seed_{seed}'/'best.pt';path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():continue
        seed_all(seed);net=BiasNet(mean,std);opt=torch.optim.Adam(net.parameters(),lr=P['learning_rate']);best=float('inf');wait=0;hist=[]
        for epoch in range(P['epochs']):
            net.train();losses=[]
            for ids in torch.randperm(len(tx)).split(P['batch_size']):
                pred=net(tx[ids]);loss=torch.nn.functional.huber_loss(pred,ty[ids],delta=.3)
                opt.zero_grad();loss.backward();opt.step();losses.append(loss.item())
            net.eval()
            with torch.no_grad():val=float(torch.mean((net(vx)-vy)**2))
            hist.append(dict(epoch=epoch+1,train_huber_loss=float(np.mean(losses)),validation_bias_rmse_m=float(np.sqrt(val))))
            if val<best:
                best=val;wait=0;torch.save(net.state_dict(),path);save_json(path.with_suffix('.json'),dict(best_epoch=epoch+1,validation_bias_rmse_m=float(np.sqrt(val))))
            else:wait+=1
            if epoch%10==0:print('UWB',seed,epoch+1,'validation bias RMSE',np.sqrt(val),flush=True)
            if wait>=P['patience']:break
        save_csv(DEST/f'training_{seed}.csv',hist)
    rows=[]
    for const in P['test']:
        for recording in records(const):
            for method in P['methods']:
                for seed in (PROTOCOL['seeds'] if method.startswith('NN') else [0]):
                    net=None
                    if method.startswith('NN'):
                        net=BiasNet(mean,std);net.load_state_dict(torch.load(MODELS/'UWB'/f'seed_{seed}'/'best.pt',weights_only=True));net.eval()
                    t,p,g,wall,e=run(recording,net,'Huber' in method)
                    row=dict(sequence=recording.stem,method=method,seed=seed,**metrics(p,g,t),wall_s=wall,updates=e.attempts,accepted_updates=e.accepted)
                    rows.append(row);np.savez_compressed(DEST/f'{recording.stem}_{method}_{seed}.npz',time=t,position=p,reference=g)
                    print('TEST',recording.stem,method,seed,row['rmse_3d_m'],flush=True)
    save_csv(DEST/'metrics.csv',rows);save_json(DEST/'status.json',{'status':'complete','methods':P['methods'],'seeds':PROTOCOL['seeds']})

if __name__=='__main__':main()
