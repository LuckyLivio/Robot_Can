"""Read completed v17 traces; do not run physics, controllers or IK.

Planning receipts, actually executed commands/observations, known-start paired
outcomes and synthetic static cache evidence are deliberately separate.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import hashlib
import json
import sys
import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v16_20261016_01 import inspect_smoke_carry as prior
from reproduction.improvement_v15_20261016_01.recovery.carry_path import HeldEnvelope

TARGET = np.array([.1975, .4025])
DETAIL = {'route', 'held', 'v17', 'v16', 'v15', 'budget'}
EVENT_KEYS = ['carry15_events', 'ik16_events', 'route17_events', 'held16_events', 'held17_events']
STARTS = {'held_transport_search', 'bounded_continuation_started', 'shared_short_route_started'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def finite_stats(values):
    values = list(values)
    if not values:
        return None
    return {'minimum': min(values), 'median': float(np.median(values)), 'maximum': max(values),
            'sum': sum(values), 'samples': len(values)}


def option_summary(option):
    result = prior.option_summary(option)
    path = option.get('path_ik', []) + option.get('prefilter_ik', [])
    result.update(
        short_original_route=option.get('short_original_route', False),
        schedule_at_start=option.get('schedule_at_start'),
        schedule_at_finish=option.get('schedule_at_finish'),
        cache_totals_at_finish=option.get('cache_totals_at_finish'),
        predicted_rigid_object_goals=option.get('predicted_rigid_object_goals'),
        reused_ik_receipts=sum(bool(item.get('cache_hit')) for item in path),
        actual_ik_iterations_excluding_reused_receipts=sum(item['iterations'] for item in path if not item.get('cache_hit')),
        # A reused receipt keeps its original iterations for provenance, but
        # production charges one work unit. Never count those as new solves.
        receipt_iterations_including_reused=sum(item['iterations'] for item in path),
    )
    return result


def segment_summary(rows, label, goal=None, reference=None):
    selected = [r for r in rows if r['recovery'].get('carry_segment') == label]
    if label == 'placement':
        selected = [r for r in rows if r['recovery'].get('mode') in ['PLACE', 'PLACE_HOLD']]
    if not selected:
        return None
    result = {'segment': label, **prior.pose_summary(selected, reference)}
    result['terminal_continuation_steps'] = [r['step'] for r in selected if r['recovery'].get('terminal_route')]
    result['terminal_phase_ages'] = [r['recovery']['terminal_phase_age'] for r in selected if r['recovery'].get('terminal_route')]
    result['command_types'] = dict(Counter(
        'mixed' if np.linalg.norm(r['submitted_action'][:3]) > 1e-10 and np.linalg.norm(r['submitted_action'][3:6]) > 1e-10
        else 'translation' if np.linalg.norm(r['submitted_action'][:3]) > 1e-10
        else 'rotation' if np.linalg.norm(r['submitted_action'][3:6]) > 1e-10 else 'zero_pose'
        for r in selected))
    mixed = [(r, r['recovery']['mixed_pose']) for r in selected if 'mixed_pose' in r['recovery']]
    if mixed:
        result['mixed_certificates'] = {'accepted': sum(bool(m['accepted']) for _, m in mixed),
                                        'rejected': sum(not m['accepted'] for _, m in mixed),
                                        'maximum_work': max(m['work'] for _, m in mixed)}
        errors = [{'step': r['step'], 'position_m': m.get('position_error_m'),
                   'angle_rad': m.get('orientation_error_rad')} for r, m in mixed if m.get('position_error_m') is not None]
        if errors:
            result.update(first_actual_error=errors[0], last_actual_error=errors[-1],
                          minimum_actual_position_error_m=min(e['position_m'] for e in errors),
                          minimum_actual_orientation_error_rad=min(e['angle_rad'] for e in errors))
        updates = [m['state_update'] for _, m in mixed if 'state_update' in m]
        if updates:
            result['actual_commanded_goal'] = updates[-1]['goal']
            result['actual_commanded_rotation'] = updates[-1]['rotation']
            if goal is not None:
                assert all(np.array_equal(np.asarray(u['goal']), np.asarray(goal)) for u in updates)
                result['saved_servo_goal_equals_search_goal'] = True
    if goal is not None:
        values = [{'step': r['step'], 'm': float(np.linalg.norm(np.asarray(r['state_before'])[:3]-goal))} for r in selected]
        result.update(search_goal=goal, distance_first=values[0], distance_last=values[-1])
    result['planning_wall_ms'] = finite_stats(r['recovery'].get('planning_ms', 0.) for r in selected)
    return result


def searches(record, rows):
    all_events = [e for key in EVENT_KEYS for e in record.get(key, [])]
    starts = sorted({e['step'] for e in all_events if e['event'] in STARTS})
    finishes = [e for e in record.get('carry15_events', []) if e['event'] == 'held_transport_search_complete']
    result = []
    for index, start in enumerate(starts):
        next_start = starts[index+1] if index+1 < len(starts) else rows[-1]['step']+1
        finish = next((e for e in finishes if start <= e['step'] < next_start), None)
        abort = next((e for e in record.get('carry15_events', [])
                      if start <= e['step'] < next_start and e['event'] in
                      ['held_transform_invalidated', 'path_stopped_parent_hold_or_phase_guard']), None)
        end = finish['step'] if finish else abort['step'] if abort else next_start-1
        observations = [r for r in rows if start <= r['step'] <= end]
        planning = [r for r in observations if r['recovery'].get('planning_kind') == 'v15_carry']
        reference = HeldEnvelope.from_state(rows[start-1]['state_before'])
        output = {'start_step': start, 'finish_step': finish['step'] if finish else None,
                  'remaining_at_start': 400-start, 'remaining_at_finish': 400-end,
                  'elapsed_control_steps_inclusive': end-start+1,
                  'planning_calls': len(planning),
                  'positive_work_calls': sum(r['recovery'].get('planning_work_units', 0) > 0 for r in planning),
                  'actual_trace_work': sum(r['recovery'].get('planning_work_units', 0) for r in planning),
                  'maximum_work_per_control_step': max((r['recovery'].get('planning_work_units', 0) for r in planning), default=0),
                  'planning_wall_ms': finite_stats(r['recovery'].get('planning_ms', 0.) for r in planning),
                  'planning_observed_hold_and_joints': prior.pose_summary(observations, reference),
                  'start_observation': rows[start-1]['state_before'],
                  'start_observed_joints': rows[start-1]['joint_positions'],
                  'chosen': finish.get('chosen') if finish else None,
                  'aborted_without_completion': abort if finish is None else None,
                  'cache_totals_available': bool(finish and finish['options'] and finish['options'][-1].get('cache_totals_at_finish') is not None)}
        if finish:
            assert output['actual_trace_work'] == finish['work'], (start, output, finish)
            output['receipt_work'] = finish['work']
            output['options'] = [option_summary(o) for o in finish['options']]
            output['actual_cache_totals'] = finish['options'][-1].get('cache_totals_at_finish') if finish['options'] else None
            accepted = next((o for o in finish['options'] if o['accepted']), None)
            if accepted:
                output['selected_candidate'] = accepted['candidate']
                output['short_original_route'] = accepted.get('short_original_route', False)
                output['selected_schedule'] = accepted.get('schedule_at_finish')
                attempt = rows[end-1]['recovery'].get('attempts')
                execution = []
                for row in rows[end:next_start-1]:
                    if row['recovery'].get('attempts') != attempt:
                        break
                    execution.append(row)
                carry = [r for r in execution if r['recovery'].get('mode') in ['CARRY_PATH', 'CARRY', 'CARRY_HOLD', 'CARRY_GUARD', 'PLACE', 'PLACE_HOLD']]
                output['execution_actual_hold_and_joints'] = prior.pose_summary(carry, reference)
                labels = list(dict.fromkeys(r['recovery'].get('carry_segment') for r in execution if r['recovery'].get('carry_segment')))+['placement']
                output['segments'] = []
                for label in labels:
                    goal = accepted.get('carry_goal') if label in ['direct_transport', 'transport'] else accepted.get('place_goal') if label == 'placement' else None
                    item = segment_summary(execution, label, goal, reference)
                    if item is not None:
                        output['segments'].append(item)
                path = accepted.get('path_ik', [])
                if path and carry:
                    output['ik_certificate_vs_observed_execution'] = {
                        'minimum_certified_joint_margin_rad': min(r['limit_margin_rad'] for r in path),
                        'minimum_observed_joint_margin_rad': min(prior.margin(r['joint_positions']) for r in carry),
                        'different_joint_paths_possible': True,
                        'certificate_does_not_prove_tracking_or_grasp_success': True}
                output['following_phase_transitions'] = [e for e in record.get('events', []) if end < e['step'] < next_start]
        result.append(output)
    return result


def inspect_job(stage, job):
    folder = stage/job['id']
    result = read(folder/'result.json')
    assert result['status'] == 'complete' and result['job'] == job and len(result['records']) == 1
    record = result['records'][0]
    rows = list(map(json.loads, (folder/'trace.jsonl').open(encoding='utf8')))
    assert len(rows) == record['steps'] and rows[-1]['success_after'] == record['success']
    assert [r['step'] for r in rows] == list(range(1, len(rows)+1))
    after = np.asarray(rows[-1]['state_after'])
    first = lambda predicate: next((r['step'] for r in rows if predicate(r)), None)
    item = {'job': job['id'], 'profile': job['id'].split('_', 1)[1], 'version': job['version'],
            'dataset': job.get('dataset'), 'demo': record['demo'], 'comparison_profile': job.get('comparison_profile'),
            'method': job['method'], 'seed': job.get('seed'), 'noise': job['noise'],
            'success': record['success'], 'steps': record['steps'],
            'first_stable_hold_step': first(lambda r: r['recovery'].get('stable_hold')),
            'first_carry_step': first(lambda r: r['recovery'].get('mode', '').startswith('CARRY')),
            'first_place_step': first(lambda r: r['recovery'].get('mode', '').startswith('PLACE')),
            'first_release_step': first(lambda r: r['recovery'].get('mode') == 'RELEASE'),
            'last_submitted_mode': rows[-1]['recovery'].get('mode'),
            'last_next_mode': rows[-1]['recovery'].get('next_mode'),
            'last_stable_hold': rows[-1]['recovery'].get('stable_hold'),
            'final_object_after_physics': after[16:19],
            'final_object_xy_error_m': float(np.linalg.norm(after[16:18]-TARGET)),
            'phase_counts': dict(Counter(r['recovery'].get('mode') for r in rows)),
            'first_observation': rows[0]['state_before'], 'first_joints': rows[0]['joint_positions'],
            'source_result_sha256': sha(folder/'result.json'), 'source_trace_sha256': sha(folder/'trace.jsonl'),
            'first_new_servo_step': first(lambda r: r['recovery'].get('planning_kind', '').startswith('v17_')),
            'new_intervention_steps': dict(Counter(r['recovery'].get('planning_kind') for r in rows if r['recovery'].get('planning_kind', '').startswith('v17_')))}
    if job['version'] in DETAIL:
        item.update(searches=searches(record, rows), phase_intervals=prior.phase_intervals(rows),
                    phase_transitions=record.get('events', []), budget_events=record.get('budget15_events', []))
        item['guard_and_settled_events'] = [{k: v for k, v in e.items() if k != 'options'}
                                          for key in EVENT_KEYS for e in record.get(key, [])
                                          if 'guard' in e['event'] or 'settled' in e['event'] or 'invalidated' in e['event']]
    return item, rows


def compare(item, rows, reference, old_rows):
    prefix = min(len(rows), len(old_rows))
    action_first = None
    state_first = None
    for row, old in zip(rows, old_rows):
        if action_first is None and not np.array_equal(row['submitted_action'], old['submitted_action']):
            action_first = {'step': row['step'], 'mode': row['recovery']['mode'],
                            'reference_mode': old['recovery']['mode'], 'planning_kind': row['recovery'].get('planning_kind'),
                            'state_before_exact': np.array_equal(row['state_before'], old['state_before'])}
        if state_first is None and not np.array_equal(row['state_before'], old['state_before']):
            state_first = row['step']
    delta = None
    if item['first_carry_step'] is not None and reference['first_carry_step'] is not None:
        delta = item['first_carry_step']-reference['first_carry_step']
    if action_first is None:
        interpretation = 'Same submitted actions over the compared prefix; no new carry repair effect demonstrated there.'
    elif action_first['mode'].startswith('EDGE') or str(action_first['planning_kind']).startswith('v17_edge'):
        interpretation = 'First changed command is upstream edge control; later carry start and remaining budget are already affected by that upstream intervention.'
    elif action_first['mode'].startswith(('CARRY', 'PLACE')):
        interpretation = 'First changed command occurs in held transport/placement after the common observed prefix; inspect bounded planning and actual tracking separately.'
    else:
        interpretation = 'First changed command occurs before the final failure; phase/attempt transitions are supplied rather than assigning causation from the last frame.'
    return {'reference_version': reference['version'], 'reference_is_new_executed_baseline': True,
            'success_pair': [reference['success'], item['success']], 'step_pair': [reference['steps'], item['steps']],
            'compared_prefix_steps': prefix, 'first_changed_submitted_action': action_first,
            'first_changed_state_before_step': state_first, 'first_carry_step_delta': delta,
            'reference_first_carry_step': reference['first_carry_step'], 'current_first_carry_step': item['first_carry_step'],
            'interpretation': interpretation}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', default='smoke_a')
    parser.add_argument('--output', default='smoke_a_carry_diagnosis.json')
    args = parser.parse_args()
    stage, destination = RUN/args.stage, RUN/'analysis'/args.output
    assert not destination.exists(), 'Preserve earlier receipts.'
    completion = read(stage/'completed.json')
    assert completion['episodes'] == 63 and completion['source_unchanged']
    jobs = read(stage/'jobs.json')
    assert len(jobs) == 63
    evidence, trajectories, profiles = [], {}, defaultdict(dict)
    for job in jobs:
        item, rows = inspect_job(stage, job)
        evidence.append(item);trajectories[item['job']] = rows
        profiles[item['profile']][item['version']] = item
    comparisons, repeated, groups = [], [], defaultdict(list)
    for profile, versions in profiles.items():
        ref = versions['v16']
        groups[(ref['dataset'], ref['demo'])].append(ref)
        for item in versions.values():
            np.testing.assert_array_equal(item['first_observation'], ref['first_observation'])
            np.testing.assert_array_equal(item['first_joints'], ref['first_joints'])
            if item['version'] in ['route', 'held', 'v17']:
                item['paired_execution_comparisons'] = [compare(item, trajectories[item['job']], versions[v], trajectories[versions[v]['job']]) for v in ['v16', 'v15', 'budget']]
        comparisons.append({'profile': profile, 'initial_inputs_exact': True,
                            'results': {v: {k: item[k] for k in ['success', 'steps', 'first_carry_step', 'last_submitted_mode']} for v, item in versions.items()}})
    for (dataset, demo), members in groups.items():
        if len(members) > 1:
            for item in members[1:]:
                np.testing.assert_array_equal(item['first_observation'], members[0]['first_observation'])
                np.testing.assert_array_equal(item['first_joints'], members[0]['first_joints'])
            repeated.append({'dataset': dataset, 'demo': demo, 'profiles': [i['profile'] for i in members],
                             'same_start_different_registered_profile': True})
    cache = []
    for item in evidence:
        for search in item.get('searches', []):
            if search.get('actual_cache_totals') is not None:
                cache.append({'job': item['job'], 'start_step': search['start_step'], 'success': item['success'],
                              'actual_trace_work': search['actual_trace_work'], 'planning_calls': search['planning_calls'],
                              'planning_wall_ms': search['planning_wall_ms'], 'chosen': search['chosen'],
                              'selected_candidate': search.get('selected_candidate'), **search['actual_cache_totals']})
    static_path = RUN/'analysis/carry_search_static_b.json'
    static = read(static_path)
    output = {'script_sha256': sha(__file__), 'shared_read_only_analysis_sha256': sha(prior.__file__),
              'completed_sha256': sha(stage/'completed.json'), 'started_sha256': sha(stage/'started.json'),
              'jobs_sha256': sha(stage/'jobs.json'), 'new_physical_episodes': 0, 'new_controller_replays': 0,
              'new_ik_searches': 0, 'saved_physical_executions_analyzed': len(evidence),
              'known_profiles': len(profiles), 'unique_dataset_demo_starts': len(groups),
              'repeated_start_profiles': repeated, 'paired_comparisons': comparisons,
              'actual_closed_loop_cache_use': cache,
              'static_mechanism_evidence_separate': {'source_sha256': sha(static_path), 'passed': static['passed'],
                                                   'cache_probe': static['cache_probe'],
                                                   'interpretation': 'Saved-state synthetic-clock mechanism test, not closed-loop savings, success or generalization evidence.'},
              'episodes': evidence,
              'scope': ['No physics, controller replay or IK executed by this analysis.',
                        'All current v15/v16/budget baselines were newly executed in this stage.',
                        'Eight unique starts reused by nine known profiles; not independent confirmation.',
                        'Cached receipt iteration counts are not charged again as actual IK work.',
                        'Wall time is observed and subject to parallel-worker scheduling; cache work savings alone do not prove wall-time or outcome gains.',
                        'IK certificates are not commanded joint paths; actual grasp loss and joint margins use saved observations.',
                        'First intervention/common-prefix evidence locates divergence; does not establish isolated causal contributions for combined changes.']}
    with destination.open('x', encoding='utf8') as handle:
        json.dump(prior.serial(output), handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'output': str(destination), 'executions': len(evidence),
                      'outcomes': {v: sum(i['success'] for i in evidence if i['version'] == v) for v in sorted({i['version'] for i in evidence})},
                      'actual_searches_with_cache_receipts': len(cache)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
