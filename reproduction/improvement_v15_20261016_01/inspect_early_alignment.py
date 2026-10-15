"""Saved-input budget diagnosis for moving clearance checks into approach.

No controller is changed and no physical episode is executed. Extrapolated
positions are explicit observation-only D2 heuristics, not simulated outcomes.
"""
from pathlib import Path
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
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin
from reproduction.improvement_v11_20261015_01.recovery.path_search import sweep_margin
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK


def replay(name, frozen):
    directory = ROOT / 'reproduction/improvement_v14_20261016_01/smoke_b' / name
    result = json.loads((directory / 'result.json').read_text(encoding='utf-8'))
    assert result['status'] == 'complete'
    job = result['job']
    record = result['records'][0]
    controller = None
    previous = np.zeros(7, np.float32)
    last = None
    measurements = []
    actual_recenter_steps = []
    replayed = 0
    for row in map(json.loads, (directory / 'trace.jsonl').open(encoding='utf-8')):
        x = np.asarray(row['state_before'], np.float32)
        if controller is None:
            cls, cfg = (V13, C13) if job['version'] == 'v13' else (frozen.RecoveryController, frozen.Config)
            controller = cls([.1975, .4025, .8], .8, x, True, cfg(**job['config']))
        controller.set_joint_positions(row['joint_positions'])
        phase = controller.mode
        if controller.edge_plan is not None and phase in ['EDGE_APPROACH', 'DESCEND']:
            rotation = Rotation.from_quat(x[3:7]).as_matrix()
            plan = controller.edge_plan
            goal = controller.grasp_target(x)
            above = plan['above']
            axis = plan['rotation'][:, 2]
            relative = x[:3] - goal
            side = relative - axis * np.dot(relative, axis)
            motion = np.zeros(3) if last is None else x[:3] - last[:3]
            predicted = x[:3] + controller.cfg.delay * motion
            forecast_side = side + controller.cfg.delay * (motion - axis * np.dot(motion, axis))
            gap = abs(float(x[7] - x[8]))
            live = object_margin(x[:3], goal, rotation, [gap-.001, gap+.001], x)
            angle = float(np.linalg.norm(Rotation.from_matrix(plan['rotation'] @ rotation.T).as_rotvec()))
            position = float(np.linalg.norm(x[:3] - above))
            predicted_position = float(np.linalg.norm(predicted - above))
            existing = position < .009 and angle < .08 and controller.gap_ready(x)
            sample = {
                'step': row['step'], 'phase': phase, 'phase_age': controller.age,
                'edge_settled_before': controller.edge_settled,
                'position_to_above_m': position, 'orientation_error_rad': angle,
                'side_error_m': float(np.linalg.norm(side)),
                'closure_axis_error_m': float(relative @ plan['rotation'][:, 1]),
                'observed_motion_m_per_step': motion.tolist(),
                'predicted_position_to_above_m': predicted_position,
                'predicted_side_error_m': float(np.linalg.norm(forecast_side)),
                'remaining_descent_can_margin_m': live,
                'aperture_ready': bool(controller.gap_ready(x)),
                'existing_settle_pass': bool(existing),
                'existing_plus_3mm_descent_pass': bool(existing and live >= .003),
                'plus_d2_position_pass': bool(existing and live >= .003 and predicted_position < .009),
            }
            if phase == 'EDGE_APPROACH' and 277 <= row['step'] <= 284:
                # Static correction feasibility at current depth, without
                # claiming that executing it would follow this saved future.
                center = x[:3] - side
                solver = IK(controller.joints, center, rotation, controller.cfg.ik_iterations_per_target)
                solver.advance(controller.cfg.ik_iterations_per_target)
                sample['same_depth_center_check'] = {
                    'goal': center.tolist(),
                    'box_margin_m': sweep_margin(x[:3], center, rotation, min(.085, gap+.002)),
                    'can_margin_m': object_margin(x[:3], center, rotation, [gap-.002, gap+.002], x),
                    'tail_can_margin_m': object_margin(center, goal, rotation, [gap-.001, gap+.001], x),
                    'ik': solver.receipt(),
                }
            measurements.append(sample)
        action, _ = controller.choose(x, np.asarray(row['original_proposal'], np.float32), previous)
        np.testing.assert_allclose(action, row['submitted_action'], rtol=0, atol=1e-7)
        assert controller.clock == row['step'] <= 400
        if row['recovery'].get('planning_kind') == 'v14_recenter' or row['recovery']['mode'] == 'PATH_RECENTER':
            actual_recenter_steps.append(row['step'])
        previous = np.asarray(row['executed_action'], np.float32)
        last = x.copy()
        replayed += 1
    assert controller.events == record['events']
    window = [sample for sample in measurements if 280 <= sample['step'] <= 284]
    assert len(window) == 5 and all(sample['existing_plus_3mm_descent_pass'] for sample in window)
    return {
        'source_job': name, 'success': record['success'], 'replayed_steps': replayed,
        'events': record['events'], 'phases': record['phases'],
        'recenter_control_steps': actual_recenter_steps,
        'settle_window_280_284': window,
        'descent_minimum_can_margin_m': min(sample['remaining_descent_can_margin_m'] for sample in measurements if sample['phase'] == 'DESCEND'),
        'measurements': measurements,
        'close_config_steps': controller.cfg.close_steps, 'delay_steps': controller.cfg.delay,
        'source_sha256': {str(path.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in [directory/'trace.jsonl', directory/'result.json']},
    }


def main():
    source = ROOT / 'reproduction/improvement_v14_20261016_01/smoke_b/source/recovery/recovery_controller.py'
    spec = importlib.util.spec_from_file_location('frozen_v14_budget_static', source)
    frozen = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = frozen
    spec.loader.exec_module(frozen)
    cases = [replay(name, frozen) for name in ['v13_regression_6000005', 'clearance_regression_6000005']]
    report = {
        'passed': True, 'validation_scope': 'Exact saved-input replay and offline geometry/IK checks; no new physical episodes.',
        'frozen_controller_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'replayed_steps': sum(case['replayed_steps'] for case in cases),
        'cases': cases,
        'findings': [
            'All five original approach-settling frames280..284 already satisfy position<9mm, angle<.08rad, stable aperture and descent margin>=3mm. Adding only the3mm test would not change this transition.',
            'The closure-axis error moves from-3.007mm to+7.034mm during those five frames; motion has not settled. The observation-based D2 forecast leaves the9mm waypoint ball in the final two frames.',
            'The original v13 descent remains above3mm throughout (minimum3.242mm) and succeeds at380. The v14C4mm early-warning trigger causes a checked but unnecessary-for-this-record recenter; this does not authorize lowering protection thresholds.',
            'The recenter occupies18 actual control calls289..306, including one planning call. CLOSE is24steps later and RELEASE22steps later than v13; the physical timing cost is larger than the recenter call count alone.',
            'A minimal prospective change is to brake near the approach endpoint and accumulate one shared5-frame confirmation requiring all original checks,3mm descent margin,and a D2 motion forecast still inside the same9mm ball. Reset that shared count if any requirement fails; never reuse nonconforming history.',
            'Reuse only the shared approach-settling counter, never a permanent clearance exemption. If the4mm early warning or1mm hard descent guard later triggers, continue to handle it; a changed pose invalidates the previous evidence. Earlier braking may prevent that second cycle but cannot be assumed to do so.',
            'No saved trace establishes the success or step saving of the proposed control change. It requires the planned small closed-loop comparison. Keep close configuration16plusD2, existing release duration16, and total400 unchanged.',
        ],
    }
    output = RUN / 'analysis/budget_early_static.json'
    output.parent.mkdir(exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({'passed': True, 'replayed_steps': report['replayed_steps'], 'report': str(output),
                      'recenter_control_calls': len(cases[1]['recenter_control_steps'])}))


if __name__ == '__main__':
    main()
