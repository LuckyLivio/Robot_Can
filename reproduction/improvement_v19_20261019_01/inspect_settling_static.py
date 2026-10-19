"""Saved-observation and synthetic checks of the v19 integral pause.

No simulator, new physics, future-state rollout, tuning sweep or readiness
mutation. Proposed changes on saved states are not closed-loop outcomes.
"""
from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json
import sys

import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v17_20261019_01.recovery import pose_servo as old
from reproduction.improvement_v18_20261019_01.recovery.recovery_controller import Config
from reproduction.improvement_v19_20261019_01.recovery import settling as new


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value):
    if isinstance(value, dict):
        return {str(k): finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [finite(v) for v in value]
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def snapshot(state):
    return finite(vars(state))


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def replay_observations(jobname):
    folder = ROOT/'reproduction/improvement_v18_20261019_01/smoke_a'/jobname
    result_path, trace_path = folder/'result.json', folder/'trace.jsonl'
    saved = read(result_path)
    assert saved['status'] == 'complete'
    rows = [json.loads(s) for s in trace_path.read_text(encoding='utf8').splitlines()]
    cfg = Config(**saved['job']['config'])
    state = old.ServoState()
    cases = []
    anchor = None
    for row in rows:
        receipt = row['recovery'].get('mixed_pose', {})
        is_held = receipt.get('held') and receipt.get('accepted') and receipt.get('state_update')
        if is_held:
            update = receipt['state_update']
            x = np.asarray(row['state_before'], np.float32)
            kwargs = dict(held=True, grip=receipt['grip_command'],
                          state=state, phase=ast.literal_eval(update['phase']),
                          previous_action=np.asarray(receipt['previous_submitted_action'], np.float32))
            args = (x, np.asarray(update['goal']), np.asarray(update['rotation']),
                    np.r_[receipt['observed_translation_per_step_m'], receipt['observed_rotation_per_step_rad']], cfg)
            before = snapshot(state)
            original_action, original_receipt = old.propose(*args, **kwargs)
            assert finite(original_receipt) == receipt, (jobname, row['step'], 'original receipt')
            np.testing.assert_array_equal(original_action, row['submitted_action'])
            action, proposed = new.propose(*args, **kwargs)
            assert snapshot(state) == before, 'propose mutated memory'
            assert proposed['work'] <= 16
            triggered = 'settling19' in proposed
            if not triggered:
                np.testing.assert_array_equal(action, original_action)
                assert finite(proposed) == finite(original_receipt), 'untriggered receipt differs'
            else:
                axes = np.asarray(proposed['settling19']['integral_brake_axes'], bool)
                assert axes.any() and (np.asarray(proposed['position_bias_m'])[axes] == 0).all()
                assert proposed['held'] and proposed['near_goal_feedback']
                assert proposed['settling19']['control_heuristic_only']
            if proposed['accepted']:
                np.testing.assert_array_equal(action, proposed['submitted_action'])
                assert proposed['box_margin_m'] >= .001 and proposed['can_margin_m'] >= .001
                assert np.linalg.norm(np.asarray(proposed['position_bias_m'])) <= .009+1e-12
                previous = kwargs['previous_action']
                assert np.linalg.norm((action[:3].astype(float)-previous[:3])*.05) <= .035/3+1e-8
                assert np.linalg.norm((action[3:6].astype(float)-previous[3:6])*.5) <= .15/3+1e-8
            cases.append({'job': jobname, 'step': row['step'], 'triggered': triggered,
                          'accepted': proposed['accepted'], 'work': proposed['work'],
                          'old_position_error_m': receipt['position_error_m'],
                          'old_angle_error_rad': receipt['orientation_error_rad'],
                          'old_state_reset_reason': receipt['state_reset_reason'],
                          'old_bias_m': receipt['position_bias_m'],
                          'old_submitted_action': original_action.tolist(),
                          'proposed_action': action.tolist(),
                          'new_bias_m': proposed['position_bias_m'],
                          'new_integral_pause': proposed.get('settling19'),
                          'old_observed_motion_m': receipt['observed_translation_per_step_m'],
                          'old_error_m': (args[1]-x[:3]).tolist(),
                          'old_fifo_before': row['queue_before']})
            if jobname == 'v18_regression_6000005' and row['step'] == 388:
                anchor = (copy.deepcopy(args), copy.deepcopy(kwargs))
        if receipt.get('accepted') and receipt.get('state_update'):
            assert state.commit(np.asarray(row['submitted_action'], np.float32), receipt)
        else:
            state.reset()
    return cases, anchor, [result_path, trace_path]


def synthetic_checks(anchor):
    args, kwargs = copy.deepcopy(anchor)
    x, _, rotation, _, cfg = args
    # Move the rigid held pair into a clear high region, retaining their relative pose.
    shift = np.array([-.3, -.4, .5])
    x[:3] += shift
    x[16:19] += shift
    rotation = Rotation.from_quat(x[3:7]).as_matrix()
    error = np.array([-.004, .003, .020])
    goal = x[:3].astype(float)+error
    motion = np.array([-.003, -.001, .001, 0., 0., 0.])
    phase = ('synthetic', 'CARRY_transport')
    state = old.ServoState()
    update = {'phase': repr(phase), 'held': True, 'goal': goal.tolist(),
              'rotation': rotation.tolist(), 'bias': [-.005, .002, .002]}
    assert state.commit(np.zeros(7, np.float32), {'accepted': True,
                        'submitted_action': [0.]*7, 'state_update': update})
    base_args = (x, goal, rotation, motion, cfg)
    base_kwargs = dict(held=True, grip=1., state=state, phase=phase,
                       previous_action=np.zeros(7, np.float32))
    checks = []

    def check(name, aa=None, kk=None, expected_axes=None, exact=False, reject=False, reset=None):
        a = copy.deepcopy(base_args if aa is None else aa)
        k = copy.deepcopy(base_kwargs if kk is None else kk)
        before = snapshot(k['state']) if k.get('state') else None
        action, receipt = new.propose(*a, **k)
        assert (snapshot(k['state']) if k.get('state') else None) == before
        assert receipt['work'] <= 16
        if expected_axes is not None:
            assert receipt['settling19']['integral_brake_axes'] == expected_axes
            assert np.asarray(receipt['position_bias_m'])[np.asarray(expected_axes)].tolist() == [0.]*sum(expected_axes)
        if exact:
            old_action, old_receipt = old.propose(*a, **k)
            np.testing.assert_array_equal(action, old_action)
            assert finite(receipt) == finite(old_receipt)
        if reset is not None:
            assert receipt['state_reset_reason'] == reset
            fresh_kwargs = {**k, 'state': old.ServoState()}
            fresh_action, fresh_receipt = new.propose(*a, **fresh_kwargs)
            np.testing.assert_array_equal(action, fresh_action)
            assert receipt['position_bias_m'] == fresh_receipt['position_bias_m']
        if reject:
            assert not receipt['accepted']
            assert not k['state'].commit(action, receipt)
            assert k['state'].goal is None and np.array_equal(k['state'].bias, np.zeros(3))
        elif receipt['accepted']:
            actual = copy.deepcopy(k['state']) if k.get('state') else old.ServoState()
            assert actual.commit(action, receipt)
            replaced = action.copy(); replaced[0] += np.float32(.001)
            assert not actual.commit(replaced, receipt)
            assert actual.goal is None
        checks.append({'name': name, 'passed': True, 'accepted': receipt['accepted'],
                       'work': receipt['work'], 'reason': receipt['reason'],
                       'reset': receipt.get('state_reset_reason'),
                       'integral_pause': receipt.get('settling19')})

    check('approaching_negative_x_crosses_d2_only_x_paused', expected_axes=[True, False, False])
    positive = list(base_args); positive[1] = x[:3]+np.array([.004, .003, .020]); positive[3] = np.array([.003, -.001, .001, 0., 0., 0.])
    check('positive_x_symmetric_crossing', positive, expected_axes=[True, False, False])
    no_cross = list(base_args); no_cross[3] = np.array([-.001, -.001, .001, 0., 0., 0.])
    check('approaching_without_crossing_exact_v17', no_cross, exact=True)
    away = list(base_args); away[3] = np.array([.003, -.001, .001, 0., 0., 0.])
    check('moving_away_exact_v17', away, exact=True)
    far = list(base_args); far[1] = x[:3]+np.array([-.061, 0., 0.]); far[3] = np.array([-.04, 0., 0., 0., 0., 0.])
    check('outside_original_60mm_near_region_exact_v17', far, exact=True)
    check('no_memory_exact_v17', kk={**base_kwargs, 'state': None}, exact=True)
    check('empty_hand_exact_v17', kk={**base_kwargs, 'held': False, 'grip': 0.}, exact=True)
    check('phase_reset', kk={**base_kwargs, 'phase': ('new', 'PLACE')}, expected_axes=[True, False, False], reset='phase_or_held_state_changed')
    changed_goal = list(base_args); changed_goal[1] = goal+np.array([0., .001, 0.])
    check('exact_goal_change_resets_bias', changed_goal, reset='target_changed')
    changed_rotation = list(base_args); changed_rotation[2] = Rotation.from_rotvec([0., 0., .001]).as_matrix()@rotation
    check('exact_rotation_change_resets_bias', changed_rotation, reset='target_changed')
    check('uncertified_interrupt_resets_bias', kk={**base_kwargs, 'previous_action': np.array([.02, 0., 0., 0., 0., 0., 0.], np.float32)}, reset='interrupted_by_uncertified_command')
    invalid = list(base_args); invalid[0] = x.copy(); invalid[0][0] = np.nan
    check('nonfinite_rejected_and_commit_clears_state', invalid, reject=True)
    invalid_motion = list(base_args); invalid_motion[3] = motion.copy(); invalid_motion[3][0] = np.inf
    check('nonfinite_motion_rejected', invalid_motion, reject=True)
    invalid_q = list(base_args); invalid_q[0] = x.copy(); invalid_q[0][3:7] = 0.
    check('invalid_observed_quaternion_rejected', invalid_q, reject=True)
    check('held_opening_rejected', kk={**base_kwargs, 'grip': -1.}, reject=True)
    collision = list(base_args); collision[0] = x.copy()
    shift = np.array([.1975, .4025, .8])-collision[0][:3]
    collision[0][:3] += shift; collision[0][16:19] += shift
    collision[1] = collision[0][:3]+error
    check('unsafe_geometry_rejected_no_bias_commit', collision, reject=True)
    return checks


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--name', default='settling_static_a'); args = parser.parse_args()
    target = RUN/'analysis'/(args.name+'.json'); assert not target.exists()
    cases = []; sources = [Path(__file__), RUN/'recovery/settling.py',
                           ROOT/'reproduction/improvement_v17_20261019_01/recovery/pose_servo.py',
                           ROOT/'reproduction/improvement_v18_20261019_01/recovery/recovery_controller.py',
                           ROOT/'reproduction/improvement_v9_20261015_01/recovery/geometry.py',
                           ROOT/'reproduction/improvement_v11_20261015_01/recovery/object_clearance.py',
                           ROOT/'reproduction/improvement_v15_20261016_01/recovery/carry_path.py']
    anchor = None
    for name in ['v18_regression_6000005', 'v17_known_full_s23_clean_demo_12000036', 'v18_held_wait_demo87']:
        observed, found, paths = replay_observations(name)
        cases.extend(observed); sources.extend(paths)
        anchor = found or anchor
    assert anchor is not None
    checks = synthetic_checks(anchor)
    primary = [c for c in cases if c['job'] == 'v18_regression_6000005']
    at388 = next(c for c in primary if c['step'] == 388)
    error = np.asarray(at388['old_error_m']); motion = np.asarray(at388['old_observed_motion_m'])
    diagnosis = {'target_and_rotation_changed_during_41_carry_controls': False,
                 'reset_reasons': {str(reason): sum(c['old_state_reset_reason']==reason for c in primary)
                                   for reason in set(c['old_state_reset_reason'] for c in primary)},
                 'observed_388_error_m': error.tolist(),
                 'observed_388_motion_m': motion.tolist(),
                 'old_388_pd_before_bias_m': (.5*error-1.5*motion).tolist(),
                 'old_388_bias_m': at388['old_bias_m'],
                 'old_388_fifo_before': at388['old_fifo_before'],
                 'interpretation': 'The stored biased command still advances past a target coordinate where the unchanged PD term would already brake. The pause is a local anti-windup hypothesis, not evidence of improved closed-loop arrival.'}
    output = {'passed': True, 'scope': 'Static mathematical/geometry tests and original saved-observation proposals only. No simulator, future-state rollout, controller clock/counter mutation or new closed-loop outcome.',
              'new_physical_episodes': 0, 'new_evaluation_samples': 0,
              'saved_observation_proposals': len(cases), 'unique_saved_start_identities': 3,
              'untriggered_exact_action_and_receipt_equivalence': sum(not c['triggered'] for c in cases),
              'triggered_proposals': sum(c['triggered'] for c in cases),
              'maximum_geometry_work_per_proposal': max([c['work'] for c in cases]+[c['work'] for c in checks]),
              'checks': checks, 'cases': cases, 'diagnosis': diagnosis,
              'preserved_thresholds': {'max_translation_m': .035, 'max_rotation_rad': .15, 'delay': 2,
                 'bias_limit_m': .009, 'hand_box_margin_m': .001, 'held_can_box_margin_m': .001,
                 'arrival_position_m': .009, 'arrival_angle_rad': .08, 'consecutive_arrival_frames': 5,
                 'held_phase_timeout': 70, 'episode_steps': 400},
              'limitations': ['The nominal two-observation crossing indication is not a future-motion or geometry certificate.',
                 'A new action evaluated at an old saved state does not predict the trajectory after that action.',
                 'Only the caller may count original arrival conditions or mutate stage/queue/clock; the helper has no such inputs.',
                 'Rejected or replaced actions must reset memory; committed bias is allowed only for the exact accepted action.'],
              'source_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in sources}}
    with target.open('x', encoding='utf8') as stream: json.dump(finite(output), stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({k:output[k] for k in ['passed','saved_observation_proposals','triggered_proposals','untriggered_exact_action_and_receipt_equivalence','maximum_geometry_work_per_proposal']}))


if __name__ == '__main__':
    main()
