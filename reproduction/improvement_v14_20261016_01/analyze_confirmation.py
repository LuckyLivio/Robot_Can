"""Evaluate the locked independent batch without changing any outcomes or design."""
from pathlib import Path
import csv,hashlib,json
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,d):
    with p.open('x',encoding='utf8') as f:json.dump(d,f,indent=2,allow_nan=False)
if __name__=='__main__':
    for rel,h in read(RUN/'protocols/confirmation_lock.json')['sha256'].items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,rel
    for n in ['confirmation_verification','confirmation_physics']:assert read(RUN/'analysis'/f'{n}.json')['passed']
    design=read(RUN/'protocols/freeze_before_states.json');versions=['v6','v13','v14'];references=['v6','v13']
    assert design['versions']==versions and design['bootstrap_seed']==2026102614 and design['bootstrap_draws']==20000
    assert design['state_names']==[f'demo_{14000000+i}' for i in range(60)]
    assert design['initialization_seeds']==list(range(2026102601,2026102661))
    assert read(RUN/'confirmation/completed.json')['source_unchanged']
    jobs=read(RUN/'confirmation/jobs.json');assert jobs==read(RUN/'protocols/confirmation_jobs.json')
    records={};export=[]
    for j in jobs:
        d=read(RUN/'confirmation'/j['id']/'result.json');assert d['status']=='complete' and d['job']==j
        rr=d['records'];assert [r['demo'] for r in rr]==j['demos']==design['state_names']
        assert len(rr)==60 and j['steps']==400 and j['config']['delay']==2
        key=(j['version'],j['id'].split('_',1)[1]);assert key not in records;records[key]=rr
    conditions=[j['id'].split('_',1)[1] for j in jobs if j['version']=='v6'];assert len(conditions)==len(set(conditions))==8
    assert set(records)=={(v,c) for v in versions for c in conditions}
    for c in conditions:
        paired=[next(j for j in jobs if j['version']==v and j['id'].split('_',1)[1]==c) for v in versions]
        for field in ['method','seed','noise','dataset','enabled','steps']:
            assert all(j.get(field)==paired[0].get(field) for j in paired),(c,field)
    values={v:np.array([[r['success'] for r in records[v,c]] for c in conditions],float) for v in versions}
    idx=np.random.default_rng(design['bootstrap_seed']).integers(0,60,(design['bootstrap_draws'],60))
    def estimate(a):return {'estimate_percent':float(a.mean()*100),'ci95_percent':(np.quantile(a[idx].mean(1),[.025,.975])*100).tolist()}
    statistics={v:estimate(a.mean(0)) for v,a in values.items()}
    rescues={r:[] for r in references};regressions={r:[] for r in references};per_condition=[]
    for ref in references:statistics['v14_minus_'+ref]=estimate((values['v14']-values[ref]).mean(0))
    for ci,c in enumerate(conditions):
        for k in range(60):
            rs={v:records[v,c][k] for v in versions};demo=rs['v14']['demo'];assert all(r['demo']==demo for r in rs.values())
            for ref in references:
                if rs['v14']['success'] and not rs[ref]['success']:rescues[ref].append([c,demo])
                if rs[ref]['success'] and not rs['v14']['success']:regressions[ref].append([c,demo])
            row={'condition':c,'demo':demo}
            for v,r in rs.items():row.update({v+'_success':r['success'],v+'_steps':r['steps']})
            row.update(tracking_events=len(rs['v14'].get('tracking14_events',[])),clearance_events=len(rs['v14'].get('clearance14_events',[])))
            export.append(row)
        per_condition.append({'condition':c,**{v+'_success':int(values[v][ci].sum()) for v in versions},'episodes':60})
    variants={v:{'success':int(a.sum()),'episodes':480,
                 'tracking_event_episodes':sum(bool(r.get('tracking14_events')) for c in conditions for r in records[v,c]),
                 'clearance_event_episodes':sum(bool(r.get('clearance14_events')) for c in conditions for r in records[v,c])} for v,a in values.items()}
    gate=all(not regressions[ref] and variants['v14']['success']>=variants[ref]['success'] for ref in references)
    positive_primary_ci=statistics['v14_minus_v6']['ci95_percent'][0]>0
    out={'stage':'confirmation','variants':variants,'unique_starts':60,'new_executions':1440,'statistics':statistics,
         'conditions':per_condition,'rescues':rescues,'regressions':regressions,'adoption_gate_passed':gate,
         'positive_primary_ci':positive_primary_ci,'overall_success_improvement_claim_supported':gate and positive_primary_ci,
         'inference':'Primary v14-v6, secondary v14-v13. Paired-start percentile bootstrap, 20000 draws, seed2026102614. Eight fixed conditions per start and three fixed Full training seeds. Adoption requires no paired loss and at least both reference success counts; an overall success-rate improvement claim separately requires the primary 95% CI to be strictly positive. Pointwise intervals, no multiplicity correction, not arbitrary retraining uncertainty. Zero interval with no discordance does not prove equivalence. Do not compare v5 from another batch.'}
    write(RUN/'analysis/confirmation.json',out)
    with (RUN/'analysis/confirmation_pairs.csv').open('x',newline='',encoding='utf8') as f:w=csv.DictWriter(f,fieldnames=export[0]);w.writeheader();w.writerows(export)
    print(json.dumps({k:out[k] for k in ['variants','statistics','rescues','regressions','adoption_gate_passed','positive_primary_ci']},indent=2))
