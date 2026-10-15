from pathlib import Path
from collections import Counter
import csv,json,hashlib
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]

def main():
    rows=[];decisions={};stage_rows={}
    for stage in ['pilot_a','pilot_b']:
        aggregate={}
        for p in (RUN/stage).glob('*/result.json'):
            d=json.loads(p.read_text());assert d['status']=='complete';j=d['job'];v=j['version']
            for r in d['records']:
                key=(j['id'].split('_',1)[1],r['demo']);aggregate.setdefault(key,{})[v]=r
        stage_rows[stage]=aggregate
        with (RUN/'analysis'/f'{stage}_pairs.csv').open('x',newline='',encoding='utf-8-sig') as f:
            w=csv.writer(f);versions=['v6','v7','geometry','retreat','v8'];w.writerow(['condition','demo']+[v+'_success' for v in versions]+[v+'_steps' for v in versions])
            for key,rr in sorted(aggregate.items()):w.writerow(list(key)+[rr[v]['success'] for v in versions]+[rr[v]['steps'] for v in versions])
    for v in ['v6','v7','geometry','retreat','v8']:
        times=[]
        for p in (RUN/'pilot_b').glob(v+'_*/trace.jsonl'):
            grouped={}
            for line in p.open():
                r=json.loads(line);grouped.setdefault(r['demo'],[]).append(r);times.append(r['decision_ms'])
            for name,rr in grouped.items():
                xyz=np.array([rr[0]['state_before'][:3]]+[r['state_after'][:3] for r in rr]);delta=np.diff(xyz,axis=0);length=np.linalg.norm(delta,axis=1)
                product=length[1:]*length[:-1];cos=np.divide(np.sum(delta[1:]*delta[:-1],axis=1),product,out=np.ones_like(product),where=product>1e-15)
                rows.append({'version':v,'condition':p.parent.name.split('_',1)[1],'demo':name,'steps':len(rr),'success':rr[-1]['success_after'],
                             'eef_path_m':float(length.sum()),'large_reversals':int(((length[1:]>.0005)&(length[:-1]>.0005)&(cos<-.5)).sum()),
                             'eef_step_mm_p95':float(np.quantile(length*1000,.95))})
        decisions[v]={'median_ms':float(np.median(times)),'p95_ms':float(np.quantile(times,.95)),'max_ms':max(times),'over_50ms_steps':int(np.sum(np.array(times)>50))}
    with (RUN/'analysis/motion_metrics.csv').open('x',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (RUN/'analysis/decision_timing.json').open('x') as f:json.dump({'by_variant':decisions,'note':'Includes candidate scoring and recovery decisions, excludes BC inference and physics; parallel execution. Simulated 20Hz is not a real-time throughput claim.'},f,indent=2)
    for name in ['pilot_a_verification','pilot_b_verification','pilot_b_physics','mechanisms_c']:
        assert json.loads((RUN/'analysis'/f'{name}.json').read_text())['passed']
    pilot=json.loads((RUN/'analysis/pilot_b.json').read_text());assert pilot['variants']['v8']['regressions']
    receipt={'status':'小测试未达标 · 保留候选，不替换','adopted':False,'pilot_gate_passed':False,'development':None,'dev_240_launched':False,
             'completed_episodes':370,'stages':['pilot_a','pilot_b'],'reason':'Both revisions retain 30/37 versus v6 31/37; no rescues and one regression.',
             'outcomes':{v:{k:d[k] for k in ['success','episodes','rescues','regressions']} for v,d in pilot['variants'].items()},
             'replay_steps':104284,'physics_replay_episodes':20,'physics_replay_steps':6566,'protected_files_or_backups':8217,
             'weights_changed':False,'training_performed':False,'paper_written':False,
             'motion_metric_definition':'Large reversal: both adjacent EEF increments exceed 0.5mm and their angle exceeds120deg. Descriptive, not a standard safety threshold; episode lengths differ.'}
    with (RUN/'analysis/final_receipt.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2,ensure_ascii=False)
    print(json.dumps({'receipt':receipt,'decision_timing':decisions},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
