"""Shared English metrics and single-axis publication plots."""
from pathlib import Path
import csv,hashlib,json,os,random,time
import numpy as np
try:
    import torch
except ModuleNotFoundError as exc:
    if exc.name != 'torch':
        raise
    torch = None
PROJECT=Path(__file__).resolve().parent
REPO=PROJECT.parents[1]
ROOT=Path(os.environ.get('CH3_ROOT',str(REPO.parent/'data/LearningAid')))
UPSTREAM=Path(os.environ.get('CH3_UPSTREAM',str(REPO.parent/'external/LearningAid')))
PROTOCOL=json.loads((REPO/'configs/LearningAid/protocol.json').read_text(encoding='utf-8'))
OUT=Path(os.environ.get('CH3_RESULTS',str(REPO/'results/LearningAid'/PROTOCOL['run_id'])))
MODELS=Path(os.environ.get('CH3_MODELS',str(REPO.parent/'models/Chapter3_3.5'/PROTOCOL['run_id'])))
if torch is not None:
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)

def seed_all(seed):
    if torch is None:
        raise RuntimeError('Training requires the recorded CPU PyTorch environment.')
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)

def save_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False))

def save_csv(path,rows):
    assert rows
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def relative_error_vectors(p,gt,t):
    e=p-gt
    goal=t+10;right=np.minimum(np.searchsorted(t,goal),len(t)-1);left=np.maximum(right-1,0)
    j=np.where(abs(t[left]-goal)<abs(t[right]-goal),left,right);i=np.arange(len(t))
    ok=abs(t[j]-t[i]-10)<.05;i,j=i[ok],j[ok]
    return e[j]-e[i]

def metrics(p,gt,t):
    assert p.shape==gt.shape and p.ndim==2 and p.shape[1]==3
    assert np.isfinite(p).all() and np.isfinite(gt).all() and np.all(np.diff(t)>0)
    e=p-gt;r=np.linalg.norm(e,axis=1)
    relative=relative_error_vectors(p,gt,t)
    return dict(samples=len(t),duration_s=float(t[-1]-t[0]),rmse_3d_m=float(np.sqrt(np.mean(r*r))),rmse_horizontal_m=float(np.sqrt(np.mean(np.sum(e[:,:2]**2,axis=1)))),mae_3d_m=float(r.mean()),p95_3d_m=float(np.percentile(r,95)),max_3d_m=float(r.max()),rpe_10s_m=float(np.sqrt(np.mean(np.sum(relative**2,axis=1)))) if len(relative) else 0.,final_drift_m=float(r[-1]))

def plot_setup():
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import font_manager
    default_fonts=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts' if os.name=='nt' else Path('/nonexistent')
    font_dir=Path(os.environ.get('CH3_FONT_DIR',str(default_fonts)))
    for font in font_dir.glob('times*.ttf'):font_manager.fontManager.addfont(str(font))
    path=font_manager.findfont('Times New Roman',fallback_to_default=False)
    assert Path(path).name.lower()=='times.ttf'
    matplotlib.rcParams.update({'font.family':'Times New Roman','font.size':10,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9,'legend.fontsize':9,'lines.linewidth':1.4,'pdf.fonttype':42,'ps.fonttype':42,'axes.unicode_minus':False,'savefig.dpi':400})
    import matplotlib.pyplot as plt
    return plt

def save_figure(fig,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    assert len(fig.axes)==1
    fig.tight_layout(pad=.5)
    for suffix in ['png','pdf']:fig.savefig(path.with_suffix('.'+suffix),bbox_inches='tight',pad_inches=.04)
    import matplotlib.pyplot as plt
    plt.close(fig)

if __name__=='__main__':
    t=np.arange(31.);g=np.zeros((31,3));p=np.ones((31,3))
    m=metrics(p,g,t)
    assert abs(m['rmse_3d_m']-np.sqrt(3))<1e-12 and m['rpe_10s_m']==0
    assert abs(metrics(g,g,t)['rmse_3d_m'])<1e-12
    fine=np.arange(0,31,.1);drift=np.column_stack([fine,np.zeros((len(fine),2))])
    assert abs(metrics(drift,np.zeros_like(drift),fine)['rpe_10s_m']-10)<1e-12
    plot_setup()
    print('Metric identity and Times New Roman checks passed.')
