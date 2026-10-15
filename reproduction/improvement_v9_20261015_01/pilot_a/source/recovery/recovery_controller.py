"""v9: joint-observed equivalent-pose checks and bounded mesh/IK work slices."""
from dataclasses import dataclass
import time
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v8_20261015_01.recovery.recovery_controller import RecoveryController as V8,Config as C8
from reproduction.improvement_v7_20261015_01.recovery.recovery_controller import RecoveryController as V7
from reproduction.improvement_v7_20261015_01.recovery.pose_guard import feasibility,difference
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5
from .geometry import Search,vertical_margin
from .kinematics import IK,LIMITS

@dataclass(frozen=True)
class Config(C8):
    joint_selection:bool=True
    bounded_planning:bool=True
    mesh_candidates_per_step:int=8
    ik_iterations_per_step:int=16
    ik_iterations_per_target:int=48
    joint_warning_rad:float=.20
    joint_solution_margin_rad:float=.04

class PoseSearch:
    def __init__(self,c,x,q):
        goal=c.grasp_target(x);above=np.r_[goal[:2],max(c.floor+c.cfg.approach_clearance_m,x[18]+.14)]
        self.targets=[above,goal];self.q=np.array(q).copy();self.rotations=[c.planned_rotation.copy(),c.planned_rotation@np.diag([-1.,-1.,1.])]
        self.gap=(c.approach_gap or .08)+c.cfg.aperture_tolerance_m+c.cfg.gap_uncertainty_m
        self.max_iterations=c.cfg.ik_iterations_per_target;self.margin=c.cfg.joint_solution_margin_rad
        self.option=0;self.target=0;self.ik=IK(q,above,self.rotations[0],self.max_iterations)
        self.done=False;self.chosen=None;self.receipts=[];self.current=[];self.work=0
    def advance(self,iterations):
        # Upper bound counts IK updates and target/family transition checks.
        for _ in range(iterations):
            if self.done:break
            self.work+=1;self.ik.advance(1)
            if not self.ik.done:continue
            r=self.ik.receipt();self.current.append(r)
            valid=r['success'] and r['limit_margin_rad']>=self.margin
            if valid and self.target==0:
                self.target=1;self.ik=IK(self.ik.q,self.targets[1],self.rotations[self.option],self.max_iterations);continue
            path=vertical_margin(self.targets[0],self.targets[1],self.rotations[self.option],self.gap) if valid else None
            feasible=valid and path>=.001
            self.receipts.append({'equivalent_flip':bool(self.option),'targets':self.current,'hand_margin_m':path,'feasible':feasible})
            if feasible:self.chosen=self.option;self.done=True;break
            self.option+=1
            if self.option==2:self.done=True;break
            self.target=0;self.current=[];self.ik=IK(self.q,self.targets[0],self.rotations[self.option],self.max_iterations)
        return self.done

