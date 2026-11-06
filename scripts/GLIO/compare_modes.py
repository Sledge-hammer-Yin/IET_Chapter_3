"""Evaluate the three frozen GLIO configurations on exactly the same epochs."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager
import matplotlib.pyplot as plt

ROOT=Path('/data/users/taslab_zxp')
OUT=ROOT/'outputs/GLIO/Deep-Urban-1/Comparison_calibrated_v2'
PROTOCOL=json.loads((OUT/'protocol.json').read_text())
RUNS=json.loads((OUT/'runs.json').read_text())
MODES=PROTOCOL['modes']
LABELS={'LC':'LC','TC_Pose':'TC-Pose','TC_Surface':'TC-Surface'}
COLORS={'LC':'#D55E00','TC_Pose':'#0072B2','TC_Surface':'#009E73'}
STYLES={'LC':'-','TC_Pose':'-.','TC_Surface':'-'}

def write_csv(name,rows,fields=None):
    with (OUT/name).open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields or list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k:round(v,6) if isinstance(v,float) else v for k,v in row.items()})

def ecef(lat,lon,height):
    lat,lon=np.deg2rad(lat),np.deg2rad(lon)
    n=6378137.0/np.sqrt(1-6.6943799901413165e-3*np.sin(lat)**2)
    return np.column_stack(((n+height)*np.cos(lat)*np.cos(lon),(n+height)*np.cos(lat)*np.sin(lon),(n*(1-6.6943799901413165e-3)+height)*np.sin(lat)))

def frame(origin):
    x,y,z=origin; lon=np.arctan2(y,x); radial=np.hypot(x,y)
    lat=np.arctan2(z,radial*(1-6.6943799901413165e-3))
    for _ in range(12):
        n=6378137.0/np.sqrt(1-6.6943799901413165e-3*np.sin(lat)**2)
        lat=np.arctan2(z+6.6943799901413165e-3*n*np.sin(lat),radial)
    return np.array([[-np.sin(lon),np.cos(lon),0],[-np.sin(lat)*np.cos(lon),-np.sin(lat)*np.sin(lon),np.cos(lat)],[np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)]])

def span_position(raw):
    # Native attitude columns are yaw, pitch, roll in degrees; R = Rz Ry Rx.
    yaw,pitch,roll=np.deg2rad(raw[:,6:9]).T
    z_axis=np.column_stack((np.cos(yaw)*np.sin(pitch)*np.cos(roll)+np.sin(yaw)*np.sin(roll),
        np.sin(yaw)*np.sin(pitch)*np.cos(roll)-np.cos(yaw)*np.sin(roll),np.cos(pitch)*np.cos(roll)))
    return raw[:,9:12]+0.14*z_axis

def interpolate_native(t,p,epochs,maximum_gap):
    right=np.searchsorted(t,epochs)
    nearest=np.minimum(right,len(t)-1)
    exact=np.abs(t[nearest]-epochs)<=1e-6
    inside=(right>0)&(right<len(t))
    bracket=np.clip(right,1,len(t)-1)
    ok=exact|(inside&((t[bracket]-t[bracket-1])<=maximum_gap))
    values=np.column_stack([np.interp(epochs,t,p[:,axis]) for axis in range(3)])
    return values,ok

def statistics(error,times):
    e3=np.linalg.norm(error,axis=1)
    lookup={int(round(t)):i for i,t in enumerate(times)}
    pairs=[(i,lookup[int(round(t))+10]) for i,t in enumerate(times) if int(round(t))+10 in lookup]
    rpe=np.array([np.linalg.norm(error[j]-error[i]) for i,j in pairs])
    return {'epochs':len(e3),'horizontal_rmse_m':float(np.sqrt(np.mean(np.sum(error[:,:2]**2,axis=1)))),
        'vertical_rmse_m':float(np.sqrt(np.mean(error[:,2]**2))),'position_3d_rmse_m':float(np.sqrt(np.mean(e3**2))),
        'position_3d_mae_m':float(np.mean(e3)),'position_3d_p95_m':float(np.percentile(e3,95)),
        'position_3d_max_m':float(np.max(e3)),'relative_displacement_10s_rmse_m':float(np.sqrt(np.mean(rpe**2))) if len(rpe) else None,
        'relative_displacement_10s_pairs':len(rpe)}

reference=np.loadtxt(PROTOCOL['assets']['UrbanNav_whampoa_raw.txt']['path'],skiprows=2)
initial=PROTOCOL['shared_config']['initialization']
origin=np.array([initial['anc_ecef_'+axis] for axis in 'xyz'])
lat=reference[:,3]+reference[:,4]/60+reference[:,5]/3600
lon=reference[:,6]+reference[:,7]/60+reference[:,8]/3600
reference_position=(ecef(lat,lon,reference[:,9])-origin)@frame(origin).T
policy=PROTOCOL['evaluation']
eligible=(reference[:,0]>=policy['start_utc'])&(reference[:,0]<=policy['end_utc'])
times=reference[eligible,0]
truth=reference_position[eligible]
quality=reference[eligible,19].astype(int)
estimates={}; valid={}; native={}; coverage=[]; frontend_hashes={}
for mode in MODES:
    folder=Path(RUNS[mode]['path'])
    completion=json.loads((folder/'backend_drain.json').read_text())
    assert completion['status']=='complete'
    position_rows='\n'.join(line.strip() for line in (folder/'rtklibResult.pos').read_text().splitlines() if line.strip() and not line.lstrip().startswith('%'))
    frontend_hashes[mode]=hashlib.sha256(position_rows.encode()).hexdigest()
    raw=np.loadtxt(folder/('lc_result.csv' if mode=='LC' else 'tc_batch_result.csv'),delimiter=',',ndmin=2)
    assert raw.shape[1]==12 and np.isfinite(raw).all()
    raw=raw[np.argsort(raw[:,0],kind='stable')]
    _,last=np.unique(raw[::-1,0],return_index=True)
    raw=raw[np.sort(len(raw)-1-last)]
    t=raw[:,0]; p=span_position(raw)
    estimates[mode],ok=interpolate_native(t,p,times,policy['max_interpolation_bracket_s'])
    valid[mode]=ok; native[mode]=raw
    factors=folder/'lc_gnss_factors.csv'
    count=sum(1 for line in factors.open()) if factors.exists() else 0
    if mode=='LC': assert count>0
    coverage.append({'method':LABELS[mode],'native_rows':len(raw),'native_start_utc':float(t[0]),'native_end_utc':float(t[-1]),
        'eligible_reference_epochs':len(times),'valid_reference_epochs':int(ok.sum()),'coverage_pct':float(ok.mean()*100),
        'accepted_lc_gnss_factors':count if mode=='LC' else 'not applicable'})
assert len(set(frontend_hashes.values()))==1,'The GNSS frontend position results differ across modes'
common=np.logical_and.reduce([valid[m] for m in MODES])
assert common.sum()>10
t=times[common]; truth=truth[common]; q=quality[common]
metrics=[]; groups=[]; resources=[]; errors={}
for mode in MODES:
    errors[mode]=estimates[mode][common]-truth
    metrics.append({'method':LABELS[mode],**statistics(errors[mode],t)})
    for code in np.unique(q):
        mask=q==code
        groups.append({'method':LABELS[mode],'reference_quality_code':int(code),**statistics(errors[mode][mask],t[mask])})
    folder=Path(RUNS[mode]['path'])
    measured=json.loads((folder/'resources.json').read_text())
    resources.append({'method':LABELS[mode],'end_to_end_wall_s':RUNS[mode]['end_to_end_wall_s'],
        'backend_wait_s':json.loads((folder/'backend_drain.json').read_text())['wait_seconds'],
        'sampled_peak_combined_native_rss_mib':measured['sampled_peak_combined_native_rss_mib'],
        'sampled_native_cpu_s':measured['sampled_native_cpu_s']})
write_csv('comparison_metrics.csv',metrics)
write_csv('reference_quality_metrics.csv',groups)
write_csv('output_coverage.csv',coverage)
write_csv('resource_summary.csv',resources)
write_csv('evaluation_epochs.csv',[{'utc_s':int(rt),'reference_quality_code':int(code)} for rt,code in zip(t,q)])
result={'profile':'calibrated_v2','eligible_reference_epochs':len(times),'common_reference_epochs':int(common.sum()),
    'common_coverage_pct':float(common.mean()*100),'common_utc_start':float(t[0]),'common_utc_end':float(t[-1]),
    'reference_quality_counts':{str(int(code)):int((q==code).sum()) for code in np.unique(q)},
    'metrics':metrics,'coverage':coverage,'resources':resources,'reference_quality_metrics':groups,
    'evaluation_point':'SPAN-CPT; transfer uses each method estimated attitude and [0,0,0.14] m, never reference attitude',
    'alignment':'No fitted rotation, translation, scale, or time shift',
    'trial_count_per_mode':1,'reference_quality_codes_interpreted_as_accuracy_bounds':False}
result['gnss_frontend_position_sha256']=frontend_hashes
(OUT/'comparison_results.json').write_text(json.dumps(result,indent=2)+'\n')

for font in (ROOT/'projects/GLIO_setup/fonts').glob('times*.ttf'): font_manager.fontManager.addfont(str(font))
plt.rcParams.update({'font.family':'Times New Roman','font.size':10,'axes.labelsize':11,'legend.fontsize':9,'pdf.fonttype':42,'ps.fonttype':42})
def export(fig,name):
    for extension in ['png','pdf']: fig.savefig(OUT/(name+'.'+extension),dpi=300,bbox_inches='tight',pad_inches=0.05)
    plt.close(fig)
fig,ax=plt.subplots(figsize=(5.0,4.3),layout='constrained')
ax.plot(truth[:,0],truth[:,1],'--',color='0.1',lw=1.2,label='Reference',zorder=5)
for mode in MODES:
    values=estimates[mode][common]
    ax.plot(values[:,0],values[:,1],color=COLORS[mode],ls=STYLES[mode],lw=1.0,label=LABELS[mode])
ax.set(xlabel='East (m)',ylabel='North (m)'); ax.set_aspect('equal',adjustable='box')
ax.grid(alpha=0.2,lw=0.5); ax.legend(frameon=False,loc='upper right')
export(fig,'comparison_trajectory')
fig,ax=plt.subplots(figsize=(5.4,3.3),layout='constrained')
for mode in MODES:
    ax.plot(t-t[0],np.linalg.norm(errors[mode],axis=1),color=COLORS[mode],ls=STYLES[mode],lw=1.0,label=LABELS[mode])
ax.set(xlabel='Elapsed time (s)',ylabel='3D position error (m)')
ax.grid(alpha=0.2,lw=0.5); ax.legend(frameon=False)
export(fig,'comparison_position_error')

table='\n'.join('| {method} | {epochs} | {horizontal_rmse_m:.3f} | {vertical_rmse_m:.3f} | {position_3d_rmse_m:.3f} | {position_3d_p95_m:.3f} | {position_3d_max_m:.3f} | {relative_displacement_10s_rmse_m:.3f} |'.format(**row) for row in metrics)
quality_table='\n'.join('| {method} | {reference_quality_code} | {epochs} | {horizontal_rmse_m:.3f} | {position_3d_rmse_m:.3f} |'.format(**row) for row in groups)
coverage_table='\n'.join('| {method} | {valid_reference_epochs} | {coverage_pct:.2f} | {accepted_lc_gnss_factors} |'.format(**row) for row in coverage)
resource_table='\n'.join('| {method} | {end_to_end_wall_s:.1f} | {backend_wait_s:.1f} | {sampled_peak_combined_native_rss_mib:.1f} | {sampled_native_cpu_s:.1f} |'.format(**row) for row in resources)
rank=sorted(metrics,key=lambda row:row['position_3d_rmse_m'])
best_h=min(metrics,key=lambda row:row['horizontal_rmse_m'])
acceptable=result['common_coverage_pct']>=95
verdict=('Suitable for a clearly qualified textbook case study of these three GLIO-based configurations.' if acceptable else 'The common output coverage is insufficient for recommendation as a complete textbook case; report missing coverage first.')
chapter_text=('Three GLIO-based fusion configurations were evaluated on the Deep-Urban-1 ground-vehicle sequence of UrbanNav [12,23]. '
    'They used the same GNSS, LiDAR and IMU data, sensor extrinsics, supplied initialization prior, and feature-sampling seed. '
    'The public implementation was adjusted to activate the GNSS input of the LC branch and apply the published antenna lever arm. '
    'The shared front end used LiDAR/IMU, and the TC batch graph used double-difference pseudorange; Doppler factors were not enabled. '
    'The TC antenna offset was frozen at an adjacent estimated attitude during factor assembly. '
    'Position errors were evaluated at the SPAN-CPT reference point over '+str(int(common.sum()))+' common reference epochs, without fitted trajectory alignment. '
    'The horizontal RMSE values were '+', '.join('{:.2f}'.format(row['horizontal_rmse_m']) for row in metrics)+' m for LC, TC-Pose and TC-Surface, respectively; the corresponding three-dimensional values were '+', '.join('{:.2f}'.format(row['position_3d_rmse_m']) for row in metrics)+' m. '
    'These results illustrate the behavior of the three configurations under this shared setup. A single sequence and a supplied initial prior do not establish general superiority or UAV flight performance.')
report=f'''# GLIO fusion strategies on Deep-Urban-1

## Outcome

All three configurations completed the full prepared sequence under one frozen protocol.
{verdict} This is a calibrated, controlled implementation case, not an exact
reproduction of the numerical results in the GLIO paper or a UAV flight test.

On these common epochs, {rank[0]['method']} had the lowest 3D RMSE
({rank[0]['position_3d_rmse_m']:.3f} m); {best_h['method']} had the lowest horizontal RMSE
({best_h['horizontal_rmse_m']:.3f} m). This describes one run per mode and supports
no statistical-significance or universal-superiority claim.

## Controlled conditions and necessary corrections

- Same verified compact bag: 614,782 original 400 Hz IMU messages and 15,355 center-LiDAR scans.
  One startup LiDAR scan preceding the first IMU was removed once for every mode. Original data are retained.
- Identical rover/base RINEX and ephemeris, DGNSS frontend (L1, forward), 1.0 replay rate,
  fixed feature-sampling seed 42, four logical CPUs, nice 10, and 24 GiB virtual-memory limit per process.
- Identical IMU/LiDAR extrinsics: identity rotation and [0, 0, 0.28] m translation.
  The published antenna translation [0, 0.86, -0.31] m is applied in the LC PVT correction
  and TC DD-pseudorange factor. The antenna translation is manually measured, with reported uncertainty about 0.1 m.
- Identical author-supplied anchor and roll/pitch/yaw prior: ECEF
  [-2419233.42, 5385473.13, 2405341.30] m and [0.6825, 0.098, 60.8] degrees.
  Its original derivation is unverified. No reference measurements enter online updates.
  Initial velocity and both IMU bias vectors are zero in the shared implementation.
- Author GLIO IMU-noise model values are held identical. They differ from the dataset's
  separate published Allan-calibration numbers and are declared shared model settings,
  not claimed to be newly identified sensor calibration.
- `RTKinLocal=true` is necessary: the upstream flag also gates the actual LC GNSS queue.
  Merely enabling `LCinLocal` with `RTKinLocal=false` does not supply LC GPS factors.
- The active DD factor originally hard-coded zero lever arm. The retained source patch
  adds the estimated-attitude antenna offset to the position-only residual. Its position
  Jacobians passed finite-difference checks (maximum observed discrepancy 3.05e-7).
  An adjacent estimated attitude selected by the repository's interpolation branch
  is frozen while that factor is assembled; rotational lever-arm Jacobians are not
  introduced. This is an approximation, not continuous attitude interpolation.
- The shared front end is LiDAR/IMU. LC uses gated DGNSS position factors; TC modes
  use raw DD L1 pseudorange in the batch graph. The upstream sliding-window GNSS
  and Doppler blocks remain disabled. The paper's broader architecture is not
  claimed to be fully activated by this experiment.
- Source commit `332d19ff641f2ada9d9d75f2a6dab013d6015f76`, exact changes in
  `source.patch`, input/config/binary hashes in `protocol.json`.
  The previous uncorrected TC-Surface run is archived and excluded from this comparison.

## Evaluation and common-epoch statistics

Eligible interval: UTC {policy['start_utc']:.0f} to {policy['end_utc']:.0f}, after the
predeclared 20-second settling interval. The main table uses **{common.sum()} identical
1 Hz reference epochs**, UTC {t[0]:.0f} to {t[-1]:.0f}, with common coverage
{result['common_coverage_pct']:.2f}%. Interpolation is allowed only between estimated
samples no more than 1 second apart. All raw reference quality codes are retained.

Each estimated IMU pose is transferred to the SPAN-CPT point using its own estimated
attitude and the published [0, 0, 0.14] m body-to-SPAN translation. Reference attitude
is not used. Native CSV column 0 supplies Unix UTC; the LC GPS-week/seconds export
columns are not used for time alignment. There is no fitted rotation, translation,
scale or time shift.

| Method | Epochs | Horizontal RMSE (m) | Vertical RMSE (m) | 3D RMSE (m) | 3D P95 (m) | 3D maximum (m) | 10 s relative-displacement RMSE (m) |
|---|---:|---:|---:|---:|---:|---:|---:|
{table}

MAE and relative-displacement pair counts are also retained in `comparison_metrics.csv`.
The 10-second measure compares position displacements over matching epoch pairs;
it is not a full rotation-and-translation pose RPE.

| Method | Individually valid epochs | Coverage of eligible interval (%) | Accepted LC GNSS factors |
|---|---:|---:|---:|
{coverage_table}

The intersection does not replace the individual coverage table. LC retains its
published distance, covariance and uncertainty gates, so it does not use every
available GNSS position. Different observation forms and gating are part of the
three implementations; this is not an isolation of solver choice alone.

## Reference-quality groups

| Method | Raw quality code | Common epochs | Horizontal RMSE (m) | 3D RMSE (m) |
|---|---:|---:|---:|---:|
{quality_table}

These codes are reported as provided. No unverified centimetre-accuracy bound is
assigned to any code, and the reference is not assumed equally reliable everywhere.

## Resource observations

| Method | End-to-end wall time (s) | Final backend wait (s) | Sampled combined native RSS peak (MiB) | Sampled native CPU time (s) |
|---|---:|---:|---:|---:|
{resource_table}

Wall time includes initialization, paced playback, final optimization and cleanup.
It is not pure solver processing time or proof of real-time capability. Native-node
RSS and CPU usage are sampled every 5 seconds; RSS sums shared pages across nodes
and is not a unique-memory or exact OS-peak measure. Runs are sequential, CPU-only,
and use the same private container. GPU and system configuration are unchanged.

## Figures

Each file is one standalone figure with English labels, Times New Roman, 300 dpi
PNG and vector PDF. All common-epoch samples are shown without error clipping.

![Horizontal trajectories](comparison_trajectory.png)

![3D reference-relative position errors](comparison_position_error.png)

## Use in the book

Place the main metrics table and the error-comparison figure after the GLIO
implementation discussion in Section 3.4.6. The trajectory overview is optional
if space is limited. Keep detailed quality/resource tables and the patch with
the accompanying experiment files. This illustrates position-level versus raw-GNSS
fusion, IMU/LiDAR constraints and batch nonlinear optimization. It does not replace
the independent B1-B3 filtering/optimization comparison or validate every algorithm
in Section 3.4 separately.

Suggested concise paragraph (reuse the existing GLIO [12] and UrbanNav [23] citations;
verify their numbering in the final manuscript):

> {chapter_text}

Suggested trajectory caption: Horizontal trajectories of three GLIO-based fusion
configurations on UrbanNav Deep-Urban-1, evaluated at the SPAN-CPT reference point.

Suggested error caption: Three-dimensional position errors against the provided
SPAN-CPT reference at common evaluation epochs on UrbanNav Deep-Urban-1.

The case is conditional on the documented supplied prior, public extrinsics,
position-only frozen-attitude lever approximation and reference quality. Single-run
results on one ground vehicle sequence cannot establish statistical generality,
paper-result reproduction, or performance on UAV flight data. Fixed sampling does
not eliminate asynchronous scheduling variation.

## Files and reproduction

`comparison_metrics.csv`, `reference_quality_metrics.csv`, `output_coverage.csv`,
`resource_summary.csv`, `evaluation_epochs.csv`, `comparison_results.json`,
`protocol.json`, `profile_manifest.json`, `source.patch`, and the two PNG/PDF pairs.
Native outputs remain once in the folders listed by `runs.json`; the dataset is
shared and not copied per method.

Run instructions and scripts: `/data/users/taslab_zxp/projects/GLIO_setup`.
The profile is `profiles/calibrated_v2`; use the same prepared input and replay
rate for every mode. Do not mix the archived author-v1/short-test results into
this common-epoch table.

Sources: [GLIO code](https://github.com/XikunLiu-huskit/GLIO),
[UrbanNav dataset](https://github.com/IPNL-POLYU/UrbanNavDataset),
[official Deep-Urban-1 extrinsics](https://github.com/IPNL-POLYU/UrbanNavDataset/blob/master/UrbanNav-HK-Deep-Urban-1/extrinsic.yaml).
'''
(OUT/'COMPARISON_REPORT.md').write_text(report)
print(json.dumps({k:result[k] for k in ['eligible_reference_epochs','common_reference_epochs','common_coverage_pct','metrics']},indent=2))
