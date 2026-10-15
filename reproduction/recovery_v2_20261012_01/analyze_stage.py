"""Paired, complete-case stage analysis. No outcome selection or tuning."""
import argparse,csv,json
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup_study import ROOT,RUN,write

def main(stage):
    folder=RUN/stage;out=RUN/f'analysis_{stage}';out.mkdir(exist_ok=False)
    jobs=json.loads((folder/'jobs.json').read_text());records={};jobrows=[];episodes=[];failures=[]
    for job in jobs:
        result=json.loads((folder/job['id']/'result.json').read_text());assert result['status']=='complete'
        rows=result['records'];assert [r['demo'] for r in rows]==job['demos']
        key=(job['version'],job['method'],job['seed'],job['noise']);assert key not in records;records[key]=rows
        if stage.startswith('dev'):
            records[('v1',job['method'],job['seed'],job['noise'])]=json.loads((ROOT/job['baseline_result']).read_text())['records']
            records[('disabled',job['method'],job['seed'],job['noise'])]=json.loads((ROOT/job['original_baseline_result']).read_text())['records']
        jobrows.append({'job':job['id'],'version':job['version'],'method':job['method'],'seed':job['seed'],'noise':job['noise'],
             'successes':sum(r['success'] for r in rows),'episodes':len(rows),'intervened_episodes':sum(r['attempts']>0 for r in rows),
             'intervention_steps':sum(r['intervention_steps'] for r in rows),'total_steps':sum(r['steps'] for r in rows),
             'mean_steps_capped':float(np.mean([r['steps'] for r in rows])),'verified_regrasp_episodes':sum(r['verified_regrasps']>0 for r in rows),
             'verified_regrasp_successes':sum(r['verified_regrasps']>0 and r['success'] for r in rows),
             'event_reasons':dict(Counter(e['reason'] for r in rows for e in r['events']))})
        for r in rows:
            episodes.append({'job':job['id'],'version':job['version'],'method':job['method'],'seed':job['seed'],'noise':job['noise'],
                'demo':r['demo'],'success':r['success'],'steps':r['steps'],'attempts':r['attempts'],
                'intervention_steps':r['intervention_steps'],'verified_regrasps':r['verified_regrasps']})
            if job['version']=='v2' and not r['success']:
                failures.append({'job':job['id'],'demo':r['demo'],'attempts':r['attempts'],'stable_hold_ever':r['stable_hold_observed'],
                                 'verified_regrasps':r['verified_regrasps'],'events':r['events']})
    def outcomes(version,method,seed,noise):return np.array([r['success'] for r in records[(version,method,seed,noise)]],float)
    comparisons=[]
    for noise in [0.,.05]:
        for method,seed in [('bc_k2',None),('full',17),('full',23),('full',41)]:
            new=outcomes('v2',method,seed,noise);previous=outcomes('v1',method,seed,noise);original=outcomes('disabled',method,seed,noise)
            comparisons.append({'method':method,'seed':seed,'noise':noise,'episodes':len(new),'original_successes':int(original.sum()),
                'v1_successes':int(previous.sum()),'v2_successes':int(new.sum()),'rescued_vs_v1':int(((new==1)&(previous==0)).sum()),
                'regressed_vs_v1':int(((new==0)&(previous==1)).sum()),'rescued_vs_original':int(((new==1)&(original==0)).sum()),
                'regressed_vs_original':int(((new==0)&(original==1)).sum())})
    statistics={};rng=np.random.default_rng(20261013)
    for noise,condition in [(0.,'clean'),(.05,'noise005')]:
        n=len(outcomes('v2','bc_k2',None,noise));idx=rng.integers(0,n,(20000,n));values={}
        for version in ['disabled','v1','v2']:
            values[version+'_bc']=outcomes(version,'bc_k2',None,noise)
            values[version+'_full']=np.stack([outcomes(version,'full',s,noise) for s in [17,23,41]]).mean(0)
        for method in ['bc','full']:
            values[method+'_v2_minus_v1']=values['v2_'+method]-values['v1_'+method]
            values[method+'_v2_minus_original']=values['v2_'+method]-values['disabled_'+method]
        values['v2_full_minus_bc']=values['v2_full']-values['v2_bc']
        statistics[condition]={k:{'estimate':float(v.mean()),'ci95':np.quantile(v[idx].mean(1),[.025,.975]).tolist()} for k,v in values.items()}
    summary={'stage':stage,'new_executed_episodes':len(episodes),'unique_starts':n,'jobs':jobrows,'comparisons':comparisons,
             'v2_successes':sum(r['v2_successes'] for r in comparisons),'v1_successes':sum(r['v1_successes'] for r in comparisons),
             'regressions_vs_v1':sum(r['regressed_vs_v1'] for r in comparisons),'rescues_vs_v1':sum(r['rescued_vs_v1'] for r in comparisons),
             'statistics':statistics,'v2_failures':failures,'inference':'Paired-start bootstrap 20000, seed20261013. Full three fixed seeds averaged per start. Seed generalization not included; Full counts are not independent starts.'}
    write(out/'summary.json',summary)
    for filename,rr in [('episodes.csv',episodes),('comparisons.csv',comparisons)]:
        with (out/filename).open('x',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(11,5),sharey=True)
    for ax,condition in zip(axes,['clean','noise005']):
        for offset,version,color,label in [(-.25,'disabled','#abb5bd','Original'),(0,'v1','#5a8aa5','Recovery v1'),(.25,'v2','#147d69','Recovery v2')]:
            vals=[statistics[condition][version+'_'+m]['estimate']*100 for m in ['bc','full']]
            bars=ax.bar(np.arange(2)+offset,vals,.24,color=color,label=label);ax.bar_label(bars,labels=[f'{v:.1f}' for v in vals],padding=3,fontsize=9)
        ax.set_xticks([0,1],['BC k=2','Full (3-seed mean)']);ax.set_ylim(0,113);ax.set_title('Clean' if condition=='clean' else 'Action noise 0.05');ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    axes[0].set_ylabel('Task success (%)');axes[1].legend(loc='lower right');fig.suptitle(f'{stage} | {n} paired starts / condition');fig.tight_layout()
    fig.savefig(out/'success_comparison.png',dpi=180);fig.savefig(out/'success_comparison.svg');plt.close(fig)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['v2_failures','jobs','statistics']},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();main(a.stage)
