"""v17 finite held-route search: exact local reuse and a checked short route.

No simulator, future state, reward, case identity, or cross-search cache is used.
Unknown local IK results remain unknown. Schedule estimates are operational
heuristics, never a proof of physical reachability or completion.
"""
import copy
import hashlib
import math
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK
from reproduction.improvement_v9_20261015_01.recovery.geometry import LOCAL, CENTERS, HALVES
from reproduction.improvement_v15_20261016_01.recovery.carry_path import (
    BOX_MARGIN_M, _stage, _translation, _rotation_samples, _rotation_sample,
)
from reproduction.improvement_v16_20261016_01.recovery.carry_search import (
    CarryPathSearch as V16Search, MAX_WORK, MAX_ADVANCE_CALLS,
    MAX_WORK_PER_ADVANCE, MAX_GEOMETRY_PER_ADVANCE, WAYPOINT_M,
)
from reproduction.improvement_v16_20261016_01.recovery.pose_servo import _hand_box_translation_envelope


def _hash_arrays(prefix, *values):
    digest = hashlib.sha256(prefix.encode('ascii'))
    for value in values:
        array = np.ascontiguousarray(value, dtype='<f8')
        digest.update(str(array.shape).encode('ascii'))
        digest.update(array.tobytes())
    return digest.hexdigest()


