"""Summarize a completed frozen v21 smoke stage without new simulation.

Matched profiles and the registered component ablations are reported
descriptively. Saved-input controller/physics replays remain separate receipts;
this script reads their original observations, commands, events and outcomes.
It never treats static candidates or retrospective diagnosis as new samples.
"""
from collections import Counter
from pathlib import Path
import argparse,csv,hashlib,json
import numpy as np

RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
ORDER=['v19','v20','budget','recenter','place','v21']
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
        if info.get('planning_kind') not in ['v18_descent_handoff','v19_descent_transition','v20_directional_descent','v21_recenter_transition']:continue
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
                         'executed_action':row['executed_action'], 'transition_window':receipt.get('transition19'), 'directional20':receipt.get('direction20'), 'recenter21':receipt.get('handoff21')})
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
    braking_events=record.get('braking20_events',[])
    for event in braking_events:
        row=rows[event['step']-1]
        assert event['event']=='delayed_braking_control'
        np.testing.assert_array_equal(event['actual_submitted_action'],row['submitted_action'])
        if event['applied']:
            assert event['accepted']
            np.testing.assert_array_equal(event['submitted_action'],row['submitted_action'])
        assert event['braking20']['control_heuristic_only']
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
                    'ready_control_spans':[],'maximum_consecutive_ready':0,'integral_pause_controls':0,'braking20_controls':0,
                    'state_reset_reasons':{},'minimum_position_error_m':float('inf')}
            segments.append(active);last_key=key;consecutive_ready=0
        submitted_match=bool(receipt.get('accepted') and np.array_equal(receipt.get('submitted_action'),row['submitted_action']))
        ready=bool(submitted_match and info.get('stable_hold') and receipt['position_error_m']<.009
                   and receipt['orientation_error_rad']<.08)
        consecutive_ready=consecutive_ready+1 if ready else 0
        pause=receipt.get('settling19')
        braking=receipt.get('braking20')
        if pause:
            expected=((error*motion>0)&(error*(error-2*motion)<=0)).tolist()
            assert expected==pause['integral_brake_axes']
            assert np.asarray(receipt['position_bias_m'])[np.asarray(expected)].tolist()==[0.]*sum(expected)
        if braking:
            capture=((error*motion>0)&(np.abs(error)<=.009/np.sqrt(3.)+2*np.abs(motion)))
            inside=bool(np.linalg.norm(error)<.009)
            assert braking['capture_brake_axes']==capture.tolist()
            assert braking['inside_original_position_ball']==inside
            assert braking['integral_pause_axes']==(capture|inside).tolist()
            assert np.asarray(receipt['position_bias_m'])[capture].tolist()==[0.]*int(capture.sum())
        item={'control_step':row['step'],'phase':update['phase'],'command_mode':info['mode'],
              'mode_after':info.get('next_mode'),'accepted':receipt.get('accepted'),
              'actual_matches_certificate':submitted_match,'stable_hold':bool(info.get('stable_hold')),
              'strict_arrival_predicate':ready,'consecutive_strict_arrival':consecutive_ready,
              'goal_m':update['goal'],'observed_position_m':x[:3].tolist(),'error_m':error.tolist(),
              'position_error_m':receipt['position_error_m'],'orientation_error_rad':receipt['orientation_error_rad'],
              'observed_motion_m':motion.tolist(),'bias_m':receipt['position_bias_m'],
              'reset_reason':receipt.get('state_reset_reason'),'integral_pause':pause,'target_band_braking':braking,
              'geometry_work':receipt['work'],'box_margin_m':receipt.get('box_margin_m'),
              'carried_can_margin_m':receipt.get('can_margin_m'),
              'submitted_action':row['submitted_action'],'fifo_before':row['queue_before'],
              'executed_before_noise':row['executed_action_before_noise'],
              'executed_action':row['executed_action']}
        held.append(item);active['last_control']=row['step'];active['controls']+=1
        active['maximum_consecutive_ready']=max(active['maximum_consecutive_ready'],consecutive_ready)
        active['integral_pause_controls']+=bool(pause)
        active['braking20_controls']+=bool(braking)
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
            'braking20_triggered_events':len(braking_events),
            'braking20_applied_events':sum(e['applied'] for e in braking_events),
            'braking20_rejected_or_replaced_events':sum(not e['applied'] for e in braking_events),
            'braking20_overlap_with_settling19':len({e['step'] for e in braking_events}&{e['step'] for e in triggered}),
            'braking20_events':braking_events,
            'integral_event_count_scope':'settling19 and braking20 can overlap on the same submitted control; do not add them as independent events or samples.',
            'arrival_count_scope':'Reconstructed original strict observed predicate on actually submitted accepted held commands, separated by exact phase/goal. Five-frame confirmation governs guarded CARRY route stages. PLACE retains the inherited object XY/height/age release condition; its pose streak here is descriptive, not a new release requirement. This is not a new readiness decision or guaranteed next transition.'}


