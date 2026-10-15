"""v12: observe a passive grasp during pose waits, then resume existing transport.

No contact, reward, success, simulator state or future rollout enters this module.
The inherited v11 controller remains byte-identical. Off reproduces its decisions.
"""
from collections import deque
from dataclasses import dataclass
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v11_20261015_01.recovery.recovery_controller import RecoveryController as V11, Config as C11
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5


@dataclass(frozen=True)
class Config(C11):
    wait_hold_history: bool = True
    passive_wait_hold: bool = True
    wait_relative_tolerance_m: float = .004
    wait_center_tolerance_m: float = .030


class RecoveryController(V11):
    def __init__(self, target, floor_z, initial_state, enabled=True, config=None):
        super().__init__(target, floor_z, initial_state, enabled, config or Config())
        self.wait_observations = deque(maxlen=self.cfg.stall_steps + 1)
        self.wait_hold_events = []
        self._previous_action = np.zeros(7, np.float32)

    def begin_wait(self, reason, x):
        self.wait_observations.clear()
        return super().begin_wait(reason, x)

    def passive_evidence(self, x):
        """Require sustained centered follow during an actual upward movement.

        A stationary pair, an object resting on support, one contact impulse, or
        an opening gripper is insufficient. This is an observation-based proxy,
        not a proof of force closure or a general safety certificate.
        """
        c = self.cfg
        samples = list(self.wait_observations)
        if len(samples) < c.stable_frames:
            return False
        recent = samples[-c.stable_frames:]
        relative = x[:3] - x[16:19]
        centered = all(abs(s['local'][0]) < c.wait_center_tolerance_m
                       and abs(s['local'][1]) < min(c.wait_center_tolerance_m, s['gap']/2)
                       and -.015 < s['local'][2] < .070 for s in recent)
        consistent = max(np.linalg.norm(s['relative'] - relative) for s in recent) < c.wait_relative_tolerance_m
        aperture = (all(c.grip_gap_min_m < s['gap'] < c.grip_gap_max_m and s['grip'] >= 0 for s in recent)
                    and max(s['gap'] for s in recent) - min(s['gap'] for s in recent) < c.aperture_tolerance_m)
        # Same start observation must explain both rises; never combine extrema
        # from unrelated moments. Every intervening relative pose must agree.
        follow = any(float(x[18] - s['object'][2]) >= c.verified_lift_m
                     and float(x[2] - s['eef'][2]) >= c.verified_lift_m
                     and all(np.linalg.norm(t['relative'] - relative) < c.wait_relative_tolerance_m
                             for t in samples[i:]) for i, s in enumerate(samples))
        return bool(centered and consistent and aperture and follow
                    and x[18] > self.rest_z + c.verified_lift_m
                    and np.linalg.norm(relative) < c.near_object_m)

    def wait_action(self, x):
        if not self.enabled or not self.cfg.wait_hold_history:
            return super().wait_action(x)
        relative = x[:3] - x[16:19]
        self.history.append({'relative': relative.copy(), 'object': x[16:19].copy(),
                             'distance': float(np.linalg.norm(relative)),
                             'xygoal': float(np.linalg.norm(x[16:18] - self.target[:2]))})
        self.wait_observations.append({'relative': relative.copy(), 'object': x[16:19].copy(),
                                       'eef': x[:3].copy(), 'gap': abs(float(x[7]-x[8])),
                                       'grip': float(self._previous_action[6]),
                                       'local': Rotation.from_quat(x[3:7]).inv().apply(-relative)})
        old_hold = self.observable_hold(x, self._previous_action)
        passive = self.cfg.passive_wait_hold and self.passive_evidence(x)
        holding = old_hold or passive
        if holding:
            before = self.mode
            self.clock += 1
            self.gaps.append(abs(float(x[7]-x[8])))
            self.stable = True
            self.ever_stable = True
            self.lost_frames = 0
            self.mesh_search = self.joint_search = self.edge_search = None
            self.edge_plan = None
            self.goal_rotation = Rotation.from_quat(x[3:7]).as_matrix()
            V5.enter(self, 'LIFT', 'wait_follow_confirmed', x)
            self.verified_regrasps += 1
            self.wait_hold_events.append({'step': self.clock, 'from': before,
                                         'evidence': 'passive_follow' if passive else 'existing_hold',
                                         'observations': len(self.wait_observations)})
            action = V5.pose_action(self, x, self.waypoint, 1.)
            return action, {'mode_before': before, 'mode': 'LIFT', 'next_mode': 'LIFT',
                            'stable_hold': True, 'intervened': True, 'attempts': self.attempts,
                            'gap_m': abs(float(x[7]-x[8])), 'wait_hold_transition': True}
        if self.stable:
            self.lost_frames += 1
            if self.lost_frames >= self.cfg.stable_frames:
                self.stable = False
                self.wait_hold_events.append({'step': self.clock+1, 'event': 'wait_hold_revoked'})
        return super().wait_action(x)

    def choose(self, x, proposal, previous_action):
        self._previous_action = np.asarray(previous_action, np.float32)
        return super().choose(x, proposal, previous_action)
