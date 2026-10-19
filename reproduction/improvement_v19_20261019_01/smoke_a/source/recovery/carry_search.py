"""v19 limits optional endpoint exploration using already validated prefixes.

Only the original exact route's complete mixed transport/IK certificate can
admit the optional inset candidate, after a local placement failure. An
unadmitted or capped optional candidate stays unknown. No safety predicate,
physical budget, IK tolerance or mandatory execution guard is weakened.
"""
import copy
import numpy as np
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK
from reproduction.improvement_v17_20261019_01.recovery.carry_search import (
    MAX_WORK, MAX_ADVANCE_CALLS, MAX_WORK_PER_ADVANCE, MAX_GEOMETRY_PER_ADVANCE,
)
from reproduction.improvement_v18_20261019_01.recovery.carry_search import CarryPathSearch as V18Search

OPTIONAL_WORK_LIMIT = 48
OPTIONAL_CANDIDATE = 'current_rotation_inset'


class CarryPathSearch(V18Search):
    """Four finite families; optional admission costs one of its 48 work units.

    current_exact is first. The optional inset follows it, while the remaining
    old candidates keep their inherited relative order. The original route's
    exact goals remain unchanged. Existing chosen-route fields and mandatory
    live controller checks retain the v18 contract.
    """
    def __init__(self, *args):
        self._admission_ordered = False
        self._candidate_work_start = 0
        super().__init__(*args)

    def _start_option(self):
        super()._start_option()
        if not self._admission_ordered:
            original = next(o for o in self.options if o[0] == 'current_exact')
            optional = next(o for o in self.options if o[0] == OPTIONAL_CANDIDATE)
            remainder = [o for o in self.options if o[0] not in ['current_exact', OPTIONAL_CANDIDATE]]
            self.options = [original, optional]+remainder
            self._admission_ordered = True
            # The initial parent setup did not run numerical work or mutate
            # the controller clock. Rebuild tasks for the fixed first option.
            super()._start_option()
        self._candidate_work_start = self.work
        self.receipt.update(candidate_work_start=self.work, candidate_work=0,
                            optional_endpoint_candidate=self.options[self.index][0] == OPTIONAL_CANDIDATE)
        if self.receipt['optional_endpoint_candidate']:
            self.receipt['candidate_work_limit'] = OPTIONAL_WORK_LIMIT
            self.tasks.insert(0, ('inset_admission',))

    def _admission(self):
        original = next((r for r in self.receipts if r['candidate'] == 'current_exact'), None)
        paths = original.get('path_ik', []) if original else []
        transport = [r for r in paths if r['stage'] == 'direct_transport']
        mixed = [r for r in original.get('geometry', []) if r['kind'] == 'mixed_geometry'] if original else []
        # Match the exact arithmetic used by the inherited continuation task
        # builder at fraction=1. Its final point may differ from goal by one
        # floating-point ULP; no Cartesian tolerance is widened here.
        final_point = self.x[:3]+(np.asarray(original['carry_goal'])-self.x[:3]) if original else None
        complete = bool(original and transport and mixed and
                        np.array_equal(transport[-1]['point'], final_point) and
                        all(r['success'] and r['limit_margin_rad'] >= self.required_margin for r in transport) and
                        all(r['accepted'] for r in mixed))
        placement_failure = bool(original and not original['accepted'] and paths and
                                 paths[-1]['stage'] == 'placement_validation' and
                                 original['reason'] in ['local_ik_unconverged', 'local_joint_margin_unconfirmed'])
        return {'admitted': complete and placement_failure,
                'original_transport_complete': complete,
                'failure_confined_to_placement': placement_failure,
                'original_reason': original['reason'] if original else None,
                'validated_transport_targets': len(transport),
                'original_last_ik_stage': paths[-1]['stage'] if paths else None,
                'interpretation': 'Optional exploration policy using this search only; denied means unknown, not unreachable.'}

    def _record_candidate_work(self):
        self.receipt['candidate_work'] = self.work-self._candidate_work_start
        if self.receipt.get('optional_endpoint_candidate'):
            assert self.receipt['candidate_work'] <= OPTIONAL_WORK_LIMIT

    def _finish_option(self, reason, accepted=False):
        self._record_candidate_work()
        if reason == 'optional_candidate_work_cap_unconfirmed' and self.ik is not None:
            # Do not run even a new FK solve for this diagnostic field.
            self.receipt['unfinished_local_ik'] = {
                'iterations_so_far': self.ik.iterations,
                'target': self.tasks[self.task_index][2].tolist(),
                'stage': self.tasks[self.task_index][1]['label'],
                'status': 'unknown',
            }
        super()._finish_option(reason, accepted)

    def _stop_budget(self):
        self._record_candidate_work()
        super()._stop_budget()

    def advance(self, units=16):
        """Original v17 bounded engine plus one admission task and local cap.

        Admission and every numerical iteration share the same per-call/global
        counters. A candidate cap never resets the search or controller clock.
        """
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
            if (self.receipt.get('optional_endpoint_candidate') and
                    self.work-self._candidate_work_start >= OPTIONAL_WORK_LIMIT):
                self._finish_option('optional_candidate_work_cap_unconfirmed')
                continue
            task = self.tasks[self.task_index]
            kind = task[0]
            if kind == 'inset_admission':
                self.work += 1
                self.receipt['admission'] = self._admission()
                if not self.receipt['admission']['admitted']:
                    self._finish_option('optional_endpoint_admission_unconfirmed')
                    continue
            elif kind == 'schedule':
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
