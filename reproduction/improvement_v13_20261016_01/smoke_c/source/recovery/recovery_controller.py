"""v13: stable non-upright support eligibility and one bounded wait escape."""
from dataclasses import dataclass
import time
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v12_20261015_01.recovery.recovery_controller import RecoveryController as V12,Config as C12
from reproduction.improvement_v11_20261015_01.recovery.recovery_controller import RecoveryController as V11
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5
from reproduction.improvement_v7_20261015_01.recovery.pose_guard import difference,feasibility
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK
from reproduction.improvement_v11_20261015_01.recovery.path_search import sweep_margin
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin
from .support import support
from .search import Search,PathSearch

@dataclass(frozen=True)
class Config(C12):
    stable_support:bool=True
    wait_escape:bool=True
    escape_wait_steps:int=40
    escape_min_remaining:int=180
    escape_max_replans:int=1
    escape_raise_m:float=.08
    escape_timeout:int=36

class RecoveryController(V12):
    def __init__(self,*args,**kwargs):
        if len(args)<5 and kwargs.get('config') is None:kwargs['config']=Config()
        super().__init__(*args,**kwargs)
        self.support13=False;self.support13_events=[];self.escape_events=[]
        self.wait_since=None;self.escape_count=0;self.escape_stage=None;self.escape_ik=None
        self.support13_path_checked=False

    def raw_settled(self,x):
        return len(self.poses)>=self.cfg.pose_stable_frames and all(
            d<=self.cfg.pose_stable_position_m and a<=np.deg2rad(self.cfg.pose_stable_axis_deg)
            for d,a in [difference(p,x[16:23]) for p in self.poses])

    def plan_grasp(self,x):
        self.support13=False;self.support13_path_checked=False
        super().plan_grasp(x)
        if not self.cfg.stable_support or feasibility(self,x)[0]!='unknown':return
        domain,reason=support(x,self.floor)
        if domain is None or 'patches' not in domain:return
        self.support13=True;self.mesh_search=Search(self,x,domain);self.search_anchor=x[16:23].copy()
        self.guard_scope=False;self.plan_ok=True
        self.support13_events.append({'step':self.clock,'event':'support_candidate','kind':domain['kind'],
                                      'patches':domain['patches'],'candidates':len(self.mesh_search.opts)})
        self.refresh_feasibility(x)

    def refresh_feasibility(self,x):
        if not getattr(self,'support13',False):return super().refresh_feasibility(x)
        domain,reason=support(x,self.floor)
        if self.mesh_search is not None:status,reason='unknown','support13_search_pending'
        elif domain is None:status='unknown'
        elif not self.raw_settled(x):status,reason='unknown','support13_pose_not_stable'
        elif not self.plan_ok or self.kinematic_blocked:status,reason='infeasible','support13_no_validated_path'
        else:status,reason='feasible','support13_stable_hand_candidate'
        self.feasibility_status=status;self.feasibility_reason=reason;return status

    def begin_wait(self,reason,x):
        if self.mode not in ['POSE_WAIT','POSE_BLOCKED']:self.wait_since=self.clock
        self.support13_path_checked=False
        return super().begin_wait(reason,x)

    def try_escape(self,x):
        if not self.cfg.wait_escape or self.mode not in ['POSE_WAIT','POSE_BLOCKED','BLOCKED']:return
        since=self.wait_since if self.wait_since is not None else self.clock-self.age
        if (self.clock-since<self.cfg.escape_wait_steps or self.escape_count>=self.cfg.escape_max_replans
            or self.cfg.horizon_steps-self.clock<self.cfg.escape_min_remaining or self.stable
            or not self.raw_settled(x) or self.joints is None):return
        self.escape_count+=1
        rotation=Rotation.from_quat(x[3:7]).as_matrix();gap=abs(float(x[7]-x[8]))
        goal=x[:3].astype(float).copy()
        # The inherited wait may already have retracted to a clear height.
        # Do not spend a second full 8cm retreat when that work is complete.
        required=max(self.floor+.24,x[18]+.14)
        goal[2]=min(1.25,x[2]+self.cfg.escape_raise_m,max(required,x[2]))
        self.escape_already_elevated=bool(goal[2]-x[2]<.002)
        margin=sweep_margin(x[:3],goal,rotation,min(.085,gap+.002))
        can=object_margin(x[:3],goal,rotation,[max(0,gap-.002),min(.085,gap+.002)],x)
        self.escape_events.append({'step':self.clock,'event':'retreat_check','hand_margin_m':margin,'can_margin_m':can,
                                   'remaining':self.cfg.horizon_steps-self.clock})
        if margin<.001 or can<.001:return
        self.escape_goal=goal;self.escape_rotation=rotation;self.escape_anchor=x[16:23].copy()
        self.escape_ik=IK(self.joints,goal,rotation,self.cfg.ik_iterations_per_target)
        self.escape_stage='ik';self.escape_age=0;self.escape_settled=0
        self.mesh_search=self.joint_search=self.edge_search=None;self.edge_plan=None

    def escape_action(self,x):
        self.escape_age+=1
        action,info=self.hold(x,'wait_escape',0)
        if self.escape_stage=='ik':
            self.escape_ik.advance(self.cfg.ik_iterations_per_step)
            info['planning_work_units']=self.cfg.ik_iterations_per_step
            if self.escape_ik.done:
                receipt=self.escape_ik.receipt();ok=receipt['success'] and receipt['limit_margin_rad']>=self.cfg.joint_solution_margin_rad
                self.escape_events.append({'step':self.clock,'event':'retreat_ik','accepted':ok,'ik':receipt})
                if ok:self.escape_stage='settle' if self.escape_already_elevated else 'move'
                else:self.escape_stage=None
        else:
            self.goal_rotation=self.escape_rotation
            gap=abs(float(x[7]-x[8]));margin=sweep_margin(x[:3],self.escape_goal,self.escape_rotation,min(.085,gap+.002))
            can=object_margin(x[:3],self.escape_goal,self.escape_rotation,[max(0,gap-.002),min(.085,gap+.002)],x)
            if margin<.001 or can<.001:
                self.escape_events.append({'step':self.clock,'event':'retreat_invalidated'});self.escape_stage=None
            else:
                action=np.zeros(7,np.float32) if self.escape_stage=='settle' else V5.pose_action(self,x,self.escape_goal,0.)
                info.update(mode='WAIT_ESCAPE',retreat_hand_margin_m=margin,retreat_can_margin_m=can,
                            retreat_already_elevated=self.escape_already_elevated)
                at=(x[2]>=max(self.floor+.24,x[18]+.14)-.014 if self.escape_stage=='settle'
                    else np.linalg.norm(x[:3]-self.escape_goal)<.012)
                self.escape_settled=self.escape_settled+1 if at else 0
                if self.escape_settled>=self.cfg.delay+3:
                    self.escape_stage=None;self.waypoint=self.escape_goal.copy()
                    self.relocated_attempts.add(self.attempts)
                    self.retreat_stage='arrived';self.pose_replans+=1
                    self.plan_grasp(x)
                    self.escape_events.append({'step':self.clock,'event':'retreated_replanned','feasibility':self.feasibility_status})
                    V5.enter(self,'RETRACT','wait_escape_replan',x)
        if self.escape_age>=self.cfg.escape_timeout and self.escape_stage is not None:
            self.escape_events.append({'step':self.clock,'event':'retreat_timeout'});self.escape_stage=None
        info.update(next_mode=self.mode,escape_replans=self.escape_count)
        return action,info

    def choose(self,x,proposal,previous_action):
        if not self.enabled or (not self.cfg.stable_support and not self.cfg.wait_escape):return super().choose(x,proposal,previous_action)
        x=np.asarray(x,np.float32);tic=time.perf_counter()
        self.try_escape(x)
        if self.escape_stage is not None:action,info=self.escape_action(x)
        elif self.support13 and self.mesh_search is None and self.mode=='ALIGN' and not self.support13_path_checked:
            if not self.raw_settled(x):
                self.begin_wait('support13_unstable_before_path',x);action,info=super().choose(x,proposal,previous_action)
            else:
                assert self.joints is not None
                self.support13_path_checked=True;self.joint_checked=True;self.joint_search=None
                self.edge_search=PathSearch(self,x,self.joints);self.edge_start=x[:3].copy()
                action,info=self.hold(x,'support13_path',0)
        elif self.support13 and self.edge_search is not None:
            s=self.edge_search;d,a=difference(x[16:23],s.anchor);domain,_=support(x,self.floor);before=s.work
            if d>self.cfg.pose_position_m or a>np.deg2rad(self.cfg.pose_axis_deg) or domain is None:
                self.begin_wait('support13_path_invalidated',x)
            elif s.advance(self.cfg.ik_iterations_per_step):
                self.edge_search=None
                self.support13_events.append({'step':self.clock,'event':'path_complete','chosen':s.chosen is not None,'options':s.receipts,'work':s.work})
                if s.chosen is None:
                    self.kinematic_blocked=True;self.plan_ok=False;self.block('support13_no_validated_local_path',x)
                else:
                    self.edge_plan=s.chosen;self.mesh_offset=s.chosen['offset'];self.planned_rotation=s.chosen['rotation'].copy()
                    self.approach_gap=s.chosen['target_gap'];self.goal_rotation=self.planned_rotation.copy()
                    self.plan_anchor=x[16:23].copy();self.pose_anchor=x[16:23].copy();self.edge_age=0;self.edge_settled=0
                    V5.enter(self,'EDGE_ROTATE','support13_path_validated',x)
            action,info=self.hold(x,'support13_path',s.work-before)
        elif self.support13 and self.mode.startswith('EDGE_'):
            domain,_=support(x,self.floor)
            if self.pose_changed(x) or domain is None:
                self.begin_wait('support13_execution_pose_changed',x);action,info=super().choose(x,proposal,previous_action)
            else:action,info=V11.edge_action(self,x)
        else:action,info=super().choose(x,proposal,previous_action)
        info.update(support13_plan=self.support13,escape_replans=self.escape_count,planning_ms=1000*(time.perf_counter()-tic))
        return action,info
