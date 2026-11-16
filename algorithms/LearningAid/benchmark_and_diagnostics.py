"""Fair single-epoch GNSS timing and a transparent fixed-position IO sanity control."""
import time
import numpy as np
import torch
import tasgnss as tas
from common import ROOT,PROJECT,OUT,MODELS,PROTOCOL,save_json,save_csv,metrics
from run_gnss import Net,forward

def epoch_data(ret):
    d=ret['data'];c=ret['solve_data'];n=len(d)
    feat=np.column_stack([d[:,9].astype(float),d[:,12].astype(float),d[:,11].astype(float),ret['residual_info']['residual'].ravel(),np.eye(5)[[['G','R','E','C','J'].index(s) for s in d[:,2]]]])
    raw=dict(feat=feat[None],pos=ret['pos'][None],cb=ret['cb'][None],sat=c['satpos'][None,:,:3],res=ret['residual_info']['residual'].ravel()[None],clock=np.eye(7)[[list(tas.SYS_NAME).index(s) for s in c['sys']]][None],mask=np.ones((1,n)))
    return {k:torch.tensor(v,dtype=torch.float64) for k,v in raw.items()}

def gnss_timing():
    r=ROOT/'datasets/UrbanNav/Deep-Urban-1/gnss'
    obs,nav,_=tas.read_obs(str(r/'20210521.medium-urban.whampoa.ublox.f9p.obs'),str(r/'hksc141g.nav'))
    epochs=tas.filter_obs(tas.split_obs(obs),1621578528,1621580061)
    sample=[epochs[i] for i in np.linspace(0,len(epochs)-1,40).astype(int)]
    cached=dict(np.load(ROOT/'datasets/UrbanNav/learning_processed/UrbanNav-Deep-Urban-1.npz'))
    rows=[];checks=[]
    for method in PROTOCOL['gnss']['methods']:
        for seed in ([0] if method=='WLS' else PROTOCOL['seeds']):
            net=None
            if method!='WLS':
                net=Net(torch.zeros(9),torch.ones(9)).double();net.load_state_dict(torch.load(MODELS/'GNSS'/method/f'seed_{seed}'/'best.pt',weights_only=True));net.eval()
            latencies=[]
            for trial,o in enumerate(sample):
                tas.cache_data.clear();start=time.perf_counter()
                ret=tas.wls_pnt_pos(o,nav,w=1,return_residual=True)
                if not ret['status']:continue
                if method=='WLS':pred=ret['pos']
                else:
                    data=epoch_data(ret)
                    with torch.no_grad():pred=forward(net,data,method)[0].numpy()
                elapsed=(time.perf_counter()-start)*1000
                if trial>1:latencies.append(elapsed)
                timestamp=tas.obs2utc(o.data[0].time);idx=np.argmin(abs(cached['time']-timestamp))
                stored=np.load(OUT/'GNSS'/f'UrbanNav-Deep-Urban-1_{method}_{seed}.npz')
                # Comparing ENU errors is invariant to the common ECEF-to-ENU rotation.
                referr=np.linalg.norm(pred-cached['gt'][idx]);savederr=np.linalg.norm(stored['position'][idx]-stored['reference'][idx])
                checks.append(abs(referr-savederr));assert abs(referr-savederr)<.01
            rows.append(dict(method=method,seed=seed,epochs_timed=len(latencies),mean_latency_ms=float(np.mean(latencies)),p95_latency_ms=float(np.percentile(latencies,95))))
    save_csv(OUT/'GNSS/latency.csv',rows)
    save_json(OUT/'GNSS/latency_protocol.json',{'scope':'Single epoch, RINEX decoded in memory; uncached satellite/atmosphere preprocessing, initial WLS, feature construction, learned inference and correction solver; excludes disk input, network loading and plotting','warmup_epochs':2,'sample_policy':'40 uniformly spaced candidate test epochs, no reference-error screening','maximum_error_norm_difference_from_saved_result_m':float(max(checks))})

def fixed_control():
    path=OUT/'IO/metrics.csv'
    import csv
    with path.open() as f:rows=list(csv.DictReader(f))
    if any(r['method']=='Fixed position' for r in rows):return
    for seq in PROTOCOL['io']['test']:
        ref=np.load(ROOT/'datasets/EuRoC/processed_learning'/seq/'reference.npz')
        target=OUT/'IO'/f'{seq}_IMU_0.npz';d=np.load(target)
        pred=np.tile(ref['position'][0],(len(d['time']),1))
        row=dict(sequence=seq,method='Fixed position',seed=0,**metrics(pred,d['reference'],d['time']),wall_s=0.,updates=0,accepted_updates=0)
        rows.append(row);np.savez_compressed(OUT/'IO'/f'{seq}_Fixed position_0.npz',time=d['time'],position=pred,reference=d['reference'])
    save_csv(path,rows)
    save_json(OUT/'IO/fixed_position_diagnostic.json',{'purpose':'Checks whether suppressing motion alone explains an apparent benefit over drifting IMU integration','timing':'Added after the frozen main training protocol; no network or hyperparameter changed in response','state':'Keep the shared initial reference position constant for the complete sequence','not_used_for':'Training, validation checkpoint selection or parameter tuning'})

if __name__=='__main__':
    for group in ['GNSS','UWB','IO']:assert __import__('json').loads((OUT/group/'status.json').read_text())['status']=='complete'
    gnss_timing();fixed_control();print('Single-epoch timing parity and fixed-position sanity control completed.')
