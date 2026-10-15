"""Two-factor paired analysis; training seeds are averaged within each start."""
import argparse,csv,json
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup_study import ROOT,RUN,write
VERSIONS=['v2','align_only','region_only','v4']
def main(stage):
    folder=RUN/stage;out=RUN/f'analysis_{stage}';out.mkdir(exist_ok=False)
    jobs=json.loads((folder/'jobs.json').read_text());records={};jobrows=[];episodes=[]
    for j in jobs:
        result=json.loads((folder/j['id']/'result.json').read_text());assert result['status']=='complete'
        rows=result['records'];assert [r['demo'] for r in rows]==j['demos']
        key=(j['version'],j['method'],j['seed'],j['noise']);assert key not in records;records[key]=rows
        if stage.startswith('dev'):
            base=json.loads((ROOT/j['baseline_result']).read_text())['records']
            assert [r['demo'] for r in base]==j['demos'];records[('v2',j['method'],j['seed'],j['noise'])]=base
    for (version,method,seed,noise),rows in records.items():
        jobrows.append({'version':version,'method':method,'seed':seed,'noise':noise,'successes':sum(r['success'] for r in rows),'episodes':len(rows),
            'intervened_episodes':sum(r['attempts']>0 for r in rows),'mean_steps_capped':float(np.mean([r['steps'] for r in rows])),
            'events':dict(Counter(e['reason'] for r in rows for e in r['events']))})
        for r in rows:episodes.append({'version':version,'method':method,'seed':seed,'noise':noise,'demo':r['demo'],'success':r['success'],'steps':r['steps'],'attempts':r['attempts']})
    def outcomes(v,m,s,n):
        rows=records[(v,m,s,n)];assert [r['demo'] for r in rows]==[r['demo'] for r in records[('v2',m,s,n)]]
        return np.array([r['success'] for r in rows],float)
    comparisons=[]
    for v in VERSIONS[1:]:
        for noise in [0.,.05]:
            for method,seed in [('bc_k2',None),('full',17),('full',23),('full',41)]:
                a=outcomes(v,method,seed,noise);b=outcomes('v2',method,seed,noise)
                ids=[r['demo'] for r in records[(v,method,seed,noise)]]
                comparisons.append({'version':v,'method':method,'seed':seed,'noise':noise,'successes':int(a.sum()),'baseline_successes':int(b.sum()),'episodes':len(a),
                  'rescues':int(((a==1)&(b==0)).sum()),'regressions':int(((a==0)&(b==1)).sum()),
                  'rescued_demos':[d for d,x,y in zip(ids,a,b) if x and not y],'regressed_demos':[d for d,x,y in zip(ids,a,b) if y and not x]})
    rng=np.random.default_rng(20261015);stats={}
    for noise,label in [(0.,'clean'),(.05,'noise005')]:
        n=len(outcomes('v2','bc_k2',None,noise));idx=rng.integers(0,n,(20000,n));values={}
        for v in VERSIONS:
            values[v+'_bc']=outcomes(v,'bc_k2',None,noise)
            values[v+'_full']=np.stack([outcomes(v,'full',s,noise) for s in [17,23,41]]).mean(0)
        diffs={}
        for v in VERSIONS[1:]:
            for m in ['bc','full']:diffs[v+'_'+m+'_minus_v2']=values[v+'_'+m]-values['v2_'+m]
        for m in ['bc','full']:
            for v in ['align_only','region_only']:diffs['v4_'+m+'_minus_'+v]=values['v4_'+m]-values[v+'_'+m]
            diffs[m+'_interaction_AB_minus_A_minus_B_plus_v2']=values['v4_'+m]-values['align_only_'+m]-values['region_only_'+m]+values['v2_'+m]
        for v in VERSIONS:diffs[v+'_full_minus_bc']=values[v+'_full']-values[v+'_bc']
        stats[label]={k:{'estimate':float(v.mean()),'ci95':np.quantile(v[idx].mean(1),[.025,.975]).tolist()} for k,v in {**values,**diffs}.items()}
    totals={}
    for v in VERSIONS:
        jr=[r for r in jobrows if r['version']==v];cr=[r for r in comparisons if r['version']==v]
        totals[v]={'successes':sum(r['successes'] for r in jr),'episodes':sum(r['episodes'] for r in jr),
            'rescues_vs_v2':sum(r['rescues'] for r in cr),'regressions_vs_v2':sum(r['regressions'] for r in cr)}
    summary={'stage':stage,'unique_starts':n,'new_executed_episodes':sum(len(j['demos']) for j in jobs),'totals':totals,'jobs':jobrows,
        'comparisons':comparisons,'statistics':stats,'inference':'Paired-start percentile bootstrap, 20000 draws, seed20261015. Full averages 3 fixed training seeds per start. Repeated conditions/seeds are not independent starts. Degenerate CI from rare/zero discordance does not establish equivalence.'}
    write(out/'summary.json',summary)
    for name,rows in [('episodes.csv',episodes),('comparisons.csv',comparisons)]:
        with (out/name).open('x',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
    for ax,label in zip(axes,['clean','noise005']):
        for i,(v,color) in enumerate(zip(VERSIONS,['#778391','#597ec1','#b07841','#20816b'])):
            vals=[100*stats[label][v+'_'+m]['estimate'] for m in ['bc','full']]
            bars=ax.bar(np.arange(2)+(i-1.5)*.2,vals,.185,label=v,color=color)
            ax.bar_label(bars,fmt='%.1f',fontsize=8,padding=3)
        ax.set_xticks([0,1],['BC k=2','Full (3-seed mean)']);ax.set_ylim(0,113);ax.set_title(label);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    axes[0].set_ylabel('Task success (%)');axes[1].legend(loc='lower right');fig.suptitle(f'{stage} | {n} paired starts per condition');fig.tight_layout()
    fig.savefig(out/'success_comparison.png',dpi=180);fig.savefig(out/'success_comparison.svg');plt.close(fig)
    print(json.dumps(totals,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();main(a.stage)
