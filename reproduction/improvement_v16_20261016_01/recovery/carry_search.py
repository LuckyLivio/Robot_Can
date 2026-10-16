"""Bounded sequential IK for held transport, without changing safety limits.

The old direct endpoint IK could stop at a local solution before following the
actual Cartesian route. Each candidate here starts from the observed joints,
then seeds every small waypoint from the preceding accepted solution. Failure
means unknown, never a certificate that the task is unreachable.

Only current observations, controller targets and fixed geometry are inputs.
No simulator, contact, reward, future trajectory or diagnostic case ID is used.
"""
import math
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK
from reproduction.improvement_v15_20261016_01.recovery.carry_path import (
    HeldEnvelope, BOX_MARGIN_M, _rotation, _gap, _stage, _translation,
    _rotation_samples, _rotation_sample,
    translation_certificate, rotation_certificate,
)

MAX_WORK = 384
MAX_ADVANCE_CALLS = 24
MAX_WORK_PER_ADVANCE = 16
MAX_GEOMETRY_PER_ADVANCE = 4
WAYPOINT_M = .04
REGION_INSET_M = .035
PLACE_HEIGHT_M = .095


class CarryPathSearch:
    """One resumable, finite search; completed instances never restart.

    Public API mirrors v15: advance(16), done, chosen, receipts, work,
    last_work. status is planning/validated/unknown. chosen is returned only
    after every stage and the exact placement goal pass geometry and IK.
    A caller must cache this object/outcome per attempt, preserve its hold and
    time bookkeeping, and live-check each executed segment. Cartesian IK is
    only a local reachability proxy; OSC may follow a different joint branch.
    """
    def __init__(self, controller, x, q):
        self.x = np.asarray(x, float).copy()
        self.q = np.asarray(q, float).copy()
        assert self.x.shape == (23,) and self.q.shape == (7,)
        self.start_rotation = _rotation(self.x)
        self.envelope = HeldEnvelope.from_state(self.x)
        self.gap = _gap(self.x)
        self.floor = float(controller.floor)
        self.target = np.asarray(controller.target, float).copy()
        self.carry_height = self.floor+float(controller.cfg.carry_clearance_m)
        self.original_rotation = np.asarray(controller.goal_rotation, float).copy()
        self.original_offset = np.asarray(controller.held_offset, float).copy()
        self.required_margin = float(controller.cfg.joint_solution_margin_rad)
        self.ik_limit = int(controller.cfg.ik_iterations_per_target)
        assert self.required_margin >= .04 and 1 <= self.ik_limit <= 48
        # The 35mm inset stays strictly inside both original XY predicates
        # (<45mm CARRY, <50mm PLACE). 95mm is strictly below PLACE's 100mm
        # height predicate. These are commanded goals, not new tolerances.
        radial = np.array([-.5, -.1])-self.target[:2]
        radial /= max(float(np.linalg.norm(radial)), 1e-12)
        inset = self.target[:2]+REGION_INSET_M*radial
        # Construct directly rather than relying on v15's duplicate-removal
        # dictionary: the observed pose can already equal a named candidate.
        outward = -radial
        yaw = float(np.arctan2(self.start_rotation[1, 0], self.start_rotation[0, 0]))
        def tilted(degree, equivalent=False):
            down = (Rotation.from_euler('z', yaw+(np.pi if equivalent else 0.)).as_matrix()
                    @ np.diag([1., -1., -1.]))
            return Rotation.from_rotvec(-np.deg2rad(degree)*np.r_[-outward[1], outward[0], 0.]).as_matrix() @ down
        self.options = [
            ('current_exact', self.original_rotation.copy(), self.target[:2].copy(), self.floor+.085),
            ('outward_15_inset', tilted(15), inset.copy(), self.floor+PLACE_HEIGHT_M),
            ('outward_15_equivalent_inset', tilted(15, True), inset.copy(), self.floor+PLACE_HEIGHT_M),
            ('outward_30_center', tilted(30), self.target[:2].copy(), self.floor+.085),
        ]
        self.index = 0
        self.done = False
        self.status = 'planning'
        self.reason = None
        self.chosen = None
        self.receipts = []
        self.work = 0
        self.calls = 0
        self.last_work = 0
        self.last_geometry_work = 0
        self._start_option()

    def _start_option(self):
        name, rotation, xy, place_height = self.options[self.index]
        self.rotation = rotation.copy()
        self.offset = (self.original_offset.copy() if self.index == 0
                       else self.envelope.held_offset(rotation))
        start = self.x[:3].copy()
        raised = start.copy()
        raised[2] = max(raised[2], self.carry_height+self.envelope.held_offset(self.start_rotation)[2])
        carry = np.r_[xy, self.carry_height]+self.offset
        place = np.r_[xy, place_height]+self.offset
        self.stages = [
            _stage('clearance', 'translate', start, raised, self.start_rotation, self.start_rotation),
            _stage('reorient', 'rotate', raised, raised, self.start_rotation, rotation),
            _stage('transport', 'translate', raised, carry, rotation, rotation),
        ]
        self.placement = _stage('placement_validation', 'translate', carry, place, rotation, rotation)
        self.receipt = {'candidate': name, 'accepted': False, 'status': 'planning',
                        'carry_goal': carry.tolist(), 'place_goal': place.tolist(),
                        'path_ik': [], 'geometry': [], 'validated_prefix': [],
                        'required_joint_margin_rad': self.required_margin,
                        'required_box_margin_m': BOX_MARGIN_M,
                        'max_ik_iterations_per_target': self.ik_limit}
        # A cheap final descent check rejects an obviously intersecting route
        # before spending IK work. It is exactly the later executed segment.
        self.tasks = [('placement_precheck', self.placement)]
        for stage in self.stages+[self.placement]:
            if stage['kind'] == 'rotate':
                for sample_rotation, hand_bound, can_bound in _rotation_samples(
                        self.envelope, stage['start_rotation'], stage['rotation'], self.gap):
                    self.tasks.append(('rotation_geometry', stage, sample_rotation, hand_bound, can_bound))
                    self.tasks.append(('ik', stage, stage['start'].copy(), sample_rotation))
            else:
                if stage is not self.placement:
                    self.tasks.append(('translation_geometry', stage))
                count = max(1, math.ceil(float(np.linalg.norm(stage['goal']-stage['start']))/WAYPOINT_M))
                for point in np.linspace(stage['start'], stage['goal'], count+1)[1:]:
                    self.tasks.append(('ik', stage, point.copy(), stage['rotation']))
        self.task_index = 0
        self.path_q = self.q.copy()
        self.ik = None

    def _finish_option(self, reason, accepted=False):
        self.receipt.update(reason=reason, accepted=bool(accepted),
                            status='validated' if accepted else 'unknown')
        self.receipts.append(self.receipt)
        if accepted:
            self.done = True
            self.status = 'validated'
            self.reason = reason
            self.chosen = {
                'candidate': self.options[self.index][0], 'preserve_current': False,
                'stages': self.stages, 'placement': self.placement,
                'carry_goal': self.stages[-1]['goal'].copy(), 'place_goal': self.placement['goal'].copy(),
                'rotation': self.rotation.copy(), 'held_offset': self.offset.copy(),
                'held_relative_position': self.envelope.offset.copy(),
                'held_relative_rotation': self.envelope.relative_rotation.copy(),
                'minimum_joint_margin_rad': min(r['limit_margin_rad'] for r in self.receipt['path_ik']),
                'minimum_hand_margin_m': min(r['hand_margin_m'] for r in self.receipt['geometry']),
                'minimum_carried_can_margin_m': min(r['carried_can_margin_m'] for r in self.receipt['geometry']),
                'proxy': 'Sequential local IK and observed rigid hand-can hull; not closed-loop or full-arm proof.',
            }
            return
        self.index += 1
        if self.index >= len(self.options):
            self.done = True
            self.status = 'unknown'
            self.reason = 'finite_candidate_family_unconfirmed'
        else:
            self._start_option()

    def _stop_budget(self):
        self.receipt.update(accepted=False, status='unknown', reason='bounded_search_budget_exhausted')
        self.receipts.append(self.receipt)
        self.done = True
        self.status = 'unknown'
        self.reason = 'bounded_search_budget_exhausted'

    def advance(self, units=16):
        units = int(units)
        assert 1 <= units <= MAX_WORK_PER_ADVANCE
        self.last_work = 0
        self.last_geometry_work = 0
        if self.done:
            return True
        if self.calls >= MAX_ADVANCE_CALLS or self.work >= MAX_WORK:
            self._stop_budget()
            return True
        self.calls += 1
        start_work = self.work
        while not self.done and self.work-start_work < units and self.work < MAX_WORK:
            task = self.tasks[self.task_index]
            kind, stage = task[:2]
            if kind == 'ik':
                if self.ik is None:
                    self.ik = IK(self.path_q, task[2], task[3], self.ik_limit)
                self.ik.advance(1)
                self.work += 1
                if not self.ik.done:
                    continue
                receipt = {'stage': stage['label'], 'point': task[2].tolist(), **self.ik.receipt()}
                self.receipt['path_ik'].append(receipt)
                if not receipt['success'] or receipt['limit_margin_rad'] < self.required_margin:
                    reason = ('local_ik_unconverged' if not receipt['success']
                              else 'local_joint_margin_unconfirmed')
                    self._finish_option(reason)
                    continue
                self.path_q = self.ik.q.copy()
                self.receipt['validated_prefix'].append({'stage': stage['label'], 'point': task[2].tolist(),
                                                         'q': self.path_q.tolist()})
                self.ik = None
            else:
                if self.last_geometry_work >= MAX_GEOMETRY_PER_ADVANCE:
                    break
                if kind in ['placement_precheck', 'translation_geometry']:
                    receipt = _translation(self.envelope, stage['start'], stage['goal'], stage['rotation'], self.gap)
                else:
                    receipt = _rotation_sample(self.envelope, stage['start'], task[2], self.gap, task[3], task[4])
                self.work += 1
                self.last_geometry_work += 1
                self.receipt['geometry'].append({'stage': stage['label'], 'kind': kind, **receipt})
                if not receipt['accepted']:
                    self._finish_option('hand_or_carried_can_clearance_unconfirmed')
                    continue
            self.task_index += 1
            if self.task_index == len(self.tasks):
                self._finish_option('sequential_ik_and_all_stages_geometry_validated', True)
        self.last_work = self.work-start_work
        if not self.done and (self.calls >= MAX_ADVANCE_CALLS or self.work >= MAX_WORK):
            self._stop_budget()
        assert self.last_work <= units and self.last_geometry_work <= MAX_GEOMETRY_PER_ADVANCE
        return self.done
