"""Validate v18's finite endpoint family using saved observations only."""
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import argparse
import copy
import json
import sys
import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v18_20261019_01.inspect_short_route import controller, serial, sha, read
from reproduction.improvement_v18_20261019_01.recovery.carry_search import CarryPathSearch
from reproduction.improvement_v17_20261019_01.recovery import carry_search as parent
from reproduction.improvement_v16_20261016_01.recovery.pose_servo import _hand_box_translation_envelope
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK, fk


def execute(first, exact_only=False):
    c = controller(first)
    clock = c.clock
    s = CarryPathSearch(c, first['x'], first['q'])
    assert c.clock == clock
    expected = {'current_exact', 'current_rotation_inset', 'outward_15_inset', 'outward_15_equivalent_inset'}
    assert len(s.options) == 4 and {o[0] for o in s.options} == expected
    if exact_only:
        # Isolate the unchanged original target; this is not a runtime family.
        s.options = [next(o for o in s.options if o[0] == 'current_exact')]
        s.index = 0
        s._start_option()
    calls = []
    while not s.done:
        clock = c.clock
        s.advance(16)
        assert c.clock == clock, 'The helper must not change the controller clock'
        assert s.last_work <= 16 and s.last_geometry_work <= 4
        calls.append({'clock': clock, 'work': s.last_work, 'geometry': s.last_geometry_work})
        if not s.done: c.clock += 1
    assert s.work <= 384 and s.calls <= 24
    assert all(r['iterations'] <= 48 for o in s.receipts for r in o['path_ik'])
    assert all(o['status'] == 'unknown' for o in s.receipts if not o['accepted'])
    old = s.work, s.calls, len(s.receipts), s.status
    for _ in range(3): s.advance(16)
    assert old == (s.work, s.calls, len(s.receipts), s.status)
    return s, calls


def validate(s):
    if s.chosen is None: return {'chosen': False}
    p = s.chosen
    receipt = next(r for r in s.receipts if r['accepted'])
    assert p['preserve_current'] is False
    assert receipt['predicted_rigid_object_goals']['accepted_original_task_region']
    assert all(r['success'] and r['limit_margin_rad'] >= .04 and r['position_error_m'] < .004
               and r['angle_error_rad'] < .04 for r in receipt['path_ik'])
    assert all(r['accepted'] and r['hand_margin_m'] >= .001 and r['carried_can_margin_m'] >= .001
               for r in receipt['geometry'])
    for a, b in [(p['carry_goal'], p['stages'][-1]['goal']), (p['place_goal'], p['placement']['goal']),
                 (p['held_relative_position'], s.envelope.offset),
                 (p['held_relative_rotation'], s.envelope.relative_rotation)]:
        np.testing.assert_array_equal(a, b)
    result = {'chosen': True, 'live_reference_and_exact_targets_retained': True,
              'predicted_object_goals': receipt['predicted_rigid_object_goals']}
    if p['candidate'] == 'current_rotation_inset':
        assert not p['short_original_route'] and p['short_verified_route']
        assert p['endpoint_change_is_not_pure_ik_repair']
        assert len(p['stages']) == 1 and p['stages'][0]['label'] == 'direct_transport'
        assert p['stages'][0]['kind'] == 'translate'
        np.testing.assert_array_equal(p['rotation'], s.original_rotation)
        np.testing.assert_array_equal(p['held_offset'], s.envelope.held_offset(p['rotation']))
        carry = p['carry_goal']+p['rotation']@s.envelope.offset
        place = p['place_goal']+p['rotation']@s.envelope.offset
        assert abs(np.linalg.norm(carry[:2]-s.target[:2])-.035) < 1e-12
        assert abs(place[2]-(s.floor+.095)) < 1e-12
        assert np.linalg.norm(carry[:2]-s.target[:2]) < .045
        assert np.linalg.norm(place[:2]-s.target[:2]) < .05 and place[2] < s.floor+.10
        # Independent dense orientation product check complements the original
        # analytical continuous mixed-envelope certificate, not replaces it.
        stage = p['stages'][0]
        rv = Rotation.from_matrix(stage['rotation']@stage['start_rotation'].T).as_rotvec()
        margins = []
        for fraction in np.linspace(0, 1, 9):
            rotation = Rotation.from_rotvec(rv*fraction).as_matrix()@stage['start_rotation']
            margins.append(min(_hand_box_translation_envelope(stage['start'], stage['goal'], rotation, s.gap),
                               s.envelope.sweep_margin(stage['start'], stage['goal'], rotation)))
        assert min(margins) >= .001
        assert any(g.get('whole_translation_times_rotation_envelope') for g in receipt['geometry'])
        assert any(g['kind'] == 'placement_precheck' for g in receipt['geometry'])
        assert any(r['stage'] == 'placement_validation' for r in receipt['path_ik'])
        result.update(dense_mixed_product_minimum_margin_m=min(margins),
                      endpoint_family_changed=True, complete_mixed_and_placement_checks=True)
    return result


