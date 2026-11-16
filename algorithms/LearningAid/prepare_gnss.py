"""Cache only GNSS features and solver terms; raw reference never enters features."""
import json
from pathlib import Path
import numpy as np
import pymap3d as pm
import tasgnss as tas

from common import ROOT
OUT=ROOT/'datasets/UrbanNav/learning_processed'
OUT.mkdir(parents=True,exist_ok=True)

def load_span(path):
    with path.open() as f:
        rows=[np.fromstring(l,sep=' ') for l in f if l.strip()[:4] in ('1621','1623')]
    a=np.vstack(rows)
    assert a.shape[1]==20 and np.all(np.diff(a[:,0])>0)
    lat=a[:,3]+a[:,4]/60+a[:,5]/3600
    lon=a[:,6]+a[:,7]/60+a[:,8]/3600
    pos=np.array(pm.geodetic2ecef(lat,lon,a[:,9])).T
    roll,pitch,yaw=np.deg2rad(a[:,16:19]).T
    yaw=-yaw
    cp,sp,ct,st,cy,sy=np.cos(roll),np.sin(roll),np.cos(pitch),np.sin(pitch),np.cos(yaw),np.sin(yaw)
    rot=np.stack([cy*cp-sy*st*sp,-sy*ct,cy*sp+sy*st*cp,sy*cp+cy*st*sp,cy*ct,sy*sp-cy*st*cp,-ct*sp,st,ct*cp],axis=1).reshape(-1,3,3)
    # ANTENNA_T_IMU gives the IMU origin in antenna coordinates; include body_T_SPAN.
    arm=np.einsum('nij,j->ni',rot,np.array([0.,-.86,.45]))
    phi,lam=np.deg2rad(lat),np.deg2rad(lon)
    E=np.stack([-np.sin(lam),np.cos(lam),np.zeros_like(lam),-np.sin(phi)*np.cos(lam),-np.sin(phi)*np.sin(lam),np.cos(phi),np.cos(phi)*np.cos(lam),np.cos(phi)*np.sin(lam),np.sin(phi)],axis=1).reshape(-1,3,3)
    pos+=np.einsum('nji,nj->ni',E,arm)
    return a[:,0],pos,a[:,19]

def prepare(name,obsfile,navfile,truth,start,end):
    dest=OUT/(name+'.npz')
    if dest.exists(): print('Reusing',dest,flush=True);return
    gt_t,gt_p,gt_q=truth
    obs,nav,_=tas.read_obs(str(obsfile),str(navfile))
    epochs=tas.filter_obs(tas.split_obs(obs),start,end)
    records=[]; failures=[]
    for i,o in enumerate(epochs):
        t=tas.obs2utc(o.data[0].time)
        if not gt_t[0]<=t<=gt_t[-1]:continue
        ret=tas.wls_pnt_pos(o,nav,w=1,return_residual=True)
        if not ret['status']:
            failures.append([float(t),ret.get('msg','failed')]);continue
        d=ret['data']; c=ret['solve_data']; n=len(d)
        if not set(d[:,2]).issubset(set('GRE CJ'.replace(' ',''))):
            failures.append([float(t),'unsupported constellation']);continue
        feat=np.column_stack([d[:,9].astype(float),d[:,12].astype(float),d[:,11].astype(float),ret['residual_info']['residual'].ravel(),np.eye(5)[[['G','R','E','C','J'].index(s) for s in d[:,2]]]])
        target=np.array([np.interp(t,gt_t,gt_p[:,j]) for j in range(3)])
        clocks=np.eye(7)[[list(tas.SYS_NAME).index(s) for s in c['sys']]]
        records.append(dict(time=t,feat=feat,pos=ret['pos'],cb=ret['cb'],sat=c['satpos'][:,:3],res=ret['residual_info']['residual'].ravel(),clock=clocks,gt=target,quality=gt_q[np.argmin(abs(gt_t-t))]))
        tas.cache_data.clear()
        if i%200==0:print(name,i,len(epochs),flush=True)
    assert records
    m=max(len(a['feat']) for a in records);N=len(records)
    result={k:np.zeros((N,m,z)) for k,z in [('feat',9),('sat',3),('clock',7)]}
    result.update({k:np.zeros((N,m)) for k in ['res','mask']})
    for k in ['time','pos','cb','gt','quality']:result[k]=np.array([a[k] for a in records])
    for i,a in enumerate(records):
        n=len(a['feat']); result['mask'][i,:n]=1
        for k in ['feat','sat','clock','res']:result[k][i,:n]=a[k]
    assert all(np.isfinite(v).all() for v in result.values())
    np.savez_compressed(dest,**result)
    dest.with_suffix('.json').write_text(json.dumps({'candidate_epochs':len(epochs),'cached_epochs':N,'failures':failures,'reference_quality_counts':dict(zip(*[x.tolist() for x in np.unique(result['quality'],return_counts=True)]))},indent=2))
    print('Saved',name,N,'of',len(epochs),flush=True)

if __name__=='__main__':
    k=ROOT/'datasets/KLT/0610_KLT'
    truth=load_span(k/'20210610_100.txt')
    for name,a,b in [('0610_KLT1_203',1623296137,1623296340),('0610_KLT2_209',1623296900,1623297109),('0610_KLT3_404',1623297134,1623297538)]:
        prepare(name,k/'COM38_210610_025603.obs',k/'sta/hksc161d.21*',truth,a,b)
    d=ROOT/'datasets/UrbanNav/Deep-Urban-1'
    prepare('UrbanNav-Deep-Urban-1',d/'gnss/20210521.medium-urban.whampoa.ublox.f9p.obs',d/'gnss/hksc141g.nav',load_span(d/'ground_truth/UrbanNav_whampoa_raw.txt'),1621578528,1621580061)
