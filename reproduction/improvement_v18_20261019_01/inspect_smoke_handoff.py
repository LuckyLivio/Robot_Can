"""Summarize a completed frozen v18 smoke stage without new simulation.

Matched profiles and the registered two-switch ablations are reported
descriptively. Saved-input controller/physics replays remain separate receipts;
this script reads their original observations, commands, events and outcomes.
It never treats static candidates or retrospective diagnosis as new samples.
"""
from collections import Counter
from pathlib import Path
import argparse,hashlib,json
import numpy as np

RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
ORDER=['v16','v17','budget','handoff','short','v18']
AXIS_MILESTONES=['DESCEND','CLOSE','TEST_LIFT','LIFT','CARRY','PLACE','RELEASE','EXHAUSTED','POSE_WAIT']

def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def finite(v):
    if isinstance(v,dict):return {str(k):finite(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)):return [finite(x) for x in v]
    if isinstance(v,(bool,np.bool_)):return bool(v)
    if isinstance(v,(int,np.integer)):return int(v)
    if isinstance(v,(float,np.floating)):return float(v) if np.isfinite(v) else None
    return v

def suffix(job):
    prefix=job['version']+'_';assert job['id'].startswith(prefix)
    return job['id'][len(prefix):]

def profile_identity(job,demo):
    return (suffix(job),job.get('dataset'),demo,job['method'],job.get('seed'),job['noise'],
            job.get('fault'),job.get('fault_policy'),job.get('force_recovery_at'),job.get('comparison_profile','standard'))

def consecutive(items):
    spans=[]
    for item in items:
        if not spans or item['step']!=spans[-1][-1]['step']+1:spans.append([])
        spans[-1].append(item)
    return [{'first_control':group[0]['step'],'last_control':group[-1]['step'],'controls':len(group),
             'command_modes':dict(Counter(row['recovery']['mode'] for row in group))} for group in spans]

