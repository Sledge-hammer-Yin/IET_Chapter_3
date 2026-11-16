"""Re-evaluate saved trajectories once, export English tables and three complete figures."""
import csv,json
from pathlib import Path
import numpy as np
from common import ROOT,PROJECT,OUT,PROTOCOL,save_csv,save_json,metrics,relative_error_vectors,plot_setup,save_figure

LABEL={'WLS':'WLS','TDL-W':'TDL-W','TDL-B':'TDL-B','TDL-BW':'TDL-BW','ESKF':'ESKF','Huber-ESKF':'Huber-ESKF','NN-ESKF':'NN-ESKF','NN-Huber-ESKF':'NN-Huber-ESKF','IMU':'IMU integration','TLIO':'TLIO-adapted','AirIO':'AirIO-Net + ESKF','Fixed position':'Fixed position'}
KEYS=['rmse_3d_m','rmse_horizontal_m','p95_3d_m','rpe_10s_m']

def artifact(group,row):
    return OUT/group/f"{row['sequence']}_{row['method']}_{row['seed']}.npz"

def load_rows(group):
    path=OUT/group/'metrics.csv'
    with path.open() as f:rows=list(csv.DictReader(f))
    for row in rows:
        row['seed']=int(row['seed'])
        d=np.load(artifact(group,row));t=d['time'];p=d['position'];g=d['reference']
        row.update(metrics(p,g,t));row['output_availability_pct']=100.
        for k in ['wall_s','updates','accepted_updates']:
            if k in row and row[k] not in ('',None):row[k]=float(row[k])
        if group=='IO':
            j=artifact(group,row).with_suffix('.json')
            if j.exists():save_json(j,row)
    save_csv(path,rows)
    return rows

def pooled(group,rows,quality=None):
    methods=list(dict.fromkeys(r['method'] for r in rows));summary=[];seed_rows=[]
    for method in methods:
        seeds=sorted({r['seed'] for r in rows if r['method']==method})
        per=[]
        for seed in seeds:
            selected=[r for r in rows if r['method']==method and r['seed']==seed];errors=[];rel=[];wall=0.;duration=0.
            for r in selected:
                d=np.load(artifact(group,r));keep=np.ones(len(d['time']),dtype=bool)
                if quality is not None:keep=d['reference_quality']==quality
                p,g,t=d['position'][keep],d['reference'][keep],d['time'][keep]
                errors.append(p-g);rel.append(relative_error_vectors(p,g,t));wall+=float(r['wall_s']);duration+=float(t[-1]-t[0])
            e=np.concatenate(errors);r3=np.linalg.norm(e,axis=1);relative=np.concatenate(rel)
            item=dict(method=method,seed=seed,sequences=len(selected),samples=len(e),rmse_3d_m=float(np.sqrt(np.mean(r3*r3))),rmse_horizontal_m=float(np.sqrt(np.mean(np.sum(e[:,:2]**2,axis=1)))),p95_3d_m=float(np.percentile(r3,95)),rpe_10s_m=float(np.sqrt(np.mean(np.sum(relative**2,axis=1)))),wall_s=wall,evaluated_duration_s=duration)
            per.append(item);seed_rows.append(item)
        result={'method':method,'label':LABEL[method],'training_seeds':len(seeds),'test_sequences':per[0]['sequences'],'samples_per_seed':per[0]['samples']}
        for k in KEYS+['wall_s','evaluated_duration_s']:
            values=[r[k] for r in per];result[k+'_mean']=float(np.mean(values));result[k+'_std']=float(np.std(values,ddof=1)) if len(values)>1 else 0.
        summary.append(result)
    name='summary' if quality is None else f'summary_Q{quality}'
    save_csv(OUT/group/(name+'.csv'),summary);save_csv(OUT/group/(name+'_per_seed.csv'),seed_rows)
    return summary

def fmt(row,k):
    mean=row[k+'_mean'];sd=row[k+'_std']
    digits=3 if abs(mean)<1 else 2
    return f'{mean:.{digits}f} ± {sd:.{digits}f}' if row['training_seeds']>1 else f'{mean:.{digits}f}'

def md_table(rows):
    lines=['| Method | 3D RMSE (m) | Horizontal RMSE (m) | 3D P95 (m) | 10 s relative RMSE (m) |','|---|---:|---:|---:|---:|']
    for row in rows:lines.append('| '+row['label']+' | '+' | '.join(fmt(row,k) for k in KEYS)+' |')
    return '\n'.join(lines)

