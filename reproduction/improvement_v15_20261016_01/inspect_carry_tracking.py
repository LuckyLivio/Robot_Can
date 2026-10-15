"""Explain the completed smoke_a carry gate failure using stored data only.

No simulator, controller execution, new IK search, or parameter changes occur.
The known selected 30-degree target is reconstructed from the frozen formula
and the observed planning-start state; all inputs and receipts are hashed.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
STAGE = RUN/'smoke_a'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_job(name):
    folder = STAGE/name
    result = json.loads((folder/'result.json').read_text(encoding='utf8'))
    rows = list(map(json.loads, (folder/'trace.jsonl').open(encoding='utf8')))
    assert result['status'] == 'complete' and len(result['records']) == 1
    assert len(rows) == result['records'][0]['steps']
    return result, rows, {'job': name, 'result_sha256': digest(folder/'result.json'),
                          'trace_sha256': digest(folder/'trace.jsonl')}


def main():
    destination = RUN/'analysis/smoke_a_carry_tracking.json'
    assert not destination.exists(), 'Do not overwrite an existing receipt.'
    assert (STAGE/'completed.json').exists()
    suffix = 'known13_bc_k2_noise005_demo_13000021'
    result, rows, source = load_job('carry_'+suffix)
    events = result['records'][0]['carry15_events']
    start = next(event for event in events if event['event'] == 'held_transport_search')
    target_search_starts = [event for event in events if event['event'] == 'held_transport_search']
    finish = next(event for event in events if event['event'] == 'held_transport_search_complete')
    selected = next(option for option in finish['options'] if option['accepted'])
    assert selected['candidate'] == 'outward_30'
    initial = np.asarray(rows[start['step']-1]['state_before'])
    initial_rotation = Rotation.from_quat(initial[3:7]).as_matrix()
    held_relative = initial_rotation.T @ (initial[16:19]-initial[:3])
    radial = np.array([.1975, .4025])-np.array([-.5, -.1])
    radial /= np.linalg.norm(radial)
    yaw = float(np.arctan2(initial_rotation[1, 0], initial_rotation[0, 0]))
    target_rotation = (Rotation.from_rotvec(-np.deg2rad(30)*np.r_[-radial[1], radial[0], 0.]).as_matrix()
                       @ Rotation.from_euler('z', yaw).as_matrix() @ np.diag([1., -1., -1.]))
    goal = initial[:3].copy()
    goal[2] = max(goal[2], 1.08+(-initial_rotation @ held_relative)[2])
    observations = []
    for row in rows:
        if row['recovery'].get('carry_segment') != 'reorient':
            continue
        x = np.asarray(row['state_before'])
        command = np.asarray(row['submitted_action'])
        position = float(np.linalg.norm(x[:3]-goal))
        angle = float(np.linalg.norm(Rotation.from_matrix(target_rotation @ Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec()))
        translation = bool(np.linalg.norm(command[:3]) > 1e-10)
        rotation = bool(np.linalg.norm(command[3:6]) > 1e-10)
        observations.append({'step': row['step'], 'position_error_m': position, 'orientation_error_rad': angle,
                             'translation_submitted': translation, 'rotation_submitted': rotation,
                             'stable_hold': row['recovery']['stable_hold']})
    counts = Counter('translation_only' if row['translation_submitted'] and not row['rotation_submitted']
                     else 'rotation_only' if row['rotation_submitted'] and not row['translation_submitted']
                     else 'mixed_or_zero' for row in observations)
    assert len(observations) == 70 and counts == {'translation_only': 34, 'rotation_only': 36}
    guard = next(event for event in events if event['event'] == 'held_execution_guard')
    assert guard['step'] == 397
    assert observations[-1]['position_error_m'] > .009 and observations[-1]['orientation_error_rad'] > .08
    v15_result, v15_rows, v15_source = load_job('v15_'+suffix)
    assert len(v15_rows) == len(rows)
    for left, right in zip(rows, v15_rows):
        for key in ['state_before', 'state_after', 'joint_positions', 'submitted_action', 'executed_action']:
            np.testing.assert_array_equal(left[key], right[key])
    sources = [source, v15_source]
    regressions = []
    for old_suffix in ['known_bc_k2_clean_demo_12000011', 'known_full_s23_clean_demo_12000036',
                       'known_full_s23_noise005_demo_12000021']:
        baseline, original_rows, original_source = load_job('v14_'+old_suffix)
        candidate, changed_rows, changed_source = load_job('carry_'+old_suffix)
        sources.extend([original_source, changed_source])
        old, new = baseline['records'][0], candidate['records'][0]
        assert old['success'] and not new['success']
        np.testing.assert_array_equal(original_rows[0]['state_before'], changed_rows[0]['state_before'])
        starts = [event for event in new['carry15_events'] if event['event'] == 'held_transport_search']
        complete = [event for event in new['carry15_events'] if event['event'] == 'held_transport_search_complete']
        first_difference = next((left['step'] for left, right in zip(original_rows, changed_rows)
                                 if left['submitted_action'] != right['submitted_action']), None)
        planning = []
        for event in complete:
            onset = max(start['step'] for start in starts if start['step'] <= event['step'])
            current = next(option for option in event['options'] if option['candidate'] == 'current')
            planning.append({'start_step': onset, 'finish_step': event['step'],
                             'elapsed_control_steps_inclusive': event['step']-onset+1,
                             'work_units': event['work'], 'candidate_selected': event['chosen'],
                             'original_pose_prefilter': [{key: value for key, value in receipt.items() if key != 'q'}
                                                        for receipt in current['prefilter_ik']],
                             'candidate_rejection_reasons': [{'candidate': option['candidate'], 'reason': option['reason']}
                                                             for option in event['options']]})
        regressions.append({'condition': old_suffix, 'baseline_success': True, 'baseline_steps': old['steps'],
                            'carry_success': False, 'carry_steps': new['steps'],
                            'same_initial_observation': True, 'first_submitted_action_difference_step': first_difference,
                            'planning': planning, 'final_mode': changed_rows[-1]['recovery']['mode'],
                            'final_stable_hold': changed_rows[-1]['recovery'].get('stable_hold'),
                            'attempt_end_events': [event for event in new['events'] if event['reason'] in
                                                   ['v15_no_validated_held_path', 'attempt_limit']]})
    output = {'passed': True, 'new_physical_episodes': 0, 'new_controller_replays': 0, 'new_ik_searches': 0,
              'script_sha256': digest(Path(__file__)), 'stage_completion_sha256': digest(STAGE/'completed.json'),
              'sources': sources,
              'target': {'condition': suffix, 'carry_and_v15_physical_states_and_actions_exact': True,
                         'planning_start_step': start['step'], 'planning_finish_step': finish['step'],
                         'planning_work_units': finish['work'], 'remaining_at_planning_finish': 400-finish['step'],
                         'candidate': selected['candidate'], 'reconstructed_rotation_goal': target_rotation.tolist(),
                         'reconstructed_position_goal': goal.tolist(), 'turn_steps': len(observations),
                         'command_mode_counts': dict(counts), 'position_error_min_m': min(row['position_error_m'] for row in observations),
                         'position_error_max_m': max(row['position_error_m'] for row in observations),
                         'last_turn_observation': observations[-1], 'execution_guard': guard,
                         'new_search_after_guard': [event for event in target_search_starts if event['step'] > guard['step']],
                         'observations': observations},
              'unchanged_guards': {'position_arrival_m': .009, 'orientation_arrival_rad': .08,
                                   'position_correction_switch_m': .006, 'phase_timeout_steps': 70,
                                   'episode_budget_steps': 400, 'ik_solution_margin_rad': .04},
              'old_success_regressions': regressions,
              'interpretation': ['The target spends 34 steps correcting position and 36 steps rotating; its turn never meets both strict arrival tolerances before the inherited timeout.',
                                 'Three paired v14 successes fail after candidate planning rejects all paths or consumes the remaining budget. This is empirical regression from conservative planning, not proof that the original tasks were unreachable.',
                                 'An iteration-limited local IK rejection is unconfirmed reachability, not a mathematical infeasibility certificate.',
                                 'This receipt only explains the failed smoke gate. No parameters were changed and no additional physical experiments were run.']}
    with destination.open('x', encoding='utf8') as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'passed': True, 'turn_steps': len(observations), 'command_mode_counts': dict(counts),
                      'last_turn_observation': observations[-1], 'old_success_regressions': len(regressions)}))


if __name__ == '__main__':
    main()
