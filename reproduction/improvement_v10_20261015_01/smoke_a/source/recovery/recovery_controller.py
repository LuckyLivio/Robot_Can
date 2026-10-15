"""v10 wall-edge approach, isolated from frozen v9 and its assets."""
from dataclasses import dataclass
import time
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v9_20261015_01.recovery.recovery_controller import RecoveryController as V9,Config as C9
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5
from reproduction.improvement_v8_20261015_01.recovery.geometry import support
from reproduction.improvement_v7_20261015_01.recovery.pose_guard import difference
from .path_search import EdgeSearch

@dataclass(frozen=True)
class Config(C9):
    adaptive_height:bool=True
    edge_path:bool=True

class RecoveryController(V9):
    def __init__(self,*args,**kwargs):
        if len(args)<5 and kwargs.get('config') is None:kwargs['config']=Config()
        super().__init__(*args,**kwargs)
        self.edge_search=None;self.edge_plan=None;self.edge_checked=False;self.edge_events=[];self.edge_age=0;self.edge_settled=0
    def plan_grasp(self,x):
        self.edge_search=None;self.edge_plan=None;self.edge_checked=False
        return super().plan_grasp(x)
    def begin_wait(self,reason,x):
        self.edge_search=None;self.edge_plan=None
        return super().begin_wait(reason,x)
    def eligible(self,x):
        d,_=support(x,self.floor)
        return (self.mode=='ALIGN' and self.expanded_plan and self.mesh_search is None and not self.edge_checked
                and self.attempts in self.relocated_attempts and d is not None and d['kind']=='wall_top')
    def edge_action(self,x):
        phase=self.mode;self.edge_age+=1
        action,info=self.hold(x,'edge_execution',0)
        self.goal_rotation=self.edge_plan['rotation'].copy()
        goal=self.edge_start if phase=='EDGE_ROTATE' else self.edge_plan['above']
        action=self.pose_action(x,goal,0.)
        # Same observed-aperture pulse rule as v6, also in the new approach modes.
        error=abs(float(x[7]-x[8]))-self.approach_gap
        if abs(error)>self.cfg.aperture_tolerance_m and self.clock-self.last_pulse>=self.cfg.gap_pulse_interval:
            action[6]=1. if error>0 else -1.;self.last_pulse=self.clock
        angle=np.linalg.norm(Rotation.from_matrix(self.goal_rotation@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec())
        at=np.linalg.norm(x[:3]-goal)<.009 and angle<.08
        self.edge_settled=self.edge_settled+1 if at else 0
        if self.edge_settled>=self.cfg.delay+3:
            if phase=='EDGE_ROTATE':V5.enter(self,'EDGE_APPROACH','edge_rotation_settled',x);self.edge_settled=0
            elif self.gap_ready(x):self.enter('DESCEND','edge_approach_and_aperture_validated',x)
        if self.edge_age>self.cfg.stage_timeout and self.mode.startswith('EDGE_'):
            self.failed_attempts+=1;self.start_attempt('phase_timeout',x)
        info.update(mode=phase,next_mode=self.mode,feasibility='feasible',edge_phase_steps=self.edge_age,aperture_ready=self.gap_ready(x))
        return action,info
    def choose(self,x,proposal,previous_action):
        if not (self.cfg.adaptive_height or self.cfg.edge_path) or not self.enabled:return super().choose(x,proposal,previous_action)
        x=np.asarray(x,np.float32);tic=time.perf_counter()
        if self.edge_search is None and self.eligible(x):
            assert self.joints is not None
            self.edge_checked=True;self.joint_checked=True;self.joint_search=None
            self.edge_search=EdgeSearch(self,x,self.joints);self.edge_start=x[:3].copy()
        if self.edge_search is not None:
            s=self.edge_search;d,a=difference(x[16:23],s.anchor);domain,_=support(x,self.floor)
            before=s.work
            if d>self.cfg.pose_position_m or a>np.deg2rad(self.cfg.pose_axis_deg) or domain is None:
                self.edge_events.append({'step':self.clock,'event':'search_invalidated'})
                self.begin_wait('edge_search_pose_changed_or_unknown',x)
            elif s.advance(self.cfg.ik_iterations_per_step):
                self.edge_events.append({'step':self.clock,'event':'search_complete','chosen':s.chosen is not None,'options':s.receipts,'work':s.work})
                self.edge_search=None
                if s.chosen is None:
                    self.kinematic_blocked=True;self.plan_ok=False;self.block('edge_no_validated_local_path',x)
                else:
                    self.edge_plan=s.chosen;self.mesh_offset=s.chosen['offset'];self.planned_rotation=s.chosen['rotation'].copy()
                    self.goal_rotation=self.planned_rotation.copy();self.plan_anchor=x[16:23].copy();self.pose_anchor=x[16:23].copy()
                    self.edge_age=0;self.edge_settled=0;V5.enter(self,'EDGE_ROTATE','edge_path_validated',x)
            action,info=self.hold(x,'edge_search',s.work-before)
        elif self.mode.startswith('EDGE_'):
            domain,_=support(x,self.floor)
            if self.pose_changed(x) or domain is None:
                self.begin_wait('edge_execution_pose_changed_or_unknown',x);action,info=super().choose(x,proposal,previous_action)
            else:action,info=self.edge_action(x)
        else:action,info=super().choose(x,proposal,previous_action)
        info.update(edge_plan=self.edge_plan is not None,planning_ms=1000*(time.perf_counter()-tic))
        return action,info
