"""Paired frozen development outcomes, no new independent-confirmation claim."""
from pathlib import Path
import csv,hashlib,json
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    stage=RUN/'dev_a';assert (stage/'completed.json').exists();freeze=json.loads((RUN/'protocols/development_freeze.json').read_text())
    assert all(digest(ROOT/p)==s for p,s in freeze['source_sha256'].items())
    pairs=[];groups=[];activation=[];times=[]
    for j in json.loads((stage/'jobs.json').read_text()):
        new=json.loads((stage/j['id']/'result.json').read_text());old=json.loads((ROOT/j['baseline_result_v6']).read_text())
        assert new['status']==old['status']=='complete';b={r['demo']:r for r in old['records']}
        assert set(b)==set(j['demos']) and old['job']['method']==j['method'] and old['job']['seed']==j['seed'] and old['job']['noise']==j['noise']
        for r in new['records']:
            base=b[r['demo']];pairs.append({'condition':j['id'].split('_',1)[1],'demo':r['demo'],'v6_success':base['success'],'v11_success':r['success'],'v6_steps':base['steps'],'v11_steps':r['steps'],'v11_verified_regrasps':r['verified_regrasps']})
            if r.get('edge_events'):activation.append({'condition':j['id'],'demo':r['demo'],'success':r['success'],'events':r['edge_events']})
        groups.append({'condition':j['id'].split('_',1)[1],'v6_success':sum(r['success'] for r in old['records']),'v11_success':sum(r['success'] for r in new['records']),'episodes':len(new['records'])})
        for r in map(json.loads,(stage/j['id']/'trace.jsonl').open()):times.append(r['total_policy_and_supervisor_ms'])
    assert len(pairs)==240
    regressions=[p for p in pairs if p['v6_success'] and not p['v11_success']];rescues=[p for p in pairs if not p['v6_success'] and p['v11_success']]
    result={'complete':True,'stage':'dev_a','v6_success':sum(p['v6_success'] for p in pairs),'v11_success':sum(p['v11_success'] for p in pairs),'episodes':240,'regressions':regressions,'rescues':rescues,'groups':groups,'edge_activated_episodes':len(activation),'edge_activations':activation,'source_freeze_verified':True,
        'timing_ms':{'scope':'BC+WM selection+supervisor, excludes physics/render/logging; four workers, replay rendering overlapped part of the run','max':max(times),'p99':float(np.percentile(times,99)),'over50':sum(t>50 for t in times),'steps':len(times)}}
    with (RUN/'analysis/development.json').open('x') as f:json.dump(result,f,indent=2)
    with (RUN/'analysis/development_pairs.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
    print(json.dumps({k:v for k,v in result.items() if k!='edge_activations'}))
