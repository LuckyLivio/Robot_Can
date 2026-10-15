"""v15: checked held transport, segmented edge motion, and early recentering.

All clocks and the inherited guards remain active. No simulator or outcome
information enters this supervisor. Disabled extensions reproduce v14 exactly.
"""
from dataclasses import dataclass
import time
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import RecoveryController as V14, Config as C14
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5
from reproduction.improvement_v8_20261015_01.recovery.geometry import support
from reproduction.improvement_v7_20261015_01.recovery.pose_guard import difference
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
from reproduction.improvement_v11_20261015_01.recovery.path_search import sweep_margin, turn_samples
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin
from .edge_path import SegmentedEdgeSearch
from .carry_path import CarryPathSearch, HeldEnvelope, translation_certificate, rotation_certificate


@dataclass(frozen=True)
class Config(C14):
    carry_path: bool = True
    segmented_edge: bool = True
    budget_recenter: bool = True


class RecoveryController(V14):
    def __init__(self, target, floor_z, initial_state, enabled=True, config=None):
        super().__init__(target, floor_z, initial_state, enabled, config or Config())
        self.carry15_events=[]; self.edge15_events=[]; self.budget15_events=[]
        self.segmented_search=None
        self.carry_search=None; self.carry_plan=None; self.carry_checked=set()
        self.carry_index=0; self.carry_settled=0; self.carry_phase_age=0
        self.carry_reference=None
        self.budget_checked=set()

    def edge_action(self,x):
        if not (self.cfg.budget_recenter and self.mode=='EDGE_APPROACH'):
            return super().edge_action(x)
        # One shared arrival counter, not another post-arrival waiting phase.
        # The original recenter warning/guard remains active during descent.
        phase=self.mode;self.edge_age+=1
        action,info=self.hold(x,'v15_budget_approach',0)
        p=self.edge_plan;goal=p['above'];self.goal_rotation=p['rotation'].copy()
        action=V5.pose_action(self,x,goal,0.)
        if np.linalg.norm(x[:3]-goal)<=.06:action=self.damped_action(x,goal,action)
        gap=abs(float(x[7]-x[8]));error=gap-self.approach_gap
        if abs(error)>self.cfg.aperture_tolerance_m and self.clock-self.last_pulse>=self.cfg.gap_pulse_interval:
            action[6]=1. if error>0 else -1.;self.last_pulse=self.clock
        r=Rotation.from_quat(x[3:7]).as_matrix()
        angle=float(np.linalg.norm(Rotation.from_matrix(self.goal_rotation@r.T).as_rotvec()))
        position=float(np.linalg.norm(x[:3]-goal))
        forecast=float(np.linalg.norm(x[:3]+self.cfg.delay*self.motion[:3]-goal))
        tail=object_margin(x[:3],self.grasp_target(x),r,[gap-.001,gap+.001],x)
        at=bool(position<.009 and angle<.08 and self.gap_ready(x) and forecast<.009 and tail>=.003)
        self.edge_settled=self.edge_settled+1 if at else 0
        if self.attempts not in self.budget_checked:
            self.budget_checked.add(self.attempts)
            self.budget15_events.append({'step':self.clock,'event':'shared_braking_and_descent_confirmation','remaining_steps':self.cfg.horizon_steps-self.clock,'schedule_estimate':self.remaining_schedule(x)})
        if self.edge_settled>=self.cfg.delay+3:
            self.budget15_events.append({'step':self.clock,'event':'early_alignment_settled','position_error_m':position,'angle_rad':angle,'d2_forecast_error_m':forecast,'remaining_path_margin_m':tail,'remaining_steps':self.cfg.horizon_steps-self.clock})
            self.enter('DESCEND','v15_braked_approach_and_descent_validated',x)
        if self.age>self.cfg.stage_timeout and self.mode.startswith('EDGE_'):
            self.failed_attempts+=1;self.start_attempt('phase_timeout',x)
        info.update(mode=phase,next_mode=self.mode,feasibility='feasible',edge_phase_steps=self.edge_age,aperture_ready=self.gap_ready(x),d2_forecast_error_m=forecast,remaining_path_margin_m=tail)
        return action,info

    def _motion(self,x):
        if self.last_observed is not None:
            self.motion[:3]=x[:3]-self.last_observed[:3]
            self.motion[3:]=Rotation.from_matrix(Rotation.from_quat(x[3:7]).as_matrix()@Rotation.from_quat(self.last_observed[3:7]).as_matrix().T).as_rotvec()

    def checked_empty_translation(self,x,goal,rotation):
        """One checked fixed-rotation line OR a checked in-place micro-turn."""
        r=Rotation.from_quat(x[3:7]).as_matrix();gap=abs(float(x[7]-x[8]))
        angle=np.linalg.norm(Rotation.from_matrix(rotation@r.T).as_rotvec())
        if angle>.04:
            turn=self.cfg.orientation_gain*Rotation.from_matrix(rotation@r.T).as_rotvec()
            turn*=min(1.,self.cfg.max_rotation_rad/max(np.linalg.norm(turn),1e-12))
            samples=turn_samples(r,Rotation.from_rotvec(turn).as_matrix()@r,min(.085,gap+.002))
            box=min(sweep_margin(x[:3],x[:3],rr,min(.085,gap+.002))-bound for rr,bound in samples)
            can=min(object_margin(x[:3],x[:3],rr,[max(0,gap-.002),min(.085,gap+.002)],x)-bound for rr,bound in samples)
            return np.r_[np.zeros(3),turn/.5,0.].astype(np.float32),box,can
        delta=np.asarray(goal)-x[:3];distance=float(np.linalg.norm(delta));direction=delta/max(distance,1e-12)
        length=np.clip(self.cfg.position_gain*distance-self.cfg.tracking_velocity_damping*np.dot(self.motion[:3],direction),0,min(self.cfg.max_delta_m,distance))
        box=sweep_margin(x[:3],goal,r,min(.085,gap+.002))
        can=object_margin(x[:3],goal,r,[max(0,gap-.002),min(.085,gap+.002)],x)
        return np.r_[direction*length/.05,np.zeros(4)].astype(np.float32),box,can

    def segmented_action(self,x):
        if self.segmented_search is None and self.eligible(x):
            self.edge_checked=True; self.joint_checked=True; self.joint_search=None
            self.segmented_search=SegmentedEdgeSearch(self,x,self.joints)
            self.edge15_events.append({'step':self.clock,'event':'segmented_search_started'})
        if self.segmented_search is not None:
            s=self.segmented_search; before=s.work
            d,a=difference(x[16:23],s.anchor); domain,_=support(x,self.floor)
            if d>self.cfg.pose_position_m or a>np.deg2rad(self.cfg.pose_axis_deg) or domain is None:
                self.segmented_search=None; self.begin_wait('v15_segmented_search_pose_changed',x)
            elif s.advance(self.cfg.ik_iterations_per_step):
                self.segmented_search=None
                self.edge15_events.append({'step':self.clock,'event':'segmented_search_complete','chosen':s.chosen is not None,'options':s.receipts,'work':s.work})
                if s.chosen is None:
                    self.kinematic_blocked=True;self.plan_ok=False;self.block('v15_no_validated_segmented_path',x)
                else:
                    p=s.chosen; self.edge_plan=p;self.mesh_offset=p['offset'];self.planned_rotation=p['rotation'].copy()
                    self.approach_gap=p['target_gap'];self.goal_rotation=p['pre_rotation'].copy()
                    self.plan_anchor=x[16:23].copy();self.pose_anchor=x[16:23].copy()
                    self.edge_start=p['pre_goal'].copy();self.edge_settled=0;self.edge_age=0
                    V5.enter(self,'EDGE_PRETRANSLATE','v15_segmented_path_validated',x)
            action,info=self.hold(x,'v15_segmented_edge',s.work-before)
            info.update(next_mode=self.mode)
            return action,info
        if self.mode!='EDGE_PRETRANSLATE':return None
        action,info=self.hold(x,'v15_pretranslate',0)
        p=self.edge_plan; domain,_=support(x,self.floor)
        if p is None or self.pose_changed(x) or domain is None or self.age>self.cfg.stage_timeout:
            self.begin_wait('v15_pretranslate_invalidated_or_timeout',x)
            info.update(next_mode=self.mode);return action,info
        r=Rotation.from_quat(x[3:7]).as_matrix();gap=abs(float(x[7]-x[8]))
        action,box,can=self.checked_empty_translation(x,p['pre_goal'],p['pre_rotation'])
        margin=float(np.min(np.minimum(self.joints-LIMITS[:,0],LIMITS[:,1]-self.joints)))
        if box<.001 or can<.001 or margin<self.cfg.joint_solution_margin_rad:
            self.edge15_events.append({'step':self.clock,'event':'pretranslate_guard','hand_margin_m':box,'can_margin_m':can,'joint_margin_rad':margin})
            self.begin_wait('v15_pretranslate_execution_unconfirmed',x)
            info.update(next_mode=self.mode);return np.zeros(7,np.float32),info
        self.goal_rotation=p['pre_rotation'].copy()
        error=gap-self.approach_gap
        if abs(error)>self.cfg.aperture_tolerance_m and self.clock-self.last_pulse>=self.cfg.gap_pulse_interval:
            action[6]=1. if error>0 else -1.;self.last_pulse=self.clock
        angle=float(np.linalg.norm(Rotation.from_matrix(self.goal_rotation@r.T).as_rotvec()))
        ready=bool(np.linalg.norm(x[:3]-p['pre_goal'])<.009 and angle<.08 and self.gap_ready(x))
        self.edge_settled=self.edge_settled+1 if ready else 0
        if self.edge_settled>=self.cfg.delay+3:
            self.edge15_events.append({'step':self.clock,'event':'pretranslate_settled','position_error_m':float(np.linalg.norm(x[:3]-p['pre_goal'])),'angle_rad':angle})
            self.edge_settled=0;self.goal_rotation=p['rotation'].copy()
            V5.enter(self,'EDGE_ROTATE','v15_translation_confirmed_before_turn',x)
        info.update(mode='EDGE_PRETRANSLATE',next_mode=self.mode,hand_margin_m=box,can_margin_m=can,aperture_ready=self.gap_ready(x))
        return action,info

    def carry_action(self,x,action,info):
        # Parent choose has already advanced the clock, recorded current hold
        # evidence and enforced loss/timeout/attempt guards exactly once.
        if self.mode!='CARRY':
            if self.carry_search is not None or self.carry_plan is not None:
                self.carry15_events.append({'step':self.clock,'event':'path_stopped_parent_hold_or_phase_guard','phase':self.mode})
            self.carry_search=None;self.carry_plan=None
            return action,info
        if not info.get('stable_hold'):
            # A transient observation failure does not discard a validated
            # route or authorize returning to the old unvalidated transport.
            # Parent loss counting continues and may start recovery at five.
            return np.array([0,0,0,0,0,0,1],np.float32),{**info,'mode':'CARRY_HOLD','next_mode':self.mode}
        if self.attempts not in self.carry_checked:
            self.carry_checked.add(self.attempts)
            self.carry_search=CarryPathSearch(self,x,self.joints)
            self.carry_reference=self.carry_search.envelope
            self.carry15_events.append({'step':self.clock,'event':'held_transport_search','remaining_steps':self.cfg.horizon_steps-self.clock})
        if self.carry_search is not None:
            s=self.carry_search;before=s.work
            error=s.envelope.relative_errors(x)
            if error['position_m']>self.cfg.relative_tolerance_m:
                self.carry15_events.append({'step':self.clock,'event':'held_transform_invalidated',**error})
                self.carry_search=None;self.carry_plan=None
                self.failed_attempts+=1;self.start_attempt('v15_held_transform_changed',x)
            elif s.advance(self.cfg.ik_iterations_per_step):
                self.carry15_events.append({'step':self.clock,'event':'held_transport_search_complete','chosen':s.chosen is not None,'work':s.work,'options':s.receipts,'observed_position_drift_m':float(np.linalg.norm(x[:3]-s.x[:3])),'observed_joint_drift_rad':float(np.linalg.norm(self.joints-s.q))})
                self.carry_search=None
                if s.chosen is None:
                    # No unvalidated transport fallback after a failed search.
                    self.failed_attempts+=1;self.start_attempt('v15_no_validated_held_path',x,True)
                elif s.chosen.get('preserve_current',False):
                    self.carry15_events.append({'step':self.clock,'event':'existing_transport_validated'})
                    self.carry_reference=None
                else:
                    self.carry_plan=s.chosen;self.carry_index=0;self.carry_settled=0;self.carry_phase_age=0
            action=np.array([0,0,0,0,0,0,1],np.float32)
            info.update(mode='CARRY_PLAN' if self.mode=='CARRY' else 'CARRY_GUARD',next_mode=self.mode,planning_kind='v15_carry',planning_work_units=s.work-before)
            return action,info
        if self.carry_plan is None:return action,info
        p=self.carry_plan;stage=p['stages'][self.carry_index];self.carry_phase_age+=1
        r=Rotation.from_quat(x[3:7]).as_matrix();error=self.carry_reference.relative_errors(x)
        margin=float(np.min(np.minimum(self.joints-LIMITS[:,0],LIMITS[:,1]-self.joints)))
        if error['position_m']>self.cfg.relative_tolerance_m or margin<self.cfg.joint_solution_margin_rad or self.carry_phase_age>self.cfg.stage_timeout:
            self.carry15_events.append({'step':self.clock,'event':'held_execution_guard','joint_margin_rad':margin,**error})
            self.carry_plan=None;self.failed_attempts+=1;self.start_attempt('v15_held_path_execution_guard',x,True)
            return np.array([0,0,0,0,0,0,1],np.float32),{**info,'mode':'CARRY_GUARD','next_mode':self.mode,'planning_kind':'v15_carry','planning_work_units':0}
        goal=stage['goal'];rotation=stage['rotation'];delta=goal-x[:3]
        angle=float(np.linalg.norm(Rotation.from_matrix(rotation@r.T).as_rotvec()))
        self.goal_rotation=rotation.copy()
        proposed=V5.pose_action(self,x,goal,1.)
        if stage['kind']=='translate':
            cert=translation_certificate(x,goal)
            # Keep translations in the currently observed rotation; rotation
            # was settled in its own segment rather than mixed into motion.
            proposed[3:6]=0.
        else:
            # Correct residual position first at fixed orientation. The turn
            # itself is a fixed-position arc and receives its own certificate.
            if np.linalg.norm(delta)>.006:
                cert=translation_certificate(x,goal);proposed[3:6]=0.
            else:
                proposed[:3]=0.
                next_r=Rotation.from_rotvec(proposed[3:6]*.5).as_matrix()@r
                cert=rotation_certificate(x,next_r)
        if not cert['accepted']:
            self.carry15_events.append({'step':self.clock,'event':'live_held_geometry_guard',**cert})
            self.carry_plan=None;self.failed_attempts+=1;self.start_attempt('v15_held_geometry_unconfirmed',x,True)
            proposed=np.array([0,0,0,0,0,0,1],np.float32)
        else:
            ready=bool(np.linalg.norm(delta)<.009 and angle<.08 and info.get('stable_hold'))
            self.carry_settled=self.carry_settled+1 if ready else 0
            if self.carry_settled>=self.cfg.delay+3:
                self.carry15_events.append({'step':self.clock,'event':'held_segment_settled','segment':stage['label'],'position_error_m':float(np.linalg.norm(delta)),'angle_rad':angle,**cert})
                if stage['kind']=='rotate':
                    self.held_offset=x[:3].astype(float)-x[16:19]
                self.carry_index+=1;self.carry_settled=0;self.carry_phase_age=0
                if self.carry_index==len(p['stages']):self.carry_plan=None
        info.update(mode='CARRY_PATH' if self.mode=='CARRY' else 'CARRY_GUARD',next_mode=self.mode,carry_segment=stage['label'],**cert)
        return proposed,info

    def choose(self,x,proposal,previous_action):
        if not self.enabled or not (self.cfg.carry_path or self.cfg.segmented_edge or self.cfg.budget_recenter):
            return super().choose(x,proposal,previous_action)
        x=np.asarray(x,np.float32);tic=time.perf_counter();self._motion(x)
        try:
            result=self.segmented_action(x) if self.cfg.segmented_edge else None
            if result is None:
                action,info=super().choose(x,proposal,previous_action)
                if self.cfg.carry_path:action,info=self.carry_action(x,action,info)
                if self.cfg.carry_path and self.mode=='PLACE' and self.carry_reference is not None:
                    goal=np.r_[self.target[:2],self.floor+.085]+self.held_offset
                    cert=translation_certificate(x,goal)
                    angle=np.linalg.norm(Rotation.from_matrix(self.goal_rotation@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec())
                    if angle>.04:
                        action[:3]=0.
                        next_rotation=Rotation.from_rotvec(action[3:6]*.5).as_matrix()@Rotation.from_quat(x[3:7]).as_matrix()
                        cert=rotation_certificate(x,next_rotation)
                    else:action[3:6]=0.
                    if not cert['accepted']:
                        self.carry15_events.append({'step':self.clock,'event':'held_placement_geometry_guard',**cert})
                        self.failed_attempts+=1;self.start_attempt('v15_placement_geometry_unconfirmed',x,True)
                        action=np.array([0,0,0,0,0,0,1],np.float32)
                        info.update(mode='CARRY_GUARD',next_mode=self.mode,**cert)
            else:action,info=result
            info['planning_ms']=1000*(time.perf_counter()-tic)
            return action,info
        finally:
            self.last_observed=x.copy();self.last_joints=None if self.joints is None else self.joints.copy()
