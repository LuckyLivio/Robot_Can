from pathlib import Path
import csv,hashlib,json
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def write(p,d):
    with p.open('x') as f:json.dump(d,f,indent=2,allow_nan=False)
if __name__=='__main__':
    for rel,h in json.loads((RUN/'protocols/confirmation_lock.json').read_text())['sha256'].items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,rel
    for n in ['confirmation_verification','confirmation_physics']:
        assert json.loads((RUN/'analysis'/f'{n}.json').read_text())['passed']
    jobs=json.loads((RUN/'confirmation/jobs.json').read_text());records={};export=[]
    for j in jobs:
        d=json.loads((RUN/'confirmation'/j['id']/'result.json').read_text());assert d['status']=='complete'
        rr=d['records'];assert [r['demo'] for r in rr]==j['demos'];records[(j['version'],j['id'].split('_',1)[1])]=rr
    conditions=[j['id'].split('_',1)[1] for j in jobs if j['version']=='v6']
    values={v:np.array([[r['success'] for r in records[v,c]] for c in conditions],float) for v in ['v6','v12']}
    rng=np.random.default_rng(2026101512);idx=rng.integers(0,60,(20000,60))
    def estimate(a):return {'estimate_percent':float(a.mean()*100),'ci95_percent':(np.quantile(a[idx].mean(1),[.025,.975])*100).tolist()}
    statistics={v:estimate(a.mean(0)) for v,a in values.items()};statistics['v12_minus_v6']=estimate((values['v12']-values['v6']).mean(0))
    rescues=[];regressions=[];joint=[];per_condition=[]
    for ci,c in enumerate(conditions):
        a,b=records['v12',c],records['v6',c];names=[r['demo'] for r in a]
        rr=[];dd=[]
        for x,y in zip(a,b):
            if x['success'] and not y['success']:rescues.append([c,x['demo']]);rr.append(x['demo'])
            if y['success'] and not x['success']:regressions.append([c,x['demo']]);dd.append(x['demo'])
            if x['success'] and y['success']:joint.append(x['steps']-y['steps'])
            export.append({'condition':c,'demo':x['demo'],'v6_success':y['success'],'v12_success':x['success'],
                           'v6_steps':y['steps'],'v12_steps':x['steps'],'v12_wait_transfers':sum('evidence' in e for e in x.get('wait_hold_events',[]))})
        per_condition.append({'condition':c,'v6_success':int(values['v6'][ci].sum()),'v12_success':int(values['v12'][ci].sum()),
                              'episodes':60,'rescues':rr,'regressions':dd,'paired_difference':estimate(values['v12'][ci]-values['v6'][ci])})
    variants={v:{'success':int(a.sum()),'episodes':480,'wait_transfers':sum(sum('evidence' in e for e in r.get('wait_hold_events',[])) for c in conditions for r in records[v,c])} for v,a in values.items()}
    out={'stage':'confirmation','variants':variants,'unique_starts':60,'new_executions':960,'statistics':statistics,
         'conditions':per_condition,'rescues':rescues,'regressions':regressions,'distinct_rescued_starts':sorted({x[1] for x in rescues}),
         'adoption_gate_passed':not regressions and variants['v12']['success']>=variants['v6']['success'],
         'positive_primary_ci':statistics['v12_minus_v6']['ci95_percent'][0]>0,
         'joint_success_step_difference':{'n':len(joint),'median':float(np.median(joint)),'mean':float(np.mean(joint))},
         'inference':'Paired-start percentile bootstrap, 20000 draws, seed2026101512. Eight fixed conditions per start; Full three fixed training seeds. Pointwise intervals, not arbitrary retraining uncertainty. Zero interval with no discordance does not prove equivalence. No comparison to v5 from another batch.'}
    write(RUN/'analysis/confirmation.json',out)
    with (RUN/'analysis/confirmation_pairs.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=export[0]);w.writeheader();w.writerows(export)
    print(json.dumps({k:out[k] for k in ['variants','statistics','rescues','regressions','adoption_gate_passed']},indent=2))
