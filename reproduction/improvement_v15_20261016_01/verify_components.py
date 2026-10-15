"""Focused enabled-branch checks using saved inputs and explicit unit stubs.

No simulator, trained model or new evaluation samples are run. Stub geometry
isolates rejection/control-flow logic; it is not a geometric or physics proof.
"""
from pathlib import Path
from unittest.mock import patch
import argparse,hashlib,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery import recovery_controller as m
from recovery import carry_path as cp
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='components_a');args=parser.parse_args()
    output=RUN/'analysis'/f'{args.name}.json';assert not output.exists()
    source=ROOT/'reproduction/improvement_v14_20261016_01/smoke_b/v14_known13_bc_k2_noise005_demo_13000021/trace.jsonl'
    row=next(r for r in map(json.loads,source.open()) if r['step']==312)
    x=np.array(row['state_before'],np.float32);r=Rotation.from_quat(x[3:7]).as_matrix();mid=LIMITS.mean(1)
    paths=list((RUN/'recovery').glob('*.py'))+[RUN/'verify_components.py',source]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths};checks=[]
    def record(name,scope):checks.append({'name':name,'passed':True,'scope':scope});print(name,flush=True)
    def controller(**flags):
        cfg=m.Config(**{'carry_path':False,'segmented_edge':False,'budget_recenter':False,**flags})
        c=m.RecoveryController([.1975,.4025,.8],.8,x,True,cfg);c.set_joint_positions(mid)
        c.attempts=1;c.approach_gap=abs(float(x[7]-x[8]));c.goal_rotation=r.copy();c.held_offset=x[:3].astype(float)-x[16:19]
        return c
    def setup_edge():
        c=controller(segmented_edge=True);c.mode='EDGE_PRETRANSLATE';c.pose_anchor=x[16:23].copy();c.plan_anchor=x[16:23].copy()
        c.edge_plan={'pre_goal':x[:3].copy(),'pre_rotation':r.copy(),'rotation':r.copy()};c.gap_ready=lambda _:True
        c.checked_empty_translation=lambda *a:(np.zeros(7,np.float32),.01,.01)
        return c
    # Real helper: perpendicular observed velocity cannot bend the certified line.
    c=controller(segmented_edge=True);c.motion[:3]=[0,.2,0];goal=x[:3]+[.02,0,0]
    action,box,can=c.checked_empty_translation(x,goal,r)
    assert action[0]>0 and np.max(abs(action[1:]))==0 and np.isfinite([box,can]).all()
    turn_goal=Rotation.from_rotvec([0,0,.12]).as_matrix()@r
    action,box,can=c.checked_empty_translation(x,goal,turn_goal)
    assert np.max(abs(action[:3]))==0 and np.linalg.norm(action[3:6])>0 and action[6]==0
    record('empty_translation_and_turn_exclusive','Real geometry helper on saved state; checks nominal command shape, not acceptance or physics')
    # Rejected candidate must not leak the already computed nonzero command.
    with patch.object(m,'support',return_value=({'kind':'wall_top'},'unit')):
        for field in ['hand','can','joint']:
            c=setup_edge();candidate=np.array([.3,0,0,0,0,0,0],np.float32)
            c.checked_empty_translation=lambda *a:(candidate.copy(),.0005 if field=='hand' else .01,.0005 if field=='can' else .01)
            if field=='joint':c.set_joint_positions(LIMITS[:,0]+.02)
            before=c.clock;action,info=c.segmented_action(x)
            assert c.clock==before+1 and np.array_equal(action,np.zeros(7)) and c.mode!='EDGE_PRETRANSLATE'
        c=setup_edge()
        for i in range(5):
            action,info=c.segmented_action(x);assert c.clock==i+1
            assert c.mode==('EDGE_ROTATE' if i==4 else 'EDGE_PRETRANSLATE')
        for failed in ['position','angle','gap']:
            c=setup_edge()
            if failed=='position':c.edge_plan['pre_goal']=x[:3]+[.01,0,0]
            if failed=='angle':c.edge_plan['pre_rotation']=Rotation.from_rotvec([0,0,.09]).as_matrix()@r
            if failed=='gap':c.gap_ready=lambda _:False
            for _ in range(5):c.segmented_action(x)
            assert c.mode=='EDGE_PRETRANSLATE' and c.clock==5
    record('segmented_rejection_and_five_frame_arrival','Stub positive/negative margins and support; checks 1mm/joint guards, zero rejected commands, 9mm/.08rad/gap and one clock tick')
    # Unit arrival decision only: enter is a recorder, not a substitute for the
    # inherited feasibility checks exercised by full-stage replay.
    for failed in [None,'forecast','tail','gap']:
        c=controller(budget_recenter=True);c.mode='EDGE_APPROACH';c.edge_plan={'above':x[:3].copy(),'rotation':r.copy()}
        c.gap_ready=lambda _:failed!='gap';c.grasp_target=lambda _:x[:3].copy()
        c.enter=lambda mode,reason,state:setattr(c,'mode',mode)
        if failed=='forecast':c.motion[:3]=[.01,0,0]
        with patch.object(m,'object_margin',return_value=.0029 if failed=='tail' else .0031):
            for i in range(5):
                action,info=c.edge_action(x);assert c.clock==i+1
                if i<4:assert c.mode=='EDGE_APPROACH'
        assert c.mode==('DESCEND' if failed is None else 'EDGE_APPROACH')
    record('budget_shared_arrival_protection','Stub tail clearance and transition recorder; forecast,3mm,gap,5frames remain required and each call advances one tick')
    # Use the real parent choose to count consecutive failed holding observations.
    c=controller(carry_path=True);c.mode='CARRY';c.stable=True;c.ever_stable=True
    c.observable_hold=lambda *a:False;plan=object();search=object();c.carry_plan=plan;c.carry_search=search
    previous=np.array([0,0,0,0,0,0,1],np.float32)
    for i in range(4):
        action,info=c.choose(x,np.zeros(7,np.float32),previous)
        assert c.clock==i+1 and c.lost_frames==i+1 and info['mode']=='CARRY_HOLD' and c.mode=='CARRY'
        assert c.carry_plan is plan and c.carry_search is search and np.array_equal(action[:6],np.zeros(6)) and action[6]==1
    action,info=c.choose(x,np.zeros(7,np.float32),previous)
    assert c.clock==5 and c.mode!='CARRY' and c.carry_plan is None and c.carry_search is None
    assert any(e['reason']=='observed_grasp_loss' for e in c.events) and c.attempts<=2
    record('transient_hold_preserves_path_real_parent_loss_guard','Real inherited choose with only observable_hold stubbed false; path retained for four frames, parent recovery on fifth')
    # Fast current-pose option must validate BOTH exact parent endpoints.
    for outcomes in [[True,True],[True,False]]:
        created=[]
        class FakeIK:
            def __init__(self,q,goal,rotation,limit):
                self.q=np.array(q);self.goal=np.array(goal);self.rotation=np.array(rotation);self.index=len(created);created.append(self)
                self.done=False;self.iterations=0
            def advance(self,n):self.iterations+=1;self.done=True
            def receipt(self):return {'success':outcomes[self.index],'limit_margin_rad':.05,'iterations':self.iterations}
        c=controller(carry_path=True);c.goal_rotation=turn_goal.copy();c.held_offset=np.array([.01,.02,.03])
        with patch.object(cp,'IK',FakeIK),patch.object(cp,'candidates',return_value=[('current',r.copy())]):
            search=cp.CarryPathSearch(c,x,mid)
            assert not search.advance(1) and search.chosen is None and len(search.receipt['prefilter_ik'])==1
            assert search.advance(1) and len(created)==2
        for ik,height in zip(created,[c.floor+c.cfg.carry_clearance_m,c.floor+.085]):
            np.testing.assert_array_equal(ik.goal,np.r_[c.target[:2],height]+c.held_offset)
            np.testing.assert_array_equal(ik.rotation,c.goal_rotation)
        if outcomes[-1]:assert search.chosen['preserve_current'] and len(search.chosen['endpoint_ik'])==2
        else:assert search.chosen is None
    record('current_pose_both_exact_parent_endpoints','Instant IK stub isolates endpoint sequencing; failed placement IK cannot preserve current route')
    # Parent placement action can contain rotation; new checked mode separates it.
    def parent_place(self,state,proposal,previous):
        self.clock+=1;self.age+=1;self.mode='PLACE'
        return np.array([.1,.2,-.1,.1,.2,.1,1],np.float32),{'mode':'PLACE','next_mode':'PLACE','stable_hold':True,'intervened':True}
    certificate={'accepted':True,'hand_margin_m':.01,'carried_can_margin_m':.01}
    for turn in [False,True]:
        c=controller(carry_path=True);c.carry_reference=cp.HeldEnvelope.from_state(x);c.goal_rotation=turn_goal.copy() if turn else r.copy()
        with patch.object(m.V14,'choose',parent_place),patch.object(m,'translation_certificate',return_value=certificate),patch.object(m,'rotation_certificate',return_value=certificate) as rotate:
            action,info=c.choose(x,np.zeros(7,np.float32),previous)
        assert c.clock==1 and action[6]==1
        if turn:assert np.array_equal(action[:3],np.zeros(3)) and rotate.call_count==1
        else:assert np.array_equal(action[3:6],np.zeros(3)) and rotate.call_count==0
    record('placement_translation_rotation_exclusive','Stub parent action and accepted certificates; ensures one clock and no unchecked simultaneous translation/rotation')
    assert all(sha(ROOT/p)==h for p,h in hashes.items()),'Source changed during enabled-component checks'
    result={'passed':True,'checks':checks,'source_sha256':hashes,'new_evaluation_samples':0,'physical_simulation_run':False,
            'scope':'Focused enabled control-flow tests. Geometry/IK stubs are explicitly identified; no claim of physical success, generality, or full-arm safety.'}
    with output.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps({'passed':True,'check_groups':len(checks),'new_evaluation_samples':0}))
if __name__=='__main__':main()
