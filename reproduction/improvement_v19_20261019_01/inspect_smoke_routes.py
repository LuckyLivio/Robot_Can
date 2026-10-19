"""Read 72 completed v19 smoke runs; do not execute control, IK or physics."""
from pathlib import Path
from collections import Counter, defaultdict
from unittest.mock import patch
import argparse
import json
import sys
import numpy as np

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v18_20261019_01 import inspect_smoke_route as parent

VERSIONS = {'v17', 'v18', 'budget', 'transition', 'candidate', 'settling', 'ab', 'v19'}
NEW = {'transition', 'candidate', 'settling', 'ab', 'v19'}
FOCUS = {'known_full_s23_clean_demo_12000036', 'held_wait_demo87',
         'known_bc_k2_clean_demo_12000011', 'known13_bc_k2_noise005_demo_13000021',
         'known13_full_s41_noise005_demo_13000022', 'regression_6000005', 'clearance_profile_6000005'}


def inspect(stage, job):
    # Extend only the read-only analyzer's event schema, never a controller.
    with patch.object(parent, 'VERSIONS', VERSIONS), \
         patch.object(parent.common, 'EVENT_KEYS', parent.common.EVENT_KEYS+['budget19_events']), \
         patch.object(parent.common, 'STARTS', parent.common.STARTS|{'bounded_optional_search_started'}):
        item, rows = parent.inspect(stage, job)
    record = parent.read(stage/job['id']/'result.json')['records'][0]
    starts = {e['step'] for e in record.get('budget19_events', []) if e['event'] == 'bounded_optional_search_started'}
    item['candidate_budget_enabled'] = bool(job['config'].get('candidate_budget'))
    item['new_candidate_search_start_steps'] = sorted(starts)
    item['phase_entry_events'] = [e for e in record.get('events', [])
                                  if e.get('to') in ['CARRY', 'PLACE', 'RELEASE', 'EXHAUSTED']]
    item['last_remaining_steps'] = 400-item['steps']
    for search in item['searches']:
        search['v19_candidate_policy_used'] = search['start_step'] in starts
        search['candidate_cost_and_admission'] = [
            {key: option.get(key) for key in ['candidate', 'reason', 'accepted', 'status',
                                             'candidate_work_start', 'candidate_work', 'candidate_work_limit',
                                             'optional_endpoint_candidate', 'admission', 'unfinished_local_ik']}
            for option in search.get('complete_original_options', [])]
        if search['v19_candidate_policy_used']:
            for option in search.get('complete_original_options', []):
                if option['candidate'] == 'current_rotation_inset':
                    assert option['candidate_work'] <= 48
                    if 'admission' in option and not option['admission']['admitted']:
                        assert option['candidate_work'] == 1 and not option['path_ik'] and not option['geometry']
        search['post_search_phase_entry_events'] = [e for e in item['phase_entry_events']
                                                   if search['finish_step'] is not None and e['step'] >= search['finish_step']]
    return item, rows


