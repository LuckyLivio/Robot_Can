"""v8: expand only unknown support states and optionally relocate at high level."""
from dataclasses import dataclass
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v7_20261015_01.recovery.recovery_controller import RecoveryController as V7,Config as V7Config
from reproduction.improvement_v7_20261015_01.recovery.pose_guard import feasibility
from .geometry import support,plan,path_margin

@dataclass(frozen=True)
class Config(V7Config):
    geometry_support:bool=True
    retreat_replan:bool=True

class RecoveryController(V7):
    def __init__(self,*args,**kwargs):
        if len(args)<5 and kwargs.get('config') is None:kwargs['config']=Config()
        super().__init__(*args,**kwargs)
        self.expanded_plan=False;self.mesh_offset=None;self.mesh_domain=None;self.geometry_events=[]
        self.retreat_stage=None;self.last_x=None

    def refresh_feasibility(self,x):
        if self.cfg.geometry_support and self.expanded_plan:
            domain,reason=support(x,self.floor)
            self.feasibility_status='unknown' if domain is None else ('feasible' if self.plan_ok else 'infeasible')
            self.feasibility_reason=reason if domain is None else ('mesh_validated_hand_path' if self.plan_ok else 'mesh_no_feasible_hand_path')
            return self.feasibility_status
        return super().refresh_feasibility(x)

    def plan_grasp(self,x):
        self.expanded_plan=False;self.mesh_offset=None;super().plan_grasp(x)
        if not self.cfg.geometry_support or feasibility(self,x)[0]!='unknown':return
        chosen,reason,n=plan(self,x)
        self.geometry_events.append({'step':self.clock,'reason':reason,'candidates':n,'chosen':chosen is not None})
        if chosen is None:
            if n:
                self.expanded_plan=True;self.guard_scope=True;self.plan_ok=False;self.plan_reason=reason;self.plan_anchor=x[16:23].copy()
            self.refresh_feasibility(x);return
        self.expanded_plan=True;self.mesh_offset=chosen['offset'];self.mesh_domain=chosen['domain']
        self.planned_rotation=chosen['rotation'];self.grasp_kind=chosen['kind'];self.grasp_axis=chosen['domain']['axis']
        self.approach_gap=chosen['gap'];self.plan_key=chosen['key'];self.plan_margin=chosen['margin']
        self.guard_scope=True;self.plan_ok=True;self.plan_reason='mesh_feasible';self.plan_anchor=x[16:23].copy()
        self.corner_cell=None;self.side_cell=None;self.refresh_feasibility(x)

    def grasp_target(self,x):
        if self.expanded_plan and self.mesh_offset is not None:return x[16:19].astype(float)+self.mesh_offset
        return super().grasp_target(x)

    def begin_wait(self,reason,x):
        super().begin_wait(reason,x)
        if self.cfg.retreat_replan:
            self.retreat_stage='vertical';self.waypoint[2]=max(self.floor+.24,x[2])

    def pose_settled(self):
        if self.cfg.retreat_replan and self.retreat_stage is not None:
            if self.retreat_stage!='arrived':return False
        return super().pose_settled()

    def wait_action(self,x):
        if self.cfg.retreat_replan and self.mode=='POSE_WAIT':
            if self.retreat_stage=='vertical' and self.age>self.cfg.delay+5 and abs(x[2]-self.waypoint[2])<.014:
                from reproduction.recovery_v5_20261012_01.clearance import CELLS
                centers=[np.array([(a+b)/2,(c+d)/2]) for a,b,c,d in CELLS]
                center=min(centers,key=lambda p:np.linalg.norm(p-x[16:18]));goal=np.r_[center,self.waypoint[2]]
                gap=min(.085,abs(float(x[7]-x[8]))+.006)
                if path_margin(x[:3],goal,self.goal_rotation,gap)>=.001:
                    self.waypoint=goal;self.retreat_stage='lateral'
                else:self.retreat_stage='arrived'
            if self.retreat_stage=='lateral' and np.linalg.norm(x[:3]-self.waypoint)<.014:self.retreat_stage='arrived'
        return super().wait_action(x)

    def choose(self,x,proposal,previous_action):
        if not self.cfg.geometry_support and not self.cfg.retreat_replan:return super().choose(x,proposal,previous_action)
        self.last_x=np.asarray(x,np.float32)
        action,info=super().choose(x,proposal,previous_action)
        info.update(mesh_plan=self.expanded_plan,retreat_stage=self.retreat_stage)
        return action,info