class RecoveryController(V8):
    def __init__(self,*args,**kwargs):
        if len(args)<5 and kwargs.get('config') is None:kwargs['config']=Config()
        super().__init__(*args,**kwargs)
        self.joints=None;self.mesh_search=None;self.joint_search=None;self.joint_checked=False
        self.kinematic_blocked=False;self.search_anchor=None;self.search_invalidations=0
        self.planning_events=[];self.joint_events=[];self.last_plan_work=0
    def set_joint_positions(self,q):
        q=np.asarray(q,float);assert q.shape==(7,) and np.all(np.isfinite(q));self.joints=q.copy()
    def refresh_feasibility(self,x):
        if getattr(self,'mesh_search',None) is not None:
            self.feasibility_status='unknown';self.feasibility_reason='bounded_mesh_search_pending';return 'unknown'
        if getattr(self,'kinematic_blocked',False):
            self.feasibility_status='infeasible';self.feasibility_reason='no_validated_equivalent_joint_pose';return 'infeasible'
        return super().refresh_feasibility(x)
    def plan_grasp(self,x):
        self.joint_checked=False;self.kinematic_blocked=False;self.joint_search=None
        if not self.cfg.bounded_planning:return super().plan_grasp(x)
        self.mesh_search=None;self.expanded_plan=False;self.mesh_offset=None
        V7.plan_grasp(self,x)
        if not self.cfg.geometry_support or feasibility(self,x)[0]!='unknown':return
        search=Search(self,x)
        if search.domain is None:
            self.geometry_events.append({'step':self.clock,'reason':search.reason,'candidates':0,'chosen':False})
            self.refresh_feasibility(x);return
        self.mesh_search=search;self.search_anchor=x[16:23].copy()
        # Pending is not a feasible candidate: descent is prevented by refresh + hold.
        # Keep v6's synchronous abort hook inactive until the search is resolved.
        self.guard_scope=False;self.plan_ok=True
        self.refresh_feasibility(x)
    def finish_mesh(self,x):
        search=self.mesh_search;self.mesh_search=None;chosen=search.chosen
        self.geometry_events.append({'step':self.clock,'reason':search.reason,'candidates':len(search.opts),'chosen':chosen is not None})
        self.planning_events.append({'step':self.clock,'type':'mesh_complete','checked':search.checked,'reason':search.reason})
        if chosen is None:
            self.plan_ok=False;self.guard_scope=True
            self.block('bounded_mesh_no_feasible_candidate',x);return
        self.expanded_plan=True;self.mesh_offset=chosen['offset'];self.mesh_domain=chosen['domain']
        self.planned_rotation=chosen['rotation'];self.grasp_kind=chosen['kind'];self.grasp_axis=chosen['domain']['axis']
        self.approach_gap=chosen['gap'];self.plan_key=chosen['key'];self.plan_margin=chosen['margin']
        self.guard_scope=True;self.plan_ok=True;self.plan_reason='mesh_feasible'
        self.plan_anchor=x[16:23].copy();self.pose_anchor=x[16:23].copy();self.corner_cell=None;self.side_cell=None
        self.goal_rotation=Rotation.from_quat(x[3:7]).as_matrix();V5.enter(self,'RETRACT','bounded_mesh_ready',x)
        self.refresh_feasibility(x)
    def hold(self,x,kind,work):
        self.clock+=1;self.age+=1;self.poses.append(x[16:23].copy());self.gaps.append(abs(float(x[7]-x[8])))
        # Current position/rotation, zero grip increment. Queued D2 commands still run.
        action=np.zeros(7,np.float32)
        return action,{'mode_before':self.mode,'mode':'PLAN_WAIT','next_mode':self.mode,'stable_hold':False,'intervened':True,
            'attempts':self.attempts,'planning_kind':kind,'planning_work_units':work,'feasibility':'unknown','gap_m':abs(float(x[7]-x[8]))}
    def joint_needed(self):
        margin=float(np.min(np.minimum(self.joints-LIMITS[:,0],LIMITS[:,1]-self.joints)))
        return self.expanded_plan or margin<self.cfg.joint_warning_rad
    def choose(self,x,proposal,previous_action):
        if not self.cfg.joint_selection and not self.cfg.bounded_planning:return super().choose(x,proposal,previous_action)
        x=np.asarray(x,np.float32);tic=time.perf_counter();self.last_plan_work=0
        if self.mesh_search is not None:
            d,a=difference(x[16:23],self.search_anchor)
            if d>self.cfg.pose_position_m or a>np.deg2rad(self.cfg.pose_axis_deg):
                self.search_invalidations+=1;self.mesh_search=None
                if self.search_invalidations>self.cfg.max_pose_replans:self.block('bounded_search_pose_change_limit',x)
                else:self.begin_wait('bounded_search_pose_changed',x)
            else:
                before=self.mesh_search.index;done=self.mesh_search.advance(self.cfg.mesh_candidates_per_step)
                self.last_plan_work=self.mesh_search.index-before
                if done:self.finish_mesh(x)
            action,info=self.hold(x,'mesh',self.last_plan_work)
        else:
            if self.cfg.joint_selection and self.mode=='ALIGN' and not self.joint_checked:
                assert self.joints is not None,'Current joint positions must be supplied equally for BC and Full'
                self.joint_checked=True
                if self.joint_needed():self.joint_search=PoseSearch(self,x,self.joints);self.search_anchor=x[16:23].copy()
            if self.joint_search is not None:
                d,a=difference(x[16:23],self.search_anchor)
                if d>self.cfg.pose_position_m or a>np.deg2rad(self.cfg.pose_axis_deg):
                    self.joint_search=None;self.begin_wait('joint_search_pose_changed',x)
                else:
                    search=self.joint_search;before=search.work
                    done=search.advance(self.cfg.ik_iterations_per_step if self.cfg.bounded_planning else 1000)
                    self.last_plan_work=search.work-before
                    if done:
                        self.joint_events.append({'step':self.clock,'chosen_flip':search.chosen,'options':search.receipts,'work_units':search.work})
                        self.joint_search=None
                        if search.chosen is None:
                            self.kinematic_blocked=True;self.plan_ok=False;self.guard_scope=True;self.block('no_validated_equivalent_joint_pose',x)
                        else:
                            self.planned_rotation=search.rotations[search.chosen].copy();self.goal_rotation=self.planned_rotation.copy()
                            # Keep elapsed planning steps in the phase timeout and 400-step budget.
                action,info=self.hold(x,'joint',self.last_plan_work)
            else:action,info=super().choose(x,proposal,previous_action)
        info.update(planning_ms=1000*(time.perf_counter()-tic),joint_checked=self.joint_checked,kinematic_blocked=self.kinematic_blocked)
        return action,info
