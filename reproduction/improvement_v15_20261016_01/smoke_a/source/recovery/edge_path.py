"""Bounded translate-then-turn wall-top paths using the frozen v11 certificates.

Only current observation, current joints, fixed hand/can assets and the existing
grasp family are inputs. Certificates cover hand/can geometry and local waypoint
IK; they are not full-arm collision or closed-loop tracking guarantees.
"""
import numpy as np
from scipy.spatial.transform import Rotation

from reproduction.improvement_v11_20261015_01.recovery.path_search import EdgeSearch, sweep_margin, turn_samples
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import enclosure, object_margin
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK


class SegmentedEdgeSearch:
    """At most16 work units and4 geometry predicates per advance call.

    ``chosen`` retains the existing EdgeSearch keys and adds pre_goal,
    pre_rotation, segments and waypoint_ik. A caller must complete translation
    with the current orientation, then turn in place, then approach and descend.
    Every stage remains subject to measured-pose/clearance/joint checks and the
    common episode/phase clocks. An empty result authorizes no new motion.
    """

    def __init__(self, controller, x, q):
        self.x = np.asarray(x, float).copy()
        self.q = np.asarray(q, float).copy()
        assert self.x.shape == (23,) and self.q.shape == (7,)
        assert np.all(np.isfinite(self.x)) and np.all(np.isfinite(self.q))
        base = EdgeSearch(controller, self.x, self.q)
        self.anchor = self.x[16:23].copy()
        self.start = self.x[:3].copy()
        self.current_rotation = Rotation.from_quat(self.x[3:7]).as_matrix()
        self.extra = base.extra
        self.nominal_gap = base.nominal_gap
        self.observed_gap = base.observed_gap
        self.maximum_gap = base.maximum_gap
        self.object_margin_required = base.object_margin_required
        self.required_margin = base.required_margin
        self.limit = base.limit
        self.options = []
        # Fixed geometric fractions, independent of start IDs or outcomes.
        # Keep the pre-translation at a height no lower than either endpoint.
        for candidate in base.options:
            for fraction in (.35, .65):
                waypoint = self.start + fraction * (candidate['above'] - self.start)
                waypoint[2] = max(self.start[2], candidate['above'][2])
                if np.linalg.norm(waypoint - self.start) < .015:
                    continue
                self.options.append({
                    **candidate, 'pre_goal': waypoint,
                    'pre_rotation': self.current_rotation.copy(),
                    'pre_fraction': fraction,
                })
        self.index = 0
        self.work = 0
        self.done = not self.options
        self.chosen = None
        self.receipts = []
        self.stage = 'empty'
        if not self.done:
            self.begin()

    def begin(self):
        option = self.options[self.index]
        self.targets = [
            ('pretranslate', option['pre_goal'], self.current_rotation),
            ('turn', option['pre_goal'], option['rotation']),
            ('approach', option['above'], option['rotation']),
            ('descend', option['goal'], option['rotation']),
        ]
        self.target = 0
        self.current = []
        self.margins = []
        self.checks = []
        self.check_index = 0
        self.stage = 'prefilter'
        self.ik = None

    def finish_option(self, reason, accepted=False):
        option = self.options[self.index]
        self.receipts.append({
            'index': self.index, 'pre_fraction': option['pre_fraction'],
            'distance_m': option['distance_m'], 'height_m': option.get('height_m'),
            'flip': option['flip'], 'reason': reason, 'accepted': bool(accepted),
            'ik': self.current, 'margins': self.margins,
        })
        if accepted:
            self.chosen = {
                **option,
                'waypoint_ik': self.current,
                'segments': [
                    {'kind': 'translate', 'start': self.start.copy(), 'goal': option['pre_goal'].copy(),
                     'rotation': self.current_rotation.copy()},
                    {'kind': 'rotate', 'position': option['pre_goal'].copy(),
                     'start_rotation': self.current_rotation.copy(), 'rotation': option['rotation'].copy()},
                    {'kind': 'translate', 'start': option['pre_goal'].copy(), 'goal': option['above'].copy(),
                     'rotation': option['rotation'].copy()},
                    {'kind': 'descend', 'start': option['above'].copy(), 'goal': option['goal'].copy(),
                     'rotation': option['rotation'].copy()},
                ],
            }
            self.done = True
        else:
            self.index += 1
            if self.index == len(self.options):
                self.done = True
            else:
                self.begin()

    def prefilter(self):
        option = self.options[self.index]
        envelope = enclosure(option['goal'], option['rotation'], self.nominal_gap, self.x)
        maximum = envelope['closure_extent_m'] / 2 + abs(envelope['closure_center_m'])
        needed = 2 * (maximum + .0005 + self.object_margin_required) + self.extra
        target = max(self.nominal_gap, float(np.ceil(needed / .002) * .002))
        if target > self.maximum_gap:
            self.finish_option('can_does_not_fit_bounded_aperture')
            return
        option['target_gap'] = target
        self.gap = min(.085, max(self.observed_gap, target) + self.extra)
        self.object_gap = [target-self.extra, target+self.extra]
        self.transition_gap = [min(self.observed_gap, self.object_gap[0])-.001,
                               max(self.observed_gap, self.object_gap[1])+.001]
        margin = object_margin(option['goal'], option['goal'], option['rotation'], self.object_gap, self.x)
        self.margins.append({'kind': 'terminal_open_hand_can', 'margin_m': margin, 'required_m': .003})
        if margin < self.object_margin_required:
            self.finish_option('terminal_can_clearance_not_validated')
            return
        self.ik = IK(self.q, self.targets[0][1], self.targets[0][2], self.limit)
        self.stage = 'ik'

    def prepare_checks(self):
        option = self.options[self.index]
        waypoint = option['pre_goal']
        # Each predicate is separately counted. Fixed-rotation segments cannot
        # be replaced by simultaneous translation and rotation during execution.
        self.checks = [
            ('pretranslate_boxes', 'boxes', self.start, waypoint, self.current_rotation, 0., self.transition_gap),
            ('pretranslate_can', 'can', self.start, waypoint, self.current_rotation, 0., self.transition_gap),
        ]
        for rotation, bound in turn_samples(self.current_rotation, option['rotation'], self.gap):
            self.checks.append(('turn_boxes_arc_bound', 'boxes', waypoint, waypoint, rotation, bound, self.transition_gap))
            self.checks.append(('turn_can_arc_bound', 'can', waypoint, waypoint, rotation, bound, self.transition_gap))
        for kind, start, end in [('approach', waypoint, option['above']),
                                 ('descend', option['above'], option['goal'])]:
            self.checks.append((kind+'_boxes', 'boxes', start, end, option['rotation'], 0., self.object_gap))
            self.checks.append((kind+'_can', 'can', start, end, option['rotation'], 0., self.object_gap))
        self.stage = 'geometry'

    def advance(self, units=16):
        assert isinstance(units, int) and 1 <= units <= 16
        if self.done:
            return True
        before = self.work
        geometric = 0
        while not self.done and self.work-before < units:
            if self.stage == 'prefilter':
                if geometric == 4:
                    break
                self.work += 1
                geometric += 1
                self.prefilter()
            elif self.stage == 'ik':
                self.work += 1
                self.ik.advance(1)
                if not self.ik.done:
                    continue
                receipt = self.ik.receipt()
                receipt['waypoint_kind'] = self.targets[self.target][0]
                self.current.append(receipt)
                if not receipt['success'] or receipt['limit_margin_rad'] < self.required_margin:
                    self.finish_option('local_segment_ik_not_validated')
                    continue
                self.target += 1
                if self.target == len(self.targets):
                    self.prepare_checks()
                else:
                    self.ik = IK(self.ik.q, self.targets[self.target][1], self.targets[self.target][2], self.limit)
            else:
                assert self.stage == 'geometry'
                if geometric == 4:
                    break
                self.work += 1
                geometric += 1
                kind, family, start, end, rotation, bound, gaps = self.checks[self.check_index]
                margin = (sweep_margin(start, end, rotation, self.gap) if family == 'boxes'
                          else object_margin(start, end, rotation, gaps, self.x)) - bound
                required = .001 if family == 'boxes' else self.object_margin_required
                self.margins.append({'kind': kind, 'margin_m': margin, 'required_m': required})
                if margin < required:
                    self.finish_option('segment_'+family+'_path_not_validated')
                    continue
                self.check_index += 1
                if self.check_index == len(self.checks):
                    self.finish_option('validated_translate_turn_approach_descent', True)
        assert self.work-before <= units and geometric <= 4
        return self.done
