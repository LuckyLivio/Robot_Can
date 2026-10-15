"""Replay frozen smoke_b controller inputs; explain residual path failures.

This script does not step a simulator, load a policy, or tune a controller.
All motion values come from existing saved observations. Action equality checks
establish that the reconstructed controller state explains those trajectories.
"""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import sys

import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import RecoveryController as V13, Config as C13
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_module():
    path = RUN / 'smoke_b/source/recovery/recovery_controller.py'
    spec = importlib.util.spec_from_file_location('v14_smoke_b_path_diagnosis', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, path


def reconstruct(directory, module):
    result_path = directory / 'result.json'
    trace_path = directory / 'trace.jsonl'
    result = json.loads(result_path.read_text(encoding='utf-8'))
    assert result['status'] == 'complete' and len(result['records']) == 1
    job = result['job']
    record = result['records'][0]
    cls, cfg = (V13, C13) if job['version'] == 'v13' else (module.RecoveryController, module.Config)
    controller = None
    previous = np.zeros(7, np.float32)
    previous_state = None
    observations = []
    max_action_error = 0.0
    with trace_path.open(encoding='utf-8') as stream:
        for row in map(json.loads, stream):
            assert row['demo'] == record['demo']
            x = np.asarray(row['state_before'], np.float32)
            q = np.asarray(row['joint_positions'], float)
            if controller is None:
                controller = cls([.1975, .4025, .8], .8, x, True, cfg(**job['config']))
            controller.set_joint_positions(q)
            phase = controller.mode
            margin = np.minimum(q - LIMITS[:, 0], LIMITS[:, 1] - q)
            rotation = Rotation.from_quat(x[3:7]).as_matrix()
            target_rotation = controller.goal_rotation
            goal = None
            if controller.edge_plan is not None and phase in ['EDGE_ROTATE', 'EDGE_APPROACH']:
                target_rotation = controller.edge_plan['rotation']
                goal = controller.edge_start if phase == 'EDGE_ROTATE' else controller.edge_plan['above']
            elif phase == 'DESCEND':
                goal = controller.grasp_target(x)
            elif phase == 'CARRY' and controller.held_offset is not None:
                goal = np.r_[controller.target[:2], controller.floor + controller.cfg.carry_clearance_m] + controller.held_offset
            angular = float(np.linalg.norm(Rotation.from_matrix(target_rotation @ rotation.T).as_rotvec()))
            item = {
                'job': job['id'], 'version': job['version'], 'demo': row['demo'],
                'step': int(row['step']), 'phase_before': phase,
                'phase_age_before': int(controller.age), 'attempt': int(controller.attempts),
                'eef_x_m': float(x[0]), 'eef_y_m': float(x[1]), 'eef_z_m': float(x[2]),
                'object_x_m': float(x[16]), 'object_y_m': float(x[17]), 'object_z_m': float(x[18]),
                'gap_m': abs(float(x[7] - x[8])),
                'goal_position_error_m': None if goal is None else float(np.linalg.norm(goal - x[:3])),
                'goal_orientation_error_rad': angular,
                'object_to_bin_xy_m': float(np.linalg.norm(x[16:18] - controller.target[:2])),
                'min_joint_margin_rad': float(margin.min()),
                'limiting_joint_1based': int(margin.argmin() + 1),
                'observed_translation_per_step_m': None if previous_state is None else float(np.linalg.norm(x[:3] - previous_state[:3])),
                'latched_hold_before': bool(controller.stable),
                'lost_frames_before': int(controller.lost_frames),
                'remaining_descent_can_margin_m': None,
            }
            if controller.edge_plan is not None and phase == 'DESCEND':
                gap = item['gap_m']
                item['remaining_descent_can_margin_m'] = object_margin(
                    x[:3], controller.grasp_target(x), rotation, [gap-.001, gap+.001], x)
            action, diagnostic = controller.choose(
                x, np.asarray(row['original_proposal'], np.float32), previous)
            error = float(np.max(np.abs(action - np.asarray(row['submitted_action']))))
            max_action_error = max(max_action_error, error)
            np.testing.assert_allclose(action, row['submitted_action'], rtol=0, atol=1e-7)
            assert controller.clock == row['step'] <= 400
            item['phase_after'] = controller.mode
            item['submitted_translation_norm_m'] = float(np.linalg.norm(action[:3]) * .05)
            item['submitted_rotation_norm_rad'] = float(np.linalg.norm(action[3:6]) * .5)
            observations.append(item)
            previous = np.asarray(row['executed_action'], np.float32)
            previous_state = x.copy()
            last_row = row
    assert len(observations) == record['steps']
    assert controller.events == record['events']
    phases = {}
    for phase in sorted(set(item['phase_before'] for item in observations)):
        selected = [item for item in observations if item['phase_before'] == phase]
        position = [item for item in selected if item['goal_position_error_m'] is not None]
        phases[phase] = {
            'steps': len(selected), 'first_step': selected[0]['step'], 'last_step': selected[-1]['step'],
            'minimum_joint_margin_rad': min(item['min_joint_margin_rad'] for item in selected),
            'maximum_orientation_error_rad': max(item['goal_orientation_error_rad'] for item in selected),
            'best_position_sample': None if not position else min(position, key=lambda item: item['goal_position_error_m']),
            'last_sample': selected[-1],
        }
    chosen_steps = {206, 218, 219, 220, 221, 222, 223, 230, 231, 250, 256, 258, 260, 269,
                    270, 277, 284, 288, 289, 294, 306, 311, 312, 322, 340, 346, 347,
                    350, 358, 360, 370, 380, 390, 392, 400}
    summary = {
        'job': job['id'], 'version': job['version'], 'demo': record['demo'],
        'success': record['success'], 'steps': record['steps'],
        'verified_regrasps': record['verified_regrasps'],
        'stable_hold_observed': record['stable_hold_observed'],
        'events': record['events'], 'tracking_events': record.get('tracking14_events', []),
        'clearance_events': record.get('clearance14_events', []),
        'phases': phases, 'selected_samples': [item for item in observations if item['step'] in chosen_steps],
        'terminal_observation': last_row['state_after'], 'terminal_controller_mode': controller.mode,
        'terminal_success': last_row['success_after'], 'max_submitted_action_error': max_action_error,
        'source_files': {
            str(path.relative_to(ROOT)).replace('\\', '/'): digest(path)
            for path in [result_path, trace_path]
        },
    }
    return summary, observations


def main():
    module, source = frozen_module()
    suffixes = ['known13_bc_k2_noise005_demo_13000021', 'known13_full_s41_noise005_demo_13000022']
    cases = [version + '_' + suffix for suffix in suffixes for version in ['v13', 'track', 'v14']]
    cases += ['v13_regression_6000005', 'clearance_regression_6000005']
    summaries = []
    observations = []
    for case in cases:
        summary, rows = reconstruct(RUN / 'smoke_b' / case, module)
        summaries.append(summary)
        observations.extend(rows)
    report = {
        'passed': True,
        'validation_scope': 'Exact saved-input controller replay and saved observation analysis; no new physics episodes.',
        'source_controller': str(source.relative_to(ROOT)).replace('\\', '/'),
        'source_controller_sha256': digest(source),
        'cases': len(summaries), 'replayed_steps': len(observations),
        'notes': [
            'BC leaning target: smoke_b tracking reaches DESCEND at258, verified LIFT at294 and CARRY at311. The remaining failure is held-object transport, not approach or grasp confirmation.',
            'BC target retains stable holding through the final CARRY sample. Joint4 approaches its limit during transit; position and orientation tracking errors remain. No loss of grasp is observed in this final carry phase.',
            'Full41 wall target: first EDGE_ROTATE still times out at231; later joint-aware path search/replanning consumes budget. It approaches the waypoint near400 but does not descend in the allotted budget.',
            'Old6000005 clearance-only regression: checked recenter settles, then grasp, lift and transport occur. RELEASE starts at392 and the400-step deadline arrives before success. This is an added recovery-time cost, not a permitted budget extension.',
            'Negative joint margins or geometric certificates describe the stored execution/proxy only; this report is not a full-arm collision or stability certificate.',
        ],
        'comparisons': summaries,
    }
    output = RUN / 'analysis/path_diagnosis.json'
    csv_path = RUN / 'analysis/path_diagnosis_observations.csv'
    output.parent.mkdir(exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    with csv_path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(observations[0]))
        writer.writeheader()
        writer.writerows(observations)
    print(json.dumps({'passed': True, 'cases': len(summaries), 'replayed_steps': len(observations),
                      'report': str(output), 'observations': str(csv_path)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