def summarize_release(record,rows):
    """Actual release tail and queued actions, without extending the episode."""
    events=[e for e in record['events'] if e['to']=='RELEASE']
    segments=[]
    for event in events:
        tail=[r for r in rows if r['step']>=event['step']]
        release=[r for r in tail if r['recovery']['mode']=='RELEASE']
        submitted_open=next((r['step'] for r in release if r['submitted_action'][6]<0),None)
        executed_open=next((r['step'] for r in tail if r['executed_action_before_noise'][6]<0),None)
        segments.append({'entry_event_clock':event['step'],'remaining_after_entry':400-event['step'],
            'first_release_command_control':release[0]['step'] if release else None,
            'first_submitted_open_control':submitted_open,'first_executed_open_control':executed_open,
            'observed_delay_controls':executed_open-submitted_open if submitted_open is not None and executed_open is not None else None,
            'release_command_controls':len(release),'executed_open_controls_after_entry':sum(r['executed_action_before_noise'][6]<0 for r in tail),
            'actual_success':record['success'],'actual_termination_step':record['steps'],
            'tail_controls':[{'step':r['step'],'mode':r['recovery']['mode'],'next_mode':r['recovery'].get('next_mode'),
                'submitted_action':r['submitted_action'],'fifo_before':r['queue_before'],
                'executed_before_noise':r['executed_action_before_noise'],'executed_action':r['executed_action'],
                'success_after':r['success_after'],'state_before':r['state_before'],
                'state_after':r.get('state_after')} for r in tail]})
    return {'release_tails':segments,'release_tail_scope':'Stored actual actions, FIFO and observations only. Missing controls after400 are not simulated or assumed successful.'}


def first_difference(rows,other,key):
    return next((a['step'] for a,b in zip(rows,other) if not np.array_equal(a[key],b[key])),None)