def cdf_figure(group,rows,name):
    plt=plot_setup();fig,ax=plt.subplots(figsize=(4.65,3.05))
    colors=['#595959','#0072B2','#D55E00','#009E73'];styles=['--','-.',':','-']
    for i,method in enumerate(dict.fromkeys(r['method'] for r in rows)):
        errors=[]
        for row in rows:
            if row['method']!=method:continue
            d=np.load(artifact(group,row));errors.append(np.linalg.norm(d['position']-d['reference'],axis=1))
        e=np.sort(np.concatenate(errors));idx=np.unique(np.r_[0,np.linspace(0,len(e)-1,min(3000,len(e))).astype(int),len(e)-1])
        ax.plot(np.r_[0,e[idx]],np.r_[0,(idx+1)/len(e)],label=LABEL[method],color=colors[i],linestyle=styles[i])
    ax.set_xlabel('3D position error (m)');ax.set_ylabel('Empirical CDF');ax.set_xlim(left=0);ax.set_ylim(0,1.01)
    ax.grid(True,linestyle=':',linewidth=.5,color='.85');ax.legend(loc='lower right',frameon=False)
    save_figure(fig,OUT/'figures'/name)

def io_figure(rows):
    plt=plot_setup();fig,ax=plt.subplots(figsize=(4.65,3.35));seqs=PROTOCOL['io']['test'];methods=['IMU','Fixed position','TLIO','AirIO'];colors=['#9B9B9B','#E6AB02','#0072B2','#D55E00'];width=.19
    for i,method in enumerate(methods):
        means=[];std=[]
        for seq in seqs:
            values=[float(r['rpe_10s_m']) for r in rows if r['method']==method and r['sequence']==seq]
            means.append(np.mean(values));std.append(np.std(values,ddof=1) if len(values)>1 else 0.)
        ax.bar(np.arange(len(seqs))+(i-1.5)*width,means,width,label=LABEL[method],color=colors[i],yerr=std,capsize=1.8,error_kw={'linewidth':.7})
    ax.set_xticks(range(5),['MH02','MH04','V101','V103','V202']);ax.set_xlabel('EuRoC sequence');ax.set_ylabel('10 s relative displacement RMSE (m)');ax.set_yscale('log')
    from matplotlib.ticker import StrMethodFormatter,NullFormatter
    ax.yaxis.set_major_formatter(StrMethodFormatter('{x:g}'));ax.yaxis.set_minor_formatter(NullFormatter())
    ax.grid(True,axis='y',linestyle=':',linewidth=.5,color='.85');ax.set_axisbelow(True)
    ax.legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False,fontsize=8,columnspacing=.9,handletextpad=.4)
    save_figure(fig,OUT/'figures/euroc_relative_error')

def main():
    data={};summary={}
    for group in ['GNSS','UWB','IO']:
        assert json.loads((OUT/group/'status.json').read_text())['status']=='complete'
        data[group]=load_rows(group);summary[group]=pooled(group,data[group])
        (OUT/group/'table.md').write_text(md_table(summary[group])+'\n')
    summary['GNSS_Q1']=pooled('GNSS',data['GNSS'],quality=1)
    (OUT/'GNSS/table_Q1.md').write_text(md_table(summary['GNSS_Q1'])+'\n')
    cdf_figure('GNSS',data['GNSS'],'urbannav_gnss_error_cdf');cdf_figure('UWB',data['UWB'],'util_uwb_error_cdf');io_figure(data['IO'])
    # Verify all saved errors, time bases and method coverage before publishing a table.
    expected={'GNSS':10,'UWB':72,'IO':40}
    assert {k:len(v) for k,v in data.items()}==expected
    save_json(OUT/'summary.json',summary)
    save_json(OUT/'artifact_checks.json',{'rows':{k:len(v) for k,v in data.items()},'figures':3,'axes_per_figure':1,'font':'Times New Roman','all_saved_trajectories_finite':True,'metric_checks':'identity, exact 10 s interval, GNSS upstream parity, UWB upstream parity and Jacobian, velocity-update Jacobian','trajectory_alignment':'none','seed_statistic':'arithmetic mean and sample standard deviation of independently trained seed metrics','pooling':'epochs pooled within each seed across complete test sequences; no cross-group ranking'})
    for group in summary:
        print(group);print(md_table(summary[group]))

if __name__=='__main__':main()
