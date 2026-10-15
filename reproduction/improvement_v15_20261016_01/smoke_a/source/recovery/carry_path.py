"""Bounded held-object transport certificates from current observations.

The hand collision hulls and the actual can convex hull are checked against the
fixed boxes. The can is represented by its observed rigid transform relative to
the end effector, not by an empty-hand path. This is a rigid-grasp proxy and a
local IK certificate, not full-arm collision checking or a grasp-force model.
There are no simulator, reward, contact, future-state or case-ID inputs.
"""
from dataclasses import dataclass
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v8_20261015_01.recovery.geometry import CAN, BOXES, axes_for, separation
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK
from reproduction.improvement_v11_20261015_01.recovery.path_search import sweep_margin, turn_samples

BOX_MARGIN_M = .001
MAX_TRANSLATION_SAMPLE_M = .08
MAX_GEOMETRY_UNITS_PER_ADVANCE = 4


def _rotation(x):
    return Rotation.from_quat(np.asarray(x)[3:7]).as_matrix()


@dataclass
class HeldEnvelope:
    """Observed can pose and hull in the end-effector coordinate frame."""
    offset: np.ndarray
    relative_rotation: np.ndarray
    vertices: np.ndarray

    @classmethod
    def from_state(cls, x):
        x = np.asarray(x, float)
        rotation = _rotation(x)
        object_rotation = Rotation.from_quat(x[19:23]).as_matrix()
        offset = rotation.T @ (x[16:19]-x[:3])
        relative_rotation = rotation.T @ object_rotation
        vertices = CAN @ relative_rotation.T + offset
        return cls(offset.copy(), relative_rotation.copy(), vertices)

    def world_vertices(self, position, rotation):
        return self.vertices @ np.asarray(rotation).T + np.asarray(position)

    def held_offset(self, rotation):
        """World EEF-minus-can offset after a rigid reorientation."""
        return -np.asarray(rotation) @ self.offset

    def relative_errors(self, x):
        observed = HeldEnvelope.from_state(x)
        return {'position_m': float(np.linalg.norm(observed.offset-self.offset)),
                'angle_rad': float(np.linalg.norm(Rotation.from_matrix(observed.relative_rotation @ self.relative_rotation.T).as_rotvec()))}

    def sweep_margin(self, start, end, rotation):
        vertices = np.r_[self.world_vertices(start, rotation), self.world_vertices(end, rotation)]
        axes = axes_for(vertices)
        return float(min(separation(vertices, center, half, axes) for center, half in BOXES))


def _gap(x):
    return min(.085, abs(float(x[7]-x[8]))+.002)


def _translation(envelope, start, end, rotation, gap):
    hand = float(sweep_margin(np.asarray(start), np.asarray(end), rotation, gap))
    can = envelope.sweep_margin(start, end, rotation)
    return {'hand_margin_m': hand, 'carried_can_margin_m': can,
            'accepted': bool(hand >= BOX_MARGIN_M and can >= BOX_MARGIN_M)}


def translation_certificate(x, goal):
    """Live, fixed-current-rotation segment; re-evaluate before submitting it."""
    x = np.asarray(x, float)
    return _translation(HeldEnvelope.from_state(x), x[:3], goal, _rotation(x), _gap(x))


def _rotation_samples(envelope, start_rotation, end_rotation, gap):
    samples = turn_samples(start_rotation, end_rotation, gap)
    angle = float(np.linalg.norm(Rotation.from_matrix(end_rotation @ start_rotation.T).as_rotvec()))
    intervals = max(1, len(samples)-1)
    can_radius = float(np.linalg.norm(envelope.vertices, axis=1).max())
    can_bound = float(2*can_radius*np.sin(angle/intervals/4))
    return [(rotation, float(hand_bound), can_bound) for rotation, hand_bound in samples]


def _rotation_sample(envelope, position, rotation, gap, hand_bound, can_bound):
    result = _translation(envelope, position, position, rotation, gap)
    result['hand_margin_m'] -= hand_bound
    result['carried_can_margin_m'] -= can_bound
    result.update(hand_arc_bound_m=float(hand_bound), carried_can_arc_bound_m=float(can_bound))
    result['accepted'] = bool(result['hand_margin_m'] >= BOX_MARGIN_M and result['carried_can_margin_m'] >= BOX_MARGIN_M)
    return result


def rotation_certificate(x, end_rotation):
    """Live fixed-position rotation arc, including the rotating carried can."""
    x = np.asarray(x, float)
    envelope = HeldEnvelope.from_state(x)
    samples = [_rotation_sample(envelope, x[:3], rotation, _gap(x), hand_bound, can_bound)
               for rotation, hand_bound, can_bound in _rotation_samples(envelope, _rotation(x), np.asarray(end_rotation), _gap(x))]
    return {'accepted': bool(all(sample['accepted'] for sample in samples)),
            'hand_margin_m': min(sample['hand_margin_m'] for sample in samples),
            'carried_can_margin_m': min(sample['carried_can_margin_m'] for sample in samples),
            'samples': len(samples), 'arc_bounds_applied': True}


