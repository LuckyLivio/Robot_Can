"""Read-only edge/budget diagnosis from completed, frozen saved-input traces.

This executes controllers only, not a simulator. Measured latency is taken from
the original trace, never from this diagnostic replay. Profiles are not counted
as new independent samples. Requires all selected results to be complete.
"""
from collections import Counter, deque
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import sys
import types

import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import RecoveryController as V16, Config as C16
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import RecoveryController as V15, Config as C15
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin

VERSIONS = ['v15', 'v16', 'budget', 'route', 'edge', 'held', 'v17']
CONDITIONS = ['known13_full_s41_noise005_demo_13000022',
              'known13_bc_k2_noise005_demo_13000021',
              'regression_6000005', 'clearance_profile_6000005']
EVENT_FIELDS = ['events', 'support13_events', 'escape_events', 'tracking14_events',
                'clearance14_events', 'carry15_events', 'edge15_events',
                'budget15_events', 'ik16_events', 'held16_events', 'edge16_events',
                'route17_events', 'edge17_events', 'held17_events',
                'wait_hold_events', 'guard_events', 'pose_events',
                'geometry_events', 'edge_events', 'joint_events', 'planning_events']
EDGE_PHASES = {'EDGE_PRETRANSLATE', 'EDGE_ROTATE', 'EDGE_APPROACH'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value):
    if isinstance(value, dict):
        return {str(k): finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [finite(v) for v in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def latency(rows, path):
    values = []
    for row in rows:
        item = row
        for key in path.split('.'):
            item = item.get(key) if isinstance(item, dict) else None
        if item is not None:
            values.append(float(item))
    if not values:
        return {'n': 0}
    return {'n': len(values), 'median_ms': float(np.median(values)),
            'p95_ms': float(np.percentile(values, 95)), 'max_ms': max(values),
            'above_50ms_count': sum(v > 50 for v in values),
            'sum_ms': sum(values)}


def spans(metrics):
    groups = []
    for item in metrics:
        key = (item['attempt_before'], item['logical_phase_before'], item.get('carry_segment_before'))
        if not groups or groups[-1]['key'] != key or groups[-1]['items'][-1]['step'] + 1 != item['step']:
            groups.append({'key': key, 'items': []})
        groups[-1]['items'].append(item)
    output = []
    for group in groups:
        items = group['items']
        pose_items = [x for x in items if x.get('position_error_m') is not None]
        pose_streak = aperture_streak = qualified_streak = 0
        max_pose = max_aperture = max_qualified = 0
        for item in items:
            pose_streak = pose_streak + 1 if item.get('within_pose_thresholds') else 0
            aperture_streak = aperture_streak + 1 if item.get('within_pose_thresholds') and item.get('gap_ready_after_observation') else 0
            qualified_streak = qualified_streak + 1 if item.get('observed_full_settling_qualification') else 0
            max_pose = max(max_pose, pose_streak)
            max_aperture = max(max_aperture, aperture_streak)
            max_qualified = max(max_qualified, qualified_streak)
        output.append({
            'attempt': group['key'][0], 'phase': group['key'][1], 'carry_segment': group['key'][2],
            'first_control_step': items[0]['step'], 'last_control_step': items[-1]['step'],
            'controls': len(items), 'command_modes': dict(Counter(i['command_mode'] for i in items)),
            'aperture_only_controls': sum(i['command_mode'] == 'EDGE_APERTURE' for i in items),
            'gap_not_ready_controls': sum(not i['gap_ready_after_observation'] for i in items),
            'grip_pulse_controls': sum(i['grip_command'] != 0 for i in items),
            'zero_pose_controls': sum(i['zero_pose_command'] for i in items),
            'max_pose_streak': max_pose, 'max_pose_and_aperture_streak': max_aperture,
            'max_observed_full_settling_streak': max_qualified,
            'settling_blocker_counts': dict(Counter(b for i in items for b in i.get('settling_blockers', []))),
            'position_qualified_controls': sum(i.get('position_error_m', 1.) < .009 for i in items),
            'angle_qualified_controls': sum(i.get('orientation_error_rad', 1.) < .08 for i in items),
            'observed_full_settling_qualified_controls': sum(i.get('observed_full_settling_qualification', False) for i in items),
            'max_actual_settled_counter_before': max(i['edge_settled_before'] for i in items),
            'max_actual_settled_counter_after': max(i['edge_settled_after'] for i in items),
            'min_joint_margin_rad': min(i['joint_margin_rad'] for i in items),
            'last': items[-1],
            'best_position': min(pose_items, key=lambda i: i['position_error_m']) if pose_items else None,
            'best_angle': min(pose_items, key=lambda i: i['orientation_error_rad']) if pose_items else None,
            'mixed_certificate_rejections': sum(i.get('mixed_certificate_accepted') is False for i in items),
            'max_bias_norm_m': max(i.get('bias_norm_m', 0.) for i in items),
            'max_carry_settled_before': max(i.get('carry_settled_before', 0) for i in items),
            'max_carry_settled_after': max(i.get('carry_settled_after', 0) for i in items),
        })
    return output


def frozen_module(stage):
    assert json.loads((stage/'completed.json').read_text())['source_unchanged']
    started_path = stage / 'started.json'
    started = json.loads(started_path.read_text())
    assert sha(stage / 'jobs.json') == started['jobs_sha256']
    for relative, digest in started['source_sha256'].items():
        assert sha(stage / 'source' / Path(relative).relative_to(RUN.relative_to(ROOT))) == digest, relative
    for relative, digest in started['dependency_sha256'].items():
        assert sha(ROOT / relative) == digest, relative
    package = types.ModuleType('edge_diagnosis_frozen17')
    package.__path__ = [str(stage / 'source/recovery')]
    sys.modules[package.__name__] = package
    spec = importlib.util.spec_from_file_location(package.__name__ + '.recovery_controller',
                                                 stage / 'source/recovery/recovery_controller.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def diagnose(stage, version, condition, module):
    directory = stage / (version + '_' + condition)
    result_path, trace_path = directory / 'result.json', directory / 'trace.jsonl'
    result = json.loads(result_path.read_text())
    assert result['status'] == 'complete'
    assert len(result['records']) == 1
    record, job = result['records'][0], result['job']
    rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
    cls, config = (V16, C16) if version == 'v16' else ((V15, C15) if version in ['v15', 'budget'] else (module.RecoveryController, module.Config))
    controller = cls([.1975, .4025, .8], .8, np.asarray(rows[0]['state_before'], np.float32),
                     job['enabled'], config(**job.get('config', {})))
    previous = np.zeros(7, np.float32)
    pending = deque([np.zeros(7, np.float32), np.zeros(7, np.float32)], maxlen=3)
    rng = np.random.default_rng(70000 + int(record['demo'].split('_')[1]))
    fault_left = 0
    fault_step = None
    max_action_error = 0.
    observations = []
    trace_rejections = []
    previous_submitted = np.zeros(7, np.float32)
    for row in rows:
        step = row['step']
        x = np.asarray(row['state_before'], np.float32)
        q = np.asarray(row['joint_positions'], float)
        controller.set_joint_positions(q)
        if job.get('force_recovery_at') == step:
            controller.start_attempt('diagnostic_forced_start', x)
        phase = controller.mode
        attempt = controller.attempts
        plan = copy.deepcopy(controller.edge_plan)
        start = copy.deepcopy(getattr(controller, 'edge_start', None))
        goal = rotation = None
        grasp_before = controller.grasp_target(x).copy() if plan is not None else None
        if plan is not None:
            if phase == 'EDGE_PRETRANSLATE':
                goal, rotation = plan['pre_goal'], plan['pre_rotation']
            elif phase == 'EDGE_ROTATE':
                goal, rotation = start, plan['rotation']
            elif phase == 'EDGE_APPROACH':
                goal, rotation = plan['above'], plan['rotation']
            elif phase == 'DESCEND':
                goal, rotation = grasp_before, plan['rotation']
        age = controller.age
        settled = controller.edge_settled
        carry_plan = copy.deepcopy(controller.carry_plan)
        carry_index = controller.carry_index
        carry_settled = controller.carry_settled
        carry_phase_age = controller.carry_phase_age
        carry_tail = copy.deepcopy(getattr(controller, 'carry_tail17', None))
        carry_segment = None
        route = getattr(controller, 'transport16', None)
        if getattr(controller, 'transport16_attempt', -1) != controller.attempts:
            route = None
        if phase == 'CARRY' and carry_plan is not None and controller.carry_search is None:
            active_stage = carry_plan['stages'][carry_index]
            goal, rotation = active_stage['goal'], active_stage['rotation']
            carry_segment = active_stage['label']
        elif phase == 'CARRY' and carry_plan is None and controller.carry_search is None and route is not None:
            goal, rotation = route['carry_goal'], route['rotation']
            carry_segment = 'terminal_' + str((carry_tail or {}).get('segment', 'old_route'))
        elif phase == 'PLACE':
            goal = route['place_goal'] if route is not None else np.r_[controller.target[:2], controller.floor+.085]+controller.held_offset
            rotation = route['rotation'] if route is not None else controller.goal_rotation.copy()
            carry_segment = 'place'
        held_relative = None if controller.carry_reference is None else controller.carry_reference.relative_errors(x)
        recenter_before = controller.recenter is not None
        old_position = None if controller.last_observed is None else controller.last_observed[:3].copy()
        target_gap = controller.approach_gap
        command, info = controller.choose(x, np.asarray(row['original_proposal'], np.float32), previous)
        saved, replay = dict(row['recovery']), dict(info)
        saved.pop('planning_ms', None)
        replay.pop('planning_ms', None)
        assert saved == replay, (job['id'], step, 'diagnostic replay mismatch')
        if job.get('fault') == 'open_after_verified_lift' and fault_step is None and info['stable_hold'] and .89 < x[18] < .96 and np.linalg.norm(x[16:18] - controller.target[:2]) > .30:
            fault_step, fault_left = step, 12
        assert row['fault_injected'] == (fault_left > 0)
        if fault_left > 0:
            command[6] = -1.
            fault_left -= 1
        error = float(np.max(np.abs(command - np.asarray(row['submitted_action']))))
        max_action_error = max(max_action_error, error)
        assert error <= 1e-7, (job['id'], step, error)
        np.testing.assert_array_equal(row['queue_before'], list(pending))
        pending.append(command.copy())
        executed = pending.popleft()
        np.testing.assert_array_equal(executed, row['executed_action_before_noise'])
        if job['noise']:
            executed[:3] += rng.normal(0, job['noise'], 3)
        previous = np.clip(executed, -1, 1)
        np.testing.assert_array_equal(previous, row['executed_action'])
        receipt = info.get('mixed_pose')
        if receipt is not None and not receipt['accepted']:
            trace_rejections.append({'step': step, 'phase': phase, 'receipt': receipt})
        delta_submitted = command - previous_submitted
        previous_submitted = command.copy()
        if phase not in EDGE_PHASES and phase not in ['DESCEND', 'CARRY', 'PLACE', 'LIFT', 'VERIFY'] and not recenter_before:
            continue
        r = Rotation.from_quat(x[3:7]).as_matrix()
        gap = abs(float(x[7] - x[8]))
        gap_range = max(controller.gaps) - min(controller.gaps) if controller.gaps else None
        pulse_age = controller.clock - controller.last_pulse
        # Diagnose against the target active for this submitted command, even
        # when a timeout in choose has already installed a new attempt's plan.
        gap_ready = bool(target_gap is not None and len(controller.gaps) >= 3 and
                         abs(gap - target_gap) <= controller.cfg.aperture_tolerance_m and
                         gap_range < controller.cfg.gap_settle_m and pulse_age >= controller.cfg.delay + 2)
        item = {
            'step': step, 'attempt_before': attempt, 'attempt_after': controller.attempts,
            'logical_phase_before': phase, 'command_mode': info['mode'], 'next_mode': controller.mode,
            'age_before': age, 'age_after': controller.age,
            'edge_settled_before': settled, 'edge_settled_after': controller.edge_settled,
            'carry_segment_before': carry_segment, 'carry_settled_before': carry_settled,
            'carry_settled_after': controller.carry_settled,
            'carry_phase_age_before': carry_phase_age, 'carry_phase_age_after': controller.carry_phase_age,
            'carry_terminal_state_before': carry_tail,
            'held_relative_error_before': held_relative,
            'recenter_active_before': recenter_before,
            'joint_margin_rad': float(np.min(np.minimum(q - LIMITS[:, 0], LIMITS[:, 1] - q))),
            'gap_m': gap, 'target_gap_m': target_gap,
            'gap_error_m': None if target_gap is None else gap - target_gap,
            'gap_ready_after_observation': gap_ready,
            'controller_gap_ready_after_transition': bool(controller.gap_ready(x)),
            'gap_history_range_m': gap_range, 'gap_history_length': len(controller.gaps),
            'controls_since_gap_pulse': pulse_age,
            'grip_command': float(command[6]), 'zero_pose_command': bool(np.all(command[:6] == 0)),
            'submitted_translation_m': (command[:3] * .05).tolist(),
            'submitted_rotation_rad': (command[3:6] * .5).tolist(),
            'submitted_translation_change_m': float(np.linalg.norm(delta_submitted[:3] * .05)),
            'submitted_rotation_change_rad': float(np.linalg.norm(delta_submitted[3:6] * .5)),
            'observed_position_m': x[:3].tolist(), 'observed_rotation_xyzw': x[3:7].tolist(),
            'observed_can_position_m': x[16:19].tolist(),
            'actual_can_target_xy_error_m': float(np.linalg.norm(x[16:18]-controller.target[:2])),
            'stable_hold': info['stable_hold'],
            'mixed_certificate_accepted': None if receipt is None else receipt['accepted'],
            'mixed_certificate_reason': None if receipt is None else receipt['reason'],
            'mixed_certificate_work': None if receipt is None else receipt['work'],
            'aperture_motion_certified': bool(receipt and receipt.get('accepted') and receipt.get('aperture_motion')),
            'mixed_certificate_box_margin_m': None if receipt is None else receipt.get('box_margin_m'),
            'mixed_certificate_can_margin_m': None if receipt is None else receipt.get('can_margin_m'),
            'bias_norm_m': float(np.linalg.norm(receipt.get('position_bias_m', [0,0,0]))) if receipt else 0.,
            'held_command_slew_limited': bool(receipt and receipt.get('held_command_slew_limited')),
            'original_decision_ms': row['decision_ms'],
            'original_policy_and_supervisor_ms': row['total_policy_and_supervisor_ms'],
            'original_planning_ms': row['recovery'].get('planning_ms'),
        }
        if goal is not None:
            distance = float(np.linalg.norm(x[:3] - goal))
            angle = float(np.linalg.norm(Rotation.from_matrix(rotation @ r.T).as_rotvec()))
            velocity = np.zeros(3) if old_position is None else x[:3] - old_position
            forecast = float(np.linalg.norm(x[:3] + controller.cfg.delay * velocity - goal))
            within = bool(distance < .009 and angle < .08)
            item.update(goal_m=np.asarray(goal).tolist(), goal_rotation=np.asarray(rotation).tolist(),
                        position_error_m=distance, orientation_error_rad=angle,
                        within_pose_thresholds=within, d2_forecast_error_m=forecast,
                        observed_step_translation_m=velocity.tolist())
            if plan is not None:
                grasp = grasp_before
                axis = plan['rotation'][:, 2]
                delta = x[:3] - grasp
                side = delta - axis * np.dot(delta, axis)
                tail = object_margin(x[:3], grasp, r, [gap - .001, gap + .001], x)
                item.update(descent_side_error_m=float(np.linalg.norm(side)),
                            remaining_descent_path_margin_m=float(tail))
            budget = phase == 'EDGE_APPROACH' and getattr(controller.cfg, 'budget_recenter', False)
            held_stage = phase in ['CARRY', 'PLACE']
            qualification = within and (bool(info['stable_hold']) if held_stage else gap_ready)
            if budget:
                qualification = qualification and forecast < .009 and item['remaining_descent_path_margin_m'] >= .003
            blockers = []
            if distance >= .009: blockers.append('position_ge_9mm')
            if angle >= .08: blockers.append('angle_ge_0.08rad')
            if held_stage:
                if not info['stable_hold']: blockers.append('held_not_stable')
            elif not gap_ready: blockers.append('aperture_not_settled')
            if budget and forecast >= .009: blockers.append('d2_forecast_ge_9mm')
            if budget and item['remaining_descent_path_margin_m'] < .003: blockers.append('descent_tail_lt_3mm')
            item.update(observed_full_settling_qualification=bool(qualification), settling_blockers=blockers)
        observations.append(item)
    assert record['steps'] == len(rows)
    assert record['success'] == rows[-1]['success_after']
    compared = []
    for field in EVENT_FIELDS:
        if hasattr(controller, field) and field in record:
            assert getattr(controller, field) == record[field], (job['id'], field)
            compared.append(field)
    event_rejections = []
    for field in EVENT_FIELDS:
        for event in record.get(field, []):
            if (event.get('accepted') is False or any(word in str(event.get('event', '')) for word in ['guard', 'timeout', 'aborted', 'invalidated'])):
                event_rejections.append({'source': field, **event})
    edge_steps = {item['step'] for item in observations if item['logical_phase_before'] in EDGE_PHASES}
    edge_rows = [row for row in rows if row['step'] in edge_steps]
    payload = {
        'version': version, 'condition': condition, 'comparison_profile': job.get('comparison_profile', 'standard'),
        'job': job['id'], 'success': record['success'], 'steps': record['steps'],
        'physical_budget_steps': 400, 'remaining_budget_at_end': 400 - record['steps'],
        'new_physical_episodes': 0, 'saved_input_replayed_controls': len(rows),
        'max_replay_action_error': max_action_error, 'diagnostics_exact': True,
        'event_fields_exact': compared, 'd2_queue_and_noise_exact': True,
        'fault_first_step': fault_step, 'phases': record['phases'],
        'final_command_mode': rows[-1]['recovery']['mode'], 'final_next_mode': controller.mode,
        'attempts': controller.attempts, 'failed_attempts': controller.failed_attempts,
        'verified_regrasps': record['verified_regrasps'],
        'transitions': record['events'], 'edge_and_held_phase_spans': spans(observations),
        'aperture_only_total_controls': sum(row['recovery']['mode'] == 'EDGE_APERTURE' for row in rows),
        'mixed_certificate_rejections': trace_rejections,
        'guard_timeout_and_unconfirmed_events': event_rejections,
        'original_measured_latency': {
            'scope': 'Original trace wall-clock timings; diagnostic replay timing is excluded. The 50 ms reference is 20 Hz, not a real-time guarantee.',
            'all_controls': {key: latency(rows, key) for key in ['decision_ms', 'total_policy_and_supervisor_ms', 'recovery.planning_ms']},
            'edge_pose_controls': {key: latency(edge_rows, key) for key in ['decision_ms', 'total_policy_and_supervisor_ms', 'recovery.planning_ms']},
        },
        'per_control_observations': observations,
        'source': {p.relative_to(ROOT).as_posix(): sha(p) for p in [result_path, trace_path]},
    }
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', default='smoke_a')
    parser.add_argument('--name', default=None, help='New receipt name; existing receipts are never overwritten.')
    args = parser.parse_args()
    stage = RUN / args.stage
    for condition in CONDITIONS:
        for version in VERSIONS:
            result = stage / (version + '_' + condition) / 'result.json'
            assert result.exists() and json.loads(result.read_text())['status'] == 'complete', result
    module = frozen_module(stage)
    output = {
        'passed': True, 'stage': args.stage, 'new_physical_episodes': 0,
        'diagnostic_only': True, 'selected_evaluation_executions': len(CONDITIONS) * len(VERSIONS),
        'independent_start_count': 3,
        'scope_note': 'The standard and clearance-only 6000005 profiles share an initial state; 28 executions are not 28 independent starts. route/edge/held are single v17 components on full v16; budget is v15 budget-only on v14. This replay introduces no new evaluation sample.',
        'thresholds': {'position_m': .009, 'orientation_rad': .08, 'stable_frames': 5,
                       'joint_margin_rad': .04, 'edge_timeout_controls': 70, 'physical_budget': 400,
                       'box_execution_margin_m': .001, 'empty_can_execution_margin_m': .001,
                       'empty_can_planning_and_approach_tail_margin_m': .003},
        'source': {p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), stage / 'started.json', stage / 'jobs.json', stage/'completed.json']},
        'cases': [],
        'limitations': [
            'Saved-input replay confirms action/diagnostic/queue/event consistency, not the physics model; independent physics verification is a separate receipt.',
            'Pose and clearance metrics use the stored observation before each submitted action. With D2, submitted commands do not execute immediately.',
            'An unconfirmed geometry or IK check is not proof of actual collision or global unreachability.',
            'Measured latency is local-run wall-clock timing and includes original runtime variability; no new benchmark is run.',
        ],
    }
    for condition in CONDITIONS:
        for version in VERSIONS:
            payload = diagnose(stage, version, condition, module)
            output['cases'].append(payload)
            output['source'].update(payload['source'])
            print(version, condition, payload['success'], payload['steps'], payload['final_command_mode'],
                  'aperture-only', payload['aperture_only_total_controls'], flush=True)
    output['saved_input_replayed_controls'] = sum(c['saved_input_replayed_controls'] for c in output['cases'])
    destination = RUN / 'analysis' / ((args.name or args.stage + '_edge_diagnosis') + '.json')
    with destination.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(finite(output), ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(destination, flush=True)


if __name__ == '__main__':
    main()
