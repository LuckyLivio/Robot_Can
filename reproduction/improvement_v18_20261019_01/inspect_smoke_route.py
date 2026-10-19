"""Read all completed v18 smoke trajectories; never run physics, IK or control.

New finite-route search, actual command execution, and prior static evidence
are kept separate. Baseline comparisons use new executions in this same stage.
"""
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import patch
import argparse
import hashlib
import json
import sys
import numpy as np

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v17_20261019_01 import inspect_smoke_carry as common
from reproduction.improvement_v16_20261016_01 import inspect_smoke_carry as numerical

VERSIONS = {'v16', 'v17', 'budget', 'handoff', 'short', 'v18'}
CANDIDATES = ['current_exact', 'current_rotation_inset']
FOCUS = {'known_full_s23_clean_demo_12000036', 'regression_6000005',
         'clearance_profile_6000005', 'held_wait_demo87', 'known13_bc_k2_noise005_demo_13000021'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def inspect(stage, job):
    # Extend only the read-only analyzer's recognized event vocabulary.
    # The saved result, runtime controller and parent files remain untouched.
    with patch.object(common, 'DETAIL', VERSIONS), \
         patch.object(common, 'EVENT_KEYS', common.EVENT_KEYS+['route18_events']), \
         patch.object(common, 'STARTS', common.STARTS|{'short_route_search_started'}):
        item, rows = common.inspect_job(stage, job)
    record = read(stage/job['id']/'result.json')['records'][0]
    finishes = {e['step']: e for e in record.get('carry15_events', [])
                if e['event'] == 'held_transport_search_complete'}
    item['v18_helper_start_steps'] = [e['step'] for e in record.get('route18_events', [])
                                    if e['event'] == 'short_route_search_started']
    item['v18_helper_enabled'] = bool(job['config'].get('short_route_selection'))
    item['carry_relevant_events'] = [dict(source_event_list=key, **event)
                                    for key in ['events', 'carry15_events', 'held16_events', 'held17_events', 'budget15_events']
                                    for event in record.get(key, [])
                                    if ('guard' in event.get('event', '') or 'settled' in event.get('event', '')
                                        or 'invalidated' in event.get('event', '') or 'timeout' in str(event.get('reason', ''))
                                        or event.get('from') in ['LIFT', 'CARRY', 'PLACE', 'RELEASE']
                                        or event.get('to') in ['CARRY', 'PLACE', 'RELEASE', 'EXHAUSTED'])]
    for index, search in enumerate(item['searches']):
        search['is_new_v18_helper'] = search['start_step'] in item['v18_helper_start_steps']
        finish = finishes.get(search['finish_step'])
        if not finish:
            search['route_lifecycle'] = 'search_aborted_or_unfinished'
            continue
        search['complete_original_options'] = finish['options']
        for concise, raw in zip(search['options'], finish['options']):
            assert concise['candidate'] == raw['candidate']
            concise.update(short_verified_route=raw.get('short_verified_route'),
                           endpoint_family=raw.get('endpoint_family'),
                           endpoint_change_is_not_pure_ik_repair=raw.get('endpoint_change_is_not_pure_ik_repair'))
        accepted = next((option for option in finish['options'] if option['accepted']), None)
        if accepted is None:
            search['route_lifecycle'] = 'called_but_no_route_selected'
            search['following_transition'] = next((event for event in record['events']
                                                    if event['step'] >= finish['step']), None)
            continue
        next_start = item['searches'][index+1]['start_step'] if index+1 < len(item['searches']) else len(rows)+1
        attempt = rows[finish['step']-1]['recovery'].get('attempts')
        executed = []
        for row in rows[finish['step']:next_start-1]:
            if row['recovery'].get('attempts') != attempt: break
            executed.append(row)
        carry_rows = [row for row in executed if row['recovery'].get('carry_segment')]
        succeeded = any(row['success_after'] for row in executed)
        search['selected_route_execution'] = {
            'attempt': attempt, 'first_step': executed[0]['step'] if executed else None,
            'last_step': executed[-1]['step'] if executed else None,
            'submitted_carry_segment_steps': [row['step'] for row in carry_rows],
            'nonzero_carry_commands': sum(np.linalg.norm(row['submitted_action'][:6]) > 1e-10 for row in carry_rows),
            'task_success_before_next_attempt': succeeded,
            'first_guard_or_failure_event': next((event for event in item['carry_relevant_events']
                                                  if finish['step'] < event['step'] < next_start and
                                                  ('guard' in event.get('event', '') or 'invalidated' in event.get('event', '')
                                                   or 'timeout' in str(event.get('reason', '')))), None),
            'final_episode_success_is_not_automatically_attributed_to_this_route': True,
        }
        search['route_lifecycle'] = ('selected_and_success_before_next_attempt' if succeeded else
                                     'selected_and_executed_without_success' if carry_rows else
                                     'selected_but_no_carry_segment_submitted')
    item['episode_route_lifecycle'] = ('no_search_called' if not item['searches'] else
                                      'called_no_route_selected' if not any(s.get('chosen') for s in item['searches']) else
                                      'route_selected_episode_success' if item['success'] else 'route_selected_episode_failed')
    item['candidate_lifecycle'] = {}
    for candidate in CANDIDATES:
        attempts = [(search, option) for search in item['searches']
                    for option in search.get('options', []) if option['candidate'] == candidate]
        selections = [search for search, option in attempts if option['accepted']]
        item['candidate_lifecycle'][candidate] = {
            'search_called': bool(item['searches']), 'attempted_count': len(attempts),
            'selected_count': len(selections),
            'reasons': dict(Counter(option['reason'] for _, option in attempts)),
            'selected_route_lifecycles': dict(Counter(search['route_lifecycle'] for search in selections)),
            'interpretation': ('not_called' if not item['searches'] else
                               'not_attempted_before_search_stopped_or_another_route_accepted' if not attempts else
                               'attempted_not_selected' if not selections else 'selected_inspect_execution'),
        }
    return item, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', default='smoke_a')
    parser.add_argument('--output', default='smoke_a_route_diagnosis.json')
    args = parser.parse_args()
    stage = RUN/args.stage
    destination = RUN/'analysis'/args.output
    assert not destination.exists(), 'Preserve all previous diagnostic receipts.'
    completion = read(stage/'completed.json')
    assert completion['episodes'] == 54 and completion['source_unchanged']
    jobs = read(stage/'jobs.json')
    assert len(jobs) == 54 and {j['version'] for j in jobs} == VERSIONS
    paths = [Path(__file__), Path(common.__file__), Path(numerical.__file__),
             stage/'jobs.json', stage/'completed.json', stage/'started.json',
             RUN/'analysis/short_route_static_a.json', RUN/'analysis/short_route_diagnosis_a.json']
    # Hash the frozen code snapshot, not unrelated report/frontend outputs.
    paths += [p for p in (stage/'source').rglob('*') if p.is_file() and p.suffix in ['.py', '.json', '.md']]
    for job in jobs: paths += [stage/job['id']/'result.json', stage/job['id']/'trace.jsonl']
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    episodes, trajectories, profiles = [], {}, defaultdict(dict)
    for job in jobs:
        item, rows = inspect(stage, job)
        episodes.append(item)
        trajectories[item['job']] = rows
        profiles[item['profile']][item['version']] = item
    pairings, duplicate_groups = [], defaultdict(list)
    for profile, group in profiles.items():
        reference = group['v17']
        duplicate_groups[(reference['dataset'], reference['demo'])].append(reference)
        for version, item in group.items():
            np.testing.assert_array_equal(item['first_observation'], reference['first_observation'])
            np.testing.assert_array_equal(item['first_joints'], reference['first_joints'])
            if version in ['handoff', 'short', 'v18']:
                item['comparison_to_same_stage_v17'] = common.compare(
                    item, trajectories[item['job']], reference, trajectories[reference['job']])
                item['comparison_to_same_stage_v17'].update(
                    reference_search_finishes=[s['finish_step'] for s in reference['searches']],
                    current_search_finishes=[s['finish_step'] for s in item['searches']],
                    reference_planning_work=sum(s['actual_trace_work'] for s in reference['searches']),
                    current_planning_work=sum(s['actual_trace_work'] for s in item['searches']),
                    all_searches_initial_observations_equal=[
                        bool(np.array_equal(a['start_observation'], b['start_observation']) and
                             np.array_equal(a['start_observed_joints'], b['start_observed_joints']))
                        for a, b in zip(item['searches'], reference['searches'])],
                )
        pairings.append({'profile': profile, 'initial_inputs_exact': True,
                         'results': {v: {key: item[key] for key in
                                           ['success', 'steps', 'first_carry_step', 'first_place_step',
                                            'first_release_step', 'episode_route_lifecycle', 'last_submitted_mode']}
                                     for v, item in group.items()}})
    repeated = []
    for (dataset, demo), group in duplicate_groups.items():
        if len(group) > 1:
            for item in group[1:]:
                np.testing.assert_array_equal(item['first_observation'], group[0]['first_observation'])
                np.testing.assert_array_equal(item['first_joints'], group[0]['first_joints'])
            repeated.append({'dataset': dataset, 'demo': demo, 'profiles': [i['profile'] for i in group],
                             'same_start_different_registered_profiles': True})
    statistics = {}
    for version in sorted(VERSIONS):
        group = [item for item in episodes if item['version'] == version]
        searches = [search for item in group for search in item['searches']]
        options = [option for search in searches for option in search.get('options', [])]
        statistics[version] = {
            'executions': len(group), 'successes': sum(item['success'] for item in group),
            'searches': len(searches), 'new_v18_helper_searches': sum(s['is_new_v18_helper'] for s in searches),
            'selected_candidates': dict(Counter(s['selected_candidate'] for s in searches if 'selected_candidate' in s)),
            'candidate_reasons': {candidate: dict(Counter(o['reason'] for o in options if o['candidate'] == candidate))
                                  for candidate in CANDIDATES},
            'search_lifecycles': dict(Counter(s['route_lifecycle'] for s in searches)),
            'no_search_executions': [i['job'] for i in group if not i['searches']],
            'actual_total_planning_work': sum(s['actual_trace_work'] for s in searches),
            'planning_call_counts': [s['planning_calls'] for s in searches],
            'actual_planning_wall_ms': common.finite_stats(s['planning_wall_ms']['sum'] for s in searches if s['planning_wall_ms']),
        }
    static = read(RUN/'analysis/short_route_static_a.json')
    out = {'source_sha256': sources, 'saved_physical_executions_analyzed': len(episodes),
           'new_physical_episodes': 0, 'new_controller_replays': 0, 'new_ik_searches': 0,
           'known_profiles': len(profiles), 'unique_dataset_demo_starts': len(duplicate_groups),
           'repeated_start_profiles': repeated, 'statistics': statistics,
           'paired_comparisons': pairings, 'episodes': episodes,
           'focus_profiles': {name: [item['job'] for item in episodes if item['profile'] == name] for name in sorted(FOCUS)},
           'static_evidence_separate': {'passed': static['passed'], 'chosen_counts': static['chosen_counts'],
                                        'interpretation': 'Saved-state finite route checks, not actual selections, execution savings or successes.'},
           'scope': ['All 54 result and trace files must be complete; no new simulation, controller replay or IK is run.',
                     'v16/v17/budget references are actual newly executed episodes in this stage.',
                     'Nine registered profiles use eight starts; this is a diagnostic smoke test, not independent confirmation.',
                     'No search, attempted-but-unselected and selected execution failure are reported separately.',
                     'A successful IK/geometry route certificate does not prove physical joint tracking or grasp stability.',
                     'Budget is the unchanged old profile with different held protection; its task count is not an adoptable guarded reference.',
                     'Wall time is measured under concurrent worker scheduling; work counts and physical outcomes are separate.',
                     'Paired first command/state divergence locates intervention; combined changes do not establish isolated causality.']}
    assert all(sha(ROOT/path) == digest for path, digest in sources.items()), 'An analyzed source changed'
    with destination.open('x', encoding='utf8') as handle:
        json.dump(numerical.serial(out), handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'output': str(destination), 'executions': len(episodes),
                      'statistics': statistics}, ensure_ascii=False))


if __name__ == '__main__':
    main()