def paired_searches(item, baseline):
    pairs = []
    for index, current in enumerate(item['searches']):
        if index >= len(baseline['searches']):
            pairs.append({'current_search_index': index, 'baseline_search_missing': True})
            continue
        previous = baseline['searches'][index]
        same = bool(np.array_equal(current['start_observation'], previous['start_observation']) and
                    np.array_equal(current['start_observed_joints'], previous['start_observed_joints']))
        accepted = next((o for o in current.get('complete_original_options', []) if o['accepted']), None)
        old_accepted = next((o for o in previous.get('complete_original_options', []) if o['accepted']), None)
        same_target = bool(accepted and old_accepted and
                           np.array_equal(accepted['carry_goal'], old_accepted['carry_goal']) and
                           np.array_equal(accepted['place_goal'], old_accepted['place_goal']))
        pairs.append({'current_search_index': index, 'same_search_start_observation_and_q': same,
                      'start_steps_baseline_current': [previous['start_step'], current['start_step']],
                      'finish_steps_baseline_current': [previous['finish_step'], current['finish_step']],
                      'work_baseline_current': [previous['actual_trace_work'], current['actual_trace_work']],
                      'calls_baseline_current': [previous['planning_calls'], current['planning_calls']],
                      'candidate_baseline_current': [previous.get('selected_candidate'), current.get('selected_candidate')],
                      'same_accepted_targets': same_target,
                      'current_lifecycle': current['route_lifecycle'],
                      'interpretation': ('Same recorded search inputs; numerical work and actual calls can be directly compared.' if same else
                                         'Different recorded search inputs; upstream changes or a prior attempt already affect this comparison.')})
    return pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', default='smoke_a')
    parser.add_argument('--output', default='smoke_a_route_diagnosis.json')
    args = parser.parse_args()
    stage, output = RUN/args.stage, RUN/'analysis'/args.output
    assert not output.exists()
    completion = parent.read(stage/'completed.json')
    assert completion['episodes'] == 72 and completion['source_unchanged']
    jobs = parent.read(stage/'jobs.json')
    assert len(jobs) == 72 and {j['version'] for j in jobs} == VERSIONS
    files = [Path(__file__), Path(parent.__file__), Path(parent.common.__file__), Path(parent.numerical.__file__),
             stage/'jobs.json', stage/'started.json', stage/'completed.json', RUN/'analysis/candidate_static_a.json']
    files += [p for p in (stage/'source').rglob('*') if p.is_file() and p.suffix in ['.py', '.json', '.md']]
    for job in jobs: files += [stage/job['id']/'result.json', stage/job['id']/'trace.jsonl']
    sources = {p.relative_to(ROOT).as_posix(): parent.sha(p) for p in files}
    episodes, trajectories, profiles = [], {}, defaultdict(dict)
    for job in jobs:
        item, rows = inspect(stage, job)
        episodes.append(item); trajectories[item['job']] = rows; profiles[item['profile']][item['version']] = item
    groups = defaultdict(list)
    for profile, group in profiles.items():
        ref = group['v18']
        groups[(ref['dataset'], ref['demo'])].append(ref)
        for version, item in group.items():
            np.testing.assert_array_equal(item['first_observation'], ref['first_observation'])
            np.testing.assert_array_equal(item['first_joints'], ref['first_joints'])
            if version not in NEW: continue
            item['comparisons_to_actual_baselines'] = []
            for reference_version in ['v17', 'v18', 'budget']:
                reference = group[reference_version]
                comparison = parent.common.compare(item, trajectories[item['job']], reference, trajectories[reference['job']])
                comparison.update(paired_searches=paired_searches(item, reference),
                                  baseline_phase_entry_events=reference['phase_entry_events'],
                                  current_phase_entry_events=item['phase_entry_events'],
                                  current_planning_work=sum(s['actual_trace_work'] for s in item['searches']),
                                  baseline_planning_work=sum(s['actual_trace_work'] for s in reference['searches']))
                item['comparisons_to_actual_baselines'].append(comparison)
    repeated = []
    for (dataset, demo), group in groups.items():
        if len(group) > 1:
            for item in group[1:]:
                np.testing.assert_array_equal(item['first_observation'], group[0]['first_observation'])
                np.testing.assert_array_equal(item['first_joints'], group[0]['first_joints'])
            repeated.append({'dataset': dataset, 'demo': demo, 'profiles': [i['profile'] for i in group]})
    summary = {}
    for version in sorted(VERSIONS):
        group = [e for e in episodes if e['version'] == version]
        searches = [s for e in group for s in e['searches']]
        optional = [o for s in searches for o in s.get('complete_original_options', []) if o['candidate'] == 'current_rotation_inset']
        new_optional = [o for s in searches if s['v19_candidate_policy_used']
                        for o in s.get('complete_original_options', []) if o['candidate'] == 'current_rotation_inset']
        summary[version] = {'executions': len(group), 'successes': sum(e['success'] for e in group),
                            'searches': len(searches), 'v19_candidate_searches': sum(s['v19_candidate_policy_used'] for s in searches),
                            'total_planning_work': sum(s['actual_trace_work'] for s in searches),
                            'total_planning_calls': sum(s['planning_calls'] for s in searches),
                            'chosen_candidates': dict(Counter(s['selected_candidate'] for s in searches if 'selected_candidate' in s)),
                            'search_lifecycles': dict(Counter(s['route_lifecycle'] for s in searches)),
                            'no_search_jobs': [e['job'] for e in group if not e['searches']],
                            'optional_candidate_reasons': dict(Counter(o['reason'] for o in optional)),
                            'new_policy_optional_work': [o['candidate_work'] for o in new_optional],
                            'new_policy_optional_admitted': sum(o.get('admission', {}).get('admitted', False) for o in new_optional),
                            'new_policy_optional_denied': sum('admission' in o and not o['admission']['admitted'] for o in new_optional),
                            'new_policy_optional_admission_not_reached': sum('admission' not in o for o in new_optional)}
    static = parent.read(RUN/'analysis/candidate_static_a.json')
    result = {'source_sha256': sources, 'new_physical_episodes': 0, 'new_controller_replays': 0, 'new_ik_searches': 0,
              'saved_physical_executions_analyzed': len(episodes), 'known_profiles': len(profiles),
              'unique_dataset_demo_starts': len(groups), 'repeated_start_profiles': repeated,
              'summary': summary, 'episodes': episodes,
              'focus_profiles': {profile: [e['job'] for e in episodes if e['profile'] == profile] for profile in sorted(FOCUS)},
              'static_evidence_separate': {'passed': static['passed'], 'selected_counts': static['selected_counts'],
                                           'interpretation': 'Saved-state mechanism checks do not establish actual work savings or physical success.'},
              'scope': ['All 72 actual result/trace pairs analyzed, including newly executed v17/v18/budget.',
                        'Known repeated diagnostic starts; this is not independent confirmation.',
                        'Candidate admission denial and work cap are unknown planning outcomes, not unreachable classifications.',
                        'Compare matched recorded search inputs separately from searches changed by upstream controls or prior attempts.',
                        'Candidate work/calls, observed motion, guard events and success remain separate evidence.',
                        'Phase entry events and first commands in that phase are separately labeled; they commonly differ by one tick.',
                        'Budget uses older held protection and cannot be adopted based on task-success count alone.',
                        'No runtime source, old artifact, controller, IK or simulator is modified or executed.']}
    assert all(parent.sha(ROOT/path) == digest for path, digest in sources.items())
    with output.open('x', encoding='utf8') as stream:
        json.dump(parent.numerical.serial(result), stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'output': str(output), 'summary': summary}, ensure_ascii=False))


if __name__ == '__main__': main()
