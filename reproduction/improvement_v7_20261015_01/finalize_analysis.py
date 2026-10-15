"""Summarize the completed diagnostic pilot without launching experiments."""
from pathlib import Path
from collections import Counter
import csv,json,hashlib
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]

def write(path,data):
    with path.open('x',encoding='utf8') as f:json.dump(data,f,indent=2,ensure_ascii=False)

def main():
    stage=RUN/'pilot_b';jobs=json.loads((stage/'jobs.json').read_text());pairs={};details={}
    for v in ['v6','pose','unknown','v7']:
        phases=Counter();events=Counter();replans=Counter();touched=[]
        for j in jobs:
            if j['version']!=v:continue
            d=json.loads((stage/j['id']/'result.json').read_text());assert d['status']=='complete'
            for r in d['records']:
                key=(j['id'].split('_',1)[1],r['demo']);pairs.setdefault(key,{})[v]=r
                phases.update(r['phases']);replans[r.get('pose_replans',0)]+=1
                transitions=[e for e in r['events'] if e['to'].startswith('POSE')]
                for e in transitions:events[e['to']+':'+e['reason']]+=1
                if transitions:touched.append({'job':j['id'],'demo':r['demo'],'success':r['success'],'replans':r.get('pose_replans',0)})
        details[v]={'phases':dict(phases),'new_events':dict(events),'replans_per_episode':dict(replans),'affected':touched}
    write(RUN/'analysis/pilot_b_mechanisms.json',details)
    with (RUN/'analysis/pilot_b_pairs.csv').open('x',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f);writer.writerow(['condition','demo','v6_success','pose_success','unknown_success','v7_success','v6_steps','pose_steps','unknown_steps','v7_steps'])
        for (condition,demo),row in sorted(pairs.items()):
            writer.writerow([condition,demo]+[int(row[v]['success']) for v in ['v6','pose','unknown','v7']]+[row[v]['steps'] for v in ['v6','pose','unknown','v7']])
    baseline_steps=baseline_episodes=0
    for j in jobs:
        if j['version']!='v6':continue
        prior=ROOT/'reproduction/improvement_v6_20261015_01/pilot_b'/j['id']
        old=json.loads((prior/'result.json').read_text());new=json.loads((stage/j['id']/'result.json').read_text())
        assert old['job']==j
        for a,b in zip(old['records'],new['records']):
            for k in ['demo','success','steps','phases','events','guard_events']:assert a[k]==b[k],(j['id'],k)
            baseline_episodes+=1
        old_lines=(prior/'trace.jsonl').read_text().splitlines();new_lines=(stage/j['id']/'trace.jsonl').read_text().splitlines()
        assert len(old_lines)==len(new_lines)
        for aa,bb in zip(old_lines,new_lines):
            a=json.loads(aa);b=json.loads(bb)
            for k in a:
                if k!='decision_ms':assert a[k]==b[k],(j['id'],a['step'],k)
            baseline_steps+=1
    partial={'completed_jobs':0,'completed_episodes':0,'incomplete_jobs':0,'fully_completed_batch':False}
    for p in (RUN/'pilot_a').glob('*/result.json'):
        d=json.loads(p.read_text())
        partial['completed_jobs' if d['status']=='complete' else 'incomplete_jobs']+=1
        partial['completed_episodes']+=len(d['records'])
    gate=json.loads((RUN/'analysis/pilot_b.json').read_text())
    verify=json.loads((RUN/'analysis/pilot_b_verification.json').read_text());physics=json.loads((RUN/'analysis/pilot_b_physics.json').read_text())
    receipt={'completed_diagnostic_episodes':148,'pilot_a_technical_attempt':partial,
             'v6_baseline_matches_prior_exactly':{'episodes':baseline_episodes,'control_steps':baseline_steps},
             'pilot_gate_passed':False,'reason':'unknown and combined each regress on one protected v6 success; no rescues',
             'dev_240_launched':False,'promoted':False,'training_performed':False,'paper_written':False,
             'recorded_input_verification':verify,'physical_replay_verification':physics,
             'outcomes':{v:{k:d[k] for k in ['success','episodes','rescues','regressions']} for v,d in gate['variants'].items()},
             'frontend_modified':False,'old_weights_and_results_modified':False}
    write(RUN/'analysis/final_receipt.json',receipt)
    print(json.dumps({k:receipt[k] for k in ['completed_diagnostic_episodes','pilot_a_technical_attempt','v6_baseline_matches_prior_exactly','pilot_gate_passed','dev_240_launched']}))
if __name__=='__main__':main()
