"""Focused v16 component/control-flow checks; saved inputs and explicit stubs.

No physical rollout, trained model, success-rate sample or simulator is used.
Geometry stubs isolate acceptance/rejection logic and never prove collision safety.
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
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import Config as C15
from reproduction.improvement_v15_20261016_01.recovery.carry_path import HeldEnvelope
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='components_a');args=parser.parse_args()
    output=RUN/'analysis'/f'{args.name}.json';assert not output.exists(),output
    source=ROOT/'reproduction/improvement_v15_20261016_01/smoke_a/v15_known13_bc_k2_noise005_demo_13000021/trace.jsonl'
    rows=list(map(json.loads,source.open(encoding='utf8')))
    row=next(row for row in rows if row['recovery']['mode']=='CARRY_PLAN')
    x=np.asarray(row['state_before'],np.float32);rotation=Rotation.from_quat(x[3:7]).as_matrix();mid=LIMITS.mean(1)
    paths=list((RUN/'recovery').glob('*.py'))+[Path(__file__).resolve(),source]
    paths+=list((ROOT/'reproduction/improvement_v15_20261016_01/recovery').glob('*.py'))
    hashes={path.relative_to(ROOT).as_posix():sha(path) for path in paths};checks=[]
    def record(name,scope):checks.append({'name':name,'passed':True,'scope':scope});print(name,flush=True)
    def controller(**flags):
        config=m.Config(**{'ik_continuation':False,'held_pose':False,'edge_stability':False,**flags})
        c=m.RecoveryController([.1975,.4025,.8],.8,x,True,config);c.set_joint_positions(mid)
        c.attempts=1;c.approach_gap=abs(float(x[7]-x[8]));c.goal_rotation=rotation.copy()
        c.held_offset=x[:3].astype(float)-x[16:19];c.stable=True;c.ever_stable=True
        return c
    # Every inherited field must stay exact for all single-repair/full variants.
    original=asdict(C15())
    for flags in [{},{'ik_continuation':True},{'held_pose':True},{'edge_stability':True},dict(ik_continuation=True,held_pose=True,edge_stability=True)]:
        config=asdict(controller(**flags).cfg);assert len(original)==100
        assert all(config[name]==value for name,value in original.items())
    record('all_100_inherited_config_fields_exact','Real Config values for off, single-repair and full configurations')
    # Real finite-observation motion computation; no future state is consumed.
    previous=x.astype(float).copy();previous[:3]-=[.002,-.003,.001]
    previous[3:7]=Rotation.from_matrix(Rotation.from_rotvec([0,0,-.02]).as_matrix()@rotation).as_quat()
    motion=servo.observed_motion(x,previous)
    np.testing.assert_allclose(motion,[.002,-.003,.001,0,0,.02],atol=1e-12)
    record('observed_motion_units','Translation/rotation increments recovered from two saved-shaped observations, not simulated future feedback')
    # Stub positive separators isolate quantization, mixed axes and work caps.
    goal=x[:3]+[.20,.05,0];desired=Rotation.from_rotvec([0,0,.4]).as_matrix()@rotation
    envelope=SimpleNamespace(vertices=np.array([[.02,0,0],[-.02,0,0]]),sweep_margin=lambda *a:.05)
    for held in [False,True]:
        with patch.object(servo,'_hand_box_translation_envelope',return_value=.05),patch.object(servo,'object_margin',return_value=.05),patch.object(servo.HeldEnvelope,'from_state',return_value=envelope):
            action,receipt=servo.propose(x,goal,desired,np.zeros(6),m.Config(),held=held,grip=float(held))
        assert receipt['accepted'] and 0<receipt['work']<=16
        assert np.linalg.norm(action[:3])>0 and np.linalg.norm(action[3:6])>0 and action[6]==float(held)
        np.testing.assert_array_equal(action[:3].astype(float)*.05,receipt['translation_m'])
        np.testing.assert_array_equal(action[3:6].astype(float)*.5,receipt['rotation_vector_rad'])
        assert np.linalg.norm(receipt['translation_m'])<=.035 and np.linalg.norm(receipt['rotation_vector_rad'])<=.15
    record('mixed_quantized_command_matches_certificate','Stub separators; real damped proposal, float32 decoded motion, original 35mm/.15rad limits and bounded certificate loop')
    for guard in ['hand','can']:
        with patch.object(servo,'_hand_box_translation_envelope',return_value=0. if guard=='hand' else .05),patch.object(servo,'object_margin',return_value=0. if guard=='can' else .05):
            action,receipt=servo.propose(x,goal,desired,np.zeros(6),m.Config(),held=False)
        assert not receipt['accepted'] and np.array_equal(action,np.zeros(7)) and receipt['work']<=16
    with patch.object(servo,'_hand_box_translation_envelope',return_value=.05),patch.object(servo,'object_margin',return_value=.002):
        execution=servo.mixed_certificate(x,np.zeros(3),np.zeros(3),can_margin_m=.001)
        planning=servo.mixed_certificate(x,np.zeros(3),np.zeros(3),can_margin_m=.003)
    assert execution['accepted'] and not planning['accepted']
    limited=servo.mixed_certificate(x,np.zeros(3),np.zeros(3),work_limit=1)
    assert not limited['accepted'] and limited['work']==0
    try:servo.mixed_certificate(x,np.zeros(3),np.zeros(3),can_margin_m=.0009)
    except ValueError:pass
    else:raise AssertionError('Lowered clearance threshold accepted')
    record('mixed_geometry_rejection_and_fixed_thresholds','Stub separators; rejected zero motion, strict 1mm execution/3mm planning and insufficient-work rejection')
    # Real inherited loss counting must continue during a held-pose pause.
    c=controller(held_pose=True);c.mode='CARRY';c.observable_hold=lambda *a:False
    plan=object();search=object();c.carry_plan=plan;c.carry_search=search
    previous_action=np.array([0,0,0,0,0,0,1],np.float32)
    for index in range(4):
        action,info=c.choose(x,np.zeros(7,np.float32),previous_action)
        assert c.clock==index+1 and c.lost_frames==index+1 and info['mode']=='CARRY_HOLD'
        assert c.carry_plan is plan and c.carry_search is search and np.array_equal(action[:6],np.zeros(6)) and action[6]==1
    c.choose(x,np.zeros(7,np.float32),previous_action)
    assert c.clock==5 and c.mode!='CARRY' and c.carry_plan is None and c.carry_search is None and c.attempts<=2
    record('holding_pause_retains_route_and_parent_loss_guard','Only observable_hold stubbed; actual parent choose increments clock/loss once and recovers on fifth failed hold observation')
    # Direct postprocessor checks never advance clock; choose owns that tick.
    for guard in ['joint','relative','timeout','certificate']:
        c=controller(held_pose=True);c.mode='CARRY';c.carry_checked.add(c.attempts)
        c.carry_reference=SimpleNamespace(relative_errors=lambda _:dict(position_m=.02 if guard=='relative' else 0.,angle_rad=0.))
        c.carry_plan={'stages':[{'goal':goal,'rotation':desired,'kind':'rotate','label':'unit'}]}
        if guard=='joint':c.set_joint_positions(LIMITS[:,0]+.02)
        if guard=='timeout':c.carry_phase_age=c.cfg.stage_timeout
        rejected={'kind':'mixed_pose','accepted':False,'held':True,'work':0,'box_margin_m':None,'can_margin_m':None,'required_can_margin_m':.001,'reason':'unit_rejected'}
        with patch.object(m,'propose',return_value=(previous_action.copy(),rejected)) as propose:
            action,info=c.carry_action(x,np.ones(7,np.float32),{'stable_hold':True})
        assert c.clock==0 and np.array_equal(action,previous_action) and info['mode']=='CARRY_GUARD' and c.mode!='CARRY' and c.attempts<=2
        assert propose.call_count==(1 if guard=='certificate' else 0)
    record('held_negative_guards_keep_closed_zero_motion','Stub relative transform/certificate; joint .04rad, relative .012m and stage70 guard before proposing; postprocessor never adds a clock tick')
    # Empty edge guards use exactly one hold tick; no descent on rejection.
    for guard in ['joint','timeout','certificate']:
        c=controller(edge_stability=True);c.mode='EDGE_ROTATE';c.edge_start=x[:3].copy()
        c.edge_plan={'rotation':rotation.copy(),'above':x[:3].copy()}
        c.gap_ready=lambda _:True
        if guard=='joint':c.set_joint_positions(LIMITS[:,0]+.02)
        if guard=='timeout':c.age=c.cfg.stage_timeout
        rejected={'kind':'mixed_pose','accepted':False,'held':False,'work':0,'box_margin_m':None,'can_margin_m':None,'required_can_margin_m':.001,'reason':'unit_rejected'}
        with patch.object(m,'propose',return_value=(np.zeros(7,np.float32),rejected)) as propose:
            action,info=c.mixed_edge_action(x)
        assert c.clock==1 and np.array_equal(action,np.zeros(7)) and c.mode not in ['EDGE_ROTATE','DESCEND']
        assert propose.call_count==(1 if guard=='certificate' else 0)
    record('empty_edge_negative_guards_single_clock','Stub rejected certificate; real joint/time branch and hold advance exactly one clock tick and never descend')
    accepted={'kind':'mixed_pose','accepted':True,'held':False,'work':0,'box_margin_m':.01,'can_margin_m':.01,
              'required_can_margin_m':.001,'translation_m':[0.,0.,0.],'rotation_vector_rad':[0.,0.,0.],'reason':'unit_accepted'}
    for failed in [None,'position','angle','gap','forecast','tail']:
        c=controller(edge_stability=True);c.mode='EDGE_APPROACH'
        c.edge_plan={'rotation':Rotation.from_rotvec([0,0,.09]).as_matrix()@rotation if failed=='angle' else rotation.copy(),
                     'above':x[:3]+([.01,0,0] if failed=='position' else [0,0,0])}
        c.gap_ready=lambda _:failed!='gap';c.grasp_target=lambda _:x[:3].copy()
        c.enter=lambda mode,reason,state:setattr(c,'mode',mode)
        if failed=='forecast':c.motion[:3]=[.01,0,0]
        with patch.object(m,'propose',return_value=(np.zeros(7,np.float32),accepted)),patch.object(m,'object_margin',return_value=.0029 if failed=='tail' else .0031):
            for index in range(5):
                c.mixed_edge_action(x);assert c.clock==index+1
                if index<4:assert c.mode=='EDGE_APPROACH'
        assert c.mode==('DESCEND' if failed is None else 'EDGE_APPROACH')
    record('edge_arrival_requires_all_five_protections','Stub accepted geometry and enter recorder; 9mm/.08rad/gap/D2 forecast/3mm path all remain required for five consecutive frames; actual descent feasibility is audited in complete-stage replay')
    # The parent can cancel an accepted candidate after its separate joint guard.
    c=controller(edge_stability=True);c.mode='EDGE_PRETRANSLATE';c.gap_ready=lambda _:True
    c.edge_plan={'pre_goal':x[:3]+[.01,0,0],'pre_rotation':rotation.copy(),'rotation':rotation.copy()}
    c.plan_anchor=x[16:23].copy();c.pose_anchor=x[16:23].copy();c.set_joint_positions(LIMITS[:,0]+.02)
    candidate=np.array([.2,0,0,0,0,0,0],np.float32)
    certified={**accepted,'translation_m':(candidate[:3].astype(float)*.05).tolist()}
    with patch.object(m,'propose',return_value=(candidate,certified)),patch('reproduction.improvement_v15_20261016_01.recovery.recovery_controller.support',return_value=({'kind':'wall_top'},'unit')):
        action,info=c.segmented_action(x)
    assert c.clock==1 and np.array_equal(action,np.zeros(7)) and info['mixed_pose']['accepted']
    assert info['mixed_pose_applied'] is False and info['mixed_pose_submission_reason']=='parent_joint_or_pose_guard'
    record('accepted_candidate_cancelled_by_parent_joint_guard','Stub positive geometry and support; real parent joint guard returns zero and labels candidate as unapplied')
    # Aperture adjustment is a separate zero-pose tick, never a mixed command.
    c=controller(edge_stability=True);c.mode='EDGE_ROTATE';c.edge_start=x[:3].copy()
    c.edge_plan={'rotation':rotation.copy(),'above':x[:3].copy()};c.gap_ready=lambda _:False
    c.approach_gap=abs(float(x[7]-x[8]))-.01;c.last_pulse=-100
    with patch.object(m,'propose') as propose:
        action,info=c.mixed_edge_action(x)
    assert c.clock==1 and info['mode']=='EDGE_APERTURE' and np.array_equal(action[:6],np.zeros(6)) and action[6]==1
    assert not propose.called and 'mixed_pose' not in info and c.edge_settled==0
    record('aperture_tick_has_no_pose_certificate','Stub gap-not-ready; inherited close pulse is separated from motion and increments only one tick')
    # Keep a pending route and transient hold loss from skipping phase guards.
    for flag in ['ik_continuation','held_pose']:
        c=controller(**{flag:True});c.mode='CARRY';c.carry_plan=object()
        c.enter('PLACE','above_target',x);assert c.mode=='CARRY'
        c.carry_plan=None;c.enter('PLACE','above_target',x);assert c.mode=='PLACE'
    c=controller(held_pose=True);c.mode='PLACE';c.lost_frames=1
    c.enter('RELEASE','at_release_height',x);assert c.mode=='PLACE'
    c.lost_frames=0;c.enter('RELEASE','at_release_height',x);assert c.mode=='RELEASE'
    record('route_and_release_transition_guards','Real enter checks: pending IK/held route blocks PLACE; transient observed loss blocks height-only release')
    c=controller(held_pose=True);c.mode='PLACE';c.observable_hold=lambda *a:False;c.carry_reference=HeldEnvelope.from_state(x)
    for index in range(4):
        action,info=c.choose(x,np.zeros(7,np.float32),previous_action)
        assert c.clock==index+1 and c.lost_frames==index+1 and info['mode']=='PLACE_HOLD' and c.mode=='PLACE'
        assert np.array_equal(action[:6],np.zeros(6)) and action[6]==1
    c.choose(x,np.zeros(7,np.float32),previous_action)
    assert c.clock==5 and c.mode!='PLACE' and c.attempts<=2
    record('place_hold_parent_five_frame_loss','Only observable_hold stubbed; real parent PLACE hold-loss counter reaches recovery on fifth frame')
    c=controller(held_pose=True);c.mode='PLACE';c.carry_reference=SimpleNamespace(relative_errors=lambda _:dict(position_m=0.,angle_rad=0.))
    def last_place(self,state,proposal,previous):
        self.clock+=1;self.mode='RELEASE'
        return previous_action.copy(),{'mode':'PLACE','next_mode':'RELEASE','stable_hold':True,'intervened':True}
    final_action=np.array([.1,0,0,0,0,.1,1],np.float32)
    final_receipt={**accepted,'held':True,'translation_m':(final_action[:3].astype(float)*.05).tolist(),
                   'rotation_vector_rad':(final_action[3:6].astype(float)*.5).tolist()}
    with patch.object(m.V14,'choose',last_place),patch.object(m,'propose',return_value=(final_action,final_receipt)) as propose:
        action,info=c.choose(x,np.zeros(7,np.float32),previous_action)
    assert c.clock==1 and c.mode=='RELEASE' and info['mode']=='PLACE' and propose.call_count==1
    assert np.array_equal(action,final_action) and info['mixed_pose']==final_receipt
    record('final_place_command_still_certified','Stub parent transition and certificate; final PLACE action receives its mixed certificate even after state advances to RELEASE')
    geometry={'accepted':True,'hand_margin_m':.01,'carried_can_margin_m':.01}
    for outcome in ['accepted','margin','unconverged','budget']:
        created=[]
        class FakeIK:
            def __init__(self,q,goal,desired,limit):
                self.initial=np.asarray(q).copy();self.q=self.initial.copy();self.done=False;self.iterations=0;created.append(self)
            def advance(self,units):
                assert units==1;self.iterations+=1
                if outcome!='budget':self.done=True;self.q=self.initial+.001
            def receipt(self):return {'success':outcome!='unconverged','limit_margin_rad':.039 if outcome=='margin' else .05,'iterations':self.iterations}
        c=controller(ik_continuation=True)
        with patch.object(search_module,'IK',FakeIK),patch.object(search_module,'_translation',return_value=geometry),patch.object(search_module,'_rotation_sample',return_value=geometry):
            search=search_module.CarryPathSearch(c,x,mid)
            while not search.done:
                before=search.work;search.advance(16)
                assert 0<=search.work-before<=16 and search.last_geometry_work<=4 and search.calls<=24
        assert search.work<=384 and search.calls<=24 and created
        if outcome=='accepted':
            assert search.chosen is not None and search.status=='validated'
            for first,second in zip(created,created[1:]):np.testing.assert_array_equal(first.q,second.initial)
            np.testing.assert_array_equal(search.chosen['carry_goal'],search.chosen['stages'][-1]['goal'])
            np.testing.assert_array_equal(search.chosen['place_goal'],search.chosen['placement']['goal'])
        else:assert search.chosen is None and search.status=='unknown'
    record('continuation_seed_chain_limits_and_unknown_failures','Stub local IK and separators; real search reuses previous accepted joint solution, locks actual endpoints and rejects insufficient margin/unconverged/budget with unknown status')
    assert all(sha(ROOT/rel)==digest for rel,digest in hashes.items()),'Source changed during checks'
    result={'passed':True,'checks':checks,'source_sha256':hashes,'new_evaluation_samples':0,'physical_simulation_run':False,
            'scope':'Focused enabled control-flow and nominal servo tests; all stubs stated. Does not establish physical recovery, independent generalization or full-arm collision safety.'}
    with output.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({'passed':True,'check_groups':len(checks),'new_evaluation_samples':0}))
if __name__=='__main__':main()
