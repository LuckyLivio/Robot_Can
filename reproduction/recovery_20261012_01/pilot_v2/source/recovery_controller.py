"""Observation-only recovery supervisor. No simulator, reward, or model access."""
from collections import deque
from dataclasses import dataclass, asdict
import numpy as np
from scipy.spatial.transform import Rotation


@dataclass(frozen=True)
class Config:
    delay: int = 2
    stable_frames: int = 5
    stall_steps: int = 40
    stall_progress_m: float = .005
    max_attempts: int = 2
    position_gain: float = .5
    max_delta_m: float = .035
    orientation_gain: float = .5
    max_rotation_rad: float = .15
    relative_tolerance_m: float = .012
    near_object_m: float = .09
    grip_gap_min_m: float = .025
    grip_gap_max_m: float = .067
    verified_lift_m: float = .02
    approach_clearance_m: float = .20
    carry_clearance_m: float = .28
    grasp_offset_z_m: float = .012
    close_steps: int = 16
    lift_probe_m: float = .06
    stage_timeout: int = 70


class RecoveryController:
    def __init__(self, target, floor_z, initial_state, enabled=True, config=None):
        self.cfg=config or Config();self.target=np.asarray(target,float).copy();self.floor=float(floor_z)
        self.enabled=enabled;self.history=deque(maxlen=self.cfg.stall_steps+1)
        self.rest_z=float(initial_state[18]);self.mode='NORMAL';self.age=0;self.attempts=0
        self.stable=False;self.ever_stable=False;self.lost_frames=0;self.clock=0
        self.events=[];self.held_offset=None;self.waypoint=None;self.anchor_object_z=None
        self.failed_attempts=0;self.verified_regrasps=0;self.done_cooldown=0
        self.release_until=0
        self.goal_rotation=Rotation.from_quat([1.,0.,0.,0.]).as_matrix()

    def enter(self, mode, reason, x):
        self.events.append({'step':self.clock,'from':self.mode,'to':mode,'reason':reason,
                            'attempt':self.attempts,'object_position':x[16:19].tolist()})
        self.mode=mode;self.age=0
        if mode=='RETRACT':
            self.waypoint=np.array([x[0],x[1],max(self.floor+self.cfg.approach_clearance_m,x[2])])
        if mode=='CLOSE':self.anchor_object_z=float(x[18])
        if mode=='TEST_LIFT':
            self.waypoint=np.array([x[16],x[17],x[2]+self.cfg.lift_probe_m])
        if mode=='LIFT':
            self.held_offset=x[:3].astype(float)-x[16:19]
            self.waypoint=np.array([x[16],x[17],self.floor+self.cfg.carry_clearance_m])+self.held_offset
        if mode=='RELEASE':self.waypoint=x[:3].astype(float).copy()
        if mode=='RETREAT':self.waypoint=x[:3].astype(float)+np.array([0.,0.,.12])

    def inside_goal(self, x):
        # Known target cell (half of the .39 x .49 bin), with a 1 cm margin.
        # A normal policy may release above the cell before the object lands.
        return bool(np.all(np.abs(x[16:18]-self.target[:2])<np.array([.0875,.1125])))

    def observable_hold(self, x, previous_action):
        c=self.cfg;gap=abs(float(x[7]-x[8]));relative=x[:3]-x[16:19]
        recent=list(self.history)[-c.stable_frames:]
        consistent=len(recent)==c.stable_frames and max(np.linalg.norm(h['relative']-relative) for h in recent)<c.relative_tolerance_m
        raised=float(x[18])>self.rest_z+c.verified_lift_m
        if self.mode=='TEST_LIFT' and self.anchor_object_z is not None:
            raised=float(x[18])>self.anchor_object_z+c.verified_lift_m
        return bool(c.grip_gap_min_m<gap<c.grip_gap_max_m and
                    np.linalg.norm(relative)<c.near_object_m and consistent and raised and previous_action[6]>0)

    def start_attempt(self, reason, x, holding=False):
        if self.attempts>=self.cfg.max_attempts:
            self.enter('EXHAUSTED','attempt_limit',x);return
        self.attempts+=1;self.stable=False;self.lost_frames=0
        if holding:
            self.goal_rotation=Rotation.from_quat(x[3:7]).as_matrix()
        else:
            # Choose the finger-opening direction with more wall clearance.
            # These are the task's fixed source-bin walls, not contact truth.
            clearance_x=min(abs(x[16]+.095),abs(.295-x[16]))
            clearance_y=min(abs(x[17]+.495),abs(-.005-x[17]))
            yaw=np.pi/2 if clearance_y<clearance_x else 0.
            self.goal_rotation=Rotation.from_rotvec([0,0,yaw]).as_matrix()@Rotation.from_quat([1.,0.,0.,0.]).as_matrix()
        self.enter('LIFT' if holding else 'RETRACT',reason,x)

    def pose_action(self, x, goal, grip):
        # OSC_POSE is verified to use world-frame deltas and scales .05 m/.5 rad.
        delta=self.cfg.position_gain*(np.asarray(goal)-x[:3])
        norm=np.linalg.norm(delta)
        if norm>self.cfg.max_delta_m:delta*=self.cfg.max_delta_m/norm
        current=Rotation.from_quat(x[3:7]).as_matrix()
        rot=self.cfg.orientation_gain*Rotation.from_matrix(self.goal_rotation@current.T).as_rotvec()
        size=np.linalg.norm(rot)
        if size>self.cfg.max_rotation_rad:rot*=self.cfg.max_rotation_rad/size
        return np.clip(np.r_[delta/.05,rot/.5,grip],-1,1).astype(np.float32)

    def choose(self, x, proposal, previous_action):
        x=np.asarray(x,np.float32);self.clock+=1;self.age+=1;c=self.cfg
        relative=x[:3]-x[16:19];distance=float(np.linalg.norm(relative))
        xygoal=float(np.linalg.norm(x[16:18]-self.target[:2]))
        self.history.append({'relative':relative.copy(),'object':x[16:19].copy(),'distance':distance,'xygoal':xygoal})
        holding=self.observable_hold(x,previous_action)
        if holding:
            self.stable=True;self.ever_stable=True;self.lost_frames=0
        elif self.stable:self.lost_frames+=1
        if self.mode=='NORMAL' and self.ever_stable and self.inside_goal(x) and proposal[6]<0:
            self.release_until=self.clock+25
        intentional=self.mode in ['RELEASE','RETREAT'] or self.clock<self.release_until
        loss=self.stable and self.lost_frames>=c.stable_frames and not intentional
        debug={'mode_before':self.mode,'stable_hold':holding,'latched_hold':self.stable,
               'gap_m':abs(float(x[7]-x[8])),'eef_object_distance_m':distance,
               'goal_distance_xy_m':xygoal,'loss_detected':bool(loss),'attempts':self.attempts}
        if not self.enabled:return proposal.copy(),{**debug,'mode':self.mode,'intervened':False}
        reachable=bool(-.24<x[16]<.45 and -.57<x[17]<.57 and x[18]>self.floor-.04)
        if self.mode not in ['NORMAL','EXHAUSTED'] and not reachable:
            self.failed_attempts+=1;self.enter('EXHAUSTED','object_outside_recovery_workspace',x)
        if self.mode=='NORMAL':
            if loss and reachable:self.start_attempt('observed_grasp_loss',x)
            elif self.age>c.stall_steps and len(self.history)>c.stall_steps and not intentional and reachable:
                old=self.history[0]
                if holding:
                    progress=max(float(x[18]-old['object'][2]),old['xygoal']-xygoal)
                else:
                    progress=max(old['distance']-distance,float(x[18]-old['object'][2]))
                if progress<c.stall_progress_m and (distance<.12 or self.ever_stable):
                    self.start_attempt('held_stall' if holding else 'near_object_stall',x,holding)
        elif loss and self.mode in ['LIFT','CARRY','PLACE']:
            if self.inside_goal(x):self.enter('RELEASE','object_at_goal',x)
            else:
                self.failed_attempts+=1;self.start_attempt('observed_grasp_loss',x)
        if self.mode not in ['NORMAL','EXHAUSTED','CARRY'] and self.age>c.stage_timeout:
            self.failed_attempts+=1;self.start_attempt('phase_timeout',x)
        if self.mode=='CARRY' and self.age>110:
            self.failed_attempts+=1;self.start_attempt('transport_timeout',x)
        phase=self.mode
        if phase in ['NORMAL','EXHAUSTED']:
            return proposal.copy(),{**debug,'mode':self.mode,'intervened':False,'attempts':self.attempts}
        if phase=='RETRACT':
            action=self.pose_action(x,self.waypoint,-1)
            if self.age>c.delay+5 and x[2]>=self.waypoint[2]-.012:self.enter('ALIGN','retracted',x)
        elif phase=='ALIGN':
            goal=np.r_[x[16:18],max(self.floor+c.approach_clearance_m,x[18]+.14)]
            action=self.pose_action(x,goal,-1)
            angle=np.linalg.norm(Rotation.from_matrix(self.goal_rotation@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec())
            if self.age>c.delay+5 and np.linalg.norm(x[:3]-goal)<.014 and angle<.15:self.enter('DESCEND','aligned_above_object',x)
        elif phase=='DESCEND':
            goal=x[16:19]+np.array([0.,0.,c.grasp_offset_z_m]);action=self.pose_action(x,goal,-1)
            if self.age>c.delay+5 and np.linalg.norm(x[:3]-goal)<.009:self.enter('CLOSE','at_grasp_pose',x)
        elif phase=='CLOSE':
            action=self.pose_action(x,x[16:19]+np.array([0.,0.,c.grasp_offset_z_m]),1)
            if self.age>=c.close_steps+c.delay:self.enter('TEST_LIFT','close_commands_executed',x)
        elif phase=='TEST_LIFT':
            action=self.pose_action(x,self.waypoint,1)
            if self.age>=c.delay+c.stable_frames and holding:
                self.verified_regrasps+=1;self.enter('LIFT','lift_follow_confirmed',x)
            elif self.age>=35:
                self.failed_attempts+=1;self.start_attempt('lift_probe_failed',x)
        elif phase=='LIFT':
            action=self.pose_action(x,self.waypoint,1)
            if x[18]>=self.floor+c.carry_clearance_m-.016 and holding:self.enter('CARRY','clearance_reached',x)
        elif phase=='CARRY':
            goal=np.r_[self.target[:2],self.floor+c.carry_clearance_m]+self.held_offset
            action=self.pose_action(x,goal,1)
            if self.age>c.delay+5 and xygoal<.018:self.enter('PLACE','above_target',x)
        elif phase=='PLACE':
            goal=np.r_[self.target[:2],self.floor+.085]+self.held_offset
            action=self.pose_action(x,goal,1)
            if self.age>c.delay+5 and xygoal<.025 and x[18]<self.floor+.10:self.enter('RELEASE','at_release_height',x)
        elif phase=='RELEASE':
            action=self.pose_action(x,self.waypoint,-1)
            if self.age>=14+c.delay:self.enter('RETREAT','release_commands_executed',x)
        elif phase=='RETREAT':
            action=self.pose_action(x,self.waypoint,-1)
            if self.age>c.delay+5 and np.linalg.norm(x[:3]-self.waypoint)<.02:
                self.stable=False;self.lost_frames=0;self.history.clear();self.enter('NORMAL','placement_sequence_finished',x)
        else:raise RuntimeError(phase)
        return action,{**debug,'mode':phase,'next_mode':self.mode,'intervened':True,'attempts':self.attempts}
