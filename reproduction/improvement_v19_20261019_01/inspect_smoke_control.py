"""Summarize a completed frozen v19 smoke stage without new simulation.

Matched profiles and the registered component ablations are reported
descriptively. Saved-input controller/physics replays remain separate receipts;
this script reads their original observations, commands, events and outcomes.
It never treats static candidates or retrospective diagnosis as new samples.
"""
from collections import Counter
from pathlib import Path
import argparse,hashlib,json
import numpy as np

RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
ORDER=['v17','v18','budget','transition','candidate','settling','ab','v19']
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
        if info.get('planning_kind') not in ['v18_descent_handoff','v19_descent_transition']:continue
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
                         'executed_action':row['executed_action'], 'transition_window':receipt.get('transition19')})
    assert len(handoffs)==len(events)
    for event in record.get('transition19_events',[]):
        if event['event']=='windowed_descent_control':
            meta=event['transition19'];assert meta['window_active']==(1<=meta['descent_controls']<=3)
            np.testing.assert_array_equal(event['actual_submitted_action'],rows[event['step']-1]['submitted_action'])
    recenter=[r for r in rows if r['recovery'].get('planning_kind')=='v14_recenter' or r['recovery']['mode']=='PATH_RECENTER']
    recenter_events=[e for e in record.get('clearance14_events',[]) if str(e.get('event','')).startswith('recenter_')]
    last_info=rows[-1]['recovery'];first=descents[0] if descents else None
    first_close=next((e for e in transitions if e['to']=='CLOSE' and (first is None or e['step']>=first['entry_stored_clock'])),None)
    milestones=[e for e in transitions if e['to'] in AXIS_MILESTONES]
    first_phase={phase:next((e['step'] for e in milestones if e['to']==phase),None) for phase in ['CARRY','PLACE','RELEASE']}
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
            'first_carry_clock':first_phase['CARRY'],'first_place_clock':first_phase['PLACE'],'first_release_clock':first_phase['RELEASE'],
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
            'transition_window_active_controls':sum(bool(h['transition_window'] and h['transition_window']['window_active']) for h in handoffs),
            'transition_window_inactive_controls':sum(bool(h['transition_window'] and not h['transition_window']['window_active']) for h in handoffs),
            'handoff_controls':handoffs,
            'original_total_policy_and_supervisor_ms':{'p95':float(np.percentile(all_latency,95)),'max':max(all_latency),'above50_count':sum(v>50 for v in all_latency)}}

