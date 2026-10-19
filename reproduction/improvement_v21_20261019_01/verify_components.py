"""v21 integration predicates on saved inputs with explicit geometry stubs.

No simulator, training, new start or outcome sample is produced. New helper
geometry is checked independently; stubs here isolate inherited control flow.
"""
from pathlib import Path
from dataclasses import asdict,replace
from unittest.mock import patch
from types import SimpleNamespace
import argparse,copy,hashlib,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery import recovery_controller as m
from recovery import recenter_transition as handoff
from reproduction.improvement_v20_20261019_01.recovery import delay_settling as settling
from reproduction.improvement_v19_20261019_01.recovery import settling as parent_settling
from reproduction.improvement_v19_20261019_01.recovery.recovery_controller import Config as C19
from reproduction.improvement_v15_20261016_01.recovery.carry_path import HeldEnvelope
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
from reproduction.improvement_v11_20261015_01.recovery import recovery_controller as v11_module
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import RecoveryController as V16
from verify_run import audit_handoff21,audit_braking
FLAGS=['recenter_transition','place_braking']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='components_a');args=parser.parse_args()
    output=RUN/'analysis'/f'{args.name}.json';assert not output.exists()
    folder=ROOT/'reproduction/improvement_v19_20261019_01/smoke_a/v19_regression_6000005'
    place_folder=ROOT/'reproduction/improvement_v19_20261019_01/smoke_a/v19_known_full_s23_clean_demo_12000036'
    rows=list(map(json.loads,(folder/'trace.jsonl').open(encoding='utf8')));job=read(folder/'result.json')['job']
    final_index=next(i for i,row in enumerate(rows) if row['recovery']['mode']=='DESCEND' and row['recovery'].get('next_mode')=='CLOSE')
    paths=[p for p in (RUN/'recovery').iterdir() if p.suffix in ['.py','.json']]
    paths += [Path(__file__).resolve(),RUN/'verify_run.py',RUN/'protocols/smoke_jobs.json',folder/'result.json',folder/'trace.jsonl']
    paths += [place_folder/'result.json',place_folder/'trace.jsonl']
    for version in range(6,21):
        for directory in (ROOT/'reproduction').glob(f'improvement_v{version}_*/recovery'):
            paths += [p for p in directory.iterdir() if p.suffix in ['.py','.json']]
    paths += list((ROOT/'reproduction/recovery_v5_20261012_01').glob('*.py'))
    hashes={path.relative_to(ROOT).as_posix():sha(path) for path in sorted(set(paths))};checks=[]
    def record(name,scope):
        checks.append({'name':name,'passed':True,'scope':scope});print(name,flush=True)
    configs=read(RUN/'protocols/smoke_jobs.json')
    parents={j['id'][len(j['version'])+1:]:j for j in configs if j['version']=='v19'}
    assert len(asdict(C19()))==111 and len(asdict(m.Config()))==113
    for j in configs:
        if j['version'] not in ['recenter','place','v21']:continue
        parent=parents[j['id'][len(j['version'])+1:]]['config'];current=asdict(m.Config(**j['config']))
        assert all(current[k]==value for k,value in parent.items())
        assert current['recenter_transition']==(j['version'] in ['recenter','v21'])
        assert current['place_braking']==(j['version'] in ['place','v21'])
    record('all_111_parent_fields_and_single_flags_exact','Real nine-profile configs: full v19 retained in each repair, original clearance profile retained')
    from variants import controller_class
    for version,module in [('v19','improvement_v19_20261019_01'),('v20','improvement_v20_20261019_01'),('budget','improvement_v15_20261016_01')]:
        cls,cfg=controller_class(version);assert module in cls.__module__ and module in cfg.__module__
    record('baselines_use_actual_frozen_classes','Actual v19/v20 and original v15 budget class, not fake v21 flag configurations')

    c=m.RecoveryController([.1975,.4025,.8],.8,np.asarray(rows[0]['state_before'],np.float32),True,
                           m.Config(**job['config'],recenter_transition=False,place_braking=False))
    previous=np.zeros(7,np.float32)
    for row in rows[:final_index]:
        x=np.asarray(row['state_before'],np.float32);c.set_joint_positions(row['joint_positions'])
        if job.get('force_recovery_at')==row['step']:c.start_attempt('diagnostic_forced_start',x)
        action,info=c.choose(x,np.asarray(row['original_proposal'],np.float32),previous)
        before=dict(info);saved=dict(row['recovery']);before.pop('planning_ms',None);saved.pop('planning_ms',None)
        assert before==saved and not row['fault_injected']
        np.testing.assert_allclose(action,row['submitted_action'],rtol=0,atol=1e-7)
        previous=np.asarray(row['executed_action'],np.float32)
    fixture=copy.deepcopy(c);row=rows[final_index];x=np.asarray(row['state_before'],np.float32)
    proposal=np.asarray(row['original_proposal'],np.float32);closed=np.array([0,0,0,0,0,0,1],np.float32);zero=np.zeros(7,np.float32)
    assert fixture.mode=='DESCEND' and fixture.edge_plan is not None
    def current(**flags):
        controller=copy.deepcopy(fixture);settings=dict(recenter_transition=True,place_braking=False);settings.update(flags)
        controller.cfg=replace(controller.cfg,**settings)
        controller.set_joint_positions(row['joint_positions']);return controller
    def certificate(action,accepted=True):
        return {'kind':'mixed_pose','accepted':accepted,'held':False,'work':4,'work_units':4,'trials':[],
                'reason':'explicit_geometry_stub','box_margin_m':.01 if accepted else None,
                'can_margin_m':.01 if accepted else None,'required_can_margin_m':.001,
                'translation_m':(action[:3].astype(float)*.05).tolist(),'rotation_vector_rad':(action[3:6].astype(float)*.5).tolist(),
                'submitted_action':action.tolist(),'aperture_motion':False,'handoff_feedback':True,'servo_bias_used':False,
                'handoff21':{'descent_controls':fixture.age+1,'axis':fixture.edge_plan['rotation'][:,2].tolist()}}
    baseline=copy.deepcopy(fixture);baseline.set_joint_positions(row['joint_positions'])
    baseline_action,baseline_info=baseline.choose(x,proposal,previous)
    assert baseline.mode=='CLOSE' and baseline_info['mode']=='DESCEND'
    np.testing.assert_allclose(baseline_action,row['submitted_action'],rtol=0,atol=1e-7)
    record('saved_final_descent_fixture_exact','Actual parent control flow reconstructed from saved v19 inputs and commands through the final DESCEND to CLOSE frame')

    c=current();tick=c.clock
    real_action,real_info=c.choose(x,proposal,previous)
    assert c.clock==tick+1 and c.mode=='CLOSE' and real_info['mode']=='DESCEND' and real_info['next_mode']=='CLOSE'
    assert real_info['planning_kind']=='v21_recenter_transition' and real_info['handoff18_applied']
    assert real_info['mixed_pose']['accepted'] and 'handoff21' in real_info['mixed_pose']
    np.testing.assert_array_equal(real_action,real_info['mixed_pose']['submitted_action'])
    record('actual_direction_helper_and_parent_final_close','No helper, geometry or parent stub: one actual v21 decision on the saved v19 final-DESCEND state keeps certified float32 action through the original CLOSE predicate; no simulator step')

    c=current();tick=c.clock;attempt=c.attempts
    with patch.object(handoff,'propose',return_value=(baseline_action.copy(),certificate(baseline_action))) as helper:
        action,info=c.choose(x,proposal,previous)
    assert helper.call_count==1 and c.clock==tick+1 and c.attempts==attempt and c.mode=='CLOSE'
    assert info['mode']=='DESCEND' and info['next_mode']=='CLOSE' and info['handoff18_applied']
    assert info['mixed_pose_submission_reason']=='certified_descent_submitted'
    np.testing.assert_array_equal(action,baseline_action);np.testing.assert_array_equal(helper.call_args.kwargs['previous_action'],fixture.last_submitted17)
    record('accepted_final_descent_keeps_certificate_through_close','Actual parent choose and original CLOSE predicate; only mixed geometry stubbed, one proposal and one clock tick')

    for guard in ['geometry','joint']:
        c=current();tick=c.clock;pulse=c.last_pulse
        if guard=='joint':c.set_joint_positions(LIMITS[:,0]+.02)
        with patch.object(handoff,'propose',return_value=(closed.copy(),certificate(closed,False))) as helper:
            action,info=c.choose(x,proposal,previous)
        assert c.clock==tick+1 and c.mode=='POSE_WAIT' and info['mode']=='DESCENT_GUARD'
        assert np.array_equal(action,zero) and not info['handoff18_applied'] and c.last_pulse==pulse
        assert helper.call_count==(guard=='geometry')
        assert info['mixed_pose_submission_reason']=='descent_guard_rejected'
        c.enter('CLOSE','synthetic_same_tick_parent_close',x);assert c.mode=='POSE_WAIT'
        assert c.handoff18_events[-1]['event']=='rejected_descent_cannot_close'
    record('rejected_final_descent_cannot_close_or_move','Real final-frame parent flow and explicit same-tick CLOSE attempt; low joint margin skips geometry and mixed rejection cannot be undone')

    for accepted in [False,True]:
        c=current();c.approach_gap=abs(float(x[7]-x[8]))-.006;c.last_pulse=c.clock-100
        before=c.last_pulse;tick=c.clock
        def propose_with_original_pulse(*a,**kw):
            action=zero.copy();action[6]=kw['grip'];receipt=certificate(action,accepted);receipt['aperture_motion']=True
            return action,receipt
        with patch.object(handoff,'propose',side_effect=propose_with_original_pulse) as helper:
            action=c.pose_action(x,c.grasp_target(x),-1.)
        assert c.clock==tick and helper.call_count==1 and helper.call_args.kwargs['grip']==1.
        assert helper.call_args.kwargs['aperture_motion']
        if accepted:assert action[6]==1 and c.last_pulse==tick
        else:assert np.array_equal(action,zero) and c.last_pulse==before and c.mode=='POSE_WAIT'
    record('original_aperture_pulse_is_preserved_only_if_accepted','Real inherited pulse rule with synthetic gap error: accepted helper keeps pulse; rejection rolls timestamp back and adds no clock')

    c=current();c.approach_gap=abs(float(x[7]-x[8]))-.006;c.guard_scope=False;c.last_pulse=c.clock-100
    tick=c.clock;pulse=c.last_pulse
    original_parent=m.V17.choose
    def parent_replaces(self,*args):
        _,info=original_parent(self,*args)
        return zero.copy(),info
    def accepted_pulse(*a,**kw):
        action=baseline_action.copy();action[6]=kw['grip'];receipt=certificate(action);receipt['aperture_motion']=bool(kw['aperture_motion']);return action,receipt
    with patch.object(m.V17,'choose',parent_replaces),patch.object(handoff,'propose',side_effect=accepted_pulse) as helper:
        action,info=c.choose(x,proposal,previous)
    assert helper.call_count==1 and c.clock==tick+1 and np.array_equal(action,zero)
    assert info['mixed_pose']['accepted'] and not info['handoff18_applied']
    assert info['mixed_pose_submission_reason']=='parent_replaced_proposal' and c.last_pulse==pulse
    record('accepted_but_parent_replaced_is_not_submitted','Real parent flow followed by explicit zero-action guard stub; accepted proposal is not counted as submitted and unexecuted pulse timestamp is restored')

    for guard in ['pose','unknown','path','timeout']:
        c=current();tick=c.clock
        if guard=='pose':c.pose_anchor=x[16:23].copy();c.pose_anchor[0]+=.02
        if guard=='unknown':c.refresh_feasibility=lambda state:'unknown'
        if guard=='timeout':c.age=c.cfg.stage_timeout
        context=patch.object(v11_module,'object_margin',return_value=0.) if guard=='path' else patch.object(c,'observable_hold',wraps=c.observable_hold)
        with context,patch.object(handoff,'propose',return_value=(baseline_action.copy(),certificate(baseline_action))) as helper:
            action,info=c.choose(x,proposal,previous)
        assert c.clock==tick+1 and helper.call_count==0 and c.mode!='CLOSE' and c._handoff_pending18 is None
    record('old_pose_unknown_path_and_timeout_guards_precede_handoff','Actual parent choose with isolated invalidation predicates; original guards preempt descent helper without added clock or CLOSE')

    for reason in ['disabled','flag','no_edge','no_can_guard','other_phase']:
        c=current();c._handoff_pending18=None;c._handoff_blocked18=False
        if reason=='disabled':c.enabled=False
        if reason=='flag':c.cfg=replace(c.cfg,recenter_transition=False)
        if reason=='no_edge':c.edge_plan=None
        if reason=='no_can_guard':c.cfg=replace(c.cfg,can_guard=False)
        if reason=='other_phase':c.mode='CLOSE'
        with patch.object(handoff,'propose',side_effect=AssertionError('Helper used outside registered scope')):
            c.pose_action(x,c.grasp_target(x),0.)
        if reason=='flag':
            assert c._handoff_pending18 is not None and 'handoff21' not in c._handoff_pending18['receipt'] and 'transition19' in c._handoff_pending18['receipt']
        else:assert c._handoff_pending18 is None
    record('direction_is_scoped_and_retains_v19_when_disabled','Only enabled DESCEND with edge plan/can guard invokes A; A-off preserves actual v19 certificate path, rather than disabling protection')

    for age in [1,3,4,70]:
        c=current();c.age=age;c._previous18=fixture.last_submitted17.copy()
        tick=c.clock;goal=c.grasp_target(x)
        with patch.object(handoff,'propose',return_value=(baseline_action.copy(),certificate(baseline_action))) as helper:
            c.pose_action(x,goal,-1.)
        assert c.clock==tick and c.age==age and helper.call_count==1
        assert helper.call_args.kwargs['descent_controls']==age
        np.testing.assert_array_equal(helper.call_args.kwargs['descent_axis'],c.edge_plan['rotation'][:,2])
        np.testing.assert_array_equal(helper.call_args.kwargs['previous_action'],c._previous18)
    record('direction_uses_parent_age_axis_and_one_proposal','Real adapter sends inherited age/rotation axis/previous submitted command; direct pose call adds no tick. Helper arithmetic checked in transition_static.')

    for age in [1,3,4,70]:
        c=current();c.age=age;c._previous18=fixture.last_submitted17.copy()
        c.motion=np.array([.006,-.002,.003,.01,0,0]);tick=c.clock;goal=c.grasp_target(x)
        def certify_empty(state_x,action,**kw):
            receipt=certificate(action);receipt.pop('handoff21',None)
            receipt.update(hand_margin_m=.01,aperture_range_m=[0.,.085] if kw['aperture_motion'] else [.03,.04])
            return receipt
        with patch.object(handoff,'certify_action',side_effect=certify_empty):
            action=c.pose_action(x,goal,-1.)
        receipt=c._handoff_pending18['receipt'];assert receipt['accepted'] and c.clock==tick
        audit_handoff21(receipt,x,goal,c.goal_rotation,c.edge_plan['rotation'][:,2],c.motion,c.cfg,age)
        np.testing.assert_array_equal(action,receipt['submitted_action'])
    record('direction_independent_formula_and_angular_window','Real helper with explicit geometry stub; independent audit recomputes axial/lateral decisions and raw P/damping at ages 1/3/4/70 without modifying time')

    for phase in ['CARRY','PLACE']:
        c=current();c.cfg=replace(c.cfg,place_braking=True);c.mode=phase
        c.observable_hold=lambda *a:False;c.stable=True;c.ever_stable=True;c.lost_frames=0
        c.carry_reference=HeldEnvelope.from_state(x);c.held_offset=x[:3].astype(float)-x[16:19]
        plan=object();search=SimpleNamespace(done=False)
        if phase=='CARRY':c.carry_plan=plan;c.carry_search=search
        tick=c.clock
        for index in range(4):
            action,info=c.choose(x,proposal,closed)
            assert c.clock==tick+index+1 and c.lost_frames==index+1 and c.mode==phase
            assert info['mode']==phase+'_HOLD' and np.array_equal(action,closed)
            if phase=='CARRY':assert c.carry_plan is plan and c.carry_search is search
        c.choose(x,proposal,closed);assert c.clock==tick+5 and c.mode!=phase and c.attempts<=2
    record('new_flags_keep_original_four_frame_pause_and_fifth_loss','Only observable hold stubbed; actual CARRY/PLACE parent loss rules remain under both new flags')

    def held_controller():
        c=current(place_braking=True);c.mode='PLACE';c.set_joint_positions(LIMITS.mean(1))
        c.held_offset=x[:3].astype(float)-x[16:19]
        c.carry_checked.add(c.attempts);c.last_submitted17=closed.copy();c.motion=np.array([.006,0,0,0,0,0])
        goal=x[:3].astype(float)+[.01,0,0];rotation=Rotation.from_quat(x[3:7]).as_matrix()
        state=settling.ServoState();state.phase=repr((c.attempts,'PLACE'));state.held=True
        state.goal=goal.copy();state.rotation=rotation.copy();state.bias=np.array([.008,.002,0.]);state.last_action=closed.copy()
        c.servo17['held']=state
        return c,goal,rotation,state
    def certify_held(state,action,**kw):
        receipt=certificate(action);receipt.pop('handoff21',None)
        receipt.update(held=True,hand_margin_m=.01,carried_can_margin_m=.01,aperture_range_m=[.03,.04])
        return receipt
    c,goal,rotation,state=held_controller();old_bias=state.bias.copy();before_state=copy.deepcopy(vars(state))
    with patch.object(settling,'certify_action',side_effect=certify_held):
        action,receipt=c.propose17(x,goal,rotation,held=True,grip=1.,phase='PLACE')
    assert receipt['accepted'] and receipt['braking20']['capture_brake_axes']==[True,False,False]
    audit_braking(receipt,x,c.cfg,before_state,c.last_submitted17)
    assert receipt['position_bias_m'][0]==0 and len(c._settling_pending19)==1
    np.testing.assert_array_equal(state.bias,old_bias)
    c.commit17(action,receipt);np.testing.assert_array_equal(state.last_action,action)
    np.testing.assert_array_equal(state.bias,receipt['state_update']['bias'])
    try:c.commit17(closed,receipt)
    except AssertionError:pass
    else:raise AssertionError('B committed an uncertified replacement action')
    assert state.phase is None and state.last_action is None and not state.bias.any()
    record('braking_proposal_is_pure_and_exact_commit_required','Real helper and adapter with geometry stub: axis brake clears proposed integral only, actual action commits, replacement action clears state')

    for outcome in ['submitted','not_committed','replaced_after_commit','rejected']:
        c,goal,rotation,state=held_controller();tick=c.clock
        def parent_held_step(self,state_x,*args):
            self.clock+=1
            action,receipt=self.propose17(state_x,goal,rotation,held=True,grip=1.,phase='PLACE')
            if receipt['accepted'] and outcome not in ['not_committed']:self.commit17(action,receipt)
            if outcome in ['not_committed','replaced_after_commit','rejected']:action=closed.copy()
            return action,{'mode':'PLACE','stable_hold':True,'intervened':True,'mixed_pose':receipt,'planning_kind':'v17_held_pose'}
        def maybe_rejected(state_x,action,**kw):
            receipt=certify_held(state_x,action,**kw)
            if outcome=='rejected':receipt.update(accepted=False,reason='explicit_geometry_rejection')
            return receipt
        with patch.object(V16,'choose',parent_held_step),patch.object(settling,'certify_action',side_effect=maybe_rejected):
            action,info=c.choose(x,proposal,previous)
        assert c.clock==tick+1 and len(c.place21_events)==1
        assert info['place21_applied']==(outcome=='submitted')
        if outcome=='submitted':
            assert c._committed17;np.testing.assert_array_equal(state.last_action,action)
        else:assert not c._committed17 and state.phase is None and state.last_action is None and not state.bias.any()
    record('braking_actual_submission_and_all_parent_guard_outcomes','Parent held-step stub around real v17/v18/v19/v21 choose/commit/finally: only submitted certified action retains memory; no commit, rejection and replacement after commit clear it with one clock')

    c,goal,rotation,state=held_controller();c.mode='CARRY';c.observable_hold=lambda *a:False
    c.stable=True;c.ever_stable=True;c.lost_frames=0;c.carry_reference=HeldEnvelope.from_state(x)
    c.carry_plan=object();c.carry_search=SimpleNamespace(done=False);tick=c.clock
    state.last_action=closed.copy();c.last_submitted17=closed.copy()
    action,info=c.choose(x,proposal,closed)
    assert c.clock==tick+1 and info['mode']=='CARRY_HOLD' and np.array_equal(action,closed)
    assert state.phase is None and state.last_action is None and not state.bias.any() and not c._committed17
    record('braking_equal_zero_pose_hold_pause_clears_memory','Actual parent hold guard clears bias even when the paused command equals the preceding zero-pose closed command')

    for failed in [None,'position','angle']:
        c,goal,rotation,state=held_controller();c.mode='CARRY';goal=x[:3].astype(float)+[.0091 if failed=='position' else .008,0,0]
        if failed=='angle':rotation=Rotation.from_rotvec([0,0,.0801]).as_matrix()@rotation
        c.carry_reference=SimpleNamespace(relative_errors=lambda _:dict(position_m=0.,angle_rad=0.))
        c.carry_plan={'stages':[{'goal':goal,'rotation':rotation,'kind':'translate','label':'unit'}]}
        tick=c.clock
        with patch.object(parent_settling,'certify_action',side_effect=certify_held):
            for index in range(5):
                c.held_action17(x,{'stable_hold':True});assert c.clock==tick
                if index<4:assert c.carry_plan is not None
        assert (c.carry_plan is None)==(failed is None)
    record('braking_cannot_relax_five_frame_9mm_008rad_arrival','Actual inherited CARRY stage predicates with B scoped out; five confirmations remain necessary, 9.1mm and .0801rad do not arrive')

    # A real parent trajectory supplies the transition whose returned label is
    # PLACE although the actual controller has already entered RELEASE.
    place_rows=list(map(json.loads,(place_folder/'trace.jsonl').open(encoding='utf8')))
    place_job=read(place_folder/'result.json')['job']
    release_index=next(i for i,z in enumerate(place_rows)
                       if z['recovery']['mode']=='PLACE' and z['recovery'].get('next_mode')=='RELEASE')
    c=m.RecoveryController([.1975,.4025,.8],.8,np.asarray(place_rows[0]['state_before'],np.float32),True,
                          m.Config(**place_job['config'],recenter_transition=False,place_braking=False))
    prev=np.zeros(7,np.float32);place_fixture=None
    for z in place_rows[:release_index]:
        sx=np.asarray(z['state_before'],np.float32);c.set_joint_positions(z['joint_positions'])
        if c.mode=='PLACE' and place_fixture is None:place_fixture=(copy.deepcopy(c),z,prev.copy())
        if place_job.get('force_recovery_at')==z['step']:c.start_attempt('diagnostic_forced_start',sx)
        action,info=c.choose(sx,np.asarray(z['original_proposal'],np.float32),prev)
        saved=dict(z['recovery']);compare=dict(info);saved.pop('planning_ms',None);compare.pop('planning_ms',None)
        assert compare==saved
        np.testing.assert_allclose(action,z['submitted_action'],rtol=0,atol=1e-7)
        prev=np.asarray(z['executed_action'],np.float32)
    assert place_fixture is not None and c.mode=='PLACE'
    z=place_rows[release_index];c.set_joint_positions(z['joint_positions'])
    c.cfg=replace(c.cfg,place_braking=True);tick=c.clock
    with patch.object(settling,'propose',side_effect=AssertionError('PLACE-labelled RELEASE frame invoked B')):
        action,info=c.choose(np.asarray(z['state_before'],np.float32),np.asarray(z['original_proposal'],np.float32),prev)
    assert c.clock==tick+1 and c.mode=='RELEASE' and info['mode']=='PLACE' and info['next_mode']=='RELEASE'
    assert not c._place_pending21 and not c.place21_events and 'place21' not in info['mixed_pose']
    saved=dict(z['recovery']);compare=dict(info);saved.pop('planning_ms',None);compare.pop('planning_ms',None)
    assert compare==saved;np.testing.assert_allclose(action,z['submitted_action'],rtol=0,atol=1e-7)
    record('real_final_place_release_frame_uses_actual_v19','Saved full parent choose chain reconstructed: actual mode RELEASE preempts B despite output mode/phase PLACE; original release predicate and final command are unchanged')

    c,z,prev=place_fixture;c.cfg=replace(c.cfg,place_braking=True);tick=c.clock
    action,info=c.choose(np.asarray(z['state_before'],np.float32),np.asarray(z['original_proposal'],np.float32),prev)
    assert c.clock==tick+1 and len(c.place21_events)==1 and len(c._place_pending21)==1
    meta=info['place21'];assert meta['actual_mode_at_proposal']==meta['controller_mode']==meta['phase']=='PLACE' and meta['held']
    assert info['mixed_pose']['accepted'] and info['place21_applied'] and c._committed17
    np.testing.assert_array_equal(action,info['mixed_pose']['submitted_action'])
    record('real_place_scope_certified_commit_single_clock','No helper, geometry, hold or parent stub: an actual saved PLACE state invokes B only in the double-PLACE scope and commits the certified final float32 command')

    assert all(sha(ROOT/rel)==digest for rel,digest in hashes.items()),'Source changed during checks'
    result={'passed':True,'checks':checks,'source_sha256':hashes,'new_evaluation_samples':0,'physical_simulation_run':False,
            'saved_fixture_controls_replayed':final_index+1,'fixture_source':folder.relative_to(ROOT).as_posix(),
            'saved_place_fixture_controls_replayed':release_index+1,'place_fixture_source':place_folder.relative_to(ROOT).as_posix(),
            'scope':'v21 integration with saved v19 final-descent state and explicit geometry/predicate stubs. Independent helper static and subsequent physical/decision gates are still required.'}
    with output.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({'passed':True,'check_groups':len(checks),'new_evaluation_samples':0}))
if __name__=='__main__':main()
