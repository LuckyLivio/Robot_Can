"""Replay archived decisions, queues and observation-only invariants."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,sys,types
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
import audit_core
from reproduction.improvement_v19_20261019_01.recovery.recovery_controller import RecoveryController as V19,Config as C19
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import RecoveryController as V16,Config as C16
from reproduction.improvement_v17_20261019_01.recovery.recovery_controller import RecoveryController as V17,Config as C17
from reproduction.improvement_v18_20261019_01.recovery.recovery_controller import RecoveryController as V18,Config as C18
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import RecoveryController as V15,Config as C15
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import RecoveryController as V13,Config as C13
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import RecoveryController as V14,Config as C14
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as C6
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def audit_cap(vector,maximum):
    vector=np.asarray(vector,float)
    return vector*min(1.,maximum/max(float(np.linalg.norm(vector)),1e-15))

def audit_quantized(delta,turn,grip,cfg):
    action=np.r_[delta/.05,turn/.5,grip].astype(np.float32)
    for section,unit,limit in [(slice(0,3),.05,cfg.max_delta_m),(slice(3,6),.5,cfg.max_rotation_rad)]:
        length=np.linalg.norm(action[section].astype(float)*unit)
        if length>limit:action[section]*=limit/length*(1.-1e-6)
    return action

def audit_direction(receipt,x,goal,rotation,axis,motion,cfg,age):
    """Independent direction predicates and raw law, not future-motion proof."""
    d=receipt['direction20'];assert 'transition19' not in receipt
    assert d['descent_controls']==age
    if d.get('guard_preempted'):
        assert not receipt['accepted'] and receipt['reason']=='descent_joint_margin_guard'
        return None
    assert d['angular_window_controls']==3 and d['angular_entry_window_active']==(age<=3)
    assert d['nominal_forecast_only']
    if 'axis' not in d:
        assert not receipt['accepted'];return None
    axis=np.asarray(axis,float);error=np.asarray(goal,float)-np.asarray(x[:3],float);motion=np.asarray(motion,float)
    np.testing.assert_array_equal(d['axis'],axis)
    assert abs(np.linalg.norm(axis)-1.)<1e-6
    assert min(np.linalg.norm(axis-rotation[:,2]),np.linalg.norm(axis+rotation[:,2]))<1e-6
    ep=float(error@axis);vp=float(motion[:3]@axis)
    el=error-axis*ep;vl=motion[:3]-axis*vp
    ep2=ep-2*vp;el2=el-2*vl
    axial=bool(ep*vp>0 and ep*ep2<=0)
    moving=bool(vl@vl>0);away=bool(moving and el@vl<=0);cross=bool(moving and el@el2<=0)
    lateral=bool(away or cross)
    for key,value in [('axial_error_m',ep),('axial_motion_m',vp),('lateral_error_m',el),('lateral_motion_m',vl),
                      ('axial_nominal_error_after_delay_m',ep2),('lateral_nominal_error_after_delay_m',el2),
                      ('lateral_closing_dot_m2',float(el@vl)),('lateral_nominal_crossing_dot_m2',float(el@el2))]:
        np.testing.assert_allclose(d[key],value,rtol=0,atol=1e-12)
    assert d['axial_braking']==d['axial_nominal_crossing']==axial
    assert d['lateral_braking']==lateral and d['lateral_moving_away_or_tangential']==away and d['lateral_nominal_crossing']==cross
    raw=cfg.position_gain*error
    if axial:raw=raw-cfg.tracking_velocity_damping*axis*vp
    if lateral:raw=raw-cfg.tracking_velocity_damping*vl
    angle=Rotation.from_matrix(rotation@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec()
    turn=cfg.orientation_gain*angle
    if age<=3:turn=turn-cfg.tracking_angular_damping*motion[3:]
    np.testing.assert_allclose(receipt['raw_translation_m'],raw,rtol=0,atol=1e-12)
    np.testing.assert_allclose(receipt['raw_rotation_rad'],turn,rtol=0,atol=1e-12)
    return axial,lateral

def audit_braking(receipt,x,cfg,before_state,previous):
    """Rebuild bias ordering, conditional integration and actual float32 law."""
    update=receipt['state_update'];goal=np.asarray(update['goal'],float);rotation=np.asarray(update['rotation'],float)
    error=goal-np.asarray(x[:3],float);motion=np.r_[receipt['observed_translation_per_step_m'],receipt['observed_rotation_per_step_rad']]
    distance=float(np.linalg.norm(error));near=distance<=.06;bias=np.zeros(3)
    if before_state is None or before_state['goal'] is None:reason='new_servo_state'
    elif before_state['phase']!=update['phase'] or not before_state['held']:reason='phase_or_held_state_changed'
    elif not np.array_equal(goal,before_state['goal']) or not np.array_equal(rotation,before_state['rotation']):reason='target_changed'
    elif previous is not None and not np.array_equal(np.asarray(previous),before_state['last_action']):reason='interrupted_by_uncertified_command'
    else:reason=None;bias=np.asarray(before_state['bias'],float).copy()
    assert receipt['state_reset_reason']==reason and receipt['near_goal_feedback']==near
    capture=np.zeros(3,dtype=bool);crossing=capture.copy();pause=capture.copy();inside=False
    if near:
        bias[bias*error<0]=0.
        crossing=(error*motion[:3]>0)&(error*(error-2*motion[:3])<=0)
        capture=(error*motion[:3]>0)&(np.abs(error)<=.009/np.sqrt(3.)+2*np.abs(motion[:3]))
        inside=bool(distance<.009);pause=capture|inside
        if pause.any():
            bias[capture]=0.;increment=.1*error;increment[pause]=0.;bias=audit_cap(bias+increment,.009)
        else:bias=audit_cap(bias+.1*error,.009)
    else:bias[:]=0.
    assert ('braking20' in receipt)==bool(pause.any())
    assert ('settling19' in receipt)==bool(crossing.any())
    if pause.any():
        b=receipt['braking20'];assert b['triggered'] and b['control_heuristic_only']
        assert b['no_error_extrapolation_or_additional_damping'] and b['arrival_thresholds_and_counters_unchanged']
        assert b['delay_controls']==2 and b['original_arrival_position_m']==.009 and b['axis_capture_band_m']==.009/np.sqrt(3.)
        assert b['inside_original_position_ball']==inside
        for key,value in [('capture_brake_axes',capture),('original_crossing_axes',crossing),('integral_pause_axes',pause),
                          ('current_error_m',error),('observed_motion_per_control_m',motion[:3])]:
            np.testing.assert_array_equal(b[key],value)
    np.testing.assert_allclose(update['bias'],bias,rtol=0,atol=1e-12)
    np.testing.assert_allclose(receipt['position_bias_m'],bias,rtol=0,atol=1e-12)
    delta=cfg.position_gain*error+bias
    if near:delta-=cfg.tracking_velocity_damping*motion[:3]
    turn=cfg.orientation_gain*Rotation.from_matrix(rotation@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec()-cfg.tracking_angular_damping*motion[3:]
    delta,turn=audit_cap(delta,cfg.max_delta_m),audit_cap(turn,cfg.max_rotation_rad)
    reference=np.asarray(receipt['previous_submitted_action'],float)
    np.testing.assert_array_equal(reference,np.zeros(7) if previous is None else previous)
    delta=reference[:3]*.05+audit_cap(delta-reference[:3]*.05,cfg.max_delta_m/3)
    turn=reference[3:6]*.5+audit_cap(turn-reference[3:6]*.5,cfg.max_rotation_rad/3)
    delta,turn=audit_cap(delta,cfg.max_delta_m),audit_cap(turn,cfg.max_rotation_rad)
    if receipt['accepted']:
        scale=receipt['selected_scale'];assert scale in [1.,.5,.25]
        np.testing.assert_array_equal(receipt['submitted_action'],audit_quantized(delta*scale,turn*scale,receipt['grip_command'],cfg))
    return bool(pause.any()),inside
def mixed_receipts(value):
    if isinstance(value,dict):
        if value.get('kind')=='mixed_pose':
            yield value
        else:
            for child in value.values():yield from mixed_receipts(child)
    elif isinstance(value,list):
        for child in value:yield from mixed_receipts(child)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();stage=RUN/a.stage
    assert json.loads((stage/'completed.json').read_text())['source_unchanged']
    started=json.loads((stage/'started.json').read_text())
    assert sha(stage/'jobs.json')==started['jobs_sha256']
    for rel,h in started['dependency_sha256'].items():assert sha(ROOT/rel)==h,('Dependency changed',rel)
    for rel,h in started['source_sha256'].items():
        assert sha(stage/'source'/Path(rel).relative_to(RUN.relative_to(ROOT)))==h
    pkg=types.ModuleType('archived_v20');pkg.__path__=[str(stage/'source/recovery')];sys.modules[pkg.__name__]=pkg
    spec=importlib.util.spec_from_file_location('archived_v20.recovery_controller',stage/'source/recovery/recovery_controller.py')
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    stats={'wait_transfer_steps':0,'protected_descent_steps':0,'planning_wait_steps':0,'path_recenter_steps':0,'bounded_planning_steps':0,
           'carry_planning_steps':0,'carry_path_steps':0,'carry_guard_steps':0,'carry_hold_steps':0,'place_hold_steps':0,'edge_pretranslate_steps':0,'edge_pretranslate_transitions':0,
           'mixed_pose_steps':0,'mixed_pose_rejections':0,'mixed_pose_cancellations':0,'mixed_pose_work_units':0,'edge_aperture_steps':0,
           'v17_edge_pose_steps':0,'v17_held_pose_steps':0,'v17_aperture_fallbacks':0,'v17_full_aperture_steps':0,
           'v17_committed_pose_steps':0,'v17_search_steps':0,'v17_memory_clear_steps':0,'v17_terminal_carry_steps':0,
           'v18_handoff_proposals':0,'v18_handoff_submitted':0,'v18_handoff_rejected':0,
           'v18_handoff_parent_replaced':0,'v18_final_descend_close':0,'v18_handoff_full_aperture':0,
           'v19_transition_window_steps':0,'v19_transition_postwindow_steps':0,
           'v19_settling_proposals':0,'v19_settling_submitted':0,'v19_candidate_search_steps':0,
           'v20_direction_steps':0,'v20_direction_axial_braking':0,'v20_direction_lateral_braking':0,
           'v20_braking_law_steps':0,'v20_braking_proposals':0,'v20_braking_submitted':0,'v20_inside_position_ball':0};instances=[]
    class Audited(m.RecoveryController):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);instances.append(self)
            assert self.cfg.delay==2 and self.cfg.horizon_steps==400 and self.cfg.max_attempts==2
            self.audit_pretranslate_settled=0
        def choose(self,x,proposal,previous):
            before=self.clock;before_mode=self.mode;before_age=self.age
            before_edge_plan=getattr(self,'edge_plan',None)
            before_carry_plan=getattr(self,'carry_plan',None);before_carry_search=getattr(self,'carry_search',None)
            before_lost_frames=self.lost_frames
            before_gap_ready=self.gap_ready(x)
            before_submitted=getattr(self,'last_submitted17',None)
            before_held_state=copy.deepcopy(vars(self.servo17['held'])) if 'held' in self.servo17 else None
            before_rotation=None if self.goal_rotation is None else self.goal_rotation.copy()
            before_pulse=self.last_pulse
            before_tail_age=None if self.carry_tail17 is None else self.carry_tail17['age']
            action,info=super().choose(x,proposal,previous)
            assert self.clock==before+1 and self.clock<=400
            assert self.attempts<=2
            if self.servo17 and not self._committed17:
                assert all(state.phase is None and state.last_action is None and not state.bias.any() for state in self.servo17.values())
                stats['v17_memory_clear_steps']+=1
            certificates=list(mixed_receipts(info))
            assert len(certificates)<=1,'More than one mixed certificate attached to one submitted action'
            for certificate in certificates:
                handoff=info.get('planning_kind') in ['v18_descent_handoff','v19_descent_transition','v20_directional_descent']
                work=certificate['work'];assert isinstance(work,int) and 0<=work<=16
                assert work==certificate.get('work_units',work)
                if handoff:
                    assert self.cfg.handoff_continuity and self.cfg.can_guard
                    assert before_mode=='DESCEND' and before_edge_plan is not None
                    pending=self._handoff_pending18;assert pending is not None and pending['receipt']==certificate
                    assert info['handoff18_applied'] is info['mixed_pose_applied']
                    applied=info['handoff18_applied'];stats['v18_handoff_proposals']+=1
                    if info.get('planning_kind')=='v20_directional_descent':
                        assert self.cfg.directional_transition and self.cfg.transition_window
                        assert info['direction20']==certificate['direction20']
                        predicates=audit_direction(certificate,x,pending['goal'],before_rotation,
                                                   before_edge_plan['rotation'][:,2],self.motion,self.cfg,before_age+1)
                        stats['v20_direction_steps']+=1
                        if predicates is not None:
                            stats['v20_direction_axial_braking']+=int(predicates[0])
                            stats['v20_direction_lateral_braking']+=int(predicates[1])
                    if info.get('planning_kind')=='v19_descent_transition':
                        assert self.cfg.transition_window
                        if 'transition19' in certificate:
                            window=certificate['transition19']
                            assert window['window_controls']==3 and window['descent_controls']==before_age+1
                            assert window['window_active']==(window['descent_controls']<=3)
                            stats['v19_transition_window_steps' if window['window_active'] else 'v19_transition_postwindow_steps']+=1
                        elif certificate['accepted']:raise AssertionError('Accepted transition lacks window accounting')
                    if not certificate['accepted']:
                        assert not applied and self._handoff_blocked18
                        assert np.array_equal(action,np.zeros(7)) and self.mode=='POSE_WAIT'
                        assert info['mode']=='DESCENT_GUARD' and info['next_mode']=='POSE_WAIT'
                        assert info['mixed_pose_submission_reason']=='descent_guard_rejected'
                        assert self.last_pulse==pending['pulse_before']==before_pulse
                        stats['v18_handoff_rejected']+=1
                        if certificate['reason']=='descent_joint_margin_guard':
                            assert work==0 and pending['joint_margin_rad']<self.cfg.joint_solution_margin_rad
                            stats['mixed_pose_steps']+=1;stats['mixed_pose_rejections']+=1
                            continue  # No geometric check was performed; no fabricated margin fields.
                    elif applied:
                        assert info['mixed_pose_submission_reason']=='certified_descent_submitted'
                        assert np.array_equal(action,pending['candidate'])
                        assert np.array_equal(action,np.asarray(certificate['submitted_action'],np.float32))
                        assert pending['joint_margin_rad']>=self.cfg.joint_solution_margin_rad
                        assert certificate['handoff_feedback'] and not certificate['servo_bias_used']
                        assert certificate['delay']==2 and certificate['settling_and_clock_owned_by_caller']
                        reference=np.asarray(certificate['previous_submitted_action'],float)
                        np.testing.assert_array_equal(reference,before_submitted)
                        assert np.linalg.norm(action[:3].astype(float)*.05-reference[:3]*.05)<=self.cfg.max_delta_m/3+1e-8
                        assert np.linalg.norm(action[3:6].astype(float)*.5-reference[3:6]*.5)<=self.cfg.max_rotation_rad/3+1e-8
                        if certificate['aperture_motion']:
                            assert certificate['aperture_range_m']==[0.,.085]
                            stats['v18_handoff_full_aperture']+=1
                        else:assert action[6]==0
                        if self.mode=='CLOSE':
                            assert info['mode']=='DESCEND' and info['next_mode']=='CLOSE'
                            assert np.linalg.norm(np.asarray(x[:3])-pending['goal'])<.009
                            stats['v18_final_descend_close']+=1
                        stats['v18_handoff_submitted']+=1
                    else:
                        assert info['mixed_pose_submission_reason']=='parent_replaced_proposal'
                        assert np.array_equal(action,np.zeros(7)),'Parent replaced certified descent with uncertified motion'
                        if pending['candidate'][6]!=0:assert self.last_pulse==pending['pulse_before']
                        stats['v18_handoff_parent_replaced']+=1
                assert certificate['required_can_margin_m'] in [.001,.003]
                if self.cfg.delay_braking and certificate['held'] and 'state_update' in certificate:
                    assert self.cfg.terminal_settling
                    np.testing.assert_array_equal(np.r_[certificate['observed_translation_per_step_m'],certificate['observed_rotation_per_step_rad']],self.motion)
                    triggered,inside=audit_braking(certificate,x,self.cfg,before_held_state,before_submitted)
                    stats['v20_braking_law_steps']+=1
                    if triggered:
                        stats['v20_braking_proposals']+=1;stats['v20_inside_position_ball']+=int(inside)
                        assert info['braking20']==certificate['braking20']
                        applied=bool(certificate['accepted'] and self._committed17 and
                                     np.array_equal(action,np.asarray(certificate.get('submitted_action'),np.float32)))
                        assert info['braking20_applied']==applied
                        stats['v20_braking_submitted']+=int(applied)
                if 'settling19' in certificate:
                    assert self.cfg.terminal_settling and certificate['held'] and certificate['near_goal_feedback']
                    settling=certificate['settling19'];assert settling['triggered'] and settling['control_heuristic_only']
                    assert settling['arrival_thresholds_and_counters_unchanged']
                    goal=np.asarray(certificate['state_update']['goal'],float)
                    error=goal-np.asarray(x[:3],float);motion=np.asarray(certificate['observed_translation_per_step_m'],float)
                    axes=(error*motion>0)&(error*(error-2*motion)<=0)
                    np.testing.assert_array_equal(settling['integral_brake_axes'],axes)
                    np.testing.assert_allclose(settling['nominal_error_after_delay_m'],error-2*motion,rtol=0,atol=1e-12)
                    assert axes.any() and np.linalg.norm(error)<=.06
                    assert np.all(np.asarray(certificate['state_update']['bias'])[axes]==0)
                    stats['v19_settling_proposals']+=1
                    if certificate['accepted'] and info.get('mixed_pose_applied') is not False:stats['v19_settling_submitted']+=1
                if certificate['held']:assert certificate['required_can_margin_m']==.001
                stats['mixed_pose_steps']+=1;stats['mixed_pose_work_units']+=work
                if certificate['accepted']:
                    assert certificate['box_margin_m']>=.001 and certificate['can_margin_m']>=certificate['required_can_margin_m']
                    translation=np.asarray(certificate['translation_m'],float);rotation=np.asarray(certificate['rotation_vector_rad'],float)
                    assert np.linalg.norm(translation)<=self.cfg.max_delta_m+1e-12 and np.linalg.norm(rotation)<=self.cfg.max_rotation_rad+1e-12
                    if info.get('mixed_pose_applied') is False:
                        assert np.array_equal(action[:6],np.zeros(6))
                        if info.get('settling19_submission_reason')=='parent_replaced_proposal':
                            assert self.cfg.terminal_settling and not self._committed17
                            assert all(state.phase is None and state.last_action is None and not state.bias.any() for state in self.servo17.values())
                            np.testing.assert_array_equal(self.last_submitted17,action)
                        else:assert info['mixed_pose_submission_reason'] in (['parent_replaced_proposal'] if handoff else ['parent_joint_or_pose_guard'])
                        stats['mixed_pose_cancellations']+=1
                    else:
                        np.testing.assert_allclose(action[:3].astype(float)*.05,translation,rtol=0,atol=1e-9)
                        np.testing.assert_allclose(action[3:6].astype(float)*.5,rotation,rtol=0,atol=1e-9)
                    if certificate['held']:
                        assert self.cfg.held_pose and info['stable_hold'] and action[6]==1
                    else:assert self.cfg.handoff_continuity if handoff else self.cfg.edge_stability
                    if certificate.get('trials'):
                        accepted=[trial for trial in certificate['trials'] if trial['accepted']]
                        assert len(accepted)==1 and accepted[0]['arc_bounds_applied'] and accepted[0]['whole_translation_sweep_at_each_orientation']
                    new_servo=(info.get('planning_kind') in ['v17_edge_pose','v17_held_pose'] or
                               (info.get('planning_kind')=='v17_terminal_carry' and self.cfg.held_stability))
                    if new_servo and info.get('mixed_pose_applied') is not False:
                        assert np.array_equal(action,np.asarray(certificate['submitted_action'],np.float32))
                        state=self.servo17['held' if certificate['held'] else 'edge']
                        assert np.array_equal(state.last_action,action)
                        assert np.linalg.norm(state.bias)<=.009+1e-12
                        assert np.array_equal(state.bias,np.asarray(certificate['state_update']['bias']))
                        stats['v17_committed_pose_steps']+=1
                        if certificate['held']:
                            assert self.cfg.held_stability
                            reference=np.asarray(certificate['previous_submitted_action'],float)
                            expected=np.zeros(7) if before_submitted is None else before_submitted
                            np.testing.assert_array_equal(reference,expected)
                            assert np.linalg.norm(action[:3].astype(float)*.05-reference[:3]*.05)<=self.cfg.max_delta_m/3+1e-8
                            assert np.linalg.norm(action[3:6].astype(float)*.5-reference[3:6]*.5)<=self.cfg.max_rotation_rad/3+1e-8
                        else:
                            assert self.cfg.edge_convergence
                            if certificate['aperture_motion']:
                                assert certificate['aperture_range_m']==[0.,.085]
                                assert accepted[0]['aperture_motion'] and accepted[0]['aperture_range_m']==[0.,.085]
                                stats['v17_full_aperture_steps']+=1
                            elif action[6]!=0:raise AssertionError('Empty pulse without full-aperture certificate')
                else:
                    assert np.array_equal(action[:6],np.zeros(6));stats['mixed_pose_rejections']+=1
                if info.get('planning_kind')=='v17_edge_pose':stats['v17_edge_pose_steps']+=1
                if info.get('planning_kind')=='v17_held_pose':stats['v17_held_pose_steps']+=1
            if info.get('terminal_route'):
                assert self.cfg.route_efficiency or self.cfg.held_stability
                assert before_tail_age is not None and info['terminal_phase_age']==before_tail_age+1
                assert info['terminal_phase_age']<=70
                assert len(certificates)==1 and certificates[0]['held']
                if certificates[0]['accepted']:
                    assert self.carry_plan is None and self.carry_reference is not None and self.mode=='CARRY'
                    assert self.transport16_attempt==self.attempts
                stats['v17_terminal_carry_steps']+=1
            searches={id(search):search for search in [before_carry_search,getattr(self,'carry_search',None)] if search is not None}
            for search in searches.values():
                if search is not None and hasattr(search,'cache_stats'):
                    assert self.cfg.route_efficiency and search.calls<=24 and search.work<=384 and search.last_work<=16
                    assert search.last_geometry_work<=4
                    if search.chosen is not None:
                        assert search.chosen['preserve_current'] is False
                        assert search.chosen['schedule']['minimum_command_schedule_fits']
                        assert self.carry_reference is search.envelope
                    stats['v17_search_steps']+=1
                    if hasattr(search,'_candidate_work_start'):
                        assert self.cfg.candidate_budget
                        assert len(search.options)==4 and search.options[0][0]=='current_exact'
                        assert search.options[1][0]=='current_rotation_inset'
                        for candidate in search.receipts:
                            assert candidate['candidate_work']>=0
                            if candidate.get('optional_endpoint_candidate'):
                                assert candidate['candidate_work_limit']==48 and candidate['candidate_work']<=48
                                if candidate['accepted']:
                                    admission=candidate['admission']
                                    assert admission['admitted'] and admission['original_transport_complete'] and admission['failure_confined_to_placement']
                                if candidate['reason'] in ['optional_candidate_work_cap_unconfirmed','optional_endpoint_admission_unconfirmed']:
                                    assert not candidate['accepted']
                        if not search.done and search.receipt.get('optional_endpoint_candidate'):
                            assert search.work-search._candidate_work_start<=48
                        stats['v19_candidate_search_steps']+=1
            if info.get('wait_hold_transition'):
                assert info['stable_hold'] and self.mode=='LIFT' and action[6]==1
                assert self.attempts<=2;stats['wait_transfer_steps']+=1
            if info['mode']=='DESCEND' or info.get('next_mode')=='DESCEND':
                assert self.refresh_feasibility(x)=='feasible' and not self.pose_changed(x)
                stats['protected_descent_steps']+=1
            if info['mode'] in ['POSE_WAIT','POSE_BLOCKED']:assert action[6]==0
            if info['mode']=='WAIT_ESCAPE':
                assert action[6]==0 and info['retreat_hand_margin_m']>=.001 and info['retreat_can_margin_m']>=.001
                assert self.escape_count<=self.cfg.escape_max_replans
            if info['mode']=='PATH_RECENTER':
                assert self.cfg.descent_clearance and action[6]==0
                assert info['hand_margin_m']>=.001 and info['can_margin_m']>=.001
                assert self.recenter_age<=self.cfg.recenter_timeout and self.age<=self.cfg.stage_timeout
                assert all(n<=self.cfg.recenter_max_per_attempt for n in self.recenter_counts.values())
                stats['path_recenter_steps']+=1
            if info['mode'] in ['CARRY_PLAN','CARRY_PATH']:
                assert self.cfg.carry_path and self.mode=='CARRY' and info['stable_hold']
                assert self.ever_stable and action[6]==1
                if info['mode']=='CARRY_PLAN':
                    assert np.array_equal(action[:6],np.zeros(6)) and info['planning_kind'] in ['v15_carry','v16_carry','v17_carry','v18_carry','v19_carry']
                    assert 'planning_work_units' in info
                    stats['carry_planning_steps']+=1
                else:
                    assert info['accepted'] and info['hand_margin_m']>=.001 and info['carried_can_margin_m']>=.001
                    margin=float(np.min(np.minimum(self.joints-LIMITS[:,0],LIMITS[:,1]-self.joints)))
                    assert margin>=self.cfg.joint_solution_margin_rad
                    stats['carry_path_steps']+=1
            if info['mode']=='CARRY_GUARD':
                assert np.array_equal(action[:6],np.zeros(6)) and action[6]==1
                assert info['next_mode']==self.mode and self.mode!='CARRY'
                stats['carry_guard_steps']+=1
            if info['mode']=='CARRY_HOLD':
                assert self.cfg.carry_path and self.mode=='CARRY' and not info['stable_hold']
                assert np.array_equal(action[:6],np.zeros(6)) and action[6]==1
                assert self.lost_frames==before_lost_frames+1 and self.lost_frames<self.cfg.stable_frames
                assert self.carry_plan is before_carry_plan and self.carry_search is before_carry_search
                stats['carry_hold_steps']+=1
            if info['mode']=='PLACE_HOLD':
                assert self.cfg.held_pose and self.mode=='PLACE' and not info['stable_hold']
                assert np.array_equal(action[:6],np.zeros(6)) and action[6]==1
                assert self.lost_frames==before_lost_frames+1 and self.lost_frames<self.cfg.stable_frames
                stats['place_hold_steps']+=1
            if info['mode']=='EDGE_APERTURE':
                assert self.cfg.edge_stability and self.mode in ['EDGE_PRETRANSLATE','EDGE_ROTATE','EDGE_APPROACH']
                assert np.array_equal(action[:6],np.zeros(6)) and action[6] in [-1,0,1]
                ready_after=self.gap_ready(x)
                assert info['aperture_ready']==ready_after and self.edge_settled==0
                if certificates:
                    assert info.get('planning_kind')=='v17_edge_pose' and len(certificates)==1
                    assert not certificates[0]['accepted'] and not certificates[0]['held'] and certificates[0]['aperture_motion']
                    assert self.cfg.edge_convergence
                    stats['v17_aperture_fallbacks']+=1
                assert not before_gap_ready or not ready_after
                if ready_after:
                    # Pretranslate tests readiness before hold increments time
                    # and appends the current gap. A just-settled frame waits.
                    assert before_mode=='EDGE_PRETRANSLATE' and np.array_equal(action,np.zeros(7))
                stats['edge_aperture_steps']+=1
            if before_mode=='EDGE_PRETRANSLATE' or info['mode']=='EDGE_PRETRANSLATE':
                assert self.cfg.segmented_edge
                plan=before_edge_plan if before_edge_plan is not None else self.edge_plan
                assert plan is not None and 'pre_goal' in plan and 'pre_rotation' in plan
                error=float(np.linalg.norm(np.asarray(x[:3])-plan['pre_goal']))
                angle=float(np.linalg.norm(Rotation.from_matrix(plan['pre_rotation']@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec()))
                at=error<.009 and angle<.08
                self.audit_pretranslate_settled=self.audit_pretranslate_settled+1 if at else 0
                if info['mode']=='EDGE_PRETRANSLATE':
                    assert info['hand_margin_m']>=.001 and info['can_margin_m']>=.001
                    stats['edge_pretranslate_steps']+=1
                if self.mode=='EDGE_ROTATE':
                    assert at and self.audit_pretranslate_settled>=self.cfg.delay+3 and self.gap_ready(x)
                    stats['edge_pretranslate_transitions']+=1
            else:self.audit_pretranslate_settled=0
            if 'planning_work_units' in info:
                cap=self.cfg.mesh_candidates_per_step if info.get('planning_kind')=='mesh' else self.cfg.ik_iterations_per_step
                assert 0<=info['planning_work_units']<=cap
                stats['bounded_planning_steps']+=1
            if info['mode']=='PLAN_WAIT':
                assert (action==0).all();stats['planning_wait_steps']+=1
                cap=self.cfg.mesh_candidates_per_step if info['planning_kind']=='mesh' else self.cfg.ik_iterations_per_step
                assert info['planning_work_units']<=cap
            return action,info
    parents={'v6':(V6,C6),'v13':(V13,C13),'v14':(V14,C14),'v15':(V15,C15),'budget':(V15,C15),'v16':(V16,C16),'v17':(V17,C17),'v18':(V18,C18),'v19':(V19,C19)}
    audit_core.controller_class=lambda v:parents[v] if v in parents else (Audited,m.Config)
    result=[]
    for j in json.loads((stage/'jobs.json').read_text()):
        instances.clear();result.append(audit_core.audit(stage/j['id']))
        if j['version'] not in parents:
            records=json.loads((stage/j['id']/'result.json').read_text())['records']
            for r,c in zip(records,instances):
                for k in ['support13_events','escape_events','tracking14_events','clearance14_events','carry15_events','edge15_events','budget15_events','ik16_events','held16_events','edge16_events','route17_events','edge17_events','held17_events','handoff18_events','route18_events','transition19_events','budget19_events','settling19_events','direction20_events','braking20_events','wait_hold_events','guard_events','pose_events','geometry_events','edge_events','joint_events','planning_events']:
                    assert r[k]==getattr(c,k),(j['id'],r['demo'],k)
    out={'passed':True,'stage':a.stage,'episodes':sum(r['episodes'] for r in result),
         'controls':sum(r['controls'] for r in result),'invariants':stats,'source_snapshot_verified':True}
    with (RUN/'analysis'/f'{a.stage}_verification.json').open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps(out))