def summarize_settling(record,rows):
    """Read actual held observations and commands; never invent future readiness."""
    events=record.get('settling19_events',[])
    triggered=[event for event in events if event['event']=='held_integral_brake']
    for event in triggered:
        row=rows[event['step']-1]
        np.testing.assert_array_equal(event['actual_submitted_action'],row['submitted_action'])
        if event['applied']:
            assert event['accepted']
            np.testing.assert_array_equal(event['submitted_action'],row['submitted_action'])
        assert event['settling19']['control_heuristic_only']
    held=[];segments=[];active=None;last_key=None;consecutive_ready=0
    for row in rows:
        info=row['recovery'];receipt=info.get('mixed_pose',{})
        update=receipt.get('state_update')
        if not (receipt.get('held') and update):
            active=None;last_key=None;consecutive_ready=0
            continue
        goal=np.asarray(update['goal']);x=np.asarray(row['state_before'])
        motion=np.asarray(receipt['observed_translation_per_step_m'])
        error=goal-x[:3]
        key=(update['phase'],tuple(goal),tuple(np.asarray(update['rotation']).flat))
        if key!=last_key:
            active={'phase':update['phase'],'first_control':row['step'],'last_control':row['step'],
                    'goal_m':update['goal'],'rotation':update['rotation'],'controls':0,
                    'ready_control_spans':[],'maximum_consecutive_ready':0,'integral_pause_controls':0,
                    'state_reset_reasons':{},'minimum_position_error_m':float('inf')}
            segments.append(active);last_key=key;consecutive_ready=0
        submitted_match=bool(receipt.get('accepted') and np.array_equal(receipt.get('submitted_action'),row['submitted_action']))
        ready=bool(submitted_match and info.get('stable_hold') and receipt['position_error_m']<.009
                   and receipt['orientation_error_rad']<.08)
        consecutive_ready=consecutive_ready+1 if ready else 0
        pause=receipt.get('settling19')
        if pause:
            expected=((error*motion>0)&(error*(error-2*motion)<=0)).tolist()
            assert expected==pause['integral_brake_axes']
            assert np.asarray(receipt['position_bias_m'])[np.asarray(expected)].tolist()==[0.]*sum(expected)
        item={'control_step':row['step'],'phase':update['phase'],'command_mode':info['mode'],
              'mode_after':info.get('next_mode'),'accepted':receipt.get('accepted'),
              'actual_matches_certificate':submitted_match,'stable_hold':bool(info.get('stable_hold')),
              'strict_arrival_predicate':ready,'consecutive_strict_arrival':consecutive_ready,
              'goal_m':update['goal'],'observed_position_m':x[:3].tolist(),'error_m':error.tolist(),
              'position_error_m':receipt['position_error_m'],'orientation_error_rad':receipt['orientation_error_rad'],
              'observed_motion_m':motion.tolist(),'bias_m':receipt['position_bias_m'],
              'reset_reason':receipt.get('state_reset_reason'),'integral_pause':pause,
              'geometry_work':receipt['work'],'box_margin_m':receipt.get('box_margin_m'),
              'carried_can_margin_m':receipt.get('can_margin_m'),
              'submitted_action':row['submitted_action'],'fifo_before':row['queue_before'],
              'executed_before_noise':row['executed_action_before_noise'],
              'executed_action':row['executed_action']}
        held.append(item);active['last_control']=row['step'];active['controls']+=1
        active['maximum_consecutive_ready']=max(active['maximum_consecutive_ready'],consecutive_ready)
        active['integral_pause_controls']+=bool(pause)
        reason=str(receipt.get('state_reset_reason'))
        active['state_reset_reasons'][reason]=active['state_reset_reasons'].get(reason,0)+1
        active['minimum_position_error_m']=min(active['minimum_position_error_m'],receipt['position_error_m'])
        active['last_position_error_m']=receipt['position_error_m']
        active['last_angle_error_rad']=receipt['orientation_error_rad']
        active['last_consecutive_ready']=consecutive_ready
        if ready:
            spans=active['ready_control_spans']
            if spans and spans[-1]['last_control']==row['step']-1:
                spans[-1]['last_control']=row['step'];spans[-1]['controls']+=1
            else:spans.append({'first_control':row['step'],'last_control':row['step'],'controls':1})
    return {'held_pose_controls':held,'held_pose_segments':segments,
            'settling_triggered_events':len(triggered),'settling_applied_events':sum(e['applied'] for e in triggered),
            'settling_rejected_or_replaced_events':sum(not e['applied'] for e in triggered),
            'settling_events':events,
            'arrival_count_scope':'Reconstructed original strict observed predicate on actually submitted accepted held commands, separated by exact phase/goal. This is not a new readiness decision or guaranteed next transition.'}


