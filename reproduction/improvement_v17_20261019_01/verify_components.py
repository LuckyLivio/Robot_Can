"""Focused v17 integration checks using saved inputs and explicit stubs.

No simulator, physical rollout, training or success-rate sample is used here.
Geometry stubs isolate control flow; they do not certify physical safety.
"""
from pathlib import Path
from dataclasses import asdict
from unittest.mock import patch
from types import SimpleNamespace
import argparse,hashlib,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery import recovery_controller as m
from recovery import pose_servo as servo
from recovery import carry_search as search_module
from reproduction.improvement_v16_20261016_01.recovery import recovery_controller as parent_module
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import Config as C16
from reproduction.improvement_v15_20261016_01.recovery.carry_path import HeldEnvelope
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
FLAGS=['route_efficiency','edge_convergence','held_stability']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='components_a');args=parser.parse_args()
    output=RUN/'analysis'/f'{args.name}.json';assert not output.exists(),output
    source=ROOT/'reproduction/improvement_v16_20261016_01/smoke_a/v16_known13_bc_k2_noise005_demo_13000021/trace.jsonl'
    rows=list(map(json.loads,source.open(encoding='utf8')))
    row=next(row for row in rows if row['recovery']['mode']=='CARRY_PLAN')
    x=np.asarray(row['state_before'],np.float32);rotation=Rotation.from_quat(x[3:7]).as_matrix();mid=LIMITS.mean(1)
    paths=list((RUN/'recovery').glob('*.py'))+[Path(__file__).resolve(),source]
    for v in [15,16]:paths+=list((ROOT/f'reproduction/improvement_v{v}_20261016_01/recovery').glob('*.py'))
    hashes={path.relative_to(ROOT).as_posix():sha(path) for path in paths};checks=[]
    def record(name,scope):checks.append({'name':name,'passed':True,'scope':scope});print(name,flush=True)
    def controller(**flags):
        c=m.RecoveryController([.1975,.4025,.8],.8,x,True,m.Config(**{**{k:False for k in FLAGS},**flags}))
        c.set_joint_positions(mid);c.attempts=1;c.approach_gap=abs(float(x[7]-x[8]));c.goal_rotation=rotation.copy()
        c.held_offset=x[:3].astype(float)-x[16:19];c.stable=True;c.ever_stable=True
        return c
    closed=np.array([0,0,0,0,0,0,1],np.float32)
    opened=np.zeros(7,np.float32)
    def receipt(*,held=False,accepted=True,action=None,aperture=False):
        action=(closed if held else opened) if action is None else action
        return {'kind':'mixed_pose','accepted':accepted,'held':held,'work':4,'work_units':4,
                'box_margin_m':.01 if accepted else None,'can_margin_m':.01 if accepted else None,
                'required_can_margin_m':.001,'translation_m':(action[:3].astype(float)*.05).tolist(),
                'rotation_vector_rad':(action[3:6].astype(float)*.5).tolist(),'submitted_action':action.tolist(),
                'position_error_m':0.,'orientation_error_rad':0.,'aperture_motion':aperture,
                'aperture_range_m':[0.,.085] if aperture else [.03,.04],'reason':'explicit_test_stub'}
    original=asdict(C16());assert len(original)==103
    for flags in [{},{'route_efficiency':True},{'edge_convergence':True},{'held_stability':True},{k:True for k in FLAGS}]:
        config=asdict(controller(**flags).cfg);assert len(config)==106
        assert all(config[name]==value for name,value in original.items())
    record('all_103_inherited_fields_exact','Real Config values for disabled, each single repair and full v17')

    for phase in ['CARRY','PLACE']:
        c=controller(held_stability=True,route_efficiency=True);c.mode=phase;c.observable_hold=lambda *a:False
        c.carry_reference=HeldEnvelope.from_state(x)
        plan=object();search=SimpleNamespace(done=False)
        if phase=='CARRY':c.carry_plan=plan;c.carry_search=search
        for index in range(4):
            action,info=c.choose(x,opened,closed)
            assert c.clock==index+1 and c.lost_frames==index+1 and c.mode==phase
            assert info['mode']==phase+'_HOLD' and np.array_equal(action,closed)
            if phase=='CARRY':assert c.carry_plan is plan and c.carry_search is search
        c.choose(x,opened,closed)
        assert c.clock==5 and c.mode!=phase and c.attempts<=2
    record('carry_and_place_keep_original_five_frame_loss','Only hold observation stubbed; actual choose and parent loss guards retain route during four-frame pause and recover on fifth')

    for phase in ['CARRY','PLACE']:
        c=controller(held_stability=True);c.mode=phase;c.observable_hold=lambda *a:False
        c.carry_reference=HeldEnvelope.from_state(x)
        if phase=='CARRY':c.carry_plan=object();c.carry_search=SimpleNamespace(done=False)
        state=servo.ServoState();state.bias=np.array([.005,0,0]);state.phase='same_phase'
        state.last_action=closed.copy();c.servo17['held']=state;c.last_submitted17=closed.copy()
        action,info=c.choose(x,opened,closed)
        assert info['mode']==phase+'_HOLD' and np.array_equal(action,closed) and c.clock==1
        assert not c._committed17 and state.phase is None and state.last_action is None and not state.bias.any()
    record('equal_zero_pose_pause_explicitly_resets_bias','Real choose with only hold observation stubbed: identical previous/paused zero-pose closed commands still clear feedback memory in CARRY_HOLD and PLACE_HOLD')

    for guard in ['joint','relative','timeout','certificate']:
        c=controller(held_stability=True);c.mode='CARRY';c.carry_checked.add(c.attempts)
        c.carry_reference=SimpleNamespace(relative_errors=lambda _:dict(position_m=.02 if guard=='relative' else 0.,angle_rad=0.))
        c.carry_plan={'stages':[{'goal':x[:3].copy(),'rotation':rotation.copy(),'kind':'translate','label':'unit'}]}
        if guard=='joint':c.set_joint_positions(LIMITS[:,0]+.02)
        if guard=='timeout':c.carry_phase_age=c.cfg.stage_timeout
        with patch.object(c,'propose17',return_value=(closed.copy(),receipt(held=True,accepted=False))) as propose,patch.object(c,'commit17') as commit:
            action,info=c.held_action17(x,{'stable_hold':True})
        assert c.clock==0 and np.array_equal(action,closed) and info['mode']=='CARRY_GUARD' and c.mode!='CARRY'
        assert propose.call_count==(1 if guard=='certificate' else 0) and not commit.called
    record('held_guards_and_postprocessor_clock','Stub relative/certificate; inherited joint .04rad, relative .012m and 70-step limits protect motion; carry postprocessor adds no clock tick')

    # Local edge fixtures avoid interpreting this saved held observation as a
    # real supported edge configuration. This isolates transition predicates.
    def edge_controller(phase):
        c=controller(edge_convergence=True);c.mode=phase;c.edge_start=x[:3].copy()
        c.edge_plan={'pre_goal':x[:3].copy(),'pre_rotation':rotation.copy(),'rotation':rotation.copy(),'above':x[:3].copy()}
        c.pose_changed=lambda _:False;c.gap_ready=lambda _:True;c.grasp_target=lambda _:x[:3].copy()
        return c
    support=({'kind':'wall_top'},'explicit_stub')
    for phase in ['EDGE_PRETRANSLATE','EDGE_ROTATE','EDGE_APPROACH']:
        for guard in ['joint','timeout','pose','support','certificate']:
            c=edge_controller(phase)
            if guard=='joint':c.set_joint_positions(LIMITS[:,0]+.02)
            if guard=='timeout':c.age=c.cfg.stage_timeout
            if guard=='pose':c.pose_changed=lambda _:True
            domain=(None,'explicit_stub') if guard=='support' else support
            with patch.object(m,'support',return_value=domain),patch.object(m,'support13',return_value=domain),patch.object(c,'propose17',return_value=(opened.copy(),receipt(accepted=False))) as propose,patch.object(c,'commit17') as commit:
                action,info=c.edge_action17(x)
            assert c.clock==1 and np.array_equal(action,opened) and c.mode not in [phase,'DESCEND']
            assert propose.call_count==(1 if guard=='certificate' else 0) and not commit.called
    record('edge_protections_single_clock_all_three_phases','Stub support/pose/geometry; true joint/time and control-flow guards prevent motion/descent and advance exactly once')

    for phase in ['EDGE_PRETRANSLATE','EDGE_ROTATE','EDGE_APPROACH']:
        for failed in [None,'position','angle','gap']+(['forecast','tail'] if phase=='EDGE_APPROACH' else []):
            c=edge_controller(phase)
            goalkey='pre_goal' if phase=='EDGE_PRETRANSLATE' else 'above'
            rotkey='pre_rotation' if phase=='EDGE_PRETRANSLATE' else 'rotation'
            if failed=='position':
                if phase=='EDGE_ROTATE':c.edge_start=x[:3]+[.01,0,0]
                else:c.edge_plan[goalkey]=x[:3]+[.01,0,0]
            if failed=='angle':c.edge_plan[rotkey]=Rotation.from_rotvec([0,0,.081]).as_matrix()@rotation
            if failed=='gap':c.gap_ready=lambda _:False
            if failed=='forecast':c.motion[:3]=[.01,0,0]
            # Actual V5.enter is retained for PRETRANSLATE/ROTATE; DESCEND
            # entry is recorded because feasibility is a separate replay test.
            c.enter=lambda mode,reason,state:setattr(c,'mode',mode)
            with patch.object(m,'support',return_value=support),patch.object(m,'support13',return_value=support),patch.object(c,'propose17',return_value=(opened.copy(),receipt(aperture=failed=='gap'))) as propose,patch.object(c,'commit17') as commit,patch.object(m,'object_margin',return_value=.0029 if failed=='tail' else .0031):
                for index in range(5):
                    c.edge_action17(x);assert c.clock==index+1
                    if index<4:assert c.mode==phase
            expected={'EDGE_PRETRANSLATE':'EDGE_ROTATE','EDGE_ROTATE':'EDGE_APPROACH','EDGE_APPROACH':'DESCEND'}[phase] if failed is None else phase
            assert c.mode==expected and propose.call_count==commit.call_count==5
    record('edge_arrival_five_consecutive_frames_and_original_thresholds','Stub geometry/feasibility; each edge transition retains position .009, angle .08, gap and five-frame rules; approach additionally requires D2 .009 and 3mm tail')

    c=edge_controller('EDGE_APPROACH');c.gap_ready=lambda _:False
    c.approach_gap=abs(float(x[7]-x[8]))-.01;c.last_pulse=-100;c.edge_settled=4
    rejected=receipt(accepted=False,aperture=True)
    with patch.object(m,'support',return_value=support),patch.object(m,'support13',return_value=support),patch.object(c,'propose17',return_value=(closed.copy(),rejected)) as propose,patch.object(c,'commit17') as commit:
        action,info=c.edge_action17(x)
    assert c.clock==1 and info['mode']=='EDGE_APERTURE' and c.mode=='EDGE_APPROACH'
    assert np.array_equal(action,closed) and not info['mixed_pose']['accepted'] and c.edge_settled==0
    assert propose.call_count==1 and not commit.called and info['planning_work_units']==4 and c.last_pulse==1
    record('rejected_full_aperture_proposal_uses_one_parent_pulse','Stub mixed rejection; one proposal only, no pose motion, original gap pulse/settling, rejected proposal never committed')

    c=edge_controller('EDGE_PRETRANSLATE');c.gap_ready=lambda _:False
    c.approach_gap=abs(float(x[7]-x[8]))-.01;c.last_pulse=-100
    action=np.array([.1,0,0,0,0,0,1],np.float32);accepted=receipt(action=action,aperture=True)
    with patch.object(m,'support',return_value=support),patch.object(c,'propose17',return_value=(action.copy(),accepted)) as propose,patch.object(c,'commit17') as commit:
        submitted,info=c.edge_action17(x)
    assert c.clock==1 and np.array_equal(submitted,action) and c.last_pulse==1 and c.edge_settled==0
    assert propose.call_args.kwargs['aperture_motion'] and commit.call_count==1
    np.testing.assert_array_equal(commit.call_args.args[0],submitted)
    record('certified_aperture_motion_commits_submitted_command','Stub full-range positive certificate; exact action and pulse submitted once; unmet gap still prevents arrival')

    c=controller(held_stability=True);c.mode='CARRY';c.carry_checked.add(c.attempts)
    c.carry_reference=SimpleNamespace(relative_errors=lambda _:dict(position_m=0.,angle_rad=0.))
    c.carry_plan={'stages':[{'goal':x[:3].copy(),'rotation':rotation.copy(),'kind':'translate','label':'direct_transport'}]}
    with patch.object(c,'propose17',return_value=(closed.copy(),receipt(held=True))),patch.object(c,'commit17'):
        for index in range(5):
            c.held_action17(x,{'stable_hold':True})
            assert c.clock==0
            if index<4:assert c.carry_plan is not None and c.carry_index==0
    assert c.carry_plan is None and c.carry_index==1 and c.carry_reference is not None
    record('short_transport_keeps_reference_and_five_frame_arrival','Stub positive pose certificate; direct stage cannot skip four waits or discard carried-relative reference')

    c=controller(held_stability=True);c.mode='CARRY';c.carry_checked.add(c.attempts)
    c.carry_reference=SimpleNamespace(relative_errors=lambda _:dict(position_m=0.,angle_rad=0.))
    c.carry_plan={'stages':[{'goal':x[:3].copy(),'rotation':rotation.copy(),'kind':'translate','label':'direct_transport'}]}
    c.carry_settled=4;c.carry_phase_age=23
    with patch.object(c,'propose17',return_value=(closed.copy(),receipt(held=True))),patch.object(c,'commit17'):
        c.carry_action(x,closed.copy(),{'mode':'CARRY','stable_hold':True})
    assert c.carry_plan is None and c.carry_tail17=={'attempt':1,'age':24,'segment':'direct_transport'}
    record('terminal_metadata_preserves_last_segment_age','Stub valid pose; real fifth confirmation copies elapsed segment age before reset rather than creating a fresh timeout allowance')

    def terminal_controller(flag):
        c=controller(**{flag:True});c.mode='CARRY';c.carry_checked.add(c.attempts)
        c.carry_reference=SimpleNamespace(relative_errors=lambda _:dict(position_m=0.,angle_rad=0.))
        c.transport16={'carry_goal':x[:3].astype(float)+[.01,0,0],'place_goal':x[:3].copy(),'rotation':rotation.copy()}
        c.transport16_attempt=c.attempts;c.carry_tail17={'attempt':c.attempts,'age':69,'segment':'direct_transport'}
        c.observable_hold=lambda *a:True
        return c
    tail_action=np.array([.1,0,0,0,0,0,1],np.float32);tail_receipt=receipt(held=True,action=tail_action)
    for flag in ['route_efficiency','held_stability']:
        c=terminal_controller(flag)
        with patch.object(c,'propose17',return_value=(tail_action.copy(),tail_receipt)) as new_proposal,patch.object(m,'propose16',return_value=(tail_action.copy(),tail_receipt)) as old_proposal,patch.object(c,'commit17') as commit:
            action,info=c.terminal_carry17(x,{'mode':'CARRY','stable_hold':True},c.transport16)
            assert np.array_equal(action,tail_action) and info['terminal_route'] and info['terminal_phase_age']==70 and c.clock==0
            assert info['mixed_pose']==tail_receipt and c.mode=='CARRY'
            action,info=c.terminal_carry17(x,{'mode':'CARRY','stable_hold':True},c.transport16)
        assert np.array_equal(action,closed) and info['mode']=='CARRY_GUARD' and c.mode!='CARRY' and c.clock==0
        assert old_proposal.call_count+new_proposal.call_count==1 and commit.call_count==(flag=='held_stability')
    record('terminal_age70_allowed_71_guarded','Stub positive mixed proposal; old servo for route-only/new servo for held-only, same final segment timeout across terminal continuation, no extra postprocessor clock')

    for flag in ['route_efficiency','held_stability']:
        for guard in ['metadata','wrong_attempt','joint','relative','certificate']:
            c=terminal_controller(flag)
            if guard=='metadata':c.carry_tail17=None
            if guard=='wrong_attempt':c.carry_tail17['attempt']=0
            if guard=='joint':c.set_joint_positions(LIMITS[:,0]+.02)
            if guard=='relative':c.carry_reference=SimpleNamespace(relative_errors=lambda _:dict(position_m=.02,angle_rad=0.))
            with patch.object(c,'propose17',return_value=(closed.copy(),receipt(held=True,accepted=False))) as new_proposal,patch.object(m,'propose16',return_value=(closed.copy(),receipt(held=True,accepted=False))) as old_proposal,patch.object(c,'commit17') as commit:
                action,info=c.terminal_carry17(x,{'mode':'CARRY','stable_hold':True},c.transport16)
            assert np.array_equal(action,closed) and info['mode']=='CARRY_GUARD' and c.mode!='CARRY' and c.clock==0
            assert old_proposal.call_count+new_proposal.call_count==(1 if guard=='certificate' else 0) and not commit.called
    record('terminal_missing_metadata_joint_relative_and_geometry_rejected','Stub geometry/relative error; unconfirmed tail, stale attempt and original guards never submit uncertified motion')

    for low_margin in [False,True]:
        c=terminal_controller('route_efficiency')
        if low_margin:c.set_joint_positions(LIMITS[:,0]+.02)
        assert np.linalg.norm(x[16:18]-c.target[:2])>=.045
        with patch.object(m,'propose16',return_value=(tail_action.copy(),tail_receipt)) as propose:
            action,info=c.choose(x,np.array([.8,0,0,0,0,0,1],np.float32),closed)
        assert c.clock==1
        if low_margin:assert np.array_equal(action,closed) and info['mode']=='CARRY_GUARD' and not propose.called
        else:assert np.array_equal(action,tail_action) and info['mode']=='CARRY_PATH' and info['terminal_route'] and propose.call_count==1
    record('real_choose_cannot_fall_back_to_uncertified_terminal_carry','Saved non-target can pose plus hold/geometry stubs; actual choose replaces original nonzero policy with certified tail or joint-guard stop, exactly one clock tick')

    c=controller(route_efficiency=True,held_stability=True);c.mode='CARRY';c.carry_plan=object()
    c.enter('PLACE','above_target',x);assert c.mode=='CARRY'
    c.carry_plan=None;c.carry_search=object();c.enter('PLACE','above_target',x);assert c.mode=='CARRY'
    c.carry_search=None;c.enter('PLACE','above_target',x);assert c.mode=='PLACE'
    c.lost_frames=1;c.enter('RELEASE','at_release_height',x);assert c.mode=='PLACE'
    c.lost_frames=0;c.enter('RELEASE','at_release_height',x);assert c.mode=='RELEASE'
    record('parent_place_release_transition_guards_retained','Real parent enter checks block pending-route PLACE and transient-hold-loss RELEASE')

    for guard in ['joint','relative','certificate']:
        c=controller(held_stability=True);c.mode='PLACE'
        c.carry_reference=SimpleNamespace(relative_errors=lambda _:dict(position_m=.02 if guard=='relative' else 0.,angle_rad=0.))
        if guard=='joint':c.set_joint_positions(LIMITS[:,0]+.02)
        with patch.object(c,'propose17',return_value=(closed.copy(),receipt(held=True,accepted=False))) as propose,patch.object(c,'commit17') as commit:
            action,info=c.placement_action16(x,closed.copy(),{'mode':'PLACE','stable_hold':True})
        assert c.clock==0 and c.mode!='PLACE' and info['mode']=='CARRY_GUARD' and np.array_equal(action,closed)
        assert propose.call_count==(1 if guard=='certificate' else 0) and not commit.called
    record('place_joint_relative_and_certificate_guards','Stub relative/geometry; original PLACE guards reject to closed zero motion without extra clock or memory commit')

    c=controller(held_stability=True);c.mode='PLACE';c.carry_reference=SimpleNamespace(relative_errors=lambda _:dict(position_m=0.,angle_rad=0.))
    def final_place(self,state,proposal,previous):
        self.clock+=1;self.mode='RELEASE'
        return closed.copy(),{'mode':'PLACE','next_mode':'RELEASE','stable_hold':True,'intervened':True}
    final_action=np.array([.1,0,0,0,0,.1,1],np.float32);final_receipt=receipt(held=True,action=final_action)
    with patch.object(parent_module.V14,'choose',final_place),patch.object(c,'propose17',return_value=(final_action.copy(),final_receipt)) as propose,patch.object(c,'commit17') as commit:
        action,info=c.choose(x,opened,closed)
    assert c.clock==1 and c.mode=='RELEASE' and info['mode']=='PLACE' and propose.call_count==commit.call_count==1
    np.testing.assert_array_equal(action,final_action);assert info['mixed_pose']==final_receipt
    record('last_place_command_still_protected_after_release_transition','Stub parent transition/geometry; terminal PLACE command remains certified and committed exactly once')

    c=controller(held_stability=True);goal=x[:3].astype(float)+[.01,0,0]
    state=servo.ServoState();state.phase=repr((c.attempts,'CARRY_unit'));state.held=True
    state.goal=goal.copy();state.rotation=rotation.copy();state.bias=np.array([.008,0,0])
    state.last_action=np.array([.2,0,0,0,0,0,1],np.float32)
    c.servo17['held']=state;c.last_submitted17=closed.copy()
    envelope=SimpleNamespace(vertices=np.array([[.02,0,0],[-.02,0,0]]),sweep_margin=lambda *a:.1)
    with patch.object(servo,'_hand_box_translation_envelope',return_value=.1),patch.object(servo.HeldEnvelope,'from_state',return_value=envelope):
        action,cert=c.propose17(x,goal,rotation,held=True,grip=1.,phase='CARRY_unit')
    assert cert['accepted'] and cert['state_reset_reason']=='interrupted_by_uncertified_command'
    np.testing.assert_allclose(cert['position_bias_m'],[.001,0,0],rtol=0,atol=1e-12)
    np.testing.assert_array_equal(state.bias,[.008,0,0])
    c.commit17(action,cert);np.testing.assert_array_equal(state.last_action,action)
    np.testing.assert_allclose(state.bias,[.001,0,0],rtol=0,atol=1e-12)
    try:c.commit17(closed,cert)
    except AssertionError:pass
    else:raise AssertionError('Controller accepted memory commit for an uncertified replacement action')
    assert state.last_action is None and state.phase is None and not state.bias.any()
    record('held_pause_invalidates_old_bias_and_only_exact_submission_commits','Real helper/adapter with stub separators: changed submitted hold resets prior phase bias, proposals do not mutate, exact commit updates and replaced action clears memory')

    c=controller(held_stability=True);state=servo.ServoState();state.bias[:]=.005;state.phase='old'
    c.servo17['held']=state
    with patch.object(servo,'propose',return_value=(closed.copy(),receipt(held=True,accepted=False))):
        c.propose17(x,goal,rotation,held=True,grip=1.,phase='CARRY_unit')
    assert state.phase is None and not state.bias.any() and state.last_action is None
    record('rejected_helper_proposal_clears_controller_bias','Stub failed helper; real propose17 adapter explicitly resets uncommitted state')

    # Call the real integration adapter around a fake bounded search. It must
    # create at most one search for an attempt and keep its observed envelope.
    c=controller(route_efficiency=True);c.mode='CARRY'
    class FakeSearch:
        def __init__(self,*a):
            self.envelope=HeldEnvelope.from_state(x);self.done=False;self.work=0;self.x=x.copy();self.q=mid.copy();self.chosen=None;self.receipts=[]
        def advance(self,units):self.work+=1;return False
    with patch.object(search_module,'CarryPathSearch',side_effect=FakeSearch) as factory:
        for _ in range(3):
            action,info=c.carry_action(x,closed.copy(),{'mode':'CARRY','stable_hold':True})
            assert info['mode']=='CARRY_PLAN' and np.array_equal(action,closed) and c.clock==0
    assert factory.call_count==1 and c.carry_reference is c.carry_search.envelope and c.carry_search.work==3
    record('one_bounded_route_search_per_attempt','Stub bounded unfinished search; real route factory/inherited advance keeps reference and never starts a repeated search within one attempt')

    assert all(sha(ROOT/rel)==digest for rel,digest in hashes.items()),'Source changed during checks'
    result={'passed':True,'checks':checks,'source_sha256':hashes,'new_evaluation_samples':0,'physical_simulation_run':False,
            'scope':'Focused v17 integration branches using one saved observation and explicit support, geometry, hold and search stubs. Independent helper static tests and closed-loop gates remain necessary.'}
    with output.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({'passed':True,'check_groups':len(checks),'new_evaluation_samples':0}))
if __name__=='__main__':main()
