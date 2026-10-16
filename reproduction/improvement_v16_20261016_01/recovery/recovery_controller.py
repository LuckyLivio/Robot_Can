"""v16 isolated observation-only repairs; disabled switches reproduce v15.

Mixed motion is certified before submission. All inherited clocks, grasp-loss,
pose, aperture and joint protections remain active; no simulator outcome input.
"""
from dataclasses import dataclass
import time
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import RecoveryController as V15, Config as C15
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import RecoveryController as V14
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5
from reproduction.improvement_v13_20261016_01.recovery.support import support as support13
from reproduction.improvement_v8_20261015_01.recovery.geometry import support
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin
from reproduction.improvement_v15_20261016_01.recovery.carry_path import translation_certificate, rotation_certificate
from .pose_servo import propose


@dataclass(frozen=True)
class Config(C15):
    ik_continuation: bool = True
    held_pose: bool = True
    edge_stability: bool = True


class RecoveryController(V15):
    def __init__(self, target, floor_z, initial_state, enabled=True, config=None):
        super().__init__(target, floor_z, initial_state, enabled, config or Config())
        self.ik16_events=[]; self.held16_events=[]; self.edge16_events=[]
        self.transport16=None; self.transport16_attempt=None
        self._empty16_receipt=None

    def active16(self):
        return self.enabled and (self.cfg.ik_continuation or self.cfg.held_pose or self.cfg.edge_stability)

    def joint_margin16(self):
        if self.joints is None:return -float('inf')
        return float(np.min(np.minimum(self.joints-LIMITS[:,0],LIMITS[:,1]-self.joints)))

    def enter(self,mode,reason,x):
        if (mode=='RELEASE' and reason=='at_release_height' and self.mode=='PLACE'
                and self.cfg.held_pose and self.lost_frames>0):
            return
        # Complete the checked route before the inherited position-only phase
        # transition can bypass a remaining reorientation/transport segment.
        if (mode=='PLACE' and self.active16() and (self.cfg.ik_continuation or self.cfg.held_pose)
                and (self.carry_plan is not None or self.carry_search is not None)):
            return
        return super().enter(mode,reason,x)

    def pose_action(self,x,goal,grip):
        route=getattr(self,'transport16',None)
        if route is not None and self.transport16_attempt==self.attempts:
            if self.mode=='CARRY':goal=route['carry_goal']
            elif self.mode=='PLACE':goal=route['place_goal']
        return super().pose_action(x,goal,grip)

    def checked_empty_translation(self,x,goal,rotation):
        if not self.cfg.edge_stability:return super().checked_empty_translation(x,goal,rotation)
        action,receipt=propose(x,goal,rotation,self.motion,self.cfg,held=False)
        self._empty16_receipt=receipt
        self.edge16_events.append({'step':self.clock,'event':'pretranslate_mixed_step',**receipt})
        # Parent checks both margins and current joint margin before aperture
        # pulses. A rejected mixed proposal cannot accidentally pass its guard.
        if not receipt['accepted']:return action,-1e9,-1e9
        return action,receipt['box_margin_m'],receipt['can_margin_m']

    def segmented_action(self,x):
        self._empty16_receipt=None
        if (self.cfg.edge_stability and self.mode=='EDGE_PRETRANSLATE'
                and self.edge_plan is not None and not self.gap_ready(x)):
            action,info=self.hold(x,'v16_aperture_only',0)
            domain,_=support(x,self.floor)
            if self.pose_changed(x) or domain is None or self.joint_margin16()<self.cfg.joint_solution_margin_rad:
                self.begin_wait('v16_pretranslate_pose_or_joint_guard',x)
                info.update(next_mode=self.mode);return action,info
            if self.age>self.cfg.stage_timeout:
                self.failed_attempts+=1;self.start_attempt('phase_timeout',x)
                info.update(next_mode=self.mode);return action,info
            return self.aperture_only16(x,info)
        result=super().segmented_action(x)
        if result is not None and self._empty16_receipt is not None:
            action,info=result
            info.update(mixed_pose=self._empty16_receipt,
                        planning_work_units=self._empty16_receipt['work'],planning_kind='v16_edge_mixed')
            if self._empty16_receipt['accepted'] and not np.array_equal(action[:6],np.r_[
                    np.asarray(self._empty16_receipt['translation_m'])/.05,
                    np.asarray(self._empty16_receipt['rotation_vector_rad'])/.5].astype(np.float32)):
                assert np.array_equal(action[:6],np.zeros(6))
                info.update(mixed_pose_applied=False,mixed_pose_submission_reason='parent_joint_or_pose_guard')
        return result

    def aperture_only16(self,x,info):
        """Keep inherited aperture pulses separate from certified pose moves.

        This is an observed-gap adjustment, not a mixed-pose certificate. Wait
        for the inherited aperture settling criterion before moving again.
        """
        action=np.zeros(7,np.float32);error=abs(float(x[7]-x[8]))-self.approach_gap
        if abs(error)>self.cfg.aperture_tolerance_m and self.clock-self.last_pulse>=self.cfg.gap_pulse_interval:
            action[6]=1. if error>0 else -1.;self.last_pulse=self.clock
        self.edge_settled=0
        self.edge16_events.append({'step':self.clock,'event':'aperture_only_wait','phase':self.mode,'grip':float(action[6])})
        info.update(mode='EDGE_APERTURE',next_mode=self.mode,aperture_ready=self.gap_ready(x),planning_work_units=0)
        return action,info

    def mixed_edge_action(self,x):
        phase=self.mode;self.edge_age+=1
        action,info=self.hold(x,'v16_edge_mixed',0)
        plan=self.edge_plan
        goal=self.edge_start if phase=='EDGE_ROTATE' else plan['above']
        self.goal_rotation=plan['rotation'].copy()
        margin=self.joint_margin16()
        if self.age>self.cfg.stage_timeout:
            self.edge16_events.append({'step':self.clock,'event':'edge_timeout','age':self.age})
            self.failed_attempts+=1;self.start_attempt('phase_timeout',x)
            info.update(next_mode=self.mode);return action,info
        if margin<self.cfg.joint_solution_margin_rad:
            self.edge16_events.append({'step':self.clock,'event':'edge_joint_or_timeout_guard','joint_margin_rad':margin,'age':self.age})
            self.begin_wait('v16_edge_joint_or_timeout_guard',x)
            info.update(next_mode=self.mode);return action,info
        if not self.gap_ready(x):return self.aperture_only16(x,info)
        action,receipt=propose(x,goal,self.goal_rotation,self.motion,self.cfg,held=False)
        self.edge16_events.append({'step':self.clock,'event':'edge_mixed_step','phase':phase,**receipt})
        info.update(mixed_pose=receipt,planning_kind='v16_edge_mixed',planning_work_units=receipt['work'])
        if not receipt['accepted']:
            self.begin_wait('v16_edge_mixed_geometry_unconfirmed',x)
            info.update(next_mode=self.mode);return action,info
        gap=abs(float(x[7]-x[8]));error=gap-self.approach_gap
        assert abs(error)<=self.cfg.aperture_tolerance_m and action[6]==0
        r=Rotation.from_quat(x[3:7]).as_matrix()
        position=float(np.linalg.norm(x[:3]-goal))
        angle=float(np.linalg.norm(Rotation.from_matrix(self.goal_rotation@r.T).as_rotvec()))
        ready=bool(position<.009 and angle<.08 and self.gap_ready(x))
        forecast=None;tail=None
        if phase=='EDGE_APPROACH' and self.cfg.budget_recenter:
            forecast=float(np.linalg.norm(x[:3]+self.cfg.delay*self.motion[:3]-goal))
            tail=object_margin(x[:3],self.grasp_target(x),r,[gap-.001,gap+.001],x)
            ready=bool(ready and forecast<.009 and tail>=.003)
        self.edge_settled=self.edge_settled+1 if ready else 0
        if self.edge_settled>=self.cfg.delay+3:
            self.edge16_events.append({'step':self.clock,'event':'edge_pose_settled','phase':phase,'position_error_m':position,'angle_rad':angle,'d2_forecast_error_m':forecast,'remaining_path_margin_m':tail})
            if phase=='EDGE_ROTATE':
                V5.enter(self,'EDGE_APPROACH','v16_checked_pose_settled',x);self.edge_settled=0
            else:self.enter('DESCEND','v16_checked_approach_and_aperture',x)
        info.update(mode=phase,next_mode=self.mode,feasibility='feasible',edge_phase_steps=self.edge_age,
                    aperture_ready=self.gap_ready(x),d2_forecast_error_m=forecast,remaining_path_margin_m=tail)
        return action,info

    def carry_action(self,x,action,info):
        if (self.cfg.ik_continuation and self.mode=='CARRY' and info.get('stable_hold')
                and self.attempts not in self.carry_checked):
            from .carry_search import CarryPathSearch
            self.carry_checked.add(self.attempts)
            self.carry_search=CarryPathSearch(self,x,self.joints)
            self.carry_reference=self.carry_search.envelope
            self.ik16_events.append({'step':self.clock,'event':'bounded_continuation_started','remaining_steps':self.cfg.horizon_steps-self.clock})
        search=self.carry_search
        if (not self.cfg.held_pose or self.mode!='CARRY' or not info.get('stable_hold')
                or search is not None or self.carry_plan is None):
            result=super().carry_action(x,action,info)
            if self.cfg.ik_continuation and search is not None and search.done:
                self.ik16_events.append({'step':self.clock,'event':'bounded_continuation_complete','chosen':search.chosen is not None,'work':search.work,'options':search.receipts})
                if search.chosen is not None and 'carry_goal' in search.chosen:
                    self.transport16=search.chosen;self.transport16_attempt=self.attempts
            return result
        stage=self.carry_plan['stages'][self.carry_index];self.carry_phase_age+=1
        error=self.carry_reference.relative_errors(x);margin=self.joint_margin16()
        if (error['position_m']>self.cfg.relative_tolerance_m or margin<self.cfg.joint_solution_margin_rad
                or self.carry_phase_age>self.cfg.stage_timeout):
            self.held16_events.append({'step':self.clock,'event':'held_joint_transform_or_timeout_guard','joint_margin_rad':margin,'age':self.carry_phase_age,**error})
            self.carry_plan=None;self.failed_attempts+=1;self.start_attempt('v16_held_execution_guard',x,True)
            return np.array([0,0,0,0,0,0,1],np.float32),{**info,'mode':'CARRY_GUARD','next_mode':self.mode}
        self.goal_rotation=stage['rotation'].copy()
        action,receipt=propose(x,stage['goal'],self.goal_rotation,self.motion,self.cfg,held=True,grip=1.)
        self.held16_events.append({'step':self.clock,'event':'held_mixed_step','segment':stage['label'],**receipt})
        if not receipt['accepted']:
            self.carry_plan=None;self.failed_attempts+=1;self.start_attempt('v16_held_mixed_geometry_unconfirmed',x,True)
        else:
            ready=receipt['position_error_m']<.009 and receipt['orientation_error_rad']<.08 and info.get('stable_hold')
            self.carry_settled=self.carry_settled+1 if ready else 0
            if self.carry_settled>=self.cfg.delay+3:
                self.held16_events.append({'step':self.clock,'event':'held_pose_settled','segment':stage['label'],'position_error_m':receipt['position_error_m'],'angle_rad':receipt['orientation_error_rad']})
                if stage['kind']=='rotate':self.held_offset=x[:3].astype(float)-x[16:19]
                self.carry_index+=1;self.carry_settled=0;self.carry_phase_age=0
                if self.carry_index==len(self.carry_plan['stages']):self.carry_plan=None
        info.update(mode='CARRY_PATH' if self.mode=='CARRY' else 'CARRY_GUARD',next_mode=self.mode,
                    carry_segment=stage['label'],mixed_pose=receipt,planning_kind='v16_held_mixed',planning_work_units=receipt['work'],
                    accepted=receipt['accepted'],hand_margin_m=receipt.get('box_margin_m'),carried_can_margin_m=receipt.get('can_margin_m'))
        return action,info

    def placement_action16(self,x,action,info):
        route=self.transport16 if self.transport16_attempt==self.attempts else None
        goal=route['place_goal'] if route is not None else np.r_[self.target[:2],self.floor+.085]+self.held_offset
        if route is not None:self.goal_rotation=route['rotation'].copy()
        if self.cfg.held_pose:
            error=self.carry_reference.relative_errors(x);margin=self.joint_margin16()
            if error['position_m']>self.cfg.relative_tolerance_m or margin<self.cfg.joint_solution_margin_rad:
                receipt={'accepted':False,'reason':'placement_joint_or_transform_guard','joint_margin_rad':margin,**error}
            elif not info.get('stable_hold'):
                return np.array([0,0,0,0,0,0,1],np.float32),{**info,'mode':'PLACE_HOLD','next_mode':self.mode}
            else:
                action,receipt=propose(x,goal,self.goal_rotation,self.motion,self.cfg,held=True,grip=1.)
                info.update(mixed_pose=receipt,planning_kind='v16_held_mixed',planning_work_units=receipt['work'])
            self.held16_events.append({'step':self.clock,'event':'placement_mixed_step',**receipt})
        else:
            action=V5.pose_action(self,x,goal,1.)
            r=Rotation.from_quat(x[3:7]).as_matrix()
            angle=np.linalg.norm(Rotation.from_matrix(self.goal_rotation@r.T).as_rotvec())
            if angle>.04:
                action[:3]=0.;receipt=rotation_certificate(x,Rotation.from_rotvec(action[3:6]*.5).as_matrix()@r)
            else:action[3:6]=0.;receipt=translation_certificate(x,goal)
        if not receipt['accepted']:
            self.failed_attempts+=1;self.start_attempt('v16_placement_unconfirmed',x,True)
            action=np.array([0,0,0,0,0,0,1],np.float32)
            info.update(mode='CARRY_GUARD',next_mode=self.mode)
        return action,info

    def choose(self,x,proposal,previous_action):
        if not self.active16():return super().choose(x,proposal,previous_action)
        x=np.asarray(x,np.float32);tic=time.perf_counter();self._motion(x)
        if self.transport16_attempt!=self.attempts:self.transport16=None
        try:
            result=self.segmented_action(x) if self.cfg.segmented_edge else None
            if (result is None and self.cfg.edge_stability and self.mode in ['EDGE_ROTATE','EDGE_APPROACH']
                    and self.edge_plan is not None and self.edge_search is None):
                self.joint_replan(x)
                if self.edge_plan is not None:
                    domain,_=(support13 if self.support13 else support)(x,self.floor)
                    if self.pose_changed(x) or domain is None:self.begin_wait('v16_edge_pose_changed',x)
                    else:result=self.mixed_edge_action(x)
            if result is None:
                # V14 retains all ancestral observation, loss, timeout, descent
                # and support logic. Do not run V15's split-axis postprocessor
                # after certifying a mixed command.
                action,info=V14.choose(self,x,proposal,previous_action)
                if self.cfg.carry_path:action,info=self.carry_action(x,action,info)
                if (self.cfg.carry_path and (self.mode=='PLACE' or info.get('mode')=='PLACE')
                        and self.carry_reference is not None):
                    action,info=self.placement_action16(x,action,info)
            else:action,info=result
            info['planning_ms']=1000*(time.perf_counter()-tic)
            return action,info
        finally:
            self.last_observed=x.copy();self.last_joints=None if self.joints is None else self.joints.copy()
