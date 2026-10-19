"""Bounded offline entry-preserving risk-feedback and unchanged protection checks.

Saved observations and synthetic free-space inputs are not new evaluation
episodes. The caller's clock, aperture policy, CLOSE, joint and timeout branches
are checked separately by the central-controller component harness.
"""
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import argparse
import hashlib
import json
import sys
import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v21_20261019_01.recovery import recenter_transition as H
from reproduction.improvement_v19_20261019_01.recovery.recovery_controller import Config
from reproduction.improvement_v19_20261019_01.recovery.transition import propose as old
from reproduction.improvement_v18_20261019_01.inspect_handoff_static import verify_output, finite


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='transition_static_a')
    args = parser.parse_args()
    output = RUN / 'analysis' / (args.name + '.json')
    assert not output.exists(), 'Do not overwrite static receipts.'
    evidence_path = RUN / 'analysis/recenter_axis_diagnosis.json'
    evidence = json.loads(evidence_path.read_text(encoding='utf8'))
    assert evidence['passed'] and evidence['new_physical_episodes'] == 0
    hashes = dict(evidence['source_sha256'])
    for path, digest in hashes.items():
        assert sha(ROOT / path) == digest, path
    cfg = Config()
    cases, tests = [], []
    exact_parent = 0
    exact_entry = 0
    exact_normal_progress = 0
    late_away_steps = []

    def check(action, receipt, previous):
        verify_output(action, receipt, cfg, previous)
        if receipt['accepted']:
            assert receipt['required_hand_box_margin_m'] == .001
            assert receipt['required_can_margin_m'] == .001
            assert receipt['required_second_margin_m'] == .001
            assert receipt['kind'] == 'mixed_pose' and not receipt['held']
            assert receipt['delay'] == 2 and receipt['servo_bias_used'] is False

    for case in evidence['cases']:
        first = case['per_control'][0]['control_step']
        for saved in case['per_control']:
            x = np.array(saved['state_before'])
            goal = np.array(saved['goal_m'])
            rotation = np.array(saved['target_rotation'])
            motion = np.array(saved['motion_per_control'])
            previous = np.array(saved['previous_submitted_action'])
            axis = np.array(saved['descent_axis'])
            age = saved['descent_controls'] or saved['control_step'] - first + 1
            grip = float(saved['actual_submitted_action'][6])
            kwargs = dict(descent_controls=age, descent_axis=axis, grip=grip,
                          aperture_motion=saved['aperture_motion'])
            untouched = [v.copy() for v in [x, goal, rotation, motion, previous, axis]]
            action, receipt = H.propose(x, goal, rotation, motion, cfg, previous, **kwargs)
            check(action, receipt, previous)
            again, receipt_again = H.propose(x, goal, rotation, motion, cfg, previous, **kwargs)
            np.testing.assert_array_equal(action, again)
            assert receipt == receipt_again
            for before, after in zip(untouched, [x, goal, rotation, motion, previous, axis]):
                np.testing.assert_array_equal(before, after)
            reversed_action, reversed_receipt = H.propose(x, goal, rotation, motion, cfg, previous,
                **{**kwargs, 'descent_axis': -axis})
            np.testing.assert_array_equal(action, reversed_action)
            np.testing.assert_array_equal(receipt['raw_translation_m'], reversed_receipt['raw_translation_m'])
            assert receipt['accepted'] == reversed_receipt['accepted']
            if case['version'] == 'v19':
                parent_action, parent_receipt = old(x, goal, rotation, motion, cfg, previous,
                    grip, saved['aperture_motion'], descent_controls=age)
                np.testing.assert_array_equal(parent_action, saved['actual_submitted_action'])
                np.testing.assert_array_equal(parent_receipt['raw_translation_m'], saved['original_raw_translation_m'])
                np.testing.assert_array_equal(receipt['raw_rotation_rad'], parent_receipt['raw_rotation_rad'])
                exact_parent += 1
            parent_action, parent_receipt = old(x, goal, rotation, motion, cfg, previous,
                grip, saved['aperture_motion'], descent_controls=age)
            direction = receipt['handoff21']
            expected = cfg.position_gain * (goal - x[:3])
            if direction['entry_window_active']:
                expected = expected - cfg.tracking_velocity_damping * motion[:3]
                np.testing.assert_array_equal(action, parent_action)
                assert receipt['accepted'] == parent_receipt['accepted']
                exact_entry += 1
            else:
                if direction['axial_feedback']:
                    expected = expected - cfg.tracking_velocity_damping * axis * direction['axial_motion_m']
                if direction['lateral_feedback']:
                    expected = expected - cfg.tracking_velocity_damping * np.array(direction['lateral_motion_m'])
                if not direction['axial_feedback'] and not direction['lateral_feedback']:
                    np.testing.assert_array_equal(action, parent_action)
                    assert receipt['accepted'] == parent_receipt['accepted']
                    exact_normal_progress += 1
                if direction['axial_moving_away']:
                    late_away_steps.append({'job':case['job'],'step':saved['control_step'],'age':age})
            np.testing.assert_array_equal(receipt['raw_translation_m'], expected)
            cases.append({'old_job': case['job'], 'old_control_step': saved['control_step'],
                          'candidate_action': action.tolist(), 'receipt': receipt})
    assert len(cases) == 56 and exact_parent == 32 and exact_entry == 12
    assert exact_normal_progress >= 10
    assert [r['step'] for r in late_away_steps if r['job']=='v19_regression_6000005'] == [321,322,323]

    # Free-space state is a geometric test fixture, not a new task start.
    free = np.array(evidence['cases'][0]['per_control'][0]['state_before'])
    free[:3] = [0., 0., 1.5]
    free[3:7] = [0., 0., 0., 1.]
    free[16:19] = [.4, .4, .85]
    rotation = np.eye(3)
    axis = np.array([0., 0., 1.])
    previous = np.zeros(7)

    def directional(name, error, velocity, expected_axial, expected_lateral,
                    *, expected_away=None, expected_crossing=None):
        motion = np.r_[velocity, [.001, -.002, .003]]
        goal = free[:3] + error
        outputs = []
        for age in [1, 3, 4, 85]:
            action, receipt = H.propose(free, goal, rotation, motion, cfg, previous,
                                       descent_controls=age, descent_axis=axis)
            check(action, receipt, previous)
            assert receipt['accepted'], name
            direction = receipt['handoff21']
            assert direction['axial_feedback'] == (age <= 3 or expected_axial), name
            assert direction['lateral_feedback'] == (age <= 3 or expected_lateral), name
            assert direction['entry_window_active'] == (age <= 3)
            if age <= 3:
                old_action, old_receipt = old(free, goal, rotation, motion, cfg, previous, descent_controls=age)
                np.testing.assert_array_equal(action, old_action)
                np.testing.assert_array_equal(receipt['raw_translation_m'], old_receipt['raw_translation_m'])
            if expected_away is not None:
                assert direction['lateral_moving_away_or_tangential'] == expected_away
            if expected_crossing is not None:
                assert direction['lateral_nominal_crossing'] == expected_crossing
            outputs.append(receipt['raw_translation_m'])
            tests.append({'name': name, 'existing_age': age, 'receipt': receipt})
        # Entry laws are exact parents; after the entry boundary risk feedback
        # depends only on current directions, not on a renewed window.
        np.testing.assert_array_equal(outputs[0], outputs[1])
        np.testing.assert_array_equal(outputs[2], outputs[3])
        return outputs[2]

    plain = directional('normal_axial_progress_without_extra_damping', [0., 0., .06],
                        [0., 0., .004], False, False)
    np.testing.assert_array_equal(plain, cfg.position_gain * (free[:3] + [0., 0., .06] - free[:3]))
    directional('lateral_moving_away', [.01, 0., .06], [-.002, 0., .004],
                False, True, expected_away=True, expected_crossing=False)
    directional('lateral_cross_center_while_approaching', [.003, 0., .06], [.002, 0., .004],
                False, True, expected_away=False, expected_crossing=True)
    directional('lateral_approach_without_crossing', [.01, 0., .06], [.002, 0., .004],
                False, False, expected_away=False, expected_crossing=False)
    directional('center_with_zero_velocity_no_damping', [0., 0., .06], [0., 0., 0.], False, False)
    directional('center_with_nonzero_lateral_drift', [0., 0., .06], [0., .002, .004],
                False, True, expected_away=True, expected_crossing=True)
    directional('near_center_orthogonal_motion', [1e-9, 0., .06], [0., .002, .004],
                False, True, expected_away=True, expected_crossing=False)
    directional('axial_moving_away_after_entry', [0., 0., .06], [0., 0., -.002], True, False)
    directional('negative_axial_moving_away_after_entry', [0., 0., -.06], [0., 0., .002], True, False)
    directional('axial_nominal_target_crossing', [0., 0., .003], [0., 0., .002], True, False)
    directional('negative_axis_target_crossing', [0., 0., -.003], [0., 0., -.002], True, False)
    directional('mixed_axial_crossing_lateral_away', [.01, 0., .003], [-.002, .001, .002], True, True)

    # Rotation covariance of the directional rule, including an oblique axis.
    q = Rotation.from_euler('xyz', [.31, -.23, .19]).as_matrix()
    error = np.array([.01, 0., .003]); velocity = np.array([-.002, .001, .002])
    rotated = free.copy(); rotated[3:7] = Rotation.from_matrix(q).as_quat()
    aa, rr = H.propose(free, free[:3] + error, rotation, np.r_[velocity, [0., 0., 0.]], cfg, previous,
                       descent_controls=4, descent_axis=axis)
    ba, br = H.propose(rotated, rotated[:3] + q @ error, q, np.r_[q @ velocity, [0., 0., 0.]], cfg, previous,
                       descent_controls=4, descent_axis=q[:, 2])
    check(aa, rr, previous); check(ba, br, previous)
    assert rr['accepted'] and br['accepted']
    np.testing.assert_allclose(br['raw_translation_m'], q @ np.array(rr['raw_translation_m']), rtol=0., atol=1e-15)
    tests.append({'name': 'oblique_axis_coordinate_covariance', 'receipt': br})

    def reject(name, **changes):
        inputs = dict(x=free, goal=free[:3] + [.02, 0., -.01], rotation=rotation,
                      motion=np.zeros(6), cfg=cfg, previous_action=previous,
                      grip=0., aperture_motion=False, descent_controls=4, descent_axis=axis)
        inputs.update(changes)
        action, receipt = H.propose(**inputs)
        assert not receipt['accepted'] and np.isfinite(action).all(), name
        np.testing.assert_array_equal(action[:6], np.zeros(6))
        assert receipt['work'] <= 16
        tests.append({'name': name, 'receipt': receipt})

    for age in [0, -1, 1.5, True, None]:
        reject('invalid_existing_age_' + str(age), descent_controls=age)
    for name, bad in [('zero', [0., 0., 0.]), ('nonunit', [0., 0., 2.]),
                      ('nonfinite', [0., np.nan, 1.]), ('wrong_shape', [0., 1.]),
                      ('wrong_line', [1., 0., 0.]), ('none', None)]:
        reject('invalid_axis_' + name, descent_axis=bad)
    for name, bad in [('zero', np.zeros((3, 3))), ('reflection', np.diag([1., 1., -1.])),
                      ('wrong_shape', np.zeros(3)), ('nonfinite', np.full((3, 3), np.inf))]:
        reject('invalid_rotation_' + name, rotation=bad)
    bad = free.copy(); bad[3:7] = 0.
    reject('invalid_observed_quaternion', x=bad)
    for key, bad in [('x', np.full(23, np.nan)), ('goal', np.full(3, np.inf)),
                     ('motion', np.full(6, np.nan)), ('previous_action', np.full(7, np.inf))]:
        reject('nonfinite_' + key, **{key: bad})
    reject('invalid_previous_range', previous_action=np.ones(7) * 2.)
    for name, different in [('delay', replace(cfg, delay=3)),
                            ('translation_cap', replace(cfg, max_delta_m=.036)),
                            ('rotation_cap', replace(cfg, max_rotation_rad=.151)),
                            ('linear_damping', replace(cfg, tracking_velocity_damping=1.)),
                            ('angular_damping', replace(cfg, tracking_angular_damping=.2))]:
        reject('unchanged_' + name, cfg=different)
    reject('nonfinite_grip', grip=float('nan'))
    reject('pulse_without_full_aperture_certificate', grip=-1.)

    for age in [1, 3, 4, 85]:
        action, receipt = H.propose(free, free[:3] + [.02, 0., -.01], rotation,
            np.zeros(6), cfg, previous, grip=-1., aperture_motion=True,
            descent_controls=age, descent_axis=axis)
        check(action, receipt, previous)
        assert receipt['accepted'] and receipt['aperture_range_m'] == [0., .085] and action[6] == -1.
        tests.append({'name': 'full_aperture_at_existing_age_' + str(age), 'receipt': receipt})

    # A genuine saved geometric negative, not a synthetic certificate failure.
    old_path = ROOT / 'reproduction/improvement_v18_20261019_01/analysis/handoff_diagnosis.json'
    old_data = json.loads(old_path.read_text(encoding='utf8'))
    assert old_data['passed']
    stopped = next(c for c in old_data['cases'] if c['version'] == 'v17'
                   and c['condition'].endswith('13000022'))['handoffs'][0]['last_descend']
    rejected_rotation = np.array(stopped['grasp']['target_rotation'])
    for age in [1, 4, 85]:
        reject('saved_invalidated_geometry_age_' + str(age),
            x=np.array(stopped['state_before']), goal=np.array(stopped['grasp']['goal_m']),
            rotation=rejected_rotation, motion=np.array(stopped['actual_observed_motion']),
            previous_action=np.array(stopped['previous_submitted']['action']),
            descent_controls=age, descent_axis=rejected_rotation[:, 2])

    calls = []
    def forced_rejection(*args, **kwargs):
        calls.append(kwargs['work_limit'])
        work = min(6, kwargs['work_limit'])
        return {'kind': 'mixed_pose', 'accepted': False, 'work': work,
                'work_units': work, 'reason': 'synthetic_certificate_rejection'}
    prior = np.array([.7, 0., 0., 0., 0., 0., 0.])
    with patch.object(H, 'certify_action', forced_rejection):
        action, receipt = H.propose(free, free[:3] + [.2, 0., 0.], rotation,
            np.zeros(6), cfg, prior, descent_controls=85, descent_axis=axis)
    assert not receipt['accepted'] and calls == [16] and receipt['work'] == 6
    assert sum(t['reason'] == 'submitted_command_slew_unconfirmed' for t in receipt['trials']) == 2
    tests.append({'name': 'late_age_scaled_retry_cannot_bypass_slew', 'receipt': receipt})
    calls.clear()
    with patch.object(H, 'certify_action', forced_rejection):
        action, receipt = H.propose(free, free[:3] + [.002, 0., 0.], rotation,
            np.zeros(6), cfg, previous, descent_controls=85, descent_axis=axis)
    assert not receipt['accepted'] and calls == [16, 10, 4] and receipt['work'] == 16
    tests.append({'name': 'geometry_work_budget_cannot_exceed_16', 'receipt': receipt})

    # Preserve current dependency identity without coupling this helper receipt
    # to the not-yet-frozen new central controller.
    paths = [Path(__file__), Path(H.__file__), evidence_path, old_path]
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path:
            path = Path(path).resolve()
            if path.is_relative_to(ROOT / 'reproduction') and path.suffix == '.py':
                paths.append(path)
    hashes.update({rel(path): sha(path) for path in paths})
    result = {
        'passed': True,
        'scope': 'Saved-input helper proposals and synthetic mathematical/geometry negatives only; no new closed-loop evaluation.',
        'new_physical_episodes': 0, 'new_evaluation_samples': 0,
        'saved_observation_proposals': len(cases), 'parent_v19_actions_exactly_reconstructed': exact_parent,
        'boundary_and_negative_cases': len(tests),
        'max_geometry_work_saved': max(c['receipt']['work'] for c in cases),
        'max_geometry_work_including_synthetic_budget_probe': max(t['receipt']['work'] for t in tests),
        'axis_sign_invariance_on_all_saved_inputs': True,
        'entry_v19_final_float32_actions_bitwise_equal': exact_entry,
        'late_no_risk_actions_bitwise_equal_parent': exact_normal_progress,
        'late_axial_away_saved_steps': late_away_steps,
        'risk_rule_after_original_entry_independent_of_age': True,
        'original_rotation_window_preserved': True,
        'thresholds_unchanged': {'execution_hand_box_m': .001, 'execution_hand_can_m': .001,
            'planning_hand_can_m': .003, 'position_ready_m': .009, 'angle_ready_rad': .08,
            'confirmation_controls': 5, 'recenter_timeout_controls':24, 'step_budget': 400, 'delay': 2,
            'translation_cap_m': .035, 'rotation_cap_rad': .15, 'geometry_work_per_control': 16},
        'caller_owned_checks': ['clock/age once per choose', 'joint margin', 'original CLOSE predicate',
                               'rejected pulse rollback', 'phase timeout', 'five-frame approach readiness',
                               'FIFO contents and actual delayed execution'],
        'cases': cases, 'tests': tests, 'source_sha256': hashes,
        'limitations': ['No performance, rescue, duration, or generalization claim follows from these static tests.',
                       'Direction forecasts are control heuristics, never future geometry or readiness proofs.',
                       'Original mixed certification covers a nominal observed hand/object envelope, not unknown delayed tracking or full-arm safety.',
                       'Central caller checks require the separate components/mechanisms receipts.']
    }
    with output.open('x', encoding='utf8') as f:
        json.dump(finite(result), f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({k: result[k] for k in ['passed', 'saved_observation_proposals',
        'parent_v19_actions_exactly_reconstructed', 'boundary_and_negative_cases', 'max_geometry_work_saved']},
        ensure_ascii=False))


if __name__ == '__main__':
    main()
