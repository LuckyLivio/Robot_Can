"""Read-only diagnosis of completed v15 smoke carry traces; no replay/run."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS

TARGET_SUFFIX = 'known13_bc_k2_noise005_demo_13000021'
TARGET_XY = np.array([.1975, .4025])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observation(row):
    x = np.asarray(row['state_before'])
    q = np.asarray(row['joint_positions'])
    margin = np.minimum(q-LIMITS[:, 0], LIMITS[:, 1]-q)
    rotation = Rotation.from_quat(x[3:7]).as_matrix()
    local = rotation.T @ (x[16:19]-x[:3])
    info = row['recovery']
    return {'step': row['step'], 'remaining_steps': 400-row['step'],
            'mode': info.get('mode'), 'next_mode': info.get('next_mode'),
            'carry_segment': info.get('carry_segment'),
            'stable_hold': info.get('stable_hold'), 'latched_hold': info.get('latched_hold'),
            'loss_detected': info.get('loss_detected'),
            'eef_position': x[:3].tolist(), 'object_position': x[16:19].tolist(),
            'eef_minus_object_world': (x[:3]-x[16:19]).tolist(),
            'object_in_eef_position': local.tolist(),
            'object_target_xy_distance_m': float(np.linalg.norm(x[16:18]-TARGET_XY)),
            'gap_m': float(abs(x[7]-x[8])),
            'joint_positions': q.tolist(), 'joint_margins_rad': margin.tolist(),
            'minimum_joint_margin_rad': float(margin.min()),
            'limiting_joint_1_based': int(np.argmin(margin))+1,
            'submitted_action': row['submitted_action'],
            'executed_action': row['executed_action']}


def compact_event(event):
    out = {key: value for key, value in event.items() if key != 'options'}
    if 'options' in event:
        options = []
        for option in event['options']:
            item = {key: value for key, value in option.items() if key not in ['prefilter_ik', 'path_ik', 'geometry']}
            for key in ['prefilter_ik', 'path_ik']:
                if key in option:
                    item[key] = [{field: value for field, value in row.items() if field != 'q'} for row in option[key]]
            if option.get('geometry'):
                item['geometry_summary'] = {
                    'checks': len(option['geometry']),
                    'minimum_hand_margin_m': min(row['hand_margin_m'] for row in option['geometry']),
                    'minimum_can_margin_m': min(row['carried_can_margin_m'] for row in option['geometry']),
                    'failed_checks': [row for row in option['geometry'] if not row['accepted']],
                }
            options.append(item)
        out['options'] = options
    return out


def phases(rows):
    groups = []
    for row in rows:
        info = row['recovery']
        key = (info.get('mode'), info.get('carry_segment'))
        if not groups or key != groups[-1]['key']:
            groups.append({'key': key, 'start_step': row['step'], 'end_step': row['step'], 'steps': 1})
        else:
            groups[-1]['end_step'] = row['step']
            groups[-1]['steps'] += 1
    return [{'mode': group['key'][0], 'segment': group['key'][1],
             **{key: value for key, value in group.items() if key != 'key'}} for group in groups]


def episode(job, result, rows):
    record = result['records'][0]
    carry_events = record.get('carry15_events', [])
    starts = [event for event in carry_events if event['event'] == 'held_transport_search']
    finishes = [event for event in carry_events if event['event'] == 'held_transport_search_complete']
    planning = []
    for start in starts:
        finish = next((event for event in finishes if event['step'] >= start['step']), None)
        planning.append({'start_step': start['step'], 'remaining_at_start': 400-start['step'],
                         'finish_step': None if finish is None else finish['step'],
                         'remaining_at_finish': None if finish is None else 400-finish['step'],
                         'elapsed_control_steps_inclusive': None if finish is None else finish['step']-start['step']+1,
                         'chosen': None if finish is None else finish.get('chosen'),
                         'work_units': None if finish is None else finish.get('work'),
                         'observed_position_drift_m': None if finish is None else finish.get('observed_position_drift_m'),
                         'observed_joint_drift_rad': None if finish is None else finish.get('observed_joint_drift_rad')})
    physical = [observation(row) for row in rows]
    carry_rows = [row for row in physical if row['mode'] and row['mode'].startswith('CARRY')]
    selected_steps = {1, rows[-1]['step']}
    selected_steps.update(row['step'] for row in rows if row['step'] % 20 == 0 and row['step'] >= 180)
    for event in carry_events+record.get('events', []):
        if event['step'] >= 180:
            selected_steps.update(step for step in range(event['step']-1, event['step']+3) if 1 <= step <= len(rows))
    if carry_rows:
        first_local = np.asarray(carry_rows[0]['object_in_eef_position'])
        max_relative = max(float(np.linalg.norm(np.asarray(row['object_in_eef_position'])-first_local)) for row in carry_rows)
    else:
        max_relative = None
    return {'job': job['id'], 'version': job['version'], 'demo': record['demo'],
            'success': record['success'], 'steps': record['steps'],
            'first_carry_step': None if not carry_rows else carry_rows[0]['step'],
            'remaining_at_first_carry': None if not carry_rows else 400-carry_rows[0]['step'],
            'planning': planning,
            'carry_mode_counts': dict(Counter(row['mode'] for row in carry_rows)),
            'carry_stable_hold_false_steps': [row['step'] for row in carry_rows if row['stable_hold'] is False],
            'minimum_joint_margin_rad': min(row['minimum_joint_margin_rad'] for row in physical),
            'carry_minimum_joint_margin_rad': None if not carry_rows else min(row['minimum_joint_margin_rad'] for row in carry_rows),
            'carry_max_relative_position_change_from_first_carry_m': max_relative,
            'carry_events': [compact_event(event) for event in carry_events],
            'phase_events': record.get('events', []), 'phase_intervals': phases(rows),
            'sampled_observations': [row for row in physical if row['step'] in selected_steps],
            'final_observation': physical[-1],
            'final_object_position_after_last_command': rows[-1]['state_after'][16:19],
            'recorded_attempts': record.get('attempts'), 'recorded_failed_attempts': record.get('failed_attempts')}


def main():
    stage = RUN/'smoke_a'
    destination = RUN/'analysis/smoke_a_carry_diagnosis.json'
    assert not destination.exists(), 'Will not overwrite a diagnosis.'
    assert (stage/'completed.json').exists(), 'Wait for the complete smoke stage; do not analyze partial prefixes as finished results.'
    jobs = json.loads((stage/'jobs.json').read_text(encoding='utf8'))
    results = {}
    for job in jobs:
        path = stage/job['id']/'result.json'
        result = json.loads(path.read_text(encoding='utf8'))
        assert result['status'] == 'complete'
        assert len(result['records']) == len(job['demos']) == 1
        results[job['id']] = result
    assert len(jobs) == 45
    selected = {}
    comparisons = []
    for job in jobs:
        if job['version'] not in ['carry', 'v15']:
            continue
        suffix = job['id'].split('_', 1)[1]
        baseline_id = 'v14_'+suffix
        current = results[job['id']]['records'][0]
        baseline = results[baseline_id]['records'][0]
        old_success_lost = baseline['success'] and not current['success']
        target = suffix == TARGET_SUFFIX
        if not (old_success_lost or target):
            continue
        selected[job['id']] = job
        selected[baseline_id] = next(item for item in jobs if item['id'] == baseline_id)
        comparisons.append({'baseline': baseline_id, 'candidate': job['id'],
                            'baseline_success': baseline['success'], 'candidate_success': current['success'],
                            'baseline_steps': baseline['steps'], 'candidate_steps': current['steps'],
                            'selection_reason': 'preselected_leaning_target' if target else 'old_success_regression',
                            'old_success_lost': old_success_lost})
    episodes = []
    inputs = []
    for job in selected.values():
        folder = stage/job['id']
        rows = list(map(json.loads, (folder/'trace.jsonl').open(encoding='utf8')))
        assert len(rows) == results[job['id']]['records'][0]['steps']
        episodes.append(episode(job, results[job['id']], rows))
        inputs.append({'job': job['id'], 'trace_sha256': digest(folder/'trace.jsonl'),
                       'result_sha256': digest(folder/'result.json')})
    output = {'passed': True, 'stage': 'smoke_a', 'complete_stage_executions': 45,
              'new_physical_episodes': 0, 'saved_input_replay_performed': False,
              'analysis_script_sha256': digest(Path(__file__)),
              'stage_completion_sha256': digest(stage/'completed.json'),
              'selection': 'Carry and v15 preselected leaning target plus every old v14 success lost by carry or v15; baseline paired traces included.',
              'comparisons': comparisons, 'episodes': episodes, 'input_hashes': inputs,
              'interpretation': ['Only completed stored traces and recorded events are summarized.',
                                 'An iteration-limited IK rejection means reachability was unconfirmed, not mathematical proof of unreachability.',
                                 'Planning and pause steps count toward the unchanged 400-step episode and inherited transport timeout.']}
    with destination.open('x', encoding='utf8') as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'passed': True, 'selected_episodes': len(episodes), 'comparisons': comparisons}, ensure_ascii=False))


if __name__ == '__main__':
    main()
