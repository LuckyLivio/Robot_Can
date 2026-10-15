"""Describe paired residual failures without labeling unmeasured contacts as collisions."""
import argparse,json
from collections import Counter
from setup_study import ROOT,RUN,write
def main(stage):
    jobs=json.loads((RUN/stage/'jobs.json').read_text());groups={};seen=set()
    work=[(j,RUN/stage/j['id']) for j in jobs]
    if stage.startswith('dev'):
        for j in jobs:
            if j['baseline_result'] not in seen:
                seen.add(j['baseline_result']);work.append(({**j,'version':'v2','id':j['id'].split('_',1)[-1]},(ROOT/j['baseline_result']).parent))
    for j,folder in work:
        payload=json.loads((folder/'result.json').read_text());rows=payload['records'];last={}
        for line in (folder/'trace.jsonl').open():
            r=json.loads(line);last[r['demo']]=r
        group=groups.setdefault(j['version'],{'episodes':0,'successes':0,'failures':[],'switch_cases':[],'event_reasons':Counter(),'final_failure_modes':Counter()})
        for r in rows:
            group['episodes']+=1;group['successes']+=r['success'];group['event_reasons'].update(e['reason'] for e in r['events'])
            t=last[r['demo']];x=t['state_after'];mode=t['recovery'].get('next_mode',t['recovery']['mode'])
            record={'job':j['id'],'demo':r['demo'],'success':r['success'],'steps':r['steps'],'final_mode':mode,'final_object_position':x[16:19],
                'ever_stable':r['stable_hold_observed'],'verified_regrasps':r['verified_regrasps'],'events':r['events']}
            if any(e['reason']=='alignment_stalled_switch_equivalent' for e in r['events']):group['switch_cases'].append(record)
            if not r['success']:
                group['failures'].append(record);group['final_failure_modes'][mode]+=1
    write(RUN/f'diagnosis_{stage}.json',{'stage':stage,'groups':groups,'limitation':'Phase labels identify observed termination state, not a proven physical failure cause. Consult physics probes for contact claims.'})
    print(json.dumps({v:{k:g[k] for k in ['episodes','successes','final_failure_modes']} for v,g in groups.items()},indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();main(a.stage)