def summarize_v21(record, rows):
    handoffs=record.get('handoff21_events',[]);place=record.get('place21_events',[])
    risk_controls=[]
    for event in handoffs:
        row=rows[event['step']-1];meta=event['handoff21']
        np.testing.assert_array_equal(event['actual_submitted_action'],row['submitted_action'])
        if event['applied']:
            assert event['accepted']
            np.testing.assert_array_equal(event['submitted_action'],row['submitted_action'])
        if meta.get('guard_preempted'):
            assert not event['accepted'];continue
        age=meta['descent_controls'];entry=meta['entry_window_active'];assert entry==(1<=age<=3)
        ep=meta['axial_error_m'];vp=meta['axial_motion_m']
        el=np.array(meta['lateral_error_m']);vl=np.array(meta['lateral_motion_m'])
        away=ep*vp<0;cross=ep*vp>0 and ep*(ep-2*vp)<=0
        moving=vl@vl>0;lat_away=moving and el@vl<=0;lat_cross=moving and el@(el-2*vl)<=0
        assert meta['axial_moving_away']==away and meta['axial_nominal_crossing']==cross
        assert meta['lateral_moving_away_or_tangential']==lat_away and meta['lateral_nominal_crossing']==lat_cross
        assert meta['axial_feedback']==bool(entry or away or cross)
        assert meta['lateral_feedback']==bool(entry or lat_away or lat_cross)
        risk_controls.append({'step':event['step'],'applied':event['applied'],**meta})
    for event in place:
        row=rows[event['step']-1];meta=event['place21']
        assert meta['actual_mode_at_proposal']=='PLACE' and meta['phase']=='PLACE' and meta['held']
        assert meta['terminal_place_only']
        np.testing.assert_array_equal(event['actual_submitted_action'],row['submitted_action'])
        if event['applied']:
            assert event['accepted']
            np.testing.assert_array_equal(event['submitted_action'],row['submitted_action'])
        assert meta['integral_rule_triggered']==('braking20' in event)
    # A last PLACE-labelled command can already be RELEASE. Metadata from the
    # actual proposal, not just the output label, determines B's strict scope.
    terminal_place_labels=[]
    for row in rows:
        if row['recovery']['mode']=='PLACE' and row['recovery'].get('next_mode')=='RELEASE':
            terminal_place_labels.append({'step':row['step'],'place21_present':'place21' in row['recovery'],
                                          'mixed_scope':row['recovery'].get('mixed_pose',{}).get('place21'),
                                          'parent_integral':row['recovery'].get('mixed_pose',{}).get('settling19'),
                                          'braking20_present':'braking20' in row['recovery'].get('mixed_pose',{}),
                                          'state_before':row['state_before'],'submitted_action':row['submitted_action'],
                                          'queue_before':row['queue_before'],
                                          'executed_before_noise':row['executed_action_before_noise']})
            assert 'place21' not in row['recovery']
    return {'handoff21_events':handoffs,'handoff21_risk_controls':risk_controls,
            'handoff21_summary':{'proposals':len(handoffs),'applied':sum(e['applied'] for e in handoffs),
                'entry_controls':sum(r['entry_window_active'] for r in risk_controls),
                'late_axial_away':sum(not r['entry_window_active'] and r['axial_moving_away'] for r in risk_controls),
                'late_axial_crossing':sum(not r['entry_window_active'] and r['axial_nominal_crossing'] for r in risk_controls),
                'late_lateral_away':sum(not r['entry_window_active'] and r['lateral_moving_away_or_tangential'] for r in risk_controls),
                'late_lateral_crossing':sum(not r['entry_window_active'] and r['lateral_nominal_crossing'] for r in risk_controls)},
            'place21_events':place,'place21_summary':{'proposals':len(place),'applied':sum(e['applied'] for e in place),
                'integral_rule_triggered':sum(e['place21']['integral_rule_triggered'] for e in place),
                'strict_actual_PLACE_scope':all(e['place21']['actual_mode_at_proposal']=='PLACE' for e in place)},
            'actual_RELEASE_final_PLACE_label_controls':terminal_place_labels}


def difference_context(left,right):
    for a,b in zip(left,right):
        if a['submitted_action']!=b['submitted_action']:
            return {'step':a['step'],'same_current_observation':a['state_before']==b['state_before'],
                    'same_pending_D2_queue':a['queue_before']==b['queue_before'],
                    'variant_mode':a['recovery']['mode'],'reference_mode':b['recovery']['mode'],
                    'variant_receipt':a['recovery'].get('mixed_pose'),
                    'reference_receipt':b['recovery'].get('mixed_pose'),
                    'variant_action':a['submitted_action'],'reference_action':b['submitted_action']}
    return None


def compare_entries(left,right):
    reference={r['step']:r for r in right};entries=[]
    for row in left:
        h=row['recovery'].get('mixed_pose',{}).get('handoff21',{})
        if not h.get('entry_window_active'):continue
        other=reference.get(row['step'])
        if other is None:continue
        rh=other['recovery'].get('mixed_pose',{})
        prior=rh.get('transition19',rh.get('handoff21',{}))
        matched=(row['state_before']==other['state_before'] and row['queue_before']==other['queue_before']
                 and prior.get('descent_controls')==h['descent_controls'])
        exact=row['submitted_action']==other['submitted_action']
        if matched:assert exact,'Matched actual-parent entry command changed'
        entries.append({'step':row['step'],'descent_controls':h['descent_controls'],
                        'same_state_queue_and_age':matched,'exact_action':exact,
                        'scope':'Only matched current observations and nominal history prove same-input entry equivalence.'})
    return entries


def phase_boundary_comparisons(case,reference,left,right):
    result=[]
    for phase in ['carry','place','release']:
        key='first_'+phase+'_clock';ia=case[key];ib=reference[key]
        if ia is None or ib is None:continue
        a=left[ia-1];b=right[ib-1]
        xa=np.asarray(a['state_before']);xb=np.asarray(b['state_before'])
        result.append({'phase':phase.upper(),'variant_event_clock':ia,'reference_event_clock':ib,
            'same_event_clock':ia==ib,'same_observed_state':a['state_before']==b['state_before'],
            'eef_position_distance_m':float(np.linalg.norm(xa[:3]-xb[:3])),
            'object_position_distance_m':float(np.linalg.norm(xa[16:19]-xb[16:19])),
            'joint_distance_rad':float(np.linalg.norm(np.asarray(a['joint_positions'])-np.asarray(b['joint_positions']))),
            'same_pending_queue':a['queue_before']==b['queue_before'],
            'variant_state':a['state_before'],'reference_state':b['state_before'],
            'variant_action':a['submitted_action'],'reference_action':b['submitted_action'],
            'scope':'Observed states at each original phase-entry event. Equal clocks do not imply identical continuous states or isolate a causal mechanism.'})
    return result


