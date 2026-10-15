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
        rr=d['records'];assert [r['demo'] for r in rr]==j['demos'];records[j['version'],j['id'].split('_',1)[1]]=rr
    conditions=[j['id'].split('_',1)[1] for j in jobs if j['version']=='v6'];versions=['v6','v12','v13']
    values={v:np.array([[r['success'] for r in records[v,c]] for c in conditions],float) for v in versions}
    idx=np.random.default_rng(2026101613).integers(0,60,(20000,60))
    def estimate(a):return {'estimate_percent':float(a.mean()*100),'ci95_percent':(np.quantile(a[idx].mean(1),[.025,.975])*100).tolist()}
    statistics={v:estimate(a.mean(0)) for v,a in values.items()}
    rescues={r:[] for r in ['v6','v12']};regressions={r:[] for r in rescues};per_condition=[]
    for ref in rescues:statistics['v13_minus_'+ref]=estimate((values['v13']-values[ref]).mean(0))
    for ci,c in enumerate(conditions):
        for k in range(60):
            rs={v:records[v,c][k] for v in versions};demo=rs['v13']['demo'];assert all(r['demo']==demo for r in rs.values())
            for ref in rescues:
                if rs['v13']['success'] and not rs[ref]['success']:rescues[ref].append([c,demo])
                if rs[ref]['success'] and not rs['v13']['success']:regressions[ref].append([c,demo])
            row={'condition':c,'demo':demo}
            for v,r in rs.items():row.update({v+'_success':r['success'],v+'_steps':r['steps']})
            row.update(support_events=len(rs['v13'].get('support13_events',[])),escape_events=len(rs['v13'].get('escape_events',[])))
            export.append(row)
        per_condition.append({'condition':c,**{v+'_success':int(values[v][ci].sum()) for v in versions},'episodes':60})
    variants={v:{'success':int(a.sum()),'episodes':480,
                 'support_event_episodes':sum(bool(r.get('support13_events')) for c in conditions for r in records[v,c]),
                 'escape_event_episodes':sum(bool(r.get('escape_events')) for c in conditions for r in records[v,c])} for v,a in values.items()}
    gate=all(not regressions[ref] and variants['v13']['success']>=variants[ref]['success'] for ref in rescues)
    out={'stage':'confirmation','variants':variants,'unique_starts':60,'new_executions':1440,'statistics':statistics,
         'conditions':per_condition,'rescues':rescues,'regressions':regressions,'adoption_gate_passed':gate,
         'positive_primary_ci':statistics['v13_minus_v6']['ci95_percent'][0]>0,
         'inference':'Primary v13-v6, secondary v13-v12. Paired-start percentile bootstrap, 20000 draws, seed2026101613. Eight fixed conditions per start and three fixed Full training seeds. Pointwise intervals, no multiplicity correction, not arbitrary retraining uncertainty. Zero interval with no discordance does not prove equivalence. Do not compare v5 from another batch.'}
    write(RUN/'analysis/confirmation.json',out)
    with (RUN/'analysis/confirmation_pairs.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=export[0]);w.writeheader();w.writerows(export)
    print(json.dumps({k:out[k] for k in ['variants','statistics','rescues','regressions','adoption_gate_passed']},indent=2))
