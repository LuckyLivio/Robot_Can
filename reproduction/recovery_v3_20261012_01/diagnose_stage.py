"""Post-hoc failures, regressions, and intervention costs; never changes the method."""
import argparse,json
from collections import Counter
import numpy as np
from scipy.spatial.transform import Rotation
from setup_study import ROOT,RUN,write


def main(stage):
    folder=RUN/stage;jobs=json.loads((folder/'jobs.json').read_text());records={}
    for job in jobs:
        records[(job['version'],job['method'],job['seed'],job['noise'])]=json.loads((folder/job['id']/'result.json').read_text())['records']
        if stage.startswith('dev'):
            records[('v2',job['method'],job['seed'],job['noise'])]=json.loads((ROOT/job['baseline_result']).read_text())['records']
            records[('disabled',job['method'],job['seed'],job['noise'])]=json.loads((ROOT/job['original_baseline_result']).read_text())['records']
    failures=[];regressions=[];rescues=[];first_reasons=Counter();summary=[]
    for job in jobs:
        if job['version']!='v3':continue
        key=(job['method'],job['seed'],job['noise']);new=records[('v3',*key)];old=records[('v2',*key)];original=records[('disabled',*key)]
        final={}
        for line in (folder/job['id']/'trace.jsonl').open():
            r=json.loads(line);final[r['demo']]=r
        normal_cost=[];extra_interventions=[];losses=[]
        for a,b,c in zip(old,new,original):
            assert a['demo']==b['demo']==c['demo']
            if b['events']:first_reasons[b['events'][0]['reason']]+=1
            if any(e['reason']=='observed_grasp_loss' for e in b['events']):losses.append(b)
            if c['success'] and b['attempts']>0:
                extra_interventions.append({'demo':b['demo'],'v3_success':b['success'],'original_steps':c['steps'],'v3_steps':b['steps']})
            if a['success'] and b['success']:normal_cost.append(b['steps']-a['steps'])
            paired={'job':job['id'],'demo':b['demo'],'v2_steps':a['steps'],'v3_steps':b['steps'],'original_success':c['success']}
            if not a['success'] and b['success']:rescues.append(paired)
            if a['success'] and not b['success']:regressions.append(paired)
            if not b['success']:
                last=final[b['demo']];x=np.array(last['state_after']);axis=Rotation.from_quat(x[19:23]).as_matrix()[:,2]
                mode=last['recovery']['mode'];category='outside_workspace' if x[18]<.76 else 'no_intervention' if not b['attempts'] else 'retries_exhausted' if mode=='EXHAUSTED' else 'budget_incomplete'
                failures.append({'job':job['id'],'demo':b['demo'],'v2_success':a['success'],'original_success':c['success'],
                    'attempts':b['attempts'],'final_mode':mode,'category':category,'object_position':x[16:19].tolist(),
                    'object_axis_tilt_deg':float(np.degrees(np.arccos(np.clip(abs(axis[2]),0,1)))),
                    'eef_object_distance_m':float(np.linalg.norm(x[:3]-x[16:19])),
                    'first_event':b['events'][0] if b['events'] else None,'last_events':b['events'][-4:]})
        summary.append({'job':job['id'],'loss_trigger_episodes':len(losses),'loss_trigger_successes':sum(b['success'] for b in losses),
            'both_success_steps_delta_mean':float(np.mean(normal_cost)) if normal_cost else None,
            'original_successes_intervened':extra_interventions})
    report={'stage':stage,'failures':failures,'failure_categories':dict(Counter(f['category'] for f in failures)),
            'regressions_vs_v2':regressions,'rescues_vs_v2':rescues,'first_intervention_reasons':dict(first_reasons),'intervention_metrics':summary}
    write(RUN/f'diagnosis_{stage}.json',report);print(json.dumps({'stage':stage,'failures':len(failures),'categories':report['failure_categories'],
                'regressions':len(regressions),'rescues':len(rescues),'first_intervention_reasons':dict(first_reasons)},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();main(a.stage)