def first_difference(rows,other,key):
    return next((a['step'] for a,b in zip(rows,other) if not np.array_equal(a[key],b[key])),None)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',default='smoke_a');parser.add_argument('--name',default=None);args=parser.parse_args()
    stage=RUN/args.stage;assert args.stage.startswith('smoke_')
    completed=read(stage/'completed.json');assert completed['source_unchanged'] and completed['episodes']==72
    started=read(stage/'started.json');jobs=read(stage/'jobs.json')
    assert sha(stage/'jobs.json')==started['jobs_sha256'] and set(j['version'] for j in jobs)==set(ORDER)
    for path,digest in started['source_sha256'].items():
        frozen=stage/'source'/Path(path).relative_to(RUN.relative_to(ROOT));assert sha(frozen)==digest,path
    for path,digest in started['dependency_sha256'].items():assert sha(ROOT/path)==digest,path
    output=RUN/'analysis'/((args.name or args.stage+'_control_diagnosis')+'.json');assert not output.exists()
    sources=[Path(__file__),stage/'completed.json',stage/'started.json',stage/'jobs.json']
    by_key={};all_cases=[];traces={};starts=set()
    for job in jobs:
        result=stage/job['id']/'result.json';trace=stage/job['id']/'trace.jsonl';saved=read(result)
        assert saved['status']=='complete' and saved['job']==job
        assert len(saved['records'])==len(job['demos'])==1
        record=saved['records'][0];assert record['demo']==job['demos'][0]
        rows=[json.loads(line) for line in trace.read_text(encoding='utf8').splitlines()]
        case=summarize(job,record,rows);case.update(summarize_settling(record,rows));key=profile_identity(job,record['demo'])
        assert job['version'] not in by_key.setdefault(key,{})
        by_key[key][job['version']]=case;all_cases.append(case);traces[job['id']]=rows
        sources.extend([result,trace]);starts.add((job.get('dataset'),record['demo']))
    assert len(all_cases)==72 and len(by_key)==9 and len(starts)==8
    comparisons=[]
    for key,cases in by_key.items():
        assert set(cases)==set(ORDER)
        for variant,reference,meaning in [('transition','v18','A only on full v18'),
                ('candidate','v18','B only on full v18'),('settling','v18','C only on full v18'),
                ('ab','candidate','A with B enabled'),('ab','transition','B with A enabled'),
                ('v19','ab','C with A and B enabled'),('v19','v17','actual historical architecture reference'),
                ('v19','budget','actual old protection success reference')]:
            a,b=cases[variant],cases[reference];ar,br=traces[a['job']],traces[b['job']]
            delta={}
            for metric in ['first_descend_entry_clock','first_close_clock','first_descend_to_close_controls','recenter_controls','first_carry_clock','first_place_clock','first_release_clock','steps']:
                delta[metric]=a[metric]-b[metric] if a[metric] is not None and b[metric] is not None else None
            comparisons.append({'profile':list(key),'variant':variant,'reference':reference,'comparison_scope':meaning,
                                'variant_success':a['success'],'reference_success':b['success'],
                                'rescued':a['success'] and not b['success'],'regressed':b['success'] and not a['success'],
                                'descriptive_difference':delta,
                                'compared_trace_prefix_controls':min(len(ar),len(br)),
                                'first_observation_difference':first_difference(ar,br,'state_before'),
                                'first_submitted_action_difference':first_difference(ar,br,'submitted_action')})
    summary={'passed':True,'stage':args.stage,'selected_evaluation_executions':72,'registered_profiles':9,'unique_start_identities':8,
             'new_physical_episodes':0,'new_evaluation_samples':0,'saved_controller_replay_performed':False,
             'scope':'Read-only extraction of completed original trace observations/events/actions, exact event-to-action matching, and paired component descriptions. No physics or new controller replay.',
             'cases':all_cases,'paired_component_descriptions':comparisons,
             'source_sha256':{rel(p):sha(p) for p in sources},
             'limitations':['Eight-centimeter goal jumps also occurred in successful old budget trajectories; a jump alone is not a sufficient causal explanation.',
                            'Use only the registered A/B/C/AB/full contrasts. AC and BC are absent, so this is not a complete three-factor interaction design. Certificate acceptance is not task success.',
                            'Stored event clocks and actual submitted control numbers are retained separately. Recenter checks may be emitted before the shared clock increments.',
                            'A refused pulse intent is unknown unless the receipt records it; zero submitted grip does not prove no pulse was attempted.',
                            'Budget is a historical local reference and does not enable all current held-path protections.',
                            'Static, action-replay, physical-replay and this retrospective trace analysis do not add statistical samples.']}
    with output.open('x',encoding='utf8') as f:json.dump(finite(summary),f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({'passed':True,'executions':72,'profiles':9,'new_physical_episodes':0,'output':rel(output)}))

if __name__=='__main__':main()
