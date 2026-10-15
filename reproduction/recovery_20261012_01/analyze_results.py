"""Read-only analysis of all 240 frozen development episodes and paired originals."""
import csv,json
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup_study import ROOT,RUN,write


def bootstrap(values,indices):
    values=np.asarray(values,float)
    return {'estimate':float(values.mean()),'ci95':np.quantile(values[indices].mean(1),[.025,.975]).tolist()}


def main():
    out=RUN/'analysis';out.mkdir(exist_ok=False)
    jobs=json.loads((RUN/'formal_jobs.json').read_text());summary=[];episodes=[];data={};failures=[]
    for job in jobs:
        r=json.loads((RUN/'formal'/job['id']/'result.json').read_text());assert r['status']=='complete'
        old=json.loads((ROOT/job['baseline_result']).read_text())['records'];new=r['records']
        assert [a['demo'] for a in old]==[a['demo'] for a in new]==job['demos']
        yy=np.array([a['success'] for a in new],int);bb=np.array([a['success'] for a in old],int)
        data[job['id']]={'new':yy,'old':bb,'records':new}
        losses=[a for a in new if any(e['reason']=='observed_grasp_loss' for e in a['events'])]
        item={'job':job['id'],'method':job['method'],'seed':job['seed'],'noise':job['noise'],'episodes':len(new),
              'original_successes':int(bb.sum()),'recovery_successes':int(yy.sum()),'rescued':int(((bb==0)&(yy==1)).sum()),
              'regressed':int(((bb==1)&(yy==0)).sum()),'both_failed':int(((bb==0)&(yy==0)).sum()),
              'intervened_episodes':sum(a['attempts']>0 for a in new),'intervened_original_successes':sum(a['success'] and b['attempts']>0 for a,b in zip(old,new)),
              'intervention_steps':sum(a['intervention_steps'] for a in new),'total_steps':sum(a['steps'] for a in new),
              'verified_regrasp_episodes':sum(a['verified_regrasps']>0 for a in new),
              'verified_regrasp_successes':sum(a['verified_regrasps']>0 and a['success'] for a in new),
              'loss_trigger_episodes':len(losses),'loss_trigger_successes':sum(a['success'] for a in losses),
              'mean_steps_original_capped':float(np.mean([a['steps'] for a in old])),
              'mean_steps_recovery_capped':float(np.mean([a['steps'] for a in new])),
              'mean_steps_successes_only':float(np.mean([a['steps'] for a in new if a['success']])) if yy.any() else None,
              'event_reasons':dict(Counter(e['reason'] for a in new for e in a['events']))}
        item['intervention_fraction']=item['intervention_steps']/item['total_steps'];summary.append(item)
        final={}
        for line in (RUN/'formal'/job['id']/'trace.jsonl').open():
            trace=json.loads(line);final[trace['demo']]=trace
        for a,b in zip(old,new):
            episodes.append({'job':job['id'],'method':job['method'],'seed':job['seed'],'noise':job['noise'],
                'demo':b['demo'],'original_success':a['success'],'recovery_success':b['success'],
                'original_steps':a['steps'],'recovery_steps':b['steps'],'attempts':b['attempts'],
                'intervention_steps':b['intervention_steps'],'verified_regrasps':b['verified_regrasps'],
                'loss_trigger':any(e['reason']=='observed_grasp_loss' for e in b['events']),
                'stable_hold_observed':b['stable_hold_observed']})
            if not b['success']:
                last=final[b['demo']];obj=last['state_after'][16:19]
                failures.append({'job':job['id'],'demo':b['demo'],'original_success':a['success'],'attempts':b['attempts'],
                    'final_mode':last['recovery']['mode'],'stable_hold_ever':b['stable_hold_observed'],
                    'verified_regrasps':b['verified_regrasps'],'object_final':obj,
                    'goal_xy_distance_m':float(np.linalg.norm(np.array(obj[:2])-[.1975,.4025])),
                    'last_events':b['events'][-4:]})
    assert len(episodes)==240
    statistics={};rng=np.random.default_rng(20261012)
    for condition in ['clean','noise005']:
        idx=rng.integers(0,30,(20000,30));bc=data[f'bc_k2_{condition}']
        fnew=np.stack([data[f'full_s{s}_{condition}']['new'] for s in [17,23,41]]).mean(0)
        fold=np.stack([data[f'full_s{s}_{condition}']['old'] for s in [17,23,41]]).mean(0)
        statistics[condition]={
            'bc_original':bootstrap(bc['old'],idx),'bc_recovery':bootstrap(bc['new'],idx),
            'full_original':bootstrap(fold,idx),'full_recovery':bootstrap(fnew,idx),
            'bc_recovery_gain':bootstrap(bc['new']-bc['old'],idx),
            'full_recovery_gain':bootstrap(fnew-fold,idx),
            'full_minus_bc_original':bootstrap(fold-bc['old'],idx),
            'full_minus_bc_with_recovery':bootstrap(fnew-bc['new'],idx),
            'difference_in_differences':bootstrap((fnew-fold)-(bc['new']-bc['old']),idx)}
    result={'episodes':240,'jobs':summary,'paired_start_bootstrap':statistics,
            'inference_note':'30 unique development starts per condition. Full uses the mean of three fixed training seeds. Intervals resample paired starts, conditional on those seeds; 90 Full rollouts are not 90 independent starts.',
            'failures':failures,'total_new_successes':sum(e['recovery_success'] for e in episodes),
            'total_rescued':sum(not e['original_success'] and e['recovery_success'] for e in episodes),
            'total_regressed':sum(e['original_success'] and not e['recovery_success'] for e in episodes)}
    write(out/'summary.json',result)
    for name,rows in [('episodes.csv',episodes),('jobs.csv',[{k:v for k,v in s.items() if k!='event_reasons'} for s in summary])]:
        with (out/name).open('x',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write(out/'remaining_failures.json',failures)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(11,5),sharey=True)
    for ax,condition,title in zip(axes,['clean','noise005'],['Clean execution','Action noise: 0.05']):
        stats=statistics[condition]
        old=[stats['bc_original']['estimate']*100,stats['full_original']['estimate']*100]
        new=[stats['bc_recovery']['estimate']*100,stats['full_recovery']['estimate']*100]
        xx=np.arange(2)
        for pos,values,color,label in [(xx-.19,old,'#8395a7','Original'),(xx+.19,new,'#147d92','Shared recovery')]:
            bars=ax.bar(pos,values,.35,label=label,color=color)
            ax.bar_label(bars,labels=[f'{v:.1f}%' for v in values],padding=5,fontsize=11)
        ax.scatter(np.repeat(1.19,3),[data[f'full_s{s}_{condition}']['new'].mean()*100 for s in [17,23,41]],
                   color='#152f41',s=25,zorder=5,label='Full training seeds')
        ax.set_xticks(xx,['BC k=2','Full (3-seed mean)']);ax.set_ylim(0,113);ax.set_title(title);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    axes[0].set_ylabel('Task success (%)');axes[1].legend(loc='lower right',fontsize=9)
    fig.suptitle('Frozen recovery comparison | 30 paired development starts per condition',fontsize=13)
    fig.tight_layout();fig.savefig(out/'success_comparison.png',dpi=180);fig.savefig(out/'success_comparison.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,5))
    xx=np.arange(len(summary));resc=[s['rescued'] for s in summary];reg=[-s['regressed'] for s in summary]
    ax.bar(xx,resc,color='#147d92',label='Original failure rescued');ax.bar(xx,reg,color='#c55445',label='Original success lost')
    ax.axhline(0,color='#334455',lw=.8);ax.set_xticks(xx,[s['job'].replace('_noise005','\nnoise').replace('_clean','\nclean').replace('bc_k2','BC').replace('full_','Full ') for s in summary],fontsize=9)
    ax.set_ylabel('Paired episodes (out of 30)');ax.set_title('All gains and regressions are retained');ax.legend();fig.tight_layout()
    fig.savefig(out/'paired_changes.png',dpi=180);plt.close(fig)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