def summarize(job,record,rows):
    assert record['steps']==len(rows) and record['success']==rows[-1]['success_after']
    assert [r['step'] for r in rows]==list(range(1,len(rows)+1))
    transitions=record['events'];descents=[]
    for index,event in enumerate(transitions):
        if event['to']!='DESCEND' or event['from']=='DESCEND':continue
        ending=next((e for e in transitions[index+1:] if e['from']=='DESCEND' and e['to']!='DESCEND'),None)
        end=ending['step'] if ending else record['steps']
        segment=[r for r in rows if event['step']<r['step']<=end]
        descents.append({'entry_stored_clock':event['step'],'entry_reason':event['reason'],'attempt':event['attempt'],
                         'exit_stored_clock':None if ending is None else ending['step'],
                         'exit_mode':None if ending is None else ending['to'],
                         'exit_reason':None if ending is None else ending['reason'],
                         'controls_in_stored_clock_interval':len(segment),'command_modes':dict(Counter(r['recovery']['mode'] for r in segment)),
                         'end_actual_success':rows[end-1]['success_after'],
                         'first_submitted_control':segment[0]['step'] if segment else None,
                         'first_command':segment[0]['submitted_action'] if segment else None,
                         'first_fifo_before':segment[0]['queue_before'] if segment else None,
                         'last_command':segment[-1]['submitted_action'] if segment else None})
    handoffs=[]
    events=[e for e in record.get('handoff18_events',[]) if e['event']=='descent_handoff_control']
    assert len({e['step'] for e in events})==len(events)
    by_step={e['step']:e for e in events}
    for row in rows:
        info=row['recovery']
        if info.get('planning_kind')!='v18_descent_handoff':continue
        event=by_step[row['step']];receipt=info['mixed_pose']
        assert event['accepted']==receipt['accepted'] and event['applied']==info['handoff18_applied']
        np.testing.assert_array_equal(event['actual_submitted_action'],row['submitted_action'])
        if info['handoff18_applied']:
            assert receipt['accepted']
            np.testing.assert_array_equal(receipt['submitted_action'],row['submitted_action'])
        trials=receipt.get('trials',[])
        requested_pulses=[t.get('grip_command') for t in trials if t.get('grip_command') is not None]
        pulse_known=bool(requested_pulses or 'grip_command' in receipt)
        handoffs.append({'control_step':row['step'],'command_mode':info['mode'],'mode_before':info.get('mode_before'),
                         'mode_after':info.get('next_mode'),'accepted':receipt['accepted'],'actually_applied':info['handoff18_applied'],
                         'reason':receipt['reason'],'joint_margin_rad':event['joint_margin_rad'],
                         'actual_grip_command':row['submitted_action'][6],'attempted_pulse_observable_in_receipt':pulse_known,
                         'attempted_pulse_nonzero':bool(receipt.get('grip_command',0) or any(requested_pulses)) if pulse_known else None,
                         'aperture_motion':receipt.get('aperture_motion'),
                         'position_error_m':receipt.get('position_error_m'),'orientation_error_rad':receipt.get('orientation_error_rad'),
                         'box_margin_m':receipt.get('box_margin_m'),'can_margin_m':receipt.get('can_margin_m'),
                         'translation_change_m':receipt.get('translation_change_m'),'rotation_change_rad':receipt.get('rotation_change_rad'),
                         'geometry_work':receipt['work'],'goal_m':event['goal'],
                         'observed_state':row['state_before'],'submitted_action':row['submitted_action'],
                         'fifo_before':row['queue_before'],'executed_before_noise':row['executed_action_before_noise'],
                         'executed_action':row['executed_action']})
    assert len(handoffs)==len(events)
    recenter=[r for r in rows if r['recovery'].get('planning_kind')=='v14_recenter' or r['recovery']['mode']=='PATH_RECENTER']
    recenter_events=[e for e in record.get('clearance14_events',[]) if str(e.get('event','')).startswith('recenter_')]
    last_info=rows[-1]['recovery'];first=descents[0] if descents else None
    first_close=next((e for e in transitions if e['to']=='CLOSE' and (first is None or e['step']>=first['entry_stored_clock'])),None)
    milestones=[e for e in transitions if e['to'] in AXIS_MILESTONES]
    all_latency=[r['total_policy_and_supervisor_ms'] for r in rows]
    return {'job':job['id'],'version':job['version'],'condition':suffix(job),'demo':record['demo'],
            'comparison_profile':job.get('comparison_profile','standard'),'success':record['success'],'steps':record['steps'],
            'remaining_budget':400-record['steps'],'final_command_mode':last_info['mode'],'final_next_mode':last_info.get('next_mode'),
            'first_descend_entry_clock':None if first is None else first['entry_stored_clock'],
            'first_descend_exit_clock':None if first is None else first['exit_stored_clock'],
            'first_descend_exit_mode':None if first is None else first['exit_mode'],
            'first_close_clock':None if first_close is None else first_close['step'],
            'first_close_attempt':None if first_close is None else first_close['attempt'],
            'first_close_in_first_descent_attempt':bool(first and first_close and first_close['attempt']==first['attempt']),
            'first_descend_to_close_controls':(first_close['step']-first['entry_stored_clock']) if first and first_close else None,
            'descents':descents,'subsequent_milestones':milestones,
            'recenter_start_count':sum(e.get('event')=='recenter_check' and bool(e.get('accepted')) for e in recenter_events),
            'recenter_check_count':sum(e.get('event')=='recenter_check' for e in recenter_events),
            'recenter_controls':len(recenter),'recenter_control_spans':consecutive(recenter),'recenter_events':recenter_events,
            'handoff_certified':sum(h['accepted'] for h in handoffs),'handoff_applied':sum(h['actually_applied'] for h in handoffs),
            'handoff_not_applied':sum(not h['actually_applied'] for h in handoffs),
            'handoff_joint_refusals':sum(h['reason']=='descent_joint_margin_guard' for h in handoffs),
            'handoff_geometry_or_input_refusals':sum(not h['accepted'] and h['reason']!='descent_joint_margin_guard' for h in handoffs),
            'pulse_controls_submitted':sum(h['actual_grip_command']!=0 for h in handoffs),
            'rejected_pulse_observed':sum(not h['accepted'] and h['attempted_pulse_nonzero'] is True for h in handoffs),
            'rejected_pulse_intent_not_recorded':sum(not h['accepted'] and not h['attempted_pulse_observable_in_receipt'] for h in handoffs),
            'guarded_close_preventions':[e for e in record.get('handoff18_events',[]) if e['event']=='rejected_descent_cannot_close'],
            'handoff_controls':handoffs,
            'original_total_policy_and_supervisor_ms':{'p95':float(np.percentile(all_latency,95)),'max':max(all_latency),'above50_count':sum(v>50 for v in all_latency)}}

