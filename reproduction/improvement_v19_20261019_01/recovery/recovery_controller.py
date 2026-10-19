"""v19: narrower transition damping, bounded optional search, held settling.

All three switches off reproduce actual v18. Every inherited protection and
clock remains active. New helpers see current observations/controller history.
"""
from dataclasses import dataclass
import numpy as np
from reproduction.improvement_v18_20261019_01.recovery.recovery_controller import (
    RecoveryController as V18, Config as C18,
)
from reproduction.improvement_v17_20261019_01.recovery.recovery_controller import RecoveryController as V17


@dataclass(frozen=True)
class Config(C18):
    transition_window: bool = True
    candidate_budget: bool = True
    terminal_settling: bool = True


class RecoveryController(V18):
    def __init__(self, target, floor_z, initial_state, enabled=True, config=None):
        super().__init__(target, floor_z, initial_state, enabled, config or Config())
        self.transition19_events=[]
        self.budget19_events=[]
        self.settling19_events=[]
        self._settling_pending19=[]

    def pose_action(self,x,goal,grip):
        scoped=(self.enabled and self.cfg.transition_window and self.cfg.handoff_continuity
                and self.mode=='DESCEND' and self.edge_plan is not None and self.cfg.can_guard)
        if not scoped:return super().pose_action(x,goal,grip)
        from .transition import propose
        pulse_before=self.last_pulse
        original=V17.pose_action(self,x,goal,grip)
        aperture_motion=not self.gap_ready(x) or original[6]!=0
        margin=self.joint_margin16()
        if margin<self.cfg.joint_solution_margin_rad:
            candidate=np.zeros(7,np.float32)
            receipt={'kind':'mixed_pose','accepted':False,'work':0,'work_units':0,
                     'reason':'descent_joint_margin_guard','joint_margin_rad':margin,
                     'transition19':{'window_active':self.age<=3,'descent_controls':self.age,'window_controls':3}}
        else:
            candidate,receipt=propose(x,goal,self.goal_rotation,self.motion,self.cfg,
                previous_action=self._previous18,grip=float(original[6]),
                aperture_motion=aperture_motion,descent_controls=self.age)
        # Reuse v18 final-command/pulse/CLOSE audit and rejection state exactly.
        self._handoff_pending18={'receipt':receipt,'candidate':candidate.copy(),
                                 'goal':np.asarray(goal).tolist(),'joint_margin_rad':margin,
                                 'pulse_before':pulse_before}
        if not receipt['accepted']:
            self._handoff_blocked18=True
            self.last_pulse=pulse_before
            self.begin_wait('v19_descent_mixed_or_joint_unconfirmed',x)
            return np.zeros(7,np.float32)
        return candidate

    def propose17(self,x,goal,rotation,*,held,grip,phase,aperture_motion=False):
        if not (self.enabled and self.cfg.terminal_settling and held):
            return super().propose17(x,goal,rotation,held=held,grip=grip,phase=phase,
                                     aperture_motion=aperture_motion)
        from .settling import ServoState,propose
        if 'held' not in self.servo17:self.servo17['held']=ServoState()
        self._proposal_state17=self.servo17['held']
        action,receipt=propose(x,goal,rotation,self.motion,self.cfg,held=held,grip=grip,
            state=self._proposal_state17,phase=(self.attempts,phase),
            previous_action=self.last_submitted17,aperture_motion=aperture_motion)
        if not receipt['accepted']:self._proposal_state17.reset()
        self._settling_pending19.append({'phase':phase,'receipt':receipt,'candidate':action.copy()})
        return action,receipt

    def choose(self,x,proposal,previous_action):
        self._settling_pending19=[]
        action,info=super().choose(x,proposal,previous_action)
        pending=self._handoff_pending18
        if pending is not None and 'transition19' in pending['receipt']:
            event=dict(self.handoff18_events[-1])
            event['event']='windowed_descent_control'
            self.transition19_events.append(event)
            info.update(planning_kind='v19_descent_transition',transition19=pending['receipt']['transition19'])
        for item in self._settling_pending19:
            applied=bool(item['receipt']['accepted'] and self._committed17
                         and np.array_equal(action,item['candidate']))
            # A later parent guard must never commit an unsubmitted proposal.
            # This also covers untriggered C proposals without altering their
            # helper receipt or normal execution arithmetic.
            if self._committed17 and not applied:
                for memory in self.servo17.values():memory.reset()
                self._committed17=False
                self.last_submitted17=np.asarray(action,np.float32).copy()
                info.update(mixed_pose_applied=False,settling19_applied=False,
                            settling19_submission_reason='parent_replaced_proposal')
            if 'settling19' not in item['receipt']:continue
            self.settling19_events.append({'step':self.clock,'event':'held_integral_brake',
                'phase':item['phase'],'applied':applied,'actual_submitted_action':action.tolist(),**item['receipt']})
            info.update(settling19=item['receipt']['settling19'],settling19_applied=applied)
        return action,info

    def carry_action(self,x,action,info):
        if (self.enabled and self.cfg.candidate_budget and self.cfg.short_route_selection
                and self.cfg.route_efficiency and self.cfg.ik_continuation and self.mode=='CARRY'
                and info.get('stable_hold') and self.attempts not in self.carry_checked):
            from .carry_search import CarryPathSearch
            self.carry_checked.add(self.attempts)
            self.carry_search=CarryPathSearch(self,x,self.joints)
            self.carry_reference=self.carry_search.envelope
            self.budget19_events.append({'step':self.clock,'event':'bounded_optional_search_started',
                                        'remaining_steps':self.cfg.horizon_steps-self.clock})
        search=self.carry_search
        result=super().carry_action(x,action,info)
        if self.cfg.candidate_budget and search is not None and search.done:
            self.budget19_events.append({'step':self.clock,'event':'bounded_optional_search_complete',
                                        'chosen':search.chosen is not None,'work':search.work,
                                        'options':search.receipts})
        return result