class CarryPathSearch(V16Search):
    """Compatible with v16, with four candidates and unchanged hard limits.

    All chosen routes use preserve_current=False so reference/live guards stay
    active. The first route directly carries to the *original* goal and uses
    one five-frame arrival confirmation. Its whole translation x rotation
    product is checked, not merely its endpoints or two independent motions.

    Cache entries are private to one immutable observation/geometry snapshot.
    Exact target, seed joints, orientation, gap and bounds are part of each key.
    A cache hit costs one work unit; it does not execute IK again or convert an
    unknown into an accepted result. Caller clocks and grasp checks continue.
    """
    def __init__(self, controller, x, q):
        self._controller = controller
        self._cfg = controller.cfg
        self._ordered = False
        self._context_hash = None
        self._ik_cache = {}
        self._geometry_cache = {}
        self.cache_stats = {'ik_hits': 0, 'ik_misses': 0, 'geometry_hits': 0,
                            'geometry_misses': 0, 'unknown_ik_hits': 0,
                            'ik_work_avoided': 0}
        self.schedule_rejections = 0
        super().__init__(controller, x, q)
        for value in [self.x, self.q, self.target, self.start_rotation, self.original_rotation,
                      self.original_offset, self.envelope.offset, self.envelope.relative_rotation,
                      self.envelope.vertices]:
            value.setflags(write=False)

    def _remaining(self):
        return max(0, int(self._cfg.horizon_steps)-int(self._controller.clock))

    def _context(self):
        if self._context_hash is None:
            geometry = [CENTERS, HALVES]
            for _, vertices, normals, edges in LOCAL:
                geometry.extend([vertices, normals, edges])
            self._context_hash = _hash_arrays(
                'v17-held-search-exact-cache-1', self.x, self.q, self.target,
                self.original_rotation, self.original_offset, self.envelope.offset,
                self.envelope.relative_rotation, self.envelope.vertices,
                [self.floor, self.carry_height, self.gap, self.required_margin,
                 self.ik_limit, BOX_MARGIN_M, WAYPOINT_M], *geometry)
        return self._context_hash

    def _key(self, kind, *values):
        return _hash_arrays(self._context()+kind, *values)

    def _route(self, option):
        name, rotation, xy, place_height = option
        offset = self.original_offset.copy() if name == 'current_exact' else self.envelope.held_offset(rotation)
        carry = np.r_[xy, self.carry_height]+offset
        place = np.r_[xy, place_height]+offset
        start = self.x[:3].copy()
        short = name == 'current_exact'
        if short:
            stages = [_stage('direct_transport', 'translate', start, carry, self.start_rotation, rotation)]
        else:
            raised = start.copy()
            raised[2] = max(raised[2], self.carry_height+self.envelope.held_offset(self.start_rotation)[2])
            stages = [_stage('clearance', 'translate', start, raised, self.start_rotation, self.start_rotation),
                      _stage('reorient', 'rotate', raised, raised, self.start_rotation, rotation),
                      _stage('transport', 'translate', raised, carry, rotation, rotation)]
        placement = _stage('placement_validation', 'translate', carry, place, rotation, rotation)
        return {'name': name, 'rotation': rotation.copy(), 'offset': offset, 'short': short,
                'stages': stages, 'placement': placement}

    def _schedule(self, route):
        delay = int(self._cfg.delay)
        settle = delay+3
        parts = []
        # Same 10mm/control-step nominal transport rate used by v5's budget
        # heuristic. The angular rate is explicitly heuristic, not measured
        # from a future rollout or fitted to this case.
        nominal_translation = min(.010, float(self._cfg.max_delta_m))
        nominal_rotation = float(self._cfg.max_rotation_rad)/(delay+2)
        for stage in route['stages']:
            distance = float(np.linalg.norm(stage['goal']-stage['start']))
            angle = float(np.linalg.norm(Rotation.from_matrix(stage['rotation'] @ stage['start_rotation'].T).as_rotvec()))
            command = max(math.ceil(distance/self._cfg.max_delta_m), math.ceil(angle/self._cfg.max_rotation_rad))
            estimate = max(math.ceil(distance/nominal_translation), math.ceil(angle/nominal_rotation))
            parts.append({'stage': stage['label'], 'distance_m': distance, 'angle_rad': angle,
                          'minimum_command_steps': command+delay+settle,
                          'estimated_steps': estimate+delay+settle})
        placement = route['placement']
        distance = float(np.linalg.norm(placement['goal']-placement['start']))
        # Original PLACE requires age > D2+5. Original RELEASE duration stays
        # 14+D2; do not budget using an observed earlier success termination.
        place_minimum = max(delay+6, math.ceil(distance/self._cfg.max_delta_m)+delay)
        place_estimate = max(delay+6, math.ceil(distance/nominal_translation)+delay)
        release = 14+delay
        minimum = sum(p['minimum_command_steps'] for p in parts)+place_minimum+release
        estimate = sum(p['estimated_steps'] for p in parts)+place_estimate+release
        remaining = self._remaining()
        return {'minimum_command_schedule': minimum, 'estimated_steps': estimate,
                'remaining_steps_observed': remaining, 'nominal_estimate_fits': estimate <= remaining,
                'minimum_command_schedule_fits': minimum <= remaining,
                'stage_schedules': parts, 'placement_minimum_steps': place_minimum,
                'placement_estimated_steps': place_estimate, 'release_reserved_steps': release,
                'planning_steps_already_spent': self.calls,
                'interpretation': 'Nominal commanded-motion and phase-wait budget; not a physical lower bound or guarantee.'}

    def _start_option(self):
        if not self._ordered:
            self.options.sort(key=lambda option: (
                not self._schedule(self._route(option))['minimum_command_schedule_fits'],
                not self._schedule(self._route(option))['nominal_estimate_fits'],
                option[0] != 'current_exact', self._schedule(self._route(option))['estimated_steps']))
            self._ordered = True
        route = self._route(self.options[self.index])
        self.rotation, self.offset = route['rotation'], route['offset']
        self.stages, self.placement = route['stages'], route['placement']
        self.short_route = route['short']
        self.schedule = self._schedule(route)
        self.receipt = {'candidate': route['name'], 'accepted': False, 'status': 'planning',
                        'short_original_route': self.short_route,
                        'carry_goal': self.stages[-1]['goal'].tolist(), 'place_goal': self.placement['goal'].tolist(),
                        'path_ik': [], 'geometry': [], 'validated_prefix': [],
                        'required_joint_margin_rad': self.required_margin,
                        'required_box_margin_m': BOX_MARGIN_M, 'max_ik_iterations_per_target': self.ik_limit,
                        'schedule_at_start': self.schedule, 'cache_context_sha256': self._context()}
        carry_object = self.stages[-1]['goal']+self.rotation @ self.envelope.offset
        place_object = self.placement['goal']+self.rotation @ self.envelope.offset
        self.receipt['predicted_rigid_object_goals'] = {
            'carry': carry_object.tolist(), 'place': place_object.tolist(),
            'world_offset_difference_m': float(np.linalg.norm(self.offset-self.envelope.held_offset(self.rotation))),
            'accepted_original_task_region': bool(
                np.linalg.norm(carry_object[:2]-self.target[:2]) < .045
                and np.linalg.norm(place_object[:2]-self.target[:2]) < .05
                and carry_object[2] >= self.carry_height-.016
                and place_object[2] < self.floor+.10)}
        self.tasks = [('schedule',)]
        self.tasks.append(('placement_precheck', self.placement))
        for stage in self.stages+[self.placement]:
            angle = float(np.linalg.norm(Rotation.from_matrix(stage['rotation'] @ stage['start_rotation'].T).as_rotvec()))
            mixed = stage['label'] == 'direct_transport'
            if stage['kind'] == 'rotate' or mixed:
                samples = _rotation_samples(self.envelope, stage['start_rotation'], stage['rotation'], self.gap)
                for rotation, hand_bound, can_bound in samples:
                    self.tasks.append(('mixed_geometry' if mixed else 'rotation_geometry', stage, rotation, hand_bound, can_bound))
                    if not mixed:
                        self.tasks.append(('ik', stage, stage['start'].copy(), rotation))
            elif stage is not self.placement:
                self.tasks.append(('translation_geometry', stage))
            if stage['kind'] != 'rotate':
                count = max(1, math.ceil(float(np.linalg.norm(stage['goal']-stage['start']))/WAYPOINT_M),
                            math.ceil(angle/.08) if mixed else 1)
                rv = Rotation.from_matrix(stage['rotation'] @ stage['start_rotation'].T).as_rotvec()
                for i in range(1, count+1):
                    fraction = i/count
                    point = stage['start']+(stage['goal']-stage['start'])*fraction
                    rotation = Rotation.from_rotvec(rv*fraction).as_matrix() @ stage['start_rotation'] if mixed else stage['rotation']
                    self.tasks.append(('ik', stage, point.copy(), rotation))
        self.task_index = 0
        self.path_q = self.q.copy()
        self.ik = None
        self._ik_work = 0

    def _finish_option(self, reason, accepted=False):
        self.receipt['schedule_at_finish'] = self._schedule(self._route(self.options[self.index]))
        self.receipt['cache_totals_at_finish'] = dict(self.cache_stats)
        if accepted and not self.receipt['schedule_at_finish']['minimum_command_schedule_fits']:
            accepted = False
            reason = 'remaining_command_schedule_unconfirmed'
            self.schedule_rejections += 1
        short, schedule = self.short_route, self.receipt['schedule_at_finish']
        super()._finish_option(reason, accepted)
        if accepted:
            self.chosen.update(short_original_route=short, preserve_current=False,
                               schedule=schedule, estimated_steps=schedule['estimated_steps'],
                               minimum_command_schedule=schedule['minimum_command_schedule'],
                               cache_totals=dict(self.cache_stats),
                               proxy='Full short mixed envelope or staged path plus sequential local IK; live tracking and grasp guards remain mandatory.')

    def _geometry(self, task):
        kind, stage = task[:2]
        if kind in ['placement_precheck', 'translation_geometry']:
            values = [stage['start'], stage['goal'], stage['rotation'], [self.gap]]
            key = self._key('translation_geometry', *values)
        else:
            values = [stage['start'], stage['goal'], task[2], [self.gap, task[3], task[4]]]
            key = self._key(kind, *values)
        if key in self._geometry_cache:
            self.cache_stats['geometry_hits'] += 1
            return {**copy.deepcopy(self._geometry_cache[key]), 'cache_hit': True, 'cache_key': key}
        self.cache_stats['geometry_misses'] += 1
        if kind in ['placement_precheck', 'translation_geometry']:
            result = _translation(self.envelope, stage['start'], stage['goal'], stage['rotation'], self.gap)
        elif kind == 'rotation_geometry':
            result = _rotation_sample(self.envelope, stage['start'], task[2], self.gap, task[3], task[4])
        else:
            # The continuous aperture envelope closes the gap between testing
            # only two aperture endpoints with potentially different SAT axes.
            result = {'hand_margin_m': _hand_box_translation_envelope(stage['start'], stage['goal'], task[2], self.gap)-task[3]-1e-8,
                      'carried_can_margin_m': self.envelope.sweep_margin(stage['start'], stage['goal'], task[2])-task[4]-1e-8}
            result.update(hand_arc_bound_m=task[3], carried_can_arc_bound_m=task[4],
                          whole_translation_times_rotation_envelope=True)
            result['accepted'] = bool(result['hand_margin_m'] >= BOX_MARGIN_M and result['carried_can_margin_m'] >= BOX_MARGIN_M)
        self._geometry_cache[key] = copy.deepcopy(result)
        return {**result, 'cache_hit': False, 'cache_key': key}

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
            kind = task[0]
            if kind == 'schedule':
                self.work += 1
                current = self._schedule(self._route(self.options[self.index]))
                if not self.receipt['predicted_rigid_object_goals']['accepted_original_task_region']:
                    self._finish_option('rigid_object_goal_acceptance_unconfirmed')
                    continue
                if not current['minimum_command_schedule_fits']:
                    self.schedule_rejections += 1
                    self._finish_option('remaining_command_schedule_unconfirmed')
                    continue
            elif kind == 'ik':
                stage = task[1]
                key = self._key('ik', self.path_q, task[2], task[3], [self.ik_limit, self.required_margin])
                if self.ik is None and key in self._ik_cache:
                    cached = self._ik_cache[key]
                    raw = copy.deepcopy(cached['receipt'])
                    self.cache_stats['ik_hits'] += 1
                    self.cache_stats['ik_work_avoided'] += max(0, cached['work']-1)
                    if not raw['success'] or raw['limit_margin_rad'] < self.required_margin:
                        self.cache_stats['unknown_ik_hits'] += 1
                    self.work += 1
                    hit = True
                else:
                    if self.ik is None:
                        self.ik = IK(self.path_q, task[2], task[3], self.ik_limit)
                        self.cache_stats['ik_misses'] += 1
                        self._ik_work = 0
                    self.ik.advance(1)
                    self.work += 1
                    self._ik_work += 1
                    if not self.ik.done:
                        continue
                    raw = self.ik.receipt()
                    self._ik_cache[key] = {'receipt': copy.deepcopy(raw), 'work': self._ik_work}
                    hit = False
                receipt = {'stage': stage['label'], 'point': task[2].tolist(), **raw,
                           'cache_hit': hit, 'cache_key': key}
                self.receipt['path_ik'].append(receipt)
                if not receipt['success'] or receipt['limit_margin_rad'] < self.required_margin:
                    reason = 'local_ik_unconverged' if not receipt['success'] else 'local_joint_margin_unconfirmed'
                    self.ik = None
                    self._finish_option(reason)
                    continue
                self.path_q = np.asarray(raw['q'], float).copy()
                self.receipt['validated_prefix'].append({'stage': stage['label'], 'point': task[2].tolist(), 'q': self.path_q.tolist()})
                self.ik = None
            else:
                if self.last_geometry_work >= MAX_GEOMETRY_PER_ADVANCE:
                    break
                stage = task[1]
                receipt = self._geometry(task)
                self.work += 1
                self.last_geometry_work += 1
                self.receipt['geometry'].append({'stage': stage['label'], 'kind': kind, **receipt})
                if not receipt['accepted']:
                    self._finish_option('hand_or_carried_can_clearance_unconfirmed')
                    continue
            self.task_index += 1
            if self.task_index == len(self.tasks):
                self._finish_option('sequential_ik_and_whole_route_geometry_validated', True)
        self.last_work = self.work-start_work
        if not self.done and (self.calls >= MAX_ADVANCE_CALLS or self.work >= MAX_WORK):
            self._stop_budget()
        assert self.last_work <= units and self.last_geometry_work <= MAX_GEOMETRY_PER_ADVANCE
        return self.done
