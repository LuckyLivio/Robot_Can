"""Diagnose completed v16 smoke traces; no physics/controller/IK execution.

Joint and pose statistics use each saved state_before and joint_positions.
Planning receipts are compared with the later observed motion, not substituted
for actual motion. Existing diagnostic profiles remain known, correlated data.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import hashlib
import json
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS, fk
from reproduction.improvement_v15_20261016_01.recovery.carry_path import HeldEnvelope

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
STAGE = RUN/'smoke_a'
FOCUS = {
    'known_bc_k2_clean_demo_12000011', 'known_full_s23_clean_demo_12000036',
    'known_full_s23_noise005_demo_12000021', 'known13_bc_k2_noise005_demo_13000021',
    'regression_6000005', 'clearance_profile_6000005',
}
DETAIL_VERSIONS = {'v14', 'v15', 'budget', 'ik', 'held', 'v16'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def serial(item):
    if isinstance(item, np.ndarray):
        return item.tolist()
    if isinstance(item, np.generic):
        return item.item()
    if isinstance(item, dict):
        return {str(k): serial(v) for k, v in item.items()}
    if isinstance(item, (list, tuple)):
        return [serial(v) for v in item]
    return item


def margin(q):
    q = np.asarray(q, float)
    return float(np.minimum(q-LIMITS[:, 0], LIMITS[:, 1]-q).min())


def phase_intervals(rows):
    result = []
    for row in rows:
        recovery = row['recovery']
        identity = (recovery.get('mode'), recovery.get('carry_segment'))
        if not result or tuple(result[-1]['identity']) != identity:
            result.append({'identity': identity, 'first_step': row['step'], 'last_step': row['step'], 'steps': 1})
        else:
            result[-1]['last_step'] = row['step']
            result[-1]['steps'] += 1
    return result


def pose_summary(rows, reference=None):
    if not rows:
        return None
    margins = [margin(row['joint_positions']) for row in rows]
    actual = np.asarray([row['state_before'] for row in rows], float)
    output = {
        'first_step': rows[0]['step'], 'last_step': rows[-1]['step'], 'observed_steps': len(rows),
        'minimum_actual_joint_margin_rad': min(margins),
        'minimum_margin_step': rows[int(np.argmin(margins))]['step'],
        'actual_margin_below_004_steps': [row['step'] for row, value in zip(rows, margins) if value < .04],
        'stable_hold_steps': sum(bool(row['recovery'].get('stable_hold')) for row in rows),
        'hold_false_steps': [row['step'] for row in rows if not row['recovery'].get('stable_hold')],
        'object_start_m': actual[0, 16:19], 'object_last_m': actual[-1, 16:19],
        'eef_displacement_m': float(np.linalg.norm(actual[-1, :3]-actual[0, :3])),
        'object_displacement_m': float(np.linalg.norm(actual[-1, 16:19]-actual[0, 16:19])),
        'remaining_budget_at_last_observation': 400-rows[-1]['step'],
    }
    if reference is not None:
        errors = [reference.relative_errors(x) for x in actual]
        output['maximum_held_relative_position_change_m'] = max(e['position_m'] for e in errors)
        output['maximum_held_relative_orientation_change_rad'] = max(e['angle_rad'] for e in errors)
    return output


def option_summary(option):
    path = option.get('path_ik', [])
    endpoint = option.get('prefilter_ik', [])
    geom = option.get('geometry', [])
    return {
        'candidate': option['candidate'], 'accepted': option['accepted'],
        'reason': option.get('reason'), 'status': option.get('status'),
        'carry_goal': option.get('carry_goal'), 'place_goal': option.get('place_goal'),
        'path_ik_targets': len(path), 'endpoint_ik_targets': len(endpoint),
        'ik_iterations': sum(r['iterations'] for r in path+endpoint),
        'minimum_certified_joint_margin_rad': min((r['limit_margin_rad'] for r in path+endpoint), default=None),
        'maximum_ik_iterations_per_target': max((r['iterations'] for r in path+endpoint), default=None),
        'last_ik_receipt': (path+endpoint)[-1] if path+endpoint else None,
        'minimum_hand_margin_m': min((r['hand_margin_m'] for r in geom), default=None),
        'minimum_carried_can_margin_m': min((r['carried_can_margin_m'] for r in geom), default=None),
        'geometry_checks': len(geom), 'validated_prefix_targets': len(option.get('validated_prefix', [])),
    }


def alternative_rotation(name, observed_rotation):
    if not name.startswith('outward_'):
        return None
    degree = float(name.split('_')[1])
    outward = np.array([.1975, .4025])-np.array([-.5, -.1])
    outward /= np.linalg.norm(outward)
    yaw = np.arctan2(observed_rotation[1, 0], observed_rotation[0, 0])
    down = Rotation.from_euler('z', yaw+(np.pi if 'equivalent' in name else 0.)).as_matrix() @ np.diag([1., -1., -1.])
    return Rotation.from_rotvec(-np.deg2rad(degree)*np.r_[-outward[1], outward[0], 0.]).as_matrix() @ down


def segment_detail(rows, name, goal=None, rotation=None):
    selected = [row for row in rows if row['recovery'].get('carry_segment') == name]
    if name == 'placement':
        selected = [row for row in rows if row['recovery'].get('mode') in ['PLACE', 'PLACE_HOLD']]
    if not selected:
        return None
    result = {'segment': name, **pose_summary(selected)}
    commands = Counter()
    positions, angles = [], []
    for row in selected:
        action = np.asarray(row['submitted_action'])
        translation, turn = np.linalg.norm(action[:3]) > 1e-10, np.linalg.norm(action[3:6]) > 1e-10
        commands['mixed' if translation and turn else 'translation_only' if translation else 'rotation_only' if turn else 'zero_pose'] += 1
        x = np.asarray(row['state_before'])
        if goal is not None:
            positions.append({'step': row['step'], 'value_m': float(np.linalg.norm(x[:3]-goal))})
        if rotation is not None:
            angles.append({'step': row['step'], 'value_rad': float(np.linalg.norm(Rotation.from_matrix(
                rotation @ Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec()))})
    result['submitted_command_types'] = dict(commands)
    if positions:
        result.update(executed_goal=goal, position_error_first=positions[0], position_error_last=positions[-1],
                      position_error_min_m=min(p['value_m'] for p in positions),
                      position_error_max_m=max(p['value_m'] for p in positions))
    if angles:
        result.update(rotation_goal=rotation, orientation_error_first=angles[0], orientation_error_last=angles[-1],
                      orientation_error_min_rad=min(a['value_rad'] for a in angles))
    mixed = [row['recovery']['mixed_pose'] for row in selected if 'mixed_pose' in row['recovery']]
    if mixed:
        result.update(mixed_certified_steps=sum(bool(m['accepted']) for m in mixed),
                      mixed_rejected_steps=sum(not m['accepted'] for m in mixed),
                      maximum_mixed_work_per_step=max(m['work'] for m in mixed))
    return result


def searches(record, rows):
    all_events = record.get('carry15_events', [])+record.get('ik16_events', [])
    starts = sorted({event['step'] for event in all_events if event['event'] in [
        'held_transport_search', 'bounded_continuation_started']})
    finishes = [event for event in record.get('carry15_events', [])
                if event['event'] == 'held_transport_search_complete']
    output = []
    for index, start in enumerate(starts):
        next_start = starts[index+1] if index+1 < len(starts) else rows[-1]['step']+1
        matching = [event for event in finishes if start <= event['step'] < next_start]
        finish = matching[0] if matching else None
        end = finish['step'] if finish else next_start-1
        observations = [row for row in rows if start <= row['step'] <= end]
        planning = [row for row in observations if row['recovery'].get('planning_kind') == 'v15_carry']
        first = rows[start-1]
        x = np.asarray(first['state_before'])
        reference = HeldEnvelope.from_state(x)
        row_output = {
            'start_step': start, 'finish_step': finish['step'] if finish else None,
            'elapsed_control_steps_inclusive': end-start+1,
            'remaining_at_start': 400-start, 'remaining_at_finish': 400-end,
            'observed_positive_work_calls': sum(row['recovery'].get('planning_work_units', 0) > 0 for row in planning),
            'work_sum_from_trace': sum(row['recovery'].get('planning_work_units', 0) for row in planning),
            'maximum_planning_work_per_step': max((row['recovery'].get('planning_work_units', 0) for row in planning), default=0),
            'work_receipt': finish.get('work') if finish else None,
            'chosen': finish.get('chosen') if finish else None,
            'planning_actual_observations': pose_summary(observations, reference),
            'start_observation': first['state_before'], 'start_observed_joints': first['joint_positions'],
        }
        if finish:
            assert row_output['work_sum_from_trace'] == finish['work'], (start, row_output['work_sum_from_trace'], finish['work'])
            row_output['options'] = [option_summary(option) for option in finish['options']]
            accepted = next((option for option in finish['options'] if option['accepted']), None)
            if accepted:
                row_output['selected_candidate'] = accepted['candidate']
                # Stop the execution comparison at the next attempt; a later
                # recovery is a different certificate, even without a search.
                attempt = rows[finish['step']-1]['recovery'].get('attempts')
                executed = []
                for row in rows[finish['step']:next_start-1]:
                    if row['recovery'].get('attempts') != attempt:
                        break
                    executed.append(row)
                carry = [row for row in executed if row['recovery'].get('mode') in [
                    'CARRY_PATH', 'CARRY', 'CARRY_HOLD', 'CARRY_GUARD', 'PLACE', 'PLACE_HOLD']]
                row_output['execution_actual_observations'] = pose_summary(carry, reference)
                observed_rotation = Rotation.from_quat(x[3:7]).as_matrix()
                rotation = alternative_rotation(accepted['candidate'], observed_rotation)
                raised = x[:3].copy()
                raised[2] = max(raised[2], 1.08+reference.held_offset(observed_rotation)[2])
                carry_goal = accepted.get('carry_goal')
                place_goal = accepted.get('place_goal')
                if rotation is not None:
                    if carry_goal is None:
                        carry_goal = np.array([.1975, .4025, 1.08])+reference.held_offset(rotation)
                    if place_goal is None:
                        place_goal = np.array([.1975, .4025, .885])+reference.held_offset(rotation)
                row_output['segments'] = [detail for detail in [
                    segment_detail(executed, 'clearance', raised, observed_rotation),
                    segment_detail(executed, 'reorient', raised, rotation),
                    segment_detail(executed, 'transport', carry_goal, rotation),
                    segment_detail(executed, 'placement', place_goal, rotation),
                ] if detail is not None]
                path_ik = accepted.get('path_ik', [])
                if path_ik and carry:
                    row_output['ik_versus_actual'] = {
                        'planned_minimum_joint_margin_rad': min(r['limit_margin_rad'] for r in path_ik),
                        'actual_minimum_joint_margin_rad': min(margin(row['joint_positions']) for row in carry),
                        'planned_ik_targets': len(path_ik),
                        'planned_joint_path_is_not_commanded_joint_path': True,
                        'actual_joints_from_trace_before_physics': True,
                    }
        output.append(row_output)
    return output


def inspect_job(job):
    folder = STAGE/job['id']
    result = json.loads((folder/'result.json').read_text(encoding='utf8'))
    assert result['status'] == 'complete' and len(result['records']) == 1
    record = result['records'][0]
    rows = list(map(json.loads, (folder/'trace.jsonl').open(encoding='utf8')))
    assert len(rows) == record['steps'] and rows[-1]['success_after'] == record['success']
    assert [r['step'] for r in rows] == list(range(1, len(rows)+1))
    suffix = job['id'].split('_', 1)[1]
    before = np.asarray(rows[-1]['state_before'])
    after = np.asarray(rows[-1]['state_after'])
    summary = {
        'job': job['id'], 'profile': suffix, 'version': job['version'], 'demo': record['demo'],
        'dataset': job.get('dataset'), 'comparison_profile': job.get('comparison_profile'),
        'force_recovery_at': job.get('force_recovery_at'), 'fault': job.get('fault'),
        'method': job['method'], 'seed': job.get('seed'), 'noise': job['noise'],
        'success': record['success'], 'steps': record['steps'],
        'last_submitted_mode': rows[-1]['recovery'].get('mode'),
        'last_next_mode': rows[-1]['recovery'].get('next_mode'),
        'last_stable_hold': rows[-1]['recovery'].get('stable_hold'),
        'last_object_before_physics': before[16:19], 'final_object_after_physics': after[16:19],
        'final_object_xy_error_m': float(np.linalg.norm(after[16:18]-np.array([.1975, .4025]))),
        'source_result_sha256': digest(folder/'result.json'), 'source_trace_sha256': digest(folder/'trace.jsonl'),
        'first_observation': rows[0]['state_before'], 'first_joints': rows[0]['joint_positions'],
        'phase_counts': dict(Counter(row['recovery'].get('mode') for row in rows)),
    }
    if suffix in FOCUS and job['version'] in DETAIL_VERSIONS:
        summary.update(searches=searches(record, rows), phase_intervals=phase_intervals(rows),
                       transitions=record.get('events', []),
                       carry_events=record.get('carry15_events', []),
                       held_events=[event for event in record.get('held16_events', [])
                                    if event.get('event') != 'held_mixed_step' and event.get('event') != 'placement_mixed_step'],
                       budget_events=record.get('budget15_events', []))
        # Avoid copying all candidate path arrays twice into this report.
        summary['carry_events'] = [{k: v for k, v in event.items() if k != 'options'} for event in summary['carry_events']]
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='smoke_a_carry_diagnosis.json')
    args = parser.parse_args()
    destination = RUN/'analysis'/args.output
    assert not destination.exists(), 'Preserve earlier receipts.'
    assert (STAGE/'completed.json').is_file(), 'Wait for all physical jobs and immutable-source validation.'
    completion = json.loads((STAGE/'completed.json').read_text(encoding='utf8'))
    assert completion['episodes'] == 63 and completion['source_unchanged']
    jobs = json.loads((STAGE/'jobs.json').read_text(encoding='utf8'))
    assert len(jobs) == 63
    evidence = [inspect_job(job) for job in jobs]
    groups = defaultdict(list)
    profiles = defaultdict(dict)
    for item in evidence:
        profiles[item['profile']][item['version']] = item
        key = (item['dataset'], item['demo'])
        if item['version'] == 'v14':
            groups[key].append(item)
    repeated = []
    for (dataset, demo), members in groups.items():
        if len(members) < 2:
            continue
        for item in members[1:]:
            np.testing.assert_array_equal(item['first_observation'], members[0]['first_observation'])
            np.testing.assert_array_equal(item['first_joints'], members[0]['first_joints'])
        repeated.append({'dataset': dataset, 'demo': demo, 'profiles': [item['profile'] for item in members],
                         'same_initial_physical_observation_and_joints': True,
                         'interpretation': 'Repeated known start with a different registered diagnostic profile, not independent evidence.'})
    comparisons = []
    for profile, versions in profiles.items():
        reference = versions['v14']
        for item in versions.values():
            np.testing.assert_array_equal(item['first_observation'], reference['first_observation'])
            np.testing.assert_array_equal(item['first_joints'], reference['first_joints'])
        comparisons.append({'profile': profile, 'paired_initial_inputs_equal': True,
                            'results': {version: {'success': item['success'], 'steps': item['steps'],
                                                  'last_mode': item['last_submitted_mode']}
                                        for version, item in versions.items()}})
    output = {'new_physical_episodes': 0, 'new_controller_replays': 0, 'new_ik_searches': 0,
              'saved_physical_executions_analyzed': 63, 'registered_known_profiles': len(profiles),
              'unique_dataset_demo_starts': len(groups), 'all_results_complete': True,
              'script_sha256': digest(__file__), 'completed_sha256': digest(STAGE/'completed.json'),
              'jobs_sha256': digest(STAGE/'jobs.json'), 'started_sha256': digest(STAGE/'started.json'),
              'repeated_start_profiles': repeated, 'paired_comparisons': comparisons, 'episodes': evidence,
              'scope': ['No new simulation, replay, controller execution or IK search.',
                        'Observed joints are saved state_before values; no after-step joint positions are invented.',
                        'Static IK certificates and actual Cartesian-controller behavior are reported separately.',
                        'Profile counts are not independent-start sample counts; all starts were already known.']}
    with destination.open('x', encoding='utf8') as handle:
        json.dump(serial(output), handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'output': str(destination), 'executions': len(evidence),
                      'known_profiles': len(profiles), 'unique_dataset_demo_starts': len(groups),
                      'paired_comparisons': comparisons}, ensure_ascii=False))


if __name__ == '__main__':
    main()
