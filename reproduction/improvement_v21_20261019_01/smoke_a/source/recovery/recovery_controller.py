"""v21 isolates terminal PLACE braking and risk-direction handoff feedback.

The real v19 controller owns clocks, phase transitions, FIFO semantics and all
guards. Both new switches off reproduce actual v19. No training or oracle.
"""
from dataclasses import dataclass
import numpy as np
from reproduction.improvement_v19_20261019_01.recovery.recovery_controller import (
    RecoveryController as V19, Config as C19,
)
from reproduction.improvement_v17_20261019_01.recovery.recovery_controller import RecoveryController as V17


@dataclass(frozen=True)
class Config(C19):
    recenter_transition: bool = True
    place_braking: bool = True


class RecoveryController(V19):
    def __init__(self,target,floor_z,initial_state,enabled=True,config=None):
        super().__init__(target,floor_z,initial_state,enabled,config or Config())
        self.handoff21_events=[]
        self.place21_events=[]
        self._handoff_pending21=False
        self._place_pending21=[]

    def pose_action(self,x,goal,grip):
        scoped=(self.enabled and self.cfg.recenter_transition and self.cfg.transition_window
                and self.cfg.handoff_continuity and self.mode=='DESCEND'
                and self.edge_plan is not None and self.cfg.can_guard)
        if not scoped:return super().pose_action(x,goal,grip)
        from .recenter_transition import propose
        pulse_before=self.last_pulse
        original=V17.pose_action(self,x,goal,grip)
        aperture_motion=not self.gap_ready(x) or original[6]!=0
        margin=self.joint_margin16()
        if margin<self.cfg.joint_solution_margin_rad:
            candidate=np.zeros(7,np.float32)
            receipt={'kind':'mixed_pose','accepted':False,'work':0,'work_units':0,
                     'reason':'descent_joint_margin_guard','joint_margin_rad':margin,
                     'handoff21':{'guard_preempted':True,'descent_controls':self.age}}
        else:
            candidate,receipt=propose(x,goal,self.goal_rotation,self.motion,self.cfg,
                previous_action=self._previous18,grip=float(original[6]),
                aperture_motion=aperture_motion,descent_controls=self.age,
                descent_axis=self.edge_plan['rotation'][:,2])
        self._handoff_pending21=True
        self._handoff_pending18={'receipt':receipt,'candidate':candidate.copy(),
            'goal':np.asarray(goal).tolist(),'joint_margin_rad':margin,'pulse_before':pulse_before}
        if not receipt['accepted']:
            self._handoff_blocked18=True
            self.last_pulse=pulse_before
            self.begin_wait('v21_descent_mixed_or_joint_unconfirmed',x)
            return np.zeros(7,np.float32)
        return candidate

    def propose17(self,x,goal,rotation,*,held,grip,phase,aperture_motion=False):
        # A last PLACE-labelled frame can already be in RELEASE. It and all
        # CARRY subsegments deliberately use the actual v19 implementation.
        scoped=(self.enabled and self.cfg.place_braking and self.cfg.terminal_settling
                and held and self.mode=='PLACE' and phase=='PLACE')
        if not scoped:
            return super().propose17(x,goal,rotation,held=held,grip=grip,phase=phase,
                                    aperture_motion=aperture_motion)
        from reproduction.improvement_v20_20261019_01.recovery.delay_settling import ServoState,propose
        if 'held' not in self.servo17:self.servo17['held']=ServoState()
        self._proposal_state17=self.servo17['held']
        action,receipt=propose(x,goal,rotation,self.motion,self.cfg,held=held,grip=grip,
            state=self._proposal_state17,phase=(self.attempts,phase),
            previous_action=self.last_submitted17,aperture_motion=aperture_motion)
        if not receipt['accepted']:self._proposal_state17.reset()
        receipt['place21']={'actual_mode_at_proposal':self.mode,'controller_mode':self.mode,
                            'phase':phase,'held':bool(held),
                            'terminal_place_only':True,'integral_rule_triggered':'braking20' in receipt}
        pending={'phase':phase,'receipt':receipt,'candidate':action.copy()}
        # Preserve parent final-submission protection for every proposal,
        # including those without an integral-pause trigger.
        self._settling_pending19.append(pending)
        self._place_pending21.append(pending)
        return action,receipt

    def choose(self,x,proposal,previous_action):
        self._handoff_pending21=False
        self._place_pending21=[]
        action,info=super().choose(x,proposal,previous_action)
        if self._handoff_pending21:
            event=dict(self.handoff18_events[-1]);event['event']='recenter_directional_handoff'
            self.handoff21_events.append(event)
            info.update(planning_kind='v21_recenter_transition',
                        handoff21=self._handoff_pending18['receipt'].get('handoff21'))
        for pending in self._place_pending21:
            receipt=pending['receipt']
            applied=bool(receipt['accepted'] and self._committed17
                         and np.array_equal(action,pending['candidate']))
            self.place21_events.append({'step':self.clock,'event':'terminal_place_feedback',
                'phase':pending['phase'],'applied':applied,
                'actual_submitted_action':action.tolist(),**receipt})
            info.update(place21=receipt['place21'],place21_applied=applied)
        return action,info