def boundaries(first):
    checks = []
    q = np.asarray(first['q'], float)
    p, r = fk(q)
    for position, angle, expected in [(.003999, 0., True), (.004001, 0., False),
                                      (0., .039999, True), (0., .040001, False)]:
        ik = IK(q, p+np.array([position, 0., 0.]), Rotation.from_rotvec([angle, 0., 0.]).as_matrix()@r, 1)
        ik.advance(1)
        assert ik.success is expected
        checks.append({'mechanism': 'inherited_ik_tolerance', 'position_m': position,
                       'angle_rad': angle, 'accepted': ik.success})
    # Fault injection verifies the unchanged consumer threshold independently
    # of whether a numerical solver happens to land precisely on the margin.
    for margin, success, expected in [(.04-1e-9, True, 'local_joint_margin_unconfirmed'),
                                      (.04, True, None), (.5, False, 'local_ik_unconverged')]:
        c = controller(first)
        s = CarryPathSearch(c, first['x'], first['q'])
        stage = s.stages[0]
        s.tasks = [('ik', stage, stage['goal'], stage['rotation']), ('schedule',)]
        s.task_index = 0
        class FakeIK:
            def __init__(self, *args): self.done = False
            def advance(self, n): self.done = True
            def receipt(self):
                return {'success': success, 'iterations': 1, 'q': q.tolist(),
                        'position_error_m': 0., 'angle_error_rad': 0., 'limit_margin_rad': margin}
        with patch.object(parent, 'IK', FakeIK): s.advance(1)
        actual = s.receipts[0]['reason'] if s.receipts else None
        assert actual == expected
        checks.append({'mechanism': 'joint_margin_and_unknown_ik', 'margin_rad': margin,
                       'ik_success': success, 'rejection_reason': actual})
    for desired, expected in [(.001-1e-9, False), (.001+1e-9, True)]:
        s = CarryPathSearch(controller(first), first['x'], first['q'])
        stage = s.stages[0]
        task = ('mixed_geometry', stage, stage['start_rotation'], 0., 0.)
        with patch.object(parent, '_hand_box_translation_envelope', return_value=desired+1e-8), \
             patch.object(s.envelope, 'sweep_margin', return_value=.1):
            result = s._geometry(task)
        assert result['accepted'] is expected
        checks.append({'mechanism': 'inherited_mixed_box_margin', 'margin_m': result['hand_margin_m'],
                       'accepted': result['accepted']})
    for field, value in [('joint_solution_margin_rad', .04-1e-9), ('ik_iterations_per_target', 49)]:
        c = controller(first)
        setattr(c.cfg, field, value)
        try: CarryPathSearch(c, first['x'], first['q'])
        except AssertionError: pass
        else: raise AssertionError('Relaxed inherited parameter accepted')
        checks.append({'mechanism': 'invalid_relaxed_config_rejected', 'field': field, 'value': value})
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='short_route_static_a.json')
    destination = RUN/'analysis'/parser.parse_args().output
    assert not destination.exists()
    prior_path = RUN/'analysis/short_route_diagnosis_a.json'
    prior = read(prior_path)
    sources = dict(prior['source_sha256'])
    for path in [Path(__file__), prior_path, RUN/'recovery/carry_search.py']:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT/path) == h for path, h in sources.items())
    # These numerical/geometry/time implementations must remain inherited.
    for name in ['advance', '_geometry', '_context', '_key', '_schedule']:
        assert getattr(CarryPathSearch, name) is getattr(parent.CarryPathSearch, name)
    cases = []
    for old in prior['cases']+prior['budget_success_references']:
        first = old['snapshot']
        s, calls = execute(first)
        item = {'job': old['job'], 'clock': first['clock'], 'status': s.status, 'calls': s.calls,
                'work': s.work, 'calls_detail': calls, 'candidate_family': [o[0] for o in s.options],
                'chosen': s.chosen, 'receipts': s.receipts, 'checks': validate(s)}
        if 'original_rejection' in old:
            isolated, _ = execute(first, exact_only=True)
            assert isolated.chosen is None
            original = old['original_rejection']
            assert isolated.receipts[0]['reason'] == original['reason']
            assert isolated.receipts[0]['path_ik'] == original['path_ik']
            item['unchanged_exact_route_rejection'] = {'reason': isolated.receipts[0]['reason'],
                                                       'raw_path_ik_exact': True}
        cases.append(item)
        print(json.dumps({'job': old['job'], 'clock': first['clock'], 'work': s.work,
                          'chosen': s.chosen['candidate'] if s.chosen else None}), flush=True)
    first = prior['budget_success_references'][0]['snapshot']
    tests = boundaries(first)
    late = copy.deepcopy(first); late['clock'] = 399
    s, _ = execute(late)
    assert s.chosen is None and s.work == 4 and len(s.receipts) == 4
    assert all(r['reason'] == 'remaining_command_schedule_unconfirmed' for r in s.receipts)
    # Cache is still local to each immutable search; no cross-attempt reuse.
    a = CarryPathSearch(controller(first), first['x'], first['q'])
    b = CarryPathSearch(controller(first), first['x'], first['q'])
    assert a._ik_cache is not b._ik_cache and not b._ik_cache
    altered = copy.deepcopy(first); altered['q'][0] = np.nextafter(altered['q'][0], np.inf)
    changed = CarryPathSearch(controller(altered), altered['x'], altered['q'])
    assert a._context() != changed._context()
    assert not a.q.flags.writeable and not a.envelope.offset.flags.writeable
    assert all(sha(ROOT/path) == h for path, h in sources.items())
    out = {'passed': True, 'source_sha256': sources, 'new_physical_episodes': 0,
           'new_controller_replay_steps': 0, 'saved_state_searches': len(cases),
           'chosen_counts': dict(Counter(c['chosen']['candidate'] if c['chosen'] else 'unknown' for c in cases)),
           'cases': cases, 'threshold_negative_tests': tests,
           'inherited_numerical_geometry_cache_schedule_implementations': True,
           'no_helper_clock_mutation': True, 'four_candidates_only': True,
           'exact_original_rejection_unchanged_cases': len(prior['cases']),
           'late_budget_unknown_four_work': True, 'cache_private_and_q_sensitive': True,
           'limits': prior['limits'],
           'limitations': ['Known states only, including duplicate correlated profiles; static validation is not physical success.',
                           'This is a changed endpoint candidate, not proof the original exact target was falsely rejected by IK.',
                           'Replacing outward_30_center may reduce coverage outside these saved states.',
                           'Live controller hold, geometry, actual joint, stage timeout and 5-frame arrival checks remain required.',
                           'Nominal schedules do not guarantee completion within 400 steps.']}
    with destination.open('x', encoding='utf8') as handle:
        json.dump(serial(out), handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'passed': True, 'output': str(destination), 'chosen_counts': out['chosen_counts']}))


if __name__ == '__main__':
    main()