def export_tables_and_findings(summary,output):
    csv_path=output.with_suffix('.csv');findings=output.with_name(output.stem.replace('_diagnosis','_findings')+'.json')
    md_path=output.with_name(output.stem.replace('_diagnosis','_findings')+'.md')
    assert all(not p.exists() for p in [csv_path,findings,md_path])
    table=[]
    for c in summary['cases']:
        release=c['release_tails'][0] if c['release_tails'] else {}
        table.append({'condition':c['condition'],'version':c['version'],'success':c['success'],'steps':c['steps'],
            'first_descend':c['first_descend_entry_clock'],'first_close':c['first_close_clock'],
            'first_carry':c['first_carry_clock'],'first_place':c['first_place_clock'],'first_release':c['first_release_clock'],
            'recenter_controls':c['recenter_controls'],'first_submitted_open':release.get('first_submitted_open_control'),
            'first_executed_open':release.get('first_executed_open_control'),
            'executed_open_controls_after_entry':release.get('executed_open_controls_after_entry'),
            'handoff21_proposals':c['handoff21_summary']['proposals'],'handoff21_applied':c['handoff21_summary']['applied'],
            'place21_proposals':c['place21_summary']['proposals'],'place21_applied':c['place21_summary']['applied'],
            'place21_integral_triggered':c['place21_summary']['integral_rule_triggered'],'final_mode':c['final_command_mode']})
    with csv_path.open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    focus_names=['regression_6000005','clearance_profile_6000005','known_full_s23_clean_demo_12000036',
                 'known_bc_k2_clean_demo_12000011','known13_bc_k2_noise005_demo_13000021',
                 'known13_full_s41_noise005_demo_13000022']
    focus=[c for c in summary['cases'] if c['condition'] in focus_names]
    compact={'passed':True,'new_physical_episodes':0,'new_evaluation_samples':0,
             'version_summary':summary['version_summary'],'table':table,
             'focus_cases':[{k:c[k] for k in ['job','version','condition','success','steps','descents',
                'recenter_events','handoff21_summary','place21_summary','held_pose_segments',
                'first_carry_clock','first_place_clock','first_release_clock','final_command_mode']} for c in focus],
             'entry_comparisons':summary['paired_component_descriptions'],
             'source_sha256':{rel(output):sha(output),rel(csv_path):sha(csv_path),rel(Path(__file__)):sha(Path(__file__))},
             'interpretation':'This is a descriptive summary of completed known-profile traces. Source JSON retains FIFO and actual release commands. No counterfactual dynamics or new samples.'}
    with findings.open('x',encoding='utf8') as f:json.dump(finite(compact),f,ensure_ascii=False,indent=2,allow_nan=False)
    lines=['# v21 小测试只读控制诊断','',
           '9个条件复用8个物理起点；重定位/控制器回放另计，均不增加实验样本。事件进入时刻与实际执行时刻分列。',
           '预算组本轮真实重跑但保护不同；此处是已知条件描述，不能据此宣称泛化或完整采用。','',
           '| 条件 | 版本 | 成功/步数 | DESCEND→CLOSE | CARRY→PLACE→RELEASE | 首提交/执行开爪 | 重定位控制 |',
           '|---|---|---|---|---|---|---|']
    for r in table:
        if r['condition'] not in focus_names:continue
        lines.append(f"| {r['condition']} | {r['version']} | {r['success']}/{r['steps']} | {r['first_descend']}→{r['first_close']} | {r['first_carry']}→{r['first_place']}→{r['first_release']} | {r['first_submitted_open']}/{r['first_executed_open']} | {r['recenter_controls']} |")
    lines+=['','五帧只用于原CARRY路径到位；PLACE仍使用原物体XY/高度/age释放条件。',
            'handoff21风险反馈仅是当前观测启发式，不是未来几何或成功证明；相同输入逐位比较仅限保存的共同状态/队列前缀。',
            '详细手指脉冲、D2队列、位姿误差、连续到位帧与每次阶段目标见同名JSON；精确重定位五谓词见独立recenter回放回执。']
    md_path.write_text('\n'.join(lines)+'\n',encoding='utf8')


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
        case=summarize(job,record,rows);case.update(summarize_settling(record,rows));case.update(summarize_release(record,rows))
        case['direction20_events']=record.get('direction20_events',[])
        case.update(summarize_v21(record, rows))
        key=profile_identity(job,record['demo'])
        assert job['version'] not in by_key.setdefault(key,{})
        by_key[key][job['version']]=case;all_cases.append(case);traces[job['id']]=rows
        sources.extend([result,trace]);starts.add((job.get('dataset'),record['demo']))
    assert len(all_cases)==54 and len(by_key)==9 and len(starts)==8
    comparisons=[]
    for key,cases in by_key.items():
        assert set(cases)==set(ORDER)
        for variant,reference,meaning in [('recenter','v19','A only on actual v19'),
                ('place','v19','B only on actual v19'),
                ('v21','place','A with PLACE B enabled'),('v21','recenter','PLACE B with A enabled'),
                ('v21','v20','actual previous complete architecture reference'),
                ('v21','budget','actual old protection success reference')]:
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
                                'first_submitted_action_difference':first_difference(ar,br,'submitted_action'),
                                'first_difference_context':difference_context(ar,br),
                                'entry_comparisons':compare_entries(ar,br),
                                'phase_boundary_comparisons':phase_boundary_comparisons(a,b,ar,br)})
    summary={'passed':True,'stage':args.stage,'selected_evaluation_executions':54,'registered_profiles':9,'unique_start_identities':8,
             'new_physical_episodes':0,'new_evaluation_samples':0,'saved_controller_replay_performed':False,
             'scope':'Read-only extraction of completed original trace observations/events/actions, exact event-to-action matching, and paired component descriptions. No physics or new controller replay.',
             'cases':all_cases,'paired_component_descriptions':comparisons,
             'version_summary':{v:{'executions':sum(c['version']==v for c in all_cases),
                 'success':sum(c['version']==v and c['success'] for c in all_cases),
                 'braking20_proposals':sum(c['braking20_triggered_events'] for c in all_cases if c['version']==v),
                 'braking20_actually_applied':sum(c['braking20_applied_events'] for c in all_cases if c['version']==v),
                 'overlapping_old_integral_events':sum(c['braking20_overlap_with_settling19'] for c in all_cases if c['version']==v),
                 'handoff21_proposals':sum(c['handoff21_summary']['proposals'] for c in all_cases if c['version']==v),
                 'handoff21_applied':sum(c['handoff21_summary']['applied'] for c in all_cases if c['version']==v),
                 'place21_proposals':sum(c['place21_summary']['proposals'] for c in all_cases if c['version']==v),
                 'place21_applied':sum(c['place21_summary']['applied'] for c in all_cases if c['version']==v),
                 'place21_integral_rule_triggered':sum(c['place21_summary']['integral_rule_triggered'] for c in all_cases if c['version']==v)} for v in ORDER},
             'source_sha256':{rel(p):sha(p) for p in sources},
             'limitations':['Eight-centimeter goal jumps also occurred in successful old budget trajectories; a jump alone is not a sufficient causal explanation.',
                            'Actual v19, A, PLACE B and AB form the registered paired two-factor diagnostic design. These known profiles do not establish generalization. Certificate acceptance is not task success.',
                            'Stored event clocks and actual submitted control numbers are retained separately. Recenter checks may be emitted before the shared clock increments.',
                            'A refused pulse intent is unknown unless the receipt records it; zero submitted grip does not prove no pulse was attempted.',
                            'Budget is actually rerun here but has different protections; it cannot be adopted wholesale based on task-success counts.',
                            'Static, action-replay, physical-replay and this retrospective trace analysis do not add statistical samples.']}
    with output.open('x',encoding='utf8') as f:json.dump(finite(summary),f,ensure_ascii=False,indent=2,allow_nan=False)
    export_tables_and_findings(summary,output)
    print(json.dumps({'passed':True,'executions':54,'profiles':9,'new_physical_episodes':0,'output':rel(output)}))

if __name__=='__main__':main()
