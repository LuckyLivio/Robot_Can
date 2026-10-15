"""Unsmoothened, source-linked plots for this recovery study only."""
from pathlib import Path
import csv,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
RUN=Path(__file__).resolve().parent;OUT=RUN/'figures';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})

def save(fig,name):
    for ext in ['png','pdf']:
        p=OUT/f'{name}.{ext}';assert not p.exists();fig.savefig(p,bbox_inches='tight')
    plt.close(fig)
def get(stage,job,demo):
    p=RUN/stage/job/'trace.jsonl'
    return p,[r for line in p.open() if (r:=json.loads(line))['demo']==demo]
def main():
    pilot=json.loads((RUN/'analysis/pilot_b.json').read_text())['variants'];dev=json.loads((RUN/'analysis/dev_comparison.json').read_text())
    fig,ax=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    labels=['v5','R1','R2','R1 + R2'];values=[pilot[v]['success'] for v in ['v5','r1','r2','v6']]
    bars=ax[0].bar(labels,np.array(values)/37*100,color=['#8092a2','#1868b2','#7baf8d','#182b49'],width=.6)
    for b,n in zip(bars,values):ax[0].text(b.get_x()+b.get_width()/2,b.get_height()+2,f'{n}/37',ha='center')
    ax[0].set(title='Known diagnostic pilot (revision B)',ylabel='Task success (%)',ylim=(0,108))
    bars=ax[1].bar(['v5','R1 + R2'],[dev['v5_successes']/240*100,dev['v6_successes']/240*100],color=['#8092a2','#182b49'],width=.5)
    for b,n in zip(bars,[dev['v5_successes'],dev['v6_successes']]):ax[1].text(b.get_x()+b.get_width()/2,b.get_height()+1.5,f'{n}/240',ha='center')
    ax[1].set(title='Frozen development comparison',ylabel='Task success (%)',ylim=(0,108))
    fig.supxlabel('Known starts; development = 30 starts × 4 policy settings × 2 noise conditions. No independent confirmation.',fontsize=9)
    save(fig,'01_paired_outcomes')
    fig,ax=plt.subplots(figsize=(9,4.5),layout='constrained');data=[]
    for v,color in [('v5','#8092a2'),('v6','#1868b2')]:
        p,rs=get('pilot_b',v+'_known_pressure','demo_11000013');rs=[r for r in rs if 80<=r['step']<=146]
        steps=[r['step'] for r in rs];gap=[abs(r['state_before'][7]-r['state_before'][8])*1000 for r in rs]
        ax.plot(steps,gap,label=v,color=color,lw=1.6)
        for r,g in zip(rs,gap):data.append({'variant':v,'step':r['step'],'observed_gap_mm':g,'mode':r['recovery']['mode'],'source':p.relative_to(RUN).as_posix()})
    ax.axhline(56,color='#343434',ls='--',lw=1,label='56 mm planned gap')
    ax.axhspan(51.5,60.5,color='#1868b2',alpha=.08,label='R1 achieved-gap tolerance')
    ax.set(title='Observed aperture: known sideways-loss diagnostic 11000013',xlabel='Control step (20 Hz; D = 2)',ylabel='Measured finger gap (mm)',xlim=(80,146),ylim=(0,90))
    ax.legend(loc='lower left',ncol=2,fontsize=9);save(fig,'02_observed_aperture')
    with (OUT/'02_observed_aperture.csv').open('x',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    fig,ax=plt.subplots(figsize=(9,3.5),layout='constrained');data=[]
    for y,v in enumerate(['v5','v6']):
        p,rs=get('dev_a' if v=='v6' else '../recovery_v5_20261012_01/dev_a',v+'_full_s23_clean','demo_188')
        for mode,color in [('DESCEND','#cf7351'),('ABORT_RETRACT','#8b9bac'),('BLOCKED','#1868b2')]:
            steps=[r['step'] for r in rs if r['recovery']['mode']==mode]
            if steps:ax.broken_barh([(s,1) for s in steps],(y-.25,.5),facecolors=color,label=mode if y==0 or mode!='DESCEND' else None)
            data.append({'variant':v,'mode':mode,'steps':len(steps),'success':bool(rs[-1]['success_after']),'source':str(p.relative_to(RUN))})
    ax.set(yticks=[0,1],yticklabels=['v5','R1 + R2'],xlim=(0,400),xlabel='Control step',title='No feasible candidate: Full s23 / clean / demo 188')
    handles,labels=ax.get_legend_handles_labels();unique=dict(zip(labels,handles));ax.legend(unique.values(),unique.keys(),loc='upper left',ncol=3,fontsize=8)
    fig.supxlabel('Both episodes fail the task. New behavior prevents repeated descent; it does not create a feasible grasp.',fontsize=9)
    save(fig,'03_infeasible_handling')
    with (OUT/'03_infeasible_handling.csv').open('x',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    print(json.dumps({'figures':3,'formats':['png','pdf'],'no_smoothing':True}))
if __name__=='__main__':main()
