"""v19 integration predicates on saved inputs with explicit geometry stubs.

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
from recovery import transition as handoff,carry_search,settling
from reproduction.improvement_v18_20261019_01.recovery.recovery_controller import Config as C18
from reproduction.improvement_v15_20261016_01.recovery.carry_path import HeldEnvelope
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
from reproduction.improvement_v11_20261015_01.recovery import recovery_controller as v11_module
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import RecoveryController as V16
FLAGS=['transition_window','candidate_budget','terminal_settling']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='components_a');args=parser.parse_args()
    output=RUN/'analysis'/f'{args.name}.json';assert not output.exists()
    folder=ROOT/'reproduction/improvement_v18_20261019_01/smoke_a/v18_regression_6000005'
    rows=list(map(json.loads,(folder/'trace.jsonl').open(encoding='utf8')));job=read(folder/'result.json')['job']
    final_index=next(i for i,row in enumerate(rows) if row['recovery']['mode']=='DESCEND' and row['recovery'].get('next_mode')=='CLOSE')
    paths=[p for p in (RUN/'recovery').iterdir() if p.suffix in ['.py','.json']]
    paths += [Path(__file__).resolve(),RUN/'protocols/smoke_jobs.json',folder/'result.json',folder/'trace.jsonl']
    for version in range(6,19):
        for directory in (ROOT/'reproduction').glob(f'improvement_v{version}_*/recovery'):
            paths += [p for p in directory.iterdir() if p.suffix in ['.py','.json']]
    paths += list((ROOT/'reproduction/recovery_v5_20261012_01').glob('*.py'))
    hashes={path.relative_to(ROOT).as_posix():sha(path) for path in sorted(set(paths))};checks=[]
    def record(name,scope):
        checks.append({'name':name,'passed':True,'scope':scope});print(name,flush=True)
    configs=read(RUN/'protocols/smoke_jobs.json')
    parents={j['id'][len(j['version'])+1:]:j for j in configs if j['version']=='v18'}
    assert len(asdict(C18()))==108 and len(asdict(m.Config()))==111
    for j in configs:
        if j['version'] not in ['transition','candidate','settling','ab','v19']:continue
        parent=parents[j['id'][len(j['version'])+1:]]['config'];current=asdict(m.Config(**j['config']))
        assert all(current[k]==value for k,value in parent.items())
        assert current['transition_window']==(j['version'] in ['transition','ab','v19'])
        assert current['candidate_budget']==(j['version'] in ['candidate','ab','v19'])
        assert current['terminal_settling']==(j['version'] in ['settling','v19'])
    record('all_108_parent_fields_and_single_flags_exact','Real nine-profile configs: full v18 retained in each repair, original clearance profile retained')
    from variants import controller_class
    for version,module in [('v17','improvement_v17_20261019_01'),('v18','improvement_v18_20261019_01'),('budget','improvement_v15_20261016_01')]:
        cls,cfg=controller_class(version);assert module in cls.__module__ and module in cfg.__module__
    record('baselines_use_actual_frozen_classes','Actual v17/v18 and original v15 budget class, not fake v19 flag configurations')

    c=m.RecoveryController([.1975,.4025,.8],.8,np.asarray(rows[0]['state_before'],np.float32),True,
                           m.Config(**job['config'],transition_window=False,candidate_budget=False,terminal_settling=False))
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
        controller=copy.deepcopy(fixture);settings=dict(transition_window=True,candidate_budget=False,terminal_settling=False);settings.update(flags)
        controller.cfg=replace(controller.cfg,**settings)
        controller.set_joint_positions(row['joint_positions']);return controller
    def certificate(action,accepted=True):
        return {'kind':'mixed_pose','accepted':accepted,'held':False,'work':4,'work_units':4,'trials':[],
                'reason':'explicit_geometry_stub','box_margin_m':.01 if accepted else None,
                'can_margin_m':.01 if accepted else None,'required_can_margin_m':.001,
                'translation_m':(action[:3].astype(float)*.05).tolist(),'rotation_vector_rad':(action[3:6].astype(float)*.5).tolist(),
                'submitted_action':action.tolist(),'aperture_motion':False,'handoff_feedback':True,'servo_bias_used':False,
                'transition19':{'window_active':fixture.age+1<=3,'descent_controls':fixture.age+1,'window_controls':3}}
    baseline=copy.deepcopy(fixture);baseline.set_joint_positions(row['joint_positions'])
    baseline_action,baseline_info=baseline.choose(x,proposal,previous)
    assert baseline.mode=='CLOSE' and baseline_info['mode']=='DESCEND'
    np.testing.assert_allclose(baseline_action,row['submitted_action'],rtol=0,atol=1e-7)
    record('saved_final_descent_fixture_exact','Actual parent control flow reconstructed from saved v18 inputs and commands through the final DESCEND to CLOSE frame')

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
        if reason=='flag':c.cfg=replace(c.cfg,transition_window=False)
        if reason=='no_edge':c.edge_plan=None
        if reason=='no_can_guard':c.cfg=replace(c.cfg,can_guard=False)
        if reason=='other_phase':c.mode='CLOSE'
        with patch.object(handoff,'propose',side_effect=AssertionError('Helper used outside registered scope')):
            c.pose_action(x,c.grasp_target(x),0.)
        if reason=='flag':
            assert c._handoff_pending18 is not None and 'transition19' not in c._handoff_pending18['receipt']
        else:assert c._handoff_pending18 is None
    record('transition_is_scoped_and_retains_v18_when_disabled','Only enabled DESCEND with edge plan/can guard invokes A; A-off preserves actual v18 certificate path, rather than disabling protection')

    for age in [1,3,4,70]:
        c=current();c.age=age;c._previous18=fixture.last_submitted17.copy();c.motion=np.array([.006,0,0,.01,0,0])
        tick=c.clock;goal=c.grasp_target(x);rotation=c.goal_rotation.copy()
        # Certificate stub isolates control law and accounting; the independent
        # transition static checker validates actual mixed geometry.
        def certify_empty(state,action,**kw):
            receipt=certificate(action);receipt.update(hand_margin_m=.01,aperture_range_m=[0.,.085] if kw['aperture_motion'] else [.03,.04])
            receipt.pop('transition19',None);return receipt
        with patch.object(handoff,'certify_action',side_effect=certify_empty):
            action=c.pose_action(x,goal,-1.)
        receipt=c._handoff_pending18['receipt'];window=receipt['transition19']
        assert c.clock==tick and c.age==age and receipt['accepted']
        assert window['descent_controls']==age and window['window_active']==(age<=3) and window['window_controls']==3
        expected=c.cfg.position_gain*(goal-x[:3])-(c.cfg.tracking_velocity_damping*c.motion[:3] if age<=3 else 0)
        np.testing.assert_allclose(receipt['raw_translation_m'],expected,rtol=0,atol=1e-12)
        assert np.linalg.norm(action[:3].astype(float)*.05-c._previous18[:3]*.05)<=c.cfg.max_delta_m/3+1e-8
        assert np.linalg.norm(action[3:6].astype(float)*.5-c._previous18[3:6]*.5)<=c.cfg.max_rotation_rad/3+1e-8
    record('transition_three_control_window_keeps_certification_and_slew','Real helper arithmetic and adapter, geometry stub only: age 1/3 damp, age 4/70 use P; caller clock/age, caps and slew remain unchanged')

    # The real carry adapter uses a bounded search stub, preserving parent hold
    # logic and pending-route transition checks without doing physical rollout.
    c=current();c.cfg=replace(c.cfg,candidate_budget=True,terminal_settling=True);c.mode='CARRY'
    c.carry_checked.discard(c.attempts);c.carry_search=None;c.carry_plan=None;c.set_joint_positions(LIMITS.mean(1))
    class FakeSearch:
        def __init__(self,*a):
            self.envelope=HeldEnvelope.from_state(x);self.done=False;self.work=0;self.x=x.copy();self.q=LIMITS.mean(1);self.chosen=None;self.receipts=[]
        def advance(self,units):self.work+=1;return False
    tick=c.clock
    with patch.object(carry_search,'CarryPathSearch',side_effect=FakeSearch) as factory:
        for _ in range(3):
            action,info=c.carry_action(x,closed.copy(),{'mode':'CARRY','stable_hold':True})
            assert info['mode']=='CARRY_PLAN' and np.array_equal(action,closed) and c.clock==tick
    assert factory.call_count==1 and c.carry_reference is c.carry_search.envelope and c.carry_search.work==3
    assert len([event for event in c.budget19_events if event['event']=='bounded_optional_search_started'])==1
    c.enter('PLACE','above_target',x);assert c.mode=='CARRY'
    record('bounded_candidate_search_once_per_attempt_preserves_reference','Explicit unfinished search stub; real adapter keeps envelope and pending-route PLACE protection, no extra tick')

    for phase in ['CARRY','PLACE']:
        c=current();c.cfg=replace(c.cfg,candidate_budget=True,terminal_settling=True);c.mode=phase
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
    record('new_flags_keep_original_four_frame_pause_and_fifth_loss','Only observable hold stubbed; actual CARRY/PLACE parent loss rules remain under all three new flags')

    def held_controller():
        c=current(terminal_settling=True);c.mode='CARRY';c.set_joint_positions(LIMITS.mean(1))
        c.carry_checked.add(c.attempts);c.last_submitted17=closed.copy();c.motion=np.array([.006,0,0,0,0,0])
        goal=x[:3].astype(float)+[.01,0,0];rotation=Rotation.from_quat(x[3:7]).as_matrix()
        state=settling.ServoState();state.phase=repr((c.attempts,'CARRY_unit'));state.held=True
        state.goal=goal.copy();state.rotation=rotation.copy();state.bias=np.array([.008,.002,0.]);state.last_action=closed.copy()
        c.servo17['held']=state
        return c,goal,rotation,state
    def certify_held(state,action,**kw):
        receipt=certificate(action);receipt.pop('transition19',None)
        receipt.update(held=True,hand_margin_m=.01,carried_can_margin_m=.01,aperture_range_m=[.03,.04])
        return receipt
    c,goal,rotation,state=held_controller();old_bias=state.bias.copy()
    with patch.object(settling,'certify_action',side_effect=certify_held):
        action,receipt=c.propose17(x,goal,rotation,held=True,grip=1.,phase='CARRY_unit')
    assert receipt['accepted'] and receipt['settling19']['integral_brake_axes']==[True,False,False]
    assert receipt['position_bias_m'][0]==0 and len(c._settling_pending19)==1
    np.testing.assert_array_equal(state.bias,old_bias)
    c.commit17(action,receipt);np.testing.assert_array_equal(state.last_action,action)
    np.testing.assert_array_equal(state.bias,receipt['state_update']['bias'])
    try:c.commit17(closed,receipt)
    except AssertionError:pass
    else:raise AssertionError('C committed an uncertified replacement action')
    assert state.phase is None and state.last_action is None and not state.bias.any()
    record('settling_proposal_is_pure_and_exact_commit_required','Real helper and adapter with geometry stub: axis brake clears proposed integral only, actual action commits, replacement action clears state')

    for outcome in ['submitted','not_committed','replaced_after_commit','rejected']:
        c,goal,rotation,state=held_controller();tick=c.clock
        def parent_held_step(self,state_x,*args):
            self.clock+=1
            action,receipt=self.propose17(state_x,goal,rotation,held=True,grip=1.,phase='CARRY_unit')
            if receipt['accepted'] and outcome not in ['not_committed']:self.commit17(action,receipt)
            if outcome in ['not_committed','replaced_after_commit','rejected']:action=closed.copy()
            return action,{'mode':'CARRY_PATH','stable_hold':True,'intervened':True,'mixed_pose':receipt,'planning_kind':'v17_held_pose'}
        def maybe_rejected(state_x,action,**kw):
            receipt=certify_held(state_x,action,**kw)
            if outcome=='rejected':receipt.update(accepted=False,reason='explicit_geometry_rejection')
            return receipt
        with patch.object(V16,'choose',parent_held_step),patch.object(settling,'certify_action',side_effect=maybe_rejected):
            action,info=c.choose(x,proposal,previous)
        assert c.clock==tick+1 and len(c.settling19_events)==1
        assert info['settling19_applied']==(outcome=='submitted')
        if outcome=='submitted':
            assert c._committed17;np.testing.assert_array_equal(state.last_action,action)
        else:assert not c._committed17 and state.phase is None and state.last_action is None and not state.bias.any()
    record('settling_actual_submission_and_all_parent_guard_outcomes','Parent held-step stub around real v17/v18/v19 choose/commit/finally: only submitted certified action retains memory; no commit, rejection and replacement after commit clear it with one clock')

    c,goal,rotation,state=held_controller();c.observable_hold=lambda *a:False
    c.stable=True;c.ever_stable=True;c.lost_frames=0;c.carry_reference=HeldEnvelope.from_state(x)
    c.carry_plan=object();c.carry_search=SimpleNamespace(done=False);tick=c.clock
    state.last_action=closed.copy();c.last_submitted17=closed.copy()
    action,info=c.choose(x,proposal,closed)
    assert c.clock==tick+1 and info['mode']=='CARRY_HOLD' and np.array_equal(action,closed)
    assert state.phase is None and state.last_action is None and not state.bias.any() and not c._committed17
    record('settling_equal_zero_pose_hold_pause_clears_memory','Actual parent hold guard clears bias even when the paused command equals the preceding zero-pose closed command')

    for failed in [None,'position','angle']:
        c,goal,rotation,state=held_controller();goal=x[:3].astype(float)+[.0091 if failed=='position' else .008,0,0]
        if failed=='angle':rotation=Rotation.from_rotvec([0,0,.0801]).as_matrix()@rotation
        c.carry_reference=SimpleNamespace(relative_errors=lambda _:dict(position_m=0.,angle_rad=0.))
        c.carry_plan={'stages':[{'goal':goal,'rotation':rotation,'kind':'translate','label':'unit'}]}
        tick=c.clock
        with patch.object(settling,'certify_action',side_effect=certify_held):
            for index in range(5):
                c.held_action17(x,{'stable_hold':True});assert c.clock==tick
                if index<4:assert c.carry_plan is not None
        assert (c.carry_plan is None)==(failed is None)
    record('settling_cannot_relax_five_frame_9mm_008rad_arrival','Actual inherited stage predicates around new C helper; five confirmations remain necessary, 9.1mm and .0801rad do not arrive')

    assert all(sha(ROOT/rel)==digest for rel,digest in hashes.items()),'Source changed during checks'
    result={'passed':True,'checks':checks,'source_sha256':hashes,'new_evaluation_samples':0,'physical_simulation_run':False,
            'saved_fixture_controls_replayed':final_index+1,'fixture_source':folder.relative_to(ROOT).as_posix(),
            'scope':'v19 integration with saved v18 final-descent state and explicit geometry/predicate/search stubs. Independent helper static and subsequent physical/decision gates are still required.'}
    with output.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({'passed':True,'check_groups':len(checks),'new_evaluation_samples':0}))
if __name__=='__main__':main()