def candidates(current_rotation, target_xy):
    """Fixed candidate family; tilt outward makes the wrist less extended."""
    radial = np.asarray(target_xy, float)-np.array([-.5, -.1])
    radial /= np.linalg.norm(radial)
    yaw = float(np.arctan2(current_rotation[1, 0], current_rotation[0, 0]))
    out = [('current', current_rotation.copy())]
    # Check the unchanged orientation first, then a fixed 30deg nominal tilt
    # and bounded alternatives. Check equivalent yaw last to avoid spending
    # most of the remaining episode on unnecessary large-turn candidates.
    # This order was selected using known diagnostics, before new smoke runs.
    for flip in [False, True]:
        for degree in [30., 15., 25., 35., 0.]:
            down = Rotation.from_euler('z', yaw+(np.pi if flip else 0.)).as_matrix() @ np.diag([1., -1., -1.])
            rotation = Rotation.from_rotvec(-np.deg2rad(degree)*np.r_[-radial[1], radial[0], 0.]).as_matrix() @ down
            if any(np.linalg.norm(Rotation.from_matrix(rotation @ old.T).as_rotvec()) < 1e-7 for _, old in out):
                continue
            out.append((f'outward_{int(degree)}' + ('_equivalent' if flip else ''), rotation))
    return out


def _stage(label, kind, start, goal, start_rotation, rotation):
    return {'label': label, 'kind': kind, 'start': np.asarray(start, float).copy(),
            'goal': np.asarray(goal, float).copy(), 'start_rotation': np.asarray(start_rotation).copy(),
            'rotation': np.asarray(rotation).copy()}