def first_difference(rows,other,key):
    return next((a['step'] for a,b in zip(rows,other) if not np.array_equal(a[key],b[key])),None)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',default='smoke_a');parser.add_argument('--name',default=None);args=parser.parse_args()
    stage=RUN/args.stage;assert args.stage.startswith('smoke_')
    completed=read(stage/'completed.json');assert completed['source_unchanged'] and completed['episodes']==54
    started=read(stage/'started.json');jobs=read(stage/'jobs.json')
    assert sha(stage/'jobs.json')==started['jobs_sha256'] and set(j['version'] for j in jobs)==set(ORDER)
    for path,digest in started['source_sha256'].items():
        frozen=stage/'source'/Path(path).relative_to(RUN.relative_to(ROOT));assert sha(frozen)==digest,path
    for path,digest in started['dependency_sha256'].items():assert sha(ROOT/path)==digest,path
    output=RUN/'analysis'/((args.name or args.stage+'_handoff_diagnosis')+'.json');assert not output.exists()
    sources=[Path(__file__),stage/'completed.json',stage/'started.json',stage/'jobs.json']
    by_key={};all_cases=[];traces={};starts=set()
    for job in jobs:
        result=stage/job['id']/'result.json';trace=stage/job['id']/'trace.jsonl';saved=read(result)
        assert saved['status']=='complete' and saved['job']==job
        assert len(saved['records'])==len(job['demos'])==1
        record=saved['records'][0];assert record['demo']==job['demos'][0]
        rows=[json.loads(line) for line in trace.read_text(encoding='utf8').splitlines()]
        case=summarize(job,record,rows);key=profile_identity(job,record['demo'])
        assert job['version'] not in by_key.setdefault(key,{})
        by_key[key][job['version']]=case;all_cases.append(case);traces[job['id']]=rows
        sources.extend([result,trace]);starts.add((job.get('dataset'),record['demo']))
    assert len(all_cases)==54 and len(by_key)==9 and len(starts)==8
    comparisons=[]
    for key,cases in by_key.items():
        assert set(cases)==set(ORDER)
        for variant,reference,meaning in [('handoff','v17','handoff only'),('short','v17','short route only'),
                                          ('v18','short','handoff with short route enabled'),('v18','handoff','short route with handoff enabled'),
                                          ('v18','budget','historical success reference with different protection')]:
            a,b=cases[variant],cases[reference];ar,br=traces[a['job']],traces[b['job']]
            delta={}
            for metric in ['first_descend_entry_clock','first_close_clock','first_descend_to_close_controls','recenter_controls','steps']:
                delta[metric]=a[metric]-b[metric] if a[metric] is not None and b[metric] is not None else None
            comparisons.append({'profile':list(key),'variant':variant,'reference':reference,'comparison_scope':meaning,
                                'variant_success':a['success'],'reference_success':b['success'],
                                'rescued':a['success'] and not b['success'],'regressed':b['success'] and not a['success'],
                                'descriptive_difference':delta,
                                'compared_trace_prefix_controls':min(len(ar),len(br)),
                                'first_observation_difference':first_difference(ar,br,'state_before'),
                                'first_submitted_action_difference':first_difference(ar,br,'submitted_action')})
    summary={'passed':True,'stage':args.stage,'selected_evaluation_executions':54,'registered_profiles':9,'unique_start_identities':8,
             'new_physical_episodes':0,'new_evaluation_samples':0,'saved_controller_replay_performed':False,
             'scope':'Read-only extraction of completed original trace observations/events/actions, exact event-to-action matching, and paired component descriptions. No physics or new controller replay.',
             'cases':all_cases,'paired_component_descriptions':comparisons,
             'source_sha256':{rel(p):sha(p) for p in sources},
             'limitations':['Eight-centimeter goal jumps also occurred in successful old budget trajectories; a jump alone is not a sufficient causal explanation.',
                            'Use registered handoff/short/full ablations to attribute changes; elapsed steps and certificate acceptance are not task success.',
                            'Stored event clocks and actual submitted control numbers are retained separately. Recenter checks may be emitted before the shared clock increments.',
                            'A refused pulse intent is unknown unless the receipt records it; zero submitted grip does not prove no pulse was attempted.',
                            'Budget is a historical local reference and does not enable all current held-path protections.',
                            'Static, action-replay, physical-replay and this retrospective trace analysis do not add statistical samples.']}
    with output.open('x',encoding='utf8') as f:json.dump(finite(summary),f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({'passed':True,'executions':54,'profiles':9,'new_physical_episodes':0,'output':rel(output)}))

if __name__=='__main__':main()
