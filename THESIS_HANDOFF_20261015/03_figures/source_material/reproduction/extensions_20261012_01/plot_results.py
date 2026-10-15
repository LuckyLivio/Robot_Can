"""Figures generated only from verified results, never from hand-entered rates."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
RUN=Path(__file__).resolve().parent


def main():
    out=RUN/'analysis'
    summary=json.loads((out/'summary.json').read_text())
    rows={(r['variant'],r['noise']):r for r in summary}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'figure.facecolor':'white','axes.titleweight':'bold',
                         'axes.labelcolor':'#303743','text.color':'#17202b','savefig.facecolor':'white'})
    colors=['#1768a6','#d86532']
    def save(fig,name):
        for extension in ['png','pdf']:
            path=out/f'{name}.{extension}'
            if path.exists():raise FileExistsError(path)
            fig.savefig(path,dpi=190,bbox_inches='tight')
        plt.close(fig)
    variants=['bc_k2','persistence','full','plain','oracle']
    labels=['BC k=2','Persistence\n+ gate','Full\nH=8, K=4','Plain\nH=8, K=4','True-score\nlocal oracle']
    fig,ax=plt.subplots(figsize=(10.3,5.4));x=np.arange(len(variants));w=.35
    for i,(noise,label) in enumerate([(0.,'Clean'),(.05,'Execution noise 0.05')]):
        selected=[rows[(v,noise)] for v in variants];means=[r['mean_success_percent'] for r in selected]
        ci=np.asarray([r['paired_bootstrap_ci_percent'] for r in selected]);xx=x+(i-.5)*w
        ax.bar(xx,means,w,color=colors[i],label=label,alpha=.9)
        ax.errorbar(xx,means,yerr=np.stack([np.array(means)-ci[:,0],ci[:,1]-np.array(means)]),fmt='none',ecolor='#313b45',capsize=3,lw=1)
        for a,y,r in zip(xx,means,selected):
            ax.text(a,3,f'{y:.1f}%',ha='center',va='bottom',color='white',rotation=90,fontweight='bold')
    ax.set(xticks=x,xticklabels=labels,ylim=(0,108),ylabel='Task success (%)',title='Supplemental development controls')
    ax.grid(axis='y',alpha=.13);ax.set_axisbelow(True);ax.legend(loc='upper left',ncol=2,frameon=False,bbox_to_anchor=(0,1.15))
    fig.text(.04,-.025,'30 paired development starts. Full/Plain: mean of 3 frozen training seeds; other policies run once per condition.\nWhiskers: descriptive 95% paired bootstrap intervals. Oracle uses privileged, noise-free counterfactuals; H=8 and the same gate.',fontsize=9,color='#556170')
    save(fig,'controls')
    fig,axes=plt.subplots(1,2,figsize=(11.5,4.7))
    scans=[(['h1','h3','horizon4','full'],[1,3,4,8],'Total executed prediction horizon H','K=4; D=2 included in H'),
           (['k1','k2','full','k8'],[1,2,4,8],'Candidate count K','H=8; every set retains BC k=2')]
    for ax,(vs,xs,xlabel,title) in zip(axes,scans):
        for i,(noise,label) in enumerate([(0.,'Clean'),(.05,'Noise 0.05')]):
            rr=[rows[(v,noise)] for v in vs];yy=[r['mean_success_percent'] for r in rr]
            ax.plot(xs,yy,'o-',color=colors[i],label=label,lw=2)
            for a,r in zip(xs,rr):
                values=np.asarray(r['success_counts'])/30*100
                if len(values)>1:ax.scatter(a+np.linspace(-.08,.08,len(values)),values,s=18,color=colors[i],alpha=.5)
            for v,a,y in zip(vs,xs,yy):
                other=rows[(v,.05 if noise==0 else 0.)]['mean_success_percent']
                offset=10 if y>=other else -18
                ax.annotate(f'{y:.1f}',(a,y),xytext=(0,offset),textcoords='offset points',ha='center',fontsize=8,color=colors[i])
        ax.set(xticks=xs,xlabel=xlabel,ylabel='Task success (%)',ylim=(45,100),title=title)
        ax.grid(alpha=.15);ax.legend(frameon=False,loc='lower left')
    fig.suptitle('Horizon and candidate-set sensitivity',fontsize=15,y=1.02)
    fig.text(.025,-.035,'H=1 cannot reach a new command beyond the two-step FIFO. Dots show actual seed results, not new independent starts.\nNested sets: {2}, {0,2}, {0,1,2,3}, {0,...,7}. K=8 also expands beyond the trained shift set; no retraining or test-set selection.',fontsize=9,color='#556170')
    fig.tight_layout();save(fig,'sensitivity')
    offline=json.loads((RUN/'offline_metrics.json').read_text())['rows']
    fig,axes=plt.subplots(1,2,figsize=(10,4.7));methods=['persistence','full','plain'];cc=['#939ca8','#1768a6','#428a75']
    for ax,key,title in zip(axes,['eef_position_rmse_m','object_position_rmse_m'],['End-effector position','Object position']):
        vals=[[r[key]*1000 for r in offline if r['method']==m] for m in methods]
        means=[np.mean(v) for v in vals]
        ax.bar(methods,means,color=cc,width=.55)
        for a,v in enumerate(vals):
            # The same parameter-free persistence forecast is only one comparator.
            shown=v[:1] if a==0 else v
            ax.scatter(np.repeat(a,len(shown)),shown,color='#202630',s=24,zorder=3)
            ax.text(a,max(v)+2,f'{np.mean(v):.1f}',ha='center',fontsize=11)
        ax.set(ylabel='Position RMSE (mm)',title=title,ylim=(0,70))
        ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.suptitle('Short-horizon forecast quality',fontsize=15,y=1.02)
    fig.text(.03,-.035,'64 existing development branch groups from 8 parent demos, 4 candidates x 8 steps. Bars: seed means; dots: individual seeds.\nPersistence is one parameter-free forecast. These branches were used for checkpoint selection; this is a mechanism diagnostic.',fontsize=9,color='#556170')
    fig.tight_layout();save(fig,'prediction')
    print('Saved 3 PNG and 3 PDF figures from verified source data.')


if __name__=='__main__':main()