class CarryPathSearch:
    """Resumable 11-candidate check; bounded IK and geometry work per call.

    Call advance(16) once per real control step while preserving the original
    hold/loss observation update and grasp command. Planning consumes the same
    400-step budget. A chosen path does not reset clocks, attempts or history.
    Revalidate observed execution: static local IK does not prove the OSC
    controller follows its particular joint branch.
    """
    def __init__(self, controller, x, q):
        self.x = np.asarray(x, float).copy()
        self.q = np.asarray(q, float).copy()
        assert self.x.shape == (23,) and self.q.shape == (7,)
        self.start_rotation = _rotation(x)
        self.envelope = HeldEnvelope.from_state(x)
        self.gap = _gap(x)
        self.floor = float(controller.floor)
        self.target = np.asarray(controller.target, float).copy()
        self.carry_height = self.floor + controller.cfg.carry_clearance_m
        self.placement_height = self.floor + .085
        self.original_rotation = np.asarray(getattr(controller,'goal_rotation',self.start_rotation),float).copy()
        self.original_offset = np.asarray(getattr(controller,'held_offset',self.envelope.held_offset(self.start_rotation)),float).copy()
        self.required_margin = float(controller.cfg.joint_solution_margin_rad)
        self.ik_limit = int(controller.cfg.ik_iterations_per_target)
        assert self.required_margin >= .04 and self.ik_limit <= 48
        self.options = candidates(self.start_rotation, self.target[:2])
        self.index = 0
        self.done = False
        self.chosen = None
        self.receipts = []
        self.work = 0
        self.last_work = 0
        self.last_geometry_work = 0
        self._start_option()

    def _start_option(self):
        name, rotation = self.options[self.index]
        start = self.x[:3].copy()
        raised = start.copy()
        raised[2] = max(raised[2], self.carry_height+self.envelope.held_offset(self.start_rotation)[2])
        carry = np.r_[self.target[:2], self.carry_height]+self.envelope.held_offset(rotation)
        place = np.r_[self.target[:2], self.placement_height]+self.envelope.held_offset(rotation)
        self.stages = [_stage('clearance', 'translate', start, raised, self.start_rotation, self.start_rotation),
                       _stage('reorient', 'rotate', raised, raised, self.start_rotation, rotation),
                       _stage('transport', 'translate', raised, carry, rotation, rotation)]
        self.placement = _stage('placement_validation', 'translate', carry, place, rotation, rotation)
        self.receipt = {'index': self.index, 'candidate': name, 'accepted': False, 'prefilter_ik': [],
                        'path_ik': [], 'geometry': [], 'required_joint_margin_rad': self.required_margin,
                        'required_box_margin_m': BOX_MARGIN_M}
        self.mode = 'prefilter'
        self.prefilter_index = 0
        self.prefilter_goals = [carry, place]
        self.prefilter_rotation = rotation
        if self.index == 0:
            self.prefilter_goals = [np.r_[self.target[:2],height]+self.original_offset for height in [self.carry_height,self.placement_height]]
            self.prefilter_rotation = self.original_rotation
        self.ik = IK(self.q, self.prefilter_goals[0], self.prefilter_rotation, self.ik_limit)
        self.rotation = rotation

    def _path_tasks(self):
        tasks = []
        for stage in self.stages+[self.placement]:
            if stage['kind'] == 'rotate':
                for rotation, hand_bound, can_bound in _rotation_samples(self.envelope, stage['start_rotation'], stage['rotation'], self.gap):
                    tasks.append(('rotation_geometry', stage, rotation, hand_bound, can_bound))
                    tasks.append(('ik', stage, stage['start'].copy(), rotation))
            else:
                tasks.append(('translation_geometry', stage))
                count = max(1, int(np.ceil(np.linalg.norm(stage['goal']-stage['start'])/MAX_TRANSLATION_SAMPLE_M)))
                for target in np.linspace(stage['start'], stage['goal'], count+1)[1:]:
                    tasks.append(('ik', stage, target, stage['rotation']))
        self.tasks = tasks
        self.task_index = 0
        self.path_q = self.q.copy()
        self.ik = None
        self.mode = 'path'

    def _finish(self, reason, accepted=False):
        self.receipt.update(reason=reason, accepted=bool(accepted))
        self.receipts.append(self.receipt)
        if accepted:
            self.done = True
            self.chosen = {'candidate': self.options[self.index][0], 'preserve_current': False, 'stages': self.stages,
                           'placement': self.placement, 'rotation': self.rotation.copy(),
                           'held_offset': self.envelope.held_offset(self.rotation),
                           'held_relative_position': self.envelope.offset.copy(),
                           'held_relative_rotation': self.envelope.relative_rotation.copy(),
                           'minimum_joint_margin_rad': min(r['limit_margin_rad'] for r in self.receipt['path_ik']),
                           'minimum_hand_margin_m': min(r['hand_margin_m'] for r in self.receipt['geometry']),
                           'minimum_carried_can_margin_m': min(r['carried_can_margin_m'] for r in self.receipt['geometry']),
                           'proxy': 'Observed rigid hand-can transform; not a force or full-arm safety certificate.'}
        else:
            self.index += 1
            if self.index >= len(self.options):
                self.done = True
            else:
                self._start_option()

    def advance(self, units=16):
        units = int(units)
        assert 1 <= units <= 16
        start_work = self.work
        geometry_work = 0
        while not self.done and self.work-start_work < units:
            if self.mode == 'prefilter':
                self.ik.advance(1)
                self.work += 1
                if self.ik.done:
                    receipt = self.ik.receipt()
                    self.receipt['prefilter_ik'].append(receipt)
                    if not receipt['success'] or receipt['limit_margin_rad'] < self.required_margin:
                        self._finish('transport_or_placement_endpoint_ik_unconfirmed')
                        break
                    self.prefilter_index += 1
                    if self.index == 0 and self.prefilter_index == len(self.prefilter_goals):
                        # Existing reachable CARRY keeps its original control
                        # path. This early return is deliberately NOT described
                        # as a new hand/can route or placement certificate.
                        self.receipt.update(reason='original_transport_and_place_endpoints_reachable_preserve_original_control', accepted=True)
                        self.receipts.append(self.receipt)
                        self.chosen = {'candidate': 'current', 'preserve_current': True,
                                       'stages': [], 'rotation': self.start_rotation.copy(),
                                       'held_offset': self.envelope.held_offset(self.start_rotation),
                                       'endpoint_ik': self.receipt['prefilter_ik'],
                                       'proxy': 'Exact original transport and place endpoint IK only; preserve existing controller, not a new geometry certificate.'}
                        self.done = True
                        break
                    if self.prefilter_index == len(self.prefilter_goals):
                        self._path_tasks()
                    else:
                        self.ik = IK(self.ik.q, self.prefilter_goals[self.prefilter_index], self.prefilter_rotation, self.ik_limit)
                continue
            task = self.tasks[self.task_index]
            kind, stage = task[:2]
            if kind == 'ik':
                if self.ik is None:
                    self.ik = IK(self.path_q, task[2], task[3], self.ik_limit)
                self.ik.advance(1)
                self.work += 1
                if not self.ik.done:
                    continue
                receipt = self.ik.receipt()
                self.receipt['path_ik'].append({'stage': stage['label'], **receipt})
                if not receipt['success'] or receipt['limit_margin_rad'] < self.required_margin:
                    self._finish('sequential_current_joint_path_ik_unconfirmed')
                    break
                self.path_q = self.ik.q.copy()
                self.ik = None
            else:
                if geometry_work >= MAX_GEOMETRY_UNITS_PER_ADVANCE:
                    break
                if kind == 'translation_geometry':
                    receipt = _translation(self.envelope, stage['start'], stage['goal'], stage['rotation'], self.gap)
                else:
                    receipt = _rotation_sample(self.envelope, stage['start'], task[2], self.gap, task[3], task[4])
                self.work += 1
                geometry_work += 1
                self.receipt['geometry'].append({'stage': stage['label'], 'kind': kind, **receipt})
                if not receipt['accepted']:
                    self._finish('hand_or_carried_can_box_clearance_unconfirmed')
                    break
            self.task_index += 1
            if self.task_index == len(self.tasks):
                self._finish('current_joint_path_hand_and_carried_can_validated', True)
        self.last_work = self.work-start_work
        self.last_geometry_work = geometry_work
        assert self.last_work <= units and geometry_work <= MAX_GEOMETRY_UNITS_PER_ADVANCE
        return self.done
