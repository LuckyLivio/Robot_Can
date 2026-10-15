"""Add bounded pose replanning and unknown-feasibility waits to frozen v6."""
from collections import deque
from dataclasses import dataclass
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as V6Config
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5
from .pose_guard import difference,feasibility

@dataclass(frozen=True)
class Config(V6Config):
    replan_on_change:bool=True
    unknown_guard:bool=True
    pose_position_m:float=.015
    pose_axis_deg:float=20.
    pose_stable_frames:int=4
    pose_stable_position_m:float=.003
    pose_stable_axis_deg:float=4.
    pose_wait_steps:int=40
    max_pose_replans:int=2
    unknown_recheck_interval:int=5

class RecoveryController(V6):
    PREGRASP=('RETRACT','ALIGN','APERTURE','DESCEND')
    def __init__(self,target,floor_z,initial_state,enabled=True,config=None):
        super().__init__(target,floor_z,initial_state,enabled,config or Config())
        self.pose_anchor=None;self.pose_replans=0;self.pose_events=[]
        self.poses=deque(maxlen=self.cfg.pose_stable_frames);self.last_pose_check=-100
        self.wait_reason=None;self.feasibility_status='unplanned';self.feasibility_reason='unplanned'

    def active(self):return self.enabled and (self.cfg.replan_on_change or self.cfg.unknown_guard)

    def refresh_feasibility(self,x):
        self.feasibility_status,self.feasibility_reason=feasibility(self,x)
        return self.feasibility_status

    def plan_grasp(self,x):
        super().plan_grasp(x)
        if not self.active():return
        self.pose_anchor=x[16:23].copy();self.refresh_feasibility(x)
        self.pose_events.append({'step':self.clock,'event':'plan','feasibility':self.feasibility_status,
                                 'detail':self.feasibility_reason,'grasp_kind':self.grasp_kind})

    def pose_changed(self,x):
        if self.pose_anchor is None:return False
        d,a=difference(x[16:23],self.pose_anchor)
        return d>self.cfg.pose_position_m or a>np.deg2rad(self.cfg.pose_axis_deg)

    def pose_settled(self):
        if len(self.poses)<self.cfg.pose_stable_frames:return False
        return all(d<=self.cfg.pose_stable_position_m and a<=np.deg2rad(self.cfg.pose_stable_axis_deg)
                   for d,a in [difference(p,self.poses[-1]) for p in self.poses])

    def begin_wait(self,reason,x):
        self.wait_reason=reason;self.last_pose_check=self.clock
        self.waypoint=np.r_[x[:2],max(self.floor+self.cfg.approach_clearance_m,x[2])]
        self.goal_rotation=Rotation.from_quat(x[3:7]).as_matrix()
        V5.enter(self,'POSE_WAIT',reason,x)

    def block(self,reason,x):
        self.failed_attempts+=1
        V5.enter(self,'POSE_BLOCKED',reason,x)

    def enter(self,mode,reason,x):
        if self.active() and mode in ['ALIGN','DESCEND']:
            if self.cfg.replan_on_change and self.pose_changed(x):
                self.begin_wait('pose_changed_before_'+mode.lower(),x);return
            if self.cfg.unknown_guard and self.refresh_feasibility(x)=='unknown':
                self.begin_wait('unknown_before_'+mode.lower(),x);return
        super().enter(mode,reason,x)

    def wait_action(self,x):
        phase=self.mode;self.clock+=1;self.age+=1
        self.gaps.append(abs(float(x[7]-x[8])))
        # Flush pending D2 actions, retract vertically, then keep the attained
        # gripper aperture while the object settles. No counterfactual rollout.
        action=V5.pose_action(self,x,self.waypoint,0.)
        if phase=='POSE_WAIT':
            elevated=x[2]>=self.waypoint[2]-.014 and self.age>self.cfg.delay+5
            ready=elevated and self.pose_settled() and self.clock-self.last_pose_check>=self.cfg.unknown_recheck_interval
            if ready:
                self.last_pose_check=self.clock
                if self.pose_replans>=self.cfg.max_pose_replans:self.block('pose_replan_limit',x)
                else:
                    # Unknown-state checking must refresh a newly supported
                    # pose even in the unknown-only ablation.
                    self.plan_grasp(x)
                    if self.cfg.unknown_guard and self.feasibility_status=='unknown':pass
                    elif self.feasibility_status=='infeasible':self.block('replanned_no_feasible_candidate',x)
                    else:
                        self.pose_replans+=1
                        V5.enter(self,'ALIGN','replanned_settled_pose',x)
            if self.mode=='POSE_WAIT' and self.age>=self.cfg.pose_wait_steps:self.block('unknown_or_unsettled_timeout',x)
        return action,{'mode_before':phase,'mode':phase,'next_mode':self.mode,'stable_hold':False,
                       'intervened':True,'attempts':self.attempts,'gap_m':abs(float(x[7]-x[8]))}

    def choose(self,x,proposal,previous_action):
        if not self.active():return super().choose(x,proposal,previous_action)
        x=np.asarray(x,np.float32);self.poses.append(x[16:23].copy())
        if self.mode in self.PREGRASP:
            if self.cfg.replan_on_change and self.pose_changed(x):self.begin_wait('pose_changed_during_approach',x)
            elif self.cfg.unknown_guard and self.mode in ['ALIGN','APERTURE','DESCEND'] and self.refresh_feasibility(x)=='unknown':
                self.begin_wait('unknown_during_approach',x)
        if self.mode in ['POSE_WAIT','POSE_BLOCKED']:action,info=self.wait_action(x)
        else:
            action,info=super().choose(x,proposal,previous_action)
            # v6's APERTURE handler transitions via V5.enter directly. Guard
            # that transition too, before any new descent command is issued.
            if self.mode=='DESCEND' and info.get('mode')!='DESCEND':
                if self.cfg.replan_on_change and self.pose_changed(x):self.begin_wait('pose_changed_after_aperture',x)
                elif self.cfg.unknown_guard and self.refresh_feasibility(x)!='feasible':self.begin_wait('unconfirmed_after_aperture',x)
                info['next_mode']=self.mode
        self.refresh_feasibility(x)
        info.update(feasibility=self.feasibility_status,feasibility_reason=self.feasibility_reason,
                    pose_replans=self.pose_replans,pose_changed=self.pose_changed(x))
        return action,info
