"""Bounded static positive/negative checks; no simulator or new task episode."""
from pathlib import Path
import hashlib
import json
import sys
import time
import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import Config
from reproduction.improvement_v16_20261016_01.recovery.pose_servo import (
    propose, mixed_certificate, observed_motion, arc_displacement_bound,
    _hand_box_translation_envelope, _rotation_grid,
)
from reproduction.improvement_v15_20261016_01.recovery.carry_path import HeldEnvelope
from reproduction.improvement_v9_20261015_01.recovery.geometry import LOCAL
from reproduction.improvement_v8_20261015_01.recovery.geometry import BOXES, CAN
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def load_trace(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def dense_product_check(x, action, held, receipt):
    """Finite 9x9 cross-product sanity check, additional to the analytic bound."""
    rotation = Rotation.from_quat(x[3:7]).as_matrix()
    delta, turn = action[:3].astype(float)*.05, action[3:6].astype(float)*.5
    gap = min(.085, abs(float(x[7]-x[8]))+.002)
    gaps = [max(0., abs(float(x[7]-x[8]))-.002), gap]
    envelope = HeldEnvelope.from_state(x) if held else None
    minimum_hand, minimum_second = float('inf'), float('inf')
    for t in np.linspace(0., 1., 9):
        pose = Rotation.from_rotvec(turn*t).as_matrix() @ rotation
        for s in np.linspace(0., 1., 9):
            position = x[:3]+delta*s
            hand = _hand_box_translation_envelope(position, position, pose, gap)
            second = envelope.sweep_margin(position, position, pose) if held else object_margin(position, position, pose, gaps, x)
            minimum_hand, minimum_second = min(minimum_hand, hand), min(minimum_second, second)
            assert hand >= .001 and second >= receipt['required_can_margin_m']
    return {'evaluated_poses': 81, 'hand_box_minimum_m': minimum_hand,
            'second_shape_minimum_m': minimum_second,
            'scope': 'Finite sanity check only; the radius/arc deduction supplies coverage between samples.'}


def main():
    prior = ROOT/'reproduction/improvement_v15_20261016_01'
    carry_diagnosis_path = prior/'analysis/smoke_a_carry_rotation_diagnosis.json'
    edge_diagnosis_path = prior/'analysis/segmented_edge_static.json'
    carry_trace_path = prior/'smoke_a/carry_known13_bc_k2_noise005_demo_13000021/trace.jsonl'
    edge_trace_path = prior/'smoke_a/edge_known13_full_s41_noise005_demo_13000022/trace.jsonl'
    carry = read(carry_diagnosis_path)
    edge = read(edge_diagnosis_path)['cases'][0]['chosen']
    carry_rows, edge_rows = load_trace(carry_trace_path), load_trace(edge_trace_path)
    cfg = Config()
    output = {'passed': True, 'new_physical_episodes': 0, 'new_evaluation_samples': 0,
              'scope': 'Static geometry, analytical arc bound, numerical product-grid checks and saved-observation proposals. Not controller replay, dynamic stability proof or performance evaluation.',
              'source_sha256': {path.relative_to(ROOT).as_posix(): sha(path) for path in
                  [Path(__file__), RUN/'recovery/pose_servo.py', carry_diagnosis_path, edge_diagnosis_path, carry_trace_path, edge_trace_path]},
              'positive_saved_observations': [], 'negative_checks': [], 'mathematical_checks': [],
              'fixed_thresholds': {'hand_box_m': .001, 'held_can_box_m': .001, 'empty_execution_can_m': .001,
                                   'empty_planning_can_m': .003, 'max_translation_m': .035, 'max_rotation_rad': .15,
                                   'delay': 2, 'max_work_units': 16},
              'caller_guards_required': ['joint margin', 'stable held transform', 'object pose', 'aperture',
                                         '9mm / .08rad for five consecutive frames', '70-step phase timeout', '400-step total', 'D2 FIFO retained']}
    timings = []
    for held, rows, steps, goal, rotation in [
        (True, carry_rows, [327,332,345,380,396], carry['reconstructed_stage_goal'], carry['reconstructed_target_rotation']),
        (False, edge_rows, [181,220,238,242,250], edge['pre_goal'], edge['rotation']),
    ]:
        for index, step in enumerate(steps):
            x = np.array(rows[step-1]['state_before'])
            motion = observed_motion(x, rows[step-2]['state_before'])
            tick = time.perf_counter()
            action, receipt = propose(x, goal, rotation, motion, cfg, held=held, grip=1. if held else 0.)
            timings.append(1000*(time.perf_counter()-tick))
            assert receipt['accepted'] and receipt['kind']=='mixed_pose'
            assert receipt['work'] == receipt['work_units'] <= 16
            assert np.linalg.norm(action[:3].astype(float)*.05) <= .035
            assert np.linalg.norm(action[3:6].astype(float)*.5) <= .15
            assert np.linalg.norm(action[:3]) > 0 and np.linalg.norm(action[3:6]) > 0
            selected = next(trial for trial in receipt['trials'] if trial['accepted'])
            np.testing.assert_allclose(np.asarray(receipt['translation_m']), action[:3].astype(float)*.05, atol=0, rtol=0)
            np.testing.assert_allclose(np.asarray(receipt['rotation_vector_rad']), action[3:6].astype(float)*.5, atol=0, rtol=0)
            entry = {'family': 'held_carry' if held else 'empty_edge', 'source_step': step,
                     'goal_source': 'Saved v15 carry-stage reconstruction' if held else 'Previously saved v13 static pretranslation waypoint; static goal fixture, not an exact v15 replay claim',
                     'action': action.tolist(), 'receipt': receipt}
            if index == 0:
                entry['dense_product_check'] = dense_product_check(x, action, held, receipt)
            if not held:
                planning = mixed_certificate(x, action[:3].astype(float)*.05, action[3:6].astype(float)*.5,
                                             can_margin_m=.003)
                assert planning['accepted'] and planning['required_can_margin_m']==.003
                entry['planning_threshold_check'] = planning
            output['positive_saved_observations'].append(entry)

    # Analytic nearest-rotation-sample displacement bound, with arbitrary local
    # vertex positions and independent translation (which cancels in distance).
    rng = np.random.default_rng(160016)
    points = rng.normal(size=(64, 3)); points *= .23/np.linalg.norm(points, axis=1).max()
    vector = np.array([.06, -.08, .11]); vector *= .15/np.linalg.norm(vector)
    initial = Rotation.from_euler('xyz', [.2, -.4, .7]).as_matrix()
    grid, angle, intervals = _rotation_grid(initial, vector)
    bound = arc_displacement_bound(float(np.linalg.norm(points, axis=1).max()), angle, intervals)
    observed_max = 0.
    for fraction in np.linspace(0., 1., 1001):
        nearest = int(round(fraction*intervals))
        actual = Rotation.from_rotvec(vector*fraction).as_matrix() @ initial
        distance = np.linalg.norm(points @ actual.T-points @ grid[nearest].T, axis=1).max()
        observed_max = max(observed_max, float(distance))
        assert distance <= bound+1e-12
    output['mathematical_checks'].append({'check': 'nearest_rotation_sample_radius_bound', 'passed': True,
                                          'vertices': 64, 'fractions': 1001, 'analytic_bound_m': bound,
                                          'largest_observed_distance_m': observed_max})

    x = np.array(edge_rows[180]['state_before'])
    rotation = Rotation.from_quat(x[3:7]).as_matrix()
    # At the goal but moving, the controller must brake rather than stop issuing
    # position corrections and assume the queued/noisy physical motion stopped.
    motion = np.array([.001, -.002, .001, .005, -.002, .001])
    action, receipt = propose(x, x[:3], rotation, motion, cfg)
    assert receipt['accepted'] and np.dot(action[:3], motion[:3]) < 0 and np.dot(action[3:6], motion[3:]) < 0
    output['mathematical_checks'].append({'check': 'd2_observed_velocity_brakes_at_goal', 'passed': True,
                                          'action': action.tolist(), 'work': receipt['work']})
    far_goal = x[:3]+1000
    far_rotation = Rotation.from_rotvec([3.1, 0., 0.]).as_matrix() @ rotation
    capped, cap_receipt = propose(x, far_goal, far_rotation, np.zeros(6), cfg)
    assert cap_receipt['accepted'] and np.linalg.norm(capped[:3].astype(float)*.05) <= .035
    assert np.linalg.norm(capped[3:6].astype(float)*.5) <= .15
    output['mathematical_checks'].append({'check': 'unchanged_caps_after_float32_quantization', 'passed': True,
                                          'action': capped.tolist(), 'work': cap_receipt['work']})

    # Hand/box collision: align the hand-hull centroid with an actual fixed box.
    collision = x.copy()
    hand_center = LOCAL[0][1].mean(0) @ rotation.T+x[:3]
    shift = BOXES[0][0]-hand_center
    collision[:3] += shift; collision[16:19] += shift
    bad = mixed_certificate(collision, [.005,0,0], [0,.1,0])
    assert not bad['accepted'] and bad['box_margin_m'] < .001
    output['negative_checks'].append({'check': 'hand_box_overlap_rejected', 'passed': True, 'receipt': bad})

    # Empty hand/can collision, while the unchanged hand is far from all boxes.
    collision = x.copy()
    can_rotation = Rotation.from_quat(x[19:23]).as_matrix()
    collision[16:19] = hand_center-CAN.mean(0) @ can_rotation.T
    bad = mixed_certificate(collision, [.005,0,0], [0,.1,0])
    assert not bad['accepted'] and bad['can_margin_m'] < .001 and bad['box_margin_m'] >= .001
    output['negative_checks'].append({'check': 'empty_hand_can_overlap_rejected', 'passed': True, 'receipt': bad})
    blocked_action, blocked = propose(collision, collision[:3]+[.02,0,0], far_rotation, np.zeros(6), cfg)
    assert not blocked['accepted'] and np.array_equal(blocked_action[:6], np.zeros(6))
    assert blocked['work'] <= 16 and len(blocked['trials'])==3
    output['negative_checks'].append({'check': 'all_scaled_steps_rejected_zero_pose_fallback', 'passed': True, 'receipt': blocked})

    # Adversarial held-object geometry isolates carried-can/box checking. This
    # is synthetic and makes no claim about a physically stable grasp.
    collision = x.copy()
    collision[16:19] = BOXES[0][0]-CAN.mean(0) @ can_rotation.T
    bad = mixed_certificate(collision, [.005,0,0], [0,.1,0], held=True)
    assert not bad['accepted'] and bad['can_margin_m'] < .001 and bad['box_margin_m'] >= .001
    output['negative_checks'].append({'check': 'held_can_box_overlap_rejected_even_when_hand_clear', 'passed': True, 'receipt': bad})

    for label, translation, turn in [('translation_cap', [.036,0,0], [0,0,0]),
                                      ('rotation_cap', [0,0,0], [.151,0,0])]:
        rejected = mixed_certificate(x, translation, turn)
        assert not rejected['accepted'] and rejected['work']==0
        output['negative_checks'].append({'check': label+'_rejected_before_geometry', 'passed': True, 'reason': rejected['reason']})
    insufficient = mixed_certificate(x, [.005,0,0], [0,.15,0], work_limit=5)
    assert not insufficient['accepted'] and insufficient['work']==0
    output['negative_checks'].append({'check': 'insufficient_geometry_budget_rejected', 'passed': True, 'receipt': insufficient})
    invalid = x.copy(); invalid[0] = np.nan
    action, receipt = propose(invalid, x[:3], rotation, np.zeros(6), cfg, held=True, grip=1.)
    assert not receipt['accepted'] and np.array_equal(action, [0,0,0,0,0,0,1])
    output['negative_checks'].append({'check': 'nonfinite_observation_rejected_preserves_hold', 'passed': True})
    try:
        mixed_certificate(x, np.zeros(3), np.zeros(3), can_margin_m=.0005)
        raise AssertionError('Loosened clearance was not rejected')
    except ValueError:
        output['negative_checks'].append({'check': 'loosened_margin_rejected', 'passed': True})
    output['measured_static_proposal_ms'] = {'count': len(timings), 'median': float(np.median(timings)), 'maximum': max(timings),
                                             'scope': 'Local offline helper timings only, not simulator controller latency.'}
    output['maximum_observed_work'] = max([item['receipt']['work'] for item in output['positive_saved_observations']]+[blocked['work']])
    output['limitations'] = ['No physics run and no claim of recovered task success.',
                             'Static SAT rejection means unconfirmed, not proof of collision.',
                             'Observed velocity prediction is not a guarantee of D2 queue dynamics.',
                             'Rigid held-object hull does not certify grasp force or full-arm collision safety.']
    (RUN/'analysis').mkdir(exist_ok=True)
    destination = RUN/'analysis/pose_servo_static.json'
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'saved_observation_proposals': len(output['positive_saved_observations']),
                      'negative_checks': len(output['negative_checks']), 'maximum_work': output['maximum_observed_work'],
                      'proposal_ms': output['measured_static_proposal_ms'], 'new_physical_episodes': 0}, ensure_ascii=False))


if __name__=='__main__':
    main()
