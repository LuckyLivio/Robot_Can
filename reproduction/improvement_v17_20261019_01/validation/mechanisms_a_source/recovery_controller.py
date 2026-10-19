"""Isolated v17 repairs. Disabled switches reproduce the actual v16 controller.

Only observations, observed joints and controller history enter the runtime.
The inherited clock, FIFO, success definition and protection thresholds stay
unchanged. Short paths still need geometric/IK evidence and live confirmation.
"""
from dataclasses import dataclass
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import (
    RecoveryController as V16, Config as C16,
)
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5
from reproduction.improvement_v8_20261015_01.recovery.geometry import support
from reproduction.improvement_v13_20261016_01.recovery.support import support as support13
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin


@dataclass(frozen=True)
class Config(C16):
    route_efficiency: bool = True
    edge_convergence: bool = True
    held_stability: bool = True


class RecoveryController(V16):
    def __init__(self, target, floor_z, initial_state, enabled=True, config=None):
        super().__init__(target, floor_z, initial_state, enabled, config or Config())
        self.route17_events=[]
        self.edge17_events=[]
        self.held17_events=[]
        self.servo17={}
        self.last_submitted17=None
        self._proposal_state17=None

    def choose(self,x,proposal,previous_action):
        result=super().choose(x,proposal,previous_action)
        self.last_submitted17=np.asarray(result[0],np.float32).copy()
        return result

    def propose17(self,x,goal,rotation,*,held,grip,phase,aperture_motion=False):
        from .pose_servo import ServoState,propose
        # Separate empty/held memory, with exact phase/goal reset inside the
        # helper. Previous submitted commands are known controller history.
        key='held' if held else 'edge'
        if key not in self.servo17:self.servo17[key]=ServoState()
        self._proposal_state17=self.servo17[key]
        action,receipt=propose(x,goal,rotation,self.motion,self.cfg,held=held,grip=grip,
                               state=self._proposal_state17,phase=(self.attempts,phase),
                               previous_action=self.last_submitted17,aperture_motion=aperture_motion)
        if not receipt['accepted']:self._proposal_state17.reset()
        return action,receipt

    def commit17(self,action,receipt):
        assert self._proposal_state17.commit(action,receipt),'Only the actual certified action may update feedback memory'

    def segmented_action(self,x):
        if self.enabled and self.cfg.edge_convergence and self.mode=='EDGE_PRETRANSLATE':
            return self.edge_action17(x)
        return super().segmented_action(x)

    def mixed_edge_action(self,x):
        if self.enabled and self.cfg.edge_convergence:
            return self.edge_action17(x)
        return super().mixed_edge_action(x)

    def edge_action17(self,x):
        """One clock tick, original readiness, optionally certified aperture motion."""
        phase=self.mode
        if phase!='EDGE_PRETRANSLATE':self.edge_age+=1
        action,info=self.hold(x,'v17_edge_pose',0)
        plan=self.edge_plan
        domain,_=(support13 if phase!='EDGE_PRETRANSLATE' and self.support13 else support)(x,self.floor)
        if plan is None or self.pose_changed(x) or domain is None:
            self.begin_wait('v17_edge_pose_invalidated',x)
            info.update(next_mode=self.mode);return action,info
        if self.age>self.cfg.stage_timeout:
            self.failed_attempts+=1;self.start_attempt('phase_timeout',x)
            info.update(next_mode=self.mode);return action,info
        margin=self.joint_margin16()
        if margin<self.cfg.joint_solution_margin_rad:
            self.begin_wait('v17_edge_joint_guard',x)
            info.update(next_mode=self.mode);return action,info
        if phase=='EDGE_PRETRANSLATE':
            goal=plan['pre_goal'];rotation=plan['pre_rotation']
        else:
            goal=self.edge_start if phase=='EDGE_ROTATE' else plan['above']
            rotation=plan['rotation']
        self.goal_rotation=rotation.copy()
        gap=abs(float(x[7]-x[8]));error=gap-self.approach_gap
        grip=0.
        if abs(error)>self.cfg.aperture_tolerance_m and self.clock-self.last_pulse>=self.cfg.gap_pulse_interval:
            grip=1. if error>0 else -1.
        aperture_motion=not self.gap_ready(x) or grip!=0
        action,receipt=self.propose17(x,goal,rotation,held=False,grip=grip,
                                     phase=phase,aperture_motion=aperture_motion)
        self.edge17_events.append({'step':self.clock,'event':'edge_certified_control','phase':phase,**receipt})
        info.update(mixed_pose=receipt,planning_kind='v17_edge_pose',planning_work_units=receipt['work'])
        if not receipt['accepted']:
            if aperture_motion:
                # No additional geometry search this tick. Retain the original
                # gap-only pulse and settling policy when simultaneous motion
                # over the full aperture interval cannot be certified.
                action,info=self.aperture_only16(x,info)
                info.update(planning_kind='v17_edge_pose',planning_work_units=receipt['work'],mixed_pose=receipt)
                return action,info
            self.begin_wait('v17_edge_geometry_unconfirmed',x)
            info.update(next_mode=self.mode);return action,info
        if grip:self.last_pulse=self.clock
        self.commit17(action,receipt)
        r=Rotation.from_quat(x[3:7]).as_matrix()
        position=float(np.linalg.norm(x[:3]-goal))
        angle=float(np.linalg.norm(Rotation.from_matrix(rotation@r.T).as_rotvec()))
        ready=bool(position<.009 and angle<.08 and self.gap_ready(x))
        forecast=None;tail=None
        if phase=='EDGE_APPROACH' and self.cfg.budget_recenter:
            forecast=float(np.linalg.norm(x[:3]+self.cfg.delay*self.motion[:3]-goal))
            tail=object_margin(x[:3],self.grasp_target(x),r,[gap-.001,gap+.001],x)
            ready=bool(ready and forecast<.009 and tail>=.003)
        self.edge_settled=self.edge_settled+1 if ready else 0
        if self.edge_settled>=self.cfg.delay+3:
            self.edge17_events.append({'step':self.clock,'event':'edge_pose_settled','phase':phase,
                                      'position_error_m':position,'angle_rad':angle,
                                      'd2_forecast_error_m':forecast,'remaining_path_margin_m':tail})
            if phase=='EDGE_PRETRANSLATE':
                self.goal_rotation=plan['rotation'].copy()
                V5.enter(self,'EDGE_ROTATE','v17_pretranslate_confirmed',x);self.edge_settled=0
            elif phase=='EDGE_ROTATE':
                V5.enter(self,'EDGE_APPROACH','v17_rotation_confirmed',x);self.edge_settled=0
            else:self.enter('DESCEND','v17_approach_and_aperture_confirmed',x)
        info.update(mode=phase,next_mode=self.mode,feasibility='feasible',edge_phase_steps=self.edge_age,
                    aperture_ready=self.gap_ready(x),d2_forecast_error_m=forecast,remaining_path_margin_m=tail,
                    hand_margin_m=receipt['box_margin_m'],can_margin_m=receipt['can_margin_m'])
        return action,info

    def carry_action(self, x, action, info):
        if (self.enabled and self.cfg.route_efficiency and self.cfg.ik_continuation
                and self.mode=='CARRY' and info.get('stable_hold')
                and self.attempts not in self.carry_checked):
            from .carry_search import CarryPathSearch
            self.carry_checked.add(self.attempts)
            self.carry_search=CarryPathSearch(self,x,self.joints)
            self.carry_reference=self.carry_search.envelope
            self.route17_events.append({'step':self.clock,'event':'shared_short_route_started',
                                        'remaining_steps':self.cfg.horizon_steps-self.clock})
        search=self.carry_search
        if (self.enabled and self.cfg.held_stability and self.cfg.held_pose
                and self.mode=='CARRY' and info.get('stable_hold')
                and search is None and self.carry_plan is not None):
            result=self.held_action17(x,info)
        else:
            result=super().carry_action(x,action,info)
        if self.cfg.route_efficiency and search is not None and search.done:
            self.route17_events.append({'step':self.clock,'event':'shared_short_route_complete',
                                        'chosen':search.chosen is not None,'work':search.work,
                                        'options':search.receipts})
        return result

    def held_action17(self,x,info):
        stage=self.carry_plan['stages'][self.carry_index]
        self.carry_phase_age+=1
        error=self.carry_reference.relative_errors(x);margin=self.joint_margin16()
        if (error['position_m']>self.cfg.relative_tolerance_m
                or margin<self.cfg.joint_solution_margin_rad
                or self.carry_phase_age>self.cfg.stage_timeout):
            self.held17_events.append({'step':self.clock,'event':'held_execution_guard',
                                      'joint_margin_rad':margin,'age':self.carry_phase_age,**error})
            self.carry_plan=None;self.failed_attempts+=1
            self.start_attempt('v17_held_execution_guard',x,True)
            return np.array([0,0,0,0,0,0,1],np.float32),{**info,'mode':'CARRY_GUARD','next_mode':self.mode}
        self.goal_rotation=stage['rotation'].copy()
        action,receipt=self.propose17(x,stage['goal'],self.goal_rotation,held=True,grip=1.,
                                     phase='CARRY_'+stage['label'])
        self.held17_events.append({'step':self.clock,'event':'held_certified_control',
                                  'segment':stage['label'],**receipt})
        if not receipt['accepted']:
            self.carry_plan=None;self.failed_attempts+=1
            self.start_attempt('v17_held_geometry_unconfirmed',x,True)
        else:
            self.commit17(action,receipt)
            ready=receipt['position_error_m']<.009 and receipt['orientation_error_rad']<.08 and info.get('stable_hold')
            self.carry_settled=self.carry_settled+1 if ready else 0
            if self.carry_settled>=self.cfg.delay+3:
                self.held17_events.append({'step':self.clock,'event':'held_pose_settled',
                                          'segment':stage['label'],'position_error_m':receipt['position_error_m'],
                                          'angle_rad':receipt['orientation_error_rad']})
                if stage['kind']=='rotate':self.held_offset=x[:3].astype(float)-x[16:19]
                self.carry_index+=1;self.carry_settled=0;self.carry_phase_age=0
                if self.carry_index==len(self.carry_plan['stages']):self.carry_plan=None
        info.update(mode='CARRY_PATH' if self.mode=='CARRY' else 'CARRY_GUARD',next_mode=self.mode,
                    carry_segment=stage['label'],mixed_pose=receipt,planning_kind='v17_held_pose',
                    planning_work_units=receipt['work'],accepted=receipt['accepted'],
                    hand_margin_m=receipt.get('box_margin_m'),carried_can_margin_m=receipt.get('can_margin_m'))
        return action,info

    def placement_action16(self,x,action,info):
        if not (self.enabled and self.cfg.held_stability and self.cfg.held_pose):
            return super().placement_action16(x,action,info)
        route=self.transport16 if self.transport16_attempt==self.attempts else None
        goal=route['place_goal'] if route is not None else np.r_[self.target[:2],self.floor+.085]+self.held_offset
        if route is not None:self.goal_rotation=route['rotation'].copy()
        error=self.carry_reference.relative_errors(x);margin=self.joint_margin16()
        if error['position_m']>self.cfg.relative_tolerance_m or margin<self.cfg.joint_solution_margin_rad:
            receipt={'accepted':False,'reason':'placement_joint_or_transform_guard','joint_margin_rad':margin,**error}
        elif not info.get('stable_hold'):
            return np.array([0,0,0,0,0,0,1],np.float32),{**info,'mode':'PLACE_HOLD','next_mode':self.mode}
        else:
            action,receipt=self.propose17(x,goal,self.goal_rotation,held=True,grip=1.,phase='PLACE')
            info.update(mixed_pose=receipt,planning_kind='v17_held_pose',planning_work_units=receipt['work'])
            if receipt['accepted']:self.commit17(action,receipt)
        self.held17_events.append({'step':self.clock,'event':'placement_certified_control',**receipt})
        if not receipt['accepted']:
            self.failed_attempts+=1;self.start_attempt('v17_placement_unconfirmed',x,True)
            action=np.array([0,0,0,0,0,0,1],np.float32)
            info.update(mode='CARRY_GUARD',next_mode=self.mode)
        return action,info
