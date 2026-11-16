"""EuRoC IMU-only adapter, preserving nanosecond timestamps and separate references."""
from pathlib import Path
import hashlib,json,zipfile
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation,Slerp
from common import ROOT,PROTOCOL,save_json

D=ROOT/'datasets/EuRoC';P=PROTOCOL['io'];OUT=D/'processed_learning'
OUT.mkdir(parents=True,exist_ok=True)
splits=[P[s] for s in ['train','validation','test']]
assert not set(splits[0])&set(splits[1]) and not set(splits[0])&set(splits[2]) and not set(splits[1])&set(splits[2])
corrected_path=D/'V1_01_easy/mav0/state_groundtruth_estimate0/data_openvins.csv'
if not corrected_path.exists():
    with zipfile.ZipFile(ROOT/'tmp/Chapter3_3.5/V101-reference.zip') as z:
        corrected_path.write_bytes(z.read('V101-state_groundtruth_estimate0/data.csv'))

counts={}
for seq in sum(splits,[]):
    base=D/seq/'mav0';refpath=base/'state_groundtruth_estimate0'/('data_openvins.csv' if seq=='V1_01_easy' else 'data.csv')
    imu=pd.read_csv(base/'imu0/data.csv');ref=pd.read_csv(refpath)
    ti=imu.iloc[:,0].to_numpy(dtype=np.int64);tg=ref.iloc[:,0].to_numpy(dtype=np.int64)
    assert np.all(np.diff(ti)>0) and np.all(np.diff(tg)>0)
    start=max(ti[0],tg[0]);end=min(ti[-1],tg[-1]);ok=(ti>=start)&(ti<=end)
    ti=ti[ok];samples=imu.iloc[:,1:7].to_numpy(dtype=np.float64)[ok];a=ref.iloc[:,1:].to_numpy(dtype=np.float64)
    t=(ti-ti[0])*1e-9;gt=(tg-ti[0])*1e-9
    r=Slerp(gt,Rotation.from_quat(a[:,[4,5,6,3]]))(t)
    def lerp(cols):return np.column_stack([np.interp(t,gt,a[:,c]) for c in cols])
    p=lerp([0,1,2]);v=lerp([7,8,9]);bg=lerp([10,11,12]);ba=lerp([13,14,15])
    dest=OUT/seq;dest.mkdir(exist_ok=True)
    np.savez_compressed(dest/'inputs.npz',timestamp_ns=ti,time=t,gyro=samples[:,:3].astype(np.float32),acc=samples[:,3:].astype(np.float32))
    np.savez_compressed(dest/'reference.npz',time=t,position=p,velocity=v,quaternion=r.as_quat(),gyro_bias=bg,acc_bias=ba)
    counts[seq]={'imu_samples':len(t),'duration_s':float(t[-1]),'reference_sha256':hashlib.sha256(refpath.read_bytes()).hexdigest(),'reference_path':str(refpath)}
    assert np.isfinite(samples).all() and np.max(abs(np.diff(t)-.005))<.001
save_json(OUT/'manifest.json',{'sequences':counts,'source':'https://github.com/Air-IO/Air-IO/releases/tag/datasets','timestamps':'int64 nanoseconds; relative float64 seconds','reference_feedback':'Initialization only during test inference'})
print('Prepared',len(counts),'complete EuRoC sequences',flush=True)
