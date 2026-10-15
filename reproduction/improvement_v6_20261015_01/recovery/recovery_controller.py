"""v6: achieved aperture/path guard and explicit no-feasible recovery handling."""
from collections import deque
from dataclasses import dataclass
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5,Config as V5Config
from .clearance_guard import candidates,goal_for,key,vertical_margin,clearance_margin,upright_margin


@dataclass(frozen=True)
class Config(V5Config):
    aperture_guard:bool=True
    prevent_repeat:bool=True
    aperture_tolerance_m:float=.0045
    gap_uncertainty_m:float=.001
    gap_settle_m:float=.0008
    gap_pulse_interval:int=5
    aperture_timeout:int=24
    path_margin_m:float=.001
    path_step_m:float=.005


class RecoveryController(V5):
    def __init__(self,target,floor_z,initial_state,enabled=True,config=None):
        super().__init__(target,floor_z,initial_state,enabled,config or Config())
        self.gaps=deque(maxlen=4);self.last_pulse=-100
        self.guard_scope=False;self.plan_ok=True;self.plan_reason='not_applicable';self.plan_margin=None
        self.plan_key=None;self.plan_anchor=None;self.failed_plans=[];self.block_after_retract=False
        self.guard_events=[]
        self._inside_v5=False;self._abort_pending=False

    def plan_grasp(self,x):
        super().plan_grasp(x)
        if not (self.cfg.aperture_guard or self.cfg.prevent_repeat):return
        opts,self.guard_scope=candidates(self,x)
        self.plan_ok=True;self.plan_reason='not_applicable';self.plan_margin=None;self.plan_key=None
        if not self.guard_scope:return
        rejected={'repeat':0,'geometry':0};chosen=None
        for opt in opts:
            if self.cfg.prevent_repeat and any(np.linalg.norm(x[16:19]-p['position'])<.008 and
                    np.linalg.norm(Rotation.from_quat(x[19:23]).as_rotvec()-p['rotation'])<.15 and opt['key']==p['key'] for p in self.failed_plans):
                rejected['repeat']+=1;continue
            goal=goal_for(self,x,opt)
            extra=self.cfg.aperture_tolerance_m+self.cfg.gap_uncertainty_m if self.cfg.aperture_guard else 0.
            gap=min(.085,opt['gap']+extra)
            margin=(upright_margin(goal,opt['rotation'],opt['cell'],gap) if self.grasp_kind=='upright'
                    else clearance_margin(goal,opt['rotation'],opt['cell'],self.floor,gap))
            if self.grasp_kind=='sideways' and margin>=self.cfg.path_margin_m and self.cfg.aperture_guard:
                margin=vertical_margin(goal,opt['rotation'],opt['cell'],self.floor,gap,self.cfg.path_step_m)
            if margin<self.cfg.path_margin_m:
                rejected['geometry']+=1;continue
            chosen=(opt,margin);break
        self.plan_anchor=x[16:23].copy()
        if chosen is None:
            self.plan_ok=False;self.plan_reason='no_untried_feasible_candidate'
        else:
            opt,self.plan_margin=chosen;self.planned_rotation=opt['rotation'].copy()
            self.grasp_offset=opt['grasp_offset'].copy();self.side_offset=opt['side_offset'].copy()
            self.approach_gap=opt['gap'];self.plan_key=opt['key'];self.guard_cell=opt['cell']
            self.plan_reason='feasible'
        self.guard_events.append({'step':self.clock,'reason':self.plan_reason,'candidates':len(opts),
                                  'rejected':rejected,'margin_m':self.plan_margin,
                                  'geometry_model':'v5_upright_footprint' if self.grasp_kind=='upright' else 'side_hand_finger_mesh'})

    def start_attempt(self,reason,x,holding=False):
        if self.cfg.prevent_repeat and self.plan_key is not None and reason in ['phase_timeout','lift_probe_failed','descent_stalled_preserve_budget','observed_grasp_loss','aperture_timeout','execution_guard']:
            self.failed_plans.append({'key':self.plan_key,'position':self.plan_anchor[:3].copy(),
                                     'rotation':Rotation.from_quat(self.plan_anchor[3:7]).as_rotvec()})
        super().start_attempt(reason,x,holding)
        if self.cfg.prevent_repeat and self.guard_scope and not self.plan_ok and self.mode!='EXHAUSTED' and not holding:
            self.failed_attempts+=1;self.waypoint=np.r_[x[:2],max(self.floor+self.cfg.approach_clearance_m,x[2])]
            self.goal_rotation=Rotation.from_quat(x[3:7]).as_matrix()
            if self._inside_v5:self._abort_pending=True
            else:super().enter('ABORT_RETRACT','no_untried_feasible_candidate',x)

    def gap_ready(self,x):
        return (self.approach_gap is not None and len(self.gaps)>=3 and
                abs(abs(float(x[7]-x[8]))-self.approach_gap)<=self.cfg.aperture_tolerance_m and
                max(self.gaps)-min(self.gaps)<self.cfg.gap_settle_m and self.clock-self.last_pulse>=self.cfg.delay+2)

    def enter(self,mode,reason,x):
        if mode=='DESCEND' and self.cfg.aperture_guard and self.guard_scope:
            if not self.plan_ok:
                self.start_attempt('execution_guard',x);return
            if not self.gap_ready(x):
                super().enter('APERTURE','wait_for_observed_aperture',x);return
        super().enter(mode,reason,x)

    def pose_action(self,x,goal,grip):
        action=super().pose_action(x,goal,grip)
        if self.cfg.aperture_guard and self.approach_gap is not None and self.mode in ['RETRACT','ALIGN','APERTURE','DESCEND']:
            error=abs(float(x[7]-x[8]))-self.approach_gap
            action[6]=0.
            if abs(error)>self.cfg.aperture_tolerance_m and self.clock-self.last_pulse>=self.cfg.gap_pulse_interval:
                action[6]=1. if error>0 else -1.;self.last_pulse=self.clock
        return action

    def custom_action(self,x):
        if self.mode in ['APERTURE','ABORT_RETRACT','BLOCKED']:
            phase=self.mode;self.clock+=1;self.age+=1
            if phase=='APERTURE':
                grasp=self.grasp_target(x);goal=np.r_[grasp[:2],max(self.floor+self.cfg.approach_clearance_m,x[18]+.14)]
                action=self.pose_action(x,goal,0.)
                angle=np.linalg.norm(Rotation.from_matrix(self.planned_rotation@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec())
                if self.gap_ready(x) and angle<.08:
                    super().enter('DESCEND','observed_aperture_settled',x)
                elif self.age>=self.cfg.aperture_timeout:
                    self.failed_attempts+=1;self.start_attempt('aperture_timeout',x)
            else:
                action=super().pose_action(x,self.waypoint,0.)
                if phase=='ABORT_RETRACT' and self.age>self.cfg.delay+5 and abs(x[2]-self.waypoint[2])<.014:
                    super().enter('BLOCKED','no_feasible_plan_no_repeated_descent',x)
            return action,{'mode_before':phase,'mode':phase,'next_mode':self.mode,'stable_hold':False,
                    'intervened':True,'attempts':self.attempts,'gap_m':abs(float(x[7]-x[8])),
                    'plan_status':self.plan_reason,'guard_margin_m':self.plan_margin,'gap_target_m':self.approach_gap}
        return None

    def choose(self,x,proposal,previous_action):
        if not self.enabled or not (self.cfg.aperture_guard or self.cfg.prevent_repeat):
            return super().choose(x,proposal,previous_action)
        x=np.asarray(x,np.float32);self.gaps.append(abs(float(x[7]-x[8])))
        custom=self.custom_action(x)
        if custom is not None:return custom
        if self.cfg.aperture_guard and self.mode=='DESCEND' and self.guard_scope:
            moved=self.plan_anchor is not None and np.linalg.norm(x[16:19]-self.plan_anchor[:3])>.012
            too_open=self.approach_gap is not None and abs(float(x[7]-x[8]))>self.approach_gap+self.cfg.aperture_tolerance_m+.002
            if moved or too_open:
                self.failed_attempts+=1;self.start_attempt('execution_guard',x)
                custom=self.custom_action(x)
                if custom is not None:return custom
        self._inside_v5=True
        try:action,info=super().choose(x,proposal,previous_action)
        finally:self._inside_v5=False
        if self._abort_pending:
            self._abort_pending=False;super().enter('ABORT_RETRACT','no_untried_feasible_candidate',x)
            action=super().pose_action(x,self.waypoint,0.)
            info.update(next_mode=self.mode,intervened=True)
        info.update(plan_status=self.plan_reason,guard_margin_m=self.plan_margin,
                    gap_target_m=self.approach_gap,aperture_ready=self.gap_ready(x),failed_candidate_count=len(self.failed_plans))
        return action,info
