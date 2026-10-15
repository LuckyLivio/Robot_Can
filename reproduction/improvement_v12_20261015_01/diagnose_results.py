"""Post-hoc descriptive diagnostics, never inputs to controller decisions."""
from pathlib import Path
import argparse,json
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def trace(path):
    result={}
    for row in map(json.loads,path.open()):result.setdefault(row['demo'],[]).append(row)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();stage=RUN/a.stage
    jobs=json.loads((stage/'jobs.json').read_text());timing={};failures=[];events=[];same=0;changed=[];total=0
    for j in jobs:
        rr=json.loads((stage/j['id']/'result.json').read_text())['records'];tt=trace(stage/j['id']/'trace.jsonl');key=j['version']
        timing.setdefault(key,[])
        for r in rr:
            rows=tt[r['demo']];timing[key].extend(x['total_policy_and_supervisor_ms'] for x in rows)
            if not r['success']:
                x=np.array(rows[-1]['state_after']);failures.append({'job':j['id'],'demo':r['demo'],'steps':r['steps'],
                     'last_mode':rows[-1]['recovery']['mode'],'goal_xy_m':float(np.linalg.norm(x[16:18]-[.1975,.4025])),
                     'object_z_m':float(x[18]),'ever_stable_hold':r['stable_hold_observed'],'attempts':r['attempts'],
                     'last_events':r['events'][-5:],'wait_hold_events':r.get('wait_hold_events',[])})
            for e in r.get('wait_hold_events',[]):events.append({'job':j['id'],'demo':r['demo'],'success':r['success'],**e})
        if key=='v12' and a.stage in ['pilot_a','dev_a']:
            suffix=j['id'].split('_',1)[1]
            ref=stage/('v11_'+suffix)/'trace.jsonl' if a.stage=='pilot_a' else ROOT/f'reproduction/improvement_v11_20261015_01/dev_a/v11_{suffix}/trace.jsonl'
            old=trace(ref)
            for name,rows in tt.items():
                total+=1;b=old[name];equal=len(rows)==len(b) and all(np.array_equal(x['submitted_action'],y['submitted_action']) and np.array_equal(x['state_after'],y['state_after']) for x,y in zip(rows,b))
                if equal:same+=1
                else:
                    first=next((x['step'] for x,y in zip(rows,b) if not np.array_equal(x['submitted_action'],y['submitted_action']) or not np.array_equal(x['state_after'],y['state_after'])),min(len(rows),len(b))+1)
                    changed.append({'condition':suffix,'demo':name,'first_changed_step':first})
    out={'stage':a.stage,'posthoc_only':True,'failure_records':failures,'wait_hold_events':events,
         'exact_v11_trajectory_comparison':{'episodes':total,'identical':same,'changed':changed},
         'timing':{v:{'steps':len(t),'p50_ms':float(np.median(t)),'p99_ms':float(np.quantile(t,.99)),'max_ms':float(max(t)),'over_50ms':int(np.sum(np.array(t)>50))} for v,t in timing.items()},
         'timing_scope':'BC/WM plus supervisor, excludes physics/render/logging; four concurrent workers; development overlaps demonstration replay rendering. Not a hard real-time guarantee.'}
    with (RUN/'analysis'/f'{a.stage}_diagnosis.json').open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps({k:v for k,v in out.items() if k!='failure_records'},indent=2))
