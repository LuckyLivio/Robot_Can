"""v14: observed-motion damping and checked, bounded descent recentering.

No simulator, reward, contact, future observation or case identity is used.
All inherited feasibility/clearance/settling/timeout thresholds remain unchanged.
"""
from dataclasses import dataclass
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import RecoveryController as V13,Config as C13
from reproduction.improvement_v13_20261016_01.recovery.support import support
from reproduction.improvement_v13_20261016_01.recovery.search import PathSearch
from reproduction.improvement_v11_20261015_01.recovery.path_search import EdgeSearch,sweep_margin
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK,LIMITS
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5

@dataclass(frozen=True)
class Config(C13):
    trajectory_tracking:bool=True
    descent_clearance:bool=True
    tracking_velocity_damping:float=1.5
    tracking_angular_damping:float=.3
    tracking_max_replans:int=1
    recenter_trigger_m:float=.004
    recenter_settle_m:float=.009
    recenter_max_per_attempt:int=2
    recenter_timeout:int=24

class RecoveryController(V13):
    def __init__(self,target,floor_z,initial_state,enabled=True,config=None):
        super().__init__(target,floor_z,initial_state,enabled,config or Config())
        self.tracking14_events=[];self.clearance14_events=[]
        self.last_observed=None;self.last_joints=None;self.motion=np.zeros(6)
        self.tracking_started=set();self.tracking_replans={};self.recenter_counts={}
        self.recenter=None;self.recenter_ik=None;self.recenter_age=0;self.recenter_settled=0

    def damped_action(self,x,goal,action):
        delta=self.cfg.position_gain*(np.asarray(goal)-x[:3])-self.cfg.tracking_velocity_damping*self.motion[:3]
        delta*=min(1.,self.cfg.max_delta_m/max(np.linalg.norm(delta),1e-12))
        rot=self.cfg.orientation_gain*Rotation.from_matrix(self.goal_rotation@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec()-self.cfg.tracking_angular_damping*self.motion[3:]
        rot*=min(1.,self.cfg.max_rotation_rad/max(np.linalg.norm(rot),1e-12))
        action=action.copy();action[:3]=delta/.05;action[3:6]=rot/.5
        return np.clip(action,-1,1).astype(np.float32)

    def pose_action(self,x,goal,grip):
        action=super().pose_action(x,goal,grip)
        active=(self.cfg.trajectory_tracking and self.mode in ['EDGE_ROTATE','EDGE_APPROACH'] and np.linalg.norm(np.asarray(goal)-x[:3])<=.06)
        if not self.enabled or not active:return action
        key=(self.attempts,self.mode)
        if key not in self.tracking_started:
            self.tracking_started.add(key)
            events=self.clearance14_events if self.mode=='DESCEND' else self.tracking14_events
            events.append({'step':self.clock,'event':'observed_motion_damping','phase':self.mode,'attempt':self.attempts})
        return self.damped_action(x,goal,action)

    def joint_replan(self,x):
        if not (self.cfg.trajectory_tracking and self.mode in ['EDGE_ROTATE','EDGE_APPROACH'] and self.edge_plan is not None and self.joints is not None and self.last_joints is not None):return False
        margin=float(np.min(np.minimum(self.joints-LIMITS[:,0],LIMITS[:,1]-self.joints)))
        previous=float(np.min(np.minimum(self.last_joints-LIMITS[:,0],LIMITS[:,1]-self.last_joints)))
        closing=previous-margin
        if margin>=self.cfg.joint_warning_rad or closing<=.001 or margin-(self.cfg.delay+3)*closing>=self.cfg.joint_solution_margin_rad:return False
        count=self.tracking_replans.get(self.attempts,0)
        self.tracking14_events.append({'step':self.clock,'event':'joint_margin_warning','margin_rad':margin,'previous_margin_rad':previous,'replans':count})
        if count>=self.cfg.tracking_max_replans:
            self.begin_wait('v14_joint_warning_no_untried_path',x);return False
        self.tracking_replans[self.attempts]=count+1
        old_rotation=self.edge_plan['rotation'].copy()
        search=PathSearch(self,x,self.joints) if self.support13 else EdgeSearch(self,x,self.joints)
        # Prefer the checked equivalent direction; do not reuse the same failed
        # pose merely because its static waypoint IK still converges.
        search.options.sort(key=lambda o:np.linalg.norm(Rotation.from_matrix(o['rotation']@old_rotation.T).as_rotvec())<1.)
        search.index=0;search.begin()
        self.edge_search=search;self.edge_plan=None;self.edge_start=x[:3].copy()
        return True

    def recenter_eligible(self,x):
        moved=self.plan_anchor is not None and np.linalg.norm(x[16:19]-self.plan_anchor[:3])>.012
        too_open=self.approach_gap is not None and abs(float(x[7]-x[8]))>self.approach_gap+self.cfg.aperture_tolerance_m+.002
        return bool(not moved and not too_open and not self.pose_changed(x) and self.refresh_feasibility(x)=='feasible' and self.gap_ready(x))

    def recenter_start(self,x):
        if not (self.cfg.descent_clearance and self.edge_plan is not None and self.mode=='DESCEND' and self.recenter_eligible(x)):return
        r=Rotation.from_quat(x[3:7]).as_matrix();goal=self.grasp_target(x);axis=self.edge_plan['rotation'][:,2]
        error=x[:3]-goal;side=error-axis*np.dot(error,axis)
        forecast=side+self.cfg.delay*(self.motion[:3]-axis*np.dot(self.motion[:3],axis))
        gap=abs(float(x[7]-x[8]));live=object_margin(x[:3],goal,r,[gap-.001,gap+.001],x)
        # A lateral displacement alone is not a clearance failure. The first
        # diagnostic revision over-triggered on harmless noisy motion.
        if live>=.004:return
        count=self.recenter_counts.get(self.attempts,0)
        if count>=self.cfg.recenter_max_per_attempt:return
        self.recenter_counts[self.attempts]=count+1
        center=x[:3]-side
        box=sweep_margin(x[:3],center,r,min(.085,gap+.002))
        can=object_margin(x[:3],center,r,[max(0,gap-.002),min(.085,gap+.002)],x)
        tail=object_margin(center,goal,r,[gap-.001,gap+.001],x)
        accepted=bool(box>=.001 and can>=.003 and tail>=.003 and self.joints is not None)
        self.clearance14_events.append({'step':self.clock,'event':'recenter_check','side_error_m':float(np.linalg.norm(side)),'predicted_side_error_m':float(np.linalg.norm(forecast)),'live_can_margin_m':live,'hand_margin_m':box,'can_margin_m':can,'remaining_path_margin_m':tail,'accepted':accepted})
        if not accepted:return
        self.recenter={'goal':center.copy(),'rotation':r.copy(),'axis':axis.copy(),'anchor':x[16:23].copy()}
        self.recenter_ik=IK(self.joints,center,r,self.cfg.ik_iterations_per_target)
        self.recenter_age=0;self.recenter_settled=0

    def recenter_action(self,x):
        self.recenter_age+=1
        action,info=self.hold(x,'v14_recenter',0)
        if not self.recenter_eligible(x) or self.age>self.cfg.stage_timeout or self.recenter_age>self.cfg.recenter_timeout:
            self.clearance14_events.append({'step':self.clock,'event':'recenter_aborted','phase_age':self.age})
            self.recenter=None;self.recenter_ik=None;self.begin_wait('v14_recenter_invalidated_or_timeout',x)
            info.update(next_mode=self.mode);return action,info
        plan=self.recenter
        if self.recenter_ik is not None:
            ik=self.recenter_ik;before=ik.iterations;ik.advance(self.cfg.ik_iterations_per_step)
            info['planning_work_units']=ik.iterations-before
            if ik.done:
                receipt=ik.receipt();accepted=bool(receipt['success'] and receipt['limit_margin_rad']>=self.cfg.joint_solution_margin_rad)
                self.clearance14_events.append({'step':self.clock,'event':'recenter_ik','accepted':accepted,'ik':receipt})
                self.recenter_ik=None
                if not accepted:self.recenter=None;self.begin_wait('v14_recenter_ik_unconfirmed',x)
            info.update(next_mode=self.mode);return action,info
        gap=abs(float(x[7]-x[8]));rotation=Rotation.from_quat(x[3:7]).as_matrix()
        box=sweep_margin(x[:3],plan['goal'],rotation,min(.085,gap+.002))
        can=object_margin(x[:3],plan['goal'],rotation,[max(0,gap-.002),min(.085,gap+.002)],x)
        if box<.001 or can<.001:
            self.clearance14_events.append({'step':self.clock,'event':'recenter_segment_invalidated','hand_margin_m':box,'can_margin_m':can})
            self.recenter=None;self.begin_wait('v14_recenter_segment_unconfirmed',x)
            info.update(next_mode=self.mode);return action,info
        # Commands stay on the exact checked fixed-rotation segment. Scale
        # only along its direction; do not introduce unchecked sideways or
        # rotation corrections through the velocity damping term.
        delta=plan['goal']-x[:3];distance=float(np.linalg.norm(delta));direction=delta/max(distance,1e-12)
        length=np.clip(self.cfg.position_gain*distance-self.cfg.tracking_velocity_damping*np.dot(self.motion[:3],direction),0,min(self.cfg.max_delta_m,distance))
        action=np.r_[direction*length/.05,np.zeros(4)].astype(np.float32)
        # Return to the certified center at the intervention's original depth.
        # Queued D2 descent can require a small retreat to that fixed center;
        # the queue is never removed or hidden from evaluation.
        goal=self.grasp_target(x);e=x[:3]-goal;side=e-plan['axis']*np.dot(e,plan['axis'])
        tail=object_margin(x[:3],goal,rotation,[gap-.001,gap+.001],x)
        angle=float(np.linalg.norm(Rotation.from_matrix(self.edge_plan['rotation']@rotation.T).as_rotvec()))
        ready=bool(np.linalg.norm(side)<self.cfg.recenter_settle_m and distance<.009 and angle<.08 and tail>=.003 and self.gap_ready(x))
        self.recenter_settled=self.recenter_settled+1 if ready else 0
        info.update(mode='PATH_RECENTER',next_mode=self.mode,hand_margin_m=box,can_margin_m=can,side_error_m=float(np.linalg.norm(side)))
        if self.recenter_settled>=self.cfg.delay+3:
            self.clearance14_events.append({'step':self.clock,'event':'recenter_settled','side_error_m':float(np.linalg.norm(side)),'remaining_path_margin_m':tail})
            self.recenter=None
        return action,info

    def choose(self,x,proposal,previous_action):
        if not self.enabled or not (self.cfg.trajectory_tracking or self.cfg.descent_clearance):return super().choose(x,proposal,previous_action)
        x=np.asarray(x,np.float32)
        if self.last_observed is not None:
            self.motion[:3]=x[:3]-self.last_observed[:3]
            self.motion[3:]=Rotation.from_matrix(Rotation.from_quat(x[3:7]).as_matrix()@Rotation.from_quat(self.last_observed[3:7]).as_matrix().T).as_rotvec()
        try:
            self.joint_replan(x)
            if self.recenter is None:self.recenter_start(x)
            if self.recenter is not None:action,info=self.recenter_action(x)
            else:action,info=super().choose(x,proposal,previous_action)
            return action,info
        finally:
            self.last_observed=x.copy();self.last_joints=None if self.joints is None else self.joints.copy()
