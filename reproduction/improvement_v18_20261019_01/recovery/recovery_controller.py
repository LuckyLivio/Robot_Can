"""v18: guarded approach/descent continuity and bounded short-route selection.

Both new switches disabled must reproduce the actual v17 controller. Only
current observations, observed joints and controller-owned history are inputs.
All inherited 400-step, FIFO, aperture, pose, grasp and timeout rules remain.
"""
from dataclasses import dataclass
import numpy as np
from reproduction.improvement_v17_20261019_01.recovery.recovery_controller import (
    RecoveryController as V17, Config as C17,
)


@dataclass(frozen=True)
class Config(C17):
    handoff_continuity: bool = True
    short_route_selection: bool = True


class RecoveryController(V17):
    def __init__(self, target, floor_z, initial_state, enabled=True, config=None):
        super().__init__(target, floor_z, initial_state, enabled, config or Config())
        self.handoff18_events=[]
        self.route18_events=[]
        self._previous18=None
        self._handoff_pending18=None
        self._handoff_blocked18=False

    def enter(self,mode,reason,x):
        # V5 evaluates its CLOSE predicate after calling pose_action. A new
        # guard must not be undone by that same tick's position-only predicate.
        if mode=='CLOSE' and getattr(self,'_handoff_blocked18',False):
            self.handoff18_events.append({'step':self.clock,'event':'rejected_descent_cannot_close',
                                          'reason':reason})
            return
        return super().enter(mode,reason,x)

    def pose_action(self,x,goal,grip):
        scoped=(self.enabled and self.cfg.handoff_continuity and self.mode=='DESCEND'
                and self.edge_plan is not None and self.cfg.can_guard)
        last_pulse=self.last_pulse
        original=super().pose_action(x,goal,grip)
        if not scoped:return original
        from .handoff import propose
        # Parent pose_action retains the original gap pulse decision. Restore
        # its timestamp if the final command cannot actually carry that pulse.
        aperture_motion=not self.gap_ready(x) or original[6]!=0
        joint_margin=self.joint_margin16()
        if joint_margin<self.cfg.joint_solution_margin_rad:
            candidate=np.zeros(7,np.float32)
            receipt={'kind':'mixed_pose','accepted':False,'work':0,'work_units':0,
                     'reason':'descent_joint_margin_guard','joint_margin_rad':joint_margin}
        else:
            candidate,receipt=propose(x,goal,self.goal_rotation,self.motion,self.cfg,
                                      previous_action=self._previous18,grip=float(original[6]),
                                      aperture_motion=aperture_motion)
        self._handoff_pending18={'receipt':receipt,'candidate':candidate.copy(),
                                 'goal':np.asarray(goal).tolist(),'joint_margin_rad':joint_margin,
                                 'pulse_before':last_pulse}
        if not receipt['accepted']:
            self._handoff_blocked18=True
            self.last_pulse=last_pulse
            self.begin_wait('v18_descent_mixed_or_joint_unconfirmed',x)
            return np.zeros(7,np.float32)
        return candidate

    def choose(self,x,proposal,previous_action):
        self._previous18=None if self.last_submitted17 is None else self.last_submitted17.copy()
        self._handoff_pending18=None
        self._handoff_blocked18=False
        action,info=super().choose(x,proposal,previous_action)
        pending=self._handoff_pending18
        if pending is not None:
            receipt=pending['receipt']
            applied=bool(receipt['accepted'] and np.array_equal(action,pending['candidate']))
            if (not applied and pending['candidate'][6]!=0 and action[6]==0
                    and self.last_pulse==self.clock):
                self.last_pulse=pending['pulse_before']
            self.handoff18_events.append({'step':self.clock,'event':'descent_handoff_control',
                                          'goal':pending['goal'],'joint_margin_rad':pending['joint_margin_rad'],
                                          'applied':applied,'actual_submitted_action':action.tolist(),**receipt})
            info.update(mixed_pose=receipt,mixed_pose_applied=applied,
                        planning_kind='v18_descent_handoff',planning_work_units=receipt['work'],
                        handoff18_applied=applied,
                        mixed_pose_submission_reason=('certified_descent_submitted' if applied else
                            ('parent_replaced_proposal' if receipt['accepted'] else 'descent_guard_rejected')))
            if self._handoff_blocked18:info.update(mode='DESCENT_GUARD',next_mode=self.mode)
        return action,info

    def carry_action(self,x,action,info):
        if (self.enabled and self.cfg.short_route_selection and self.cfg.route_efficiency
                and self.cfg.ik_continuation and self.mode=='CARRY'
                and info.get('stable_hold') and self.attempts not in self.carry_checked):
            from .carry_search import CarryPathSearch
            self.carry_checked.add(self.attempts)
            self.carry_search=CarryPathSearch(self,x,self.joints)
            self.carry_reference=self.carry_search.envelope
            self.route18_events.append({'step':self.clock,'event':'short_route_search_started',
                                        'remaining_steps':self.cfg.horizon_steps-self.clock})
        search=self.carry_search
        result=super().carry_action(x,action,info)
        if self.cfg.short_route_selection and search is not None and search.done:
            self.route18_events.append({'step':self.clock,'event':'short_route_search_complete',
                                        'chosen':search.chosen is not None,'work':search.work,
                                        'options':search.receipts})
        return result
