"""Compact, trace-linked v18 route findings after the 54-run smoke completes."""
from pathlib import Path
import hashlib
import json

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
STAGE = RUN/'smoke_a'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def main():
    prior_path = RUN/'analysis/smoke_a_route_diagnosis.json'
    prior = read(prior_path)
    assert prior['saved_physical_executions_analyzed'] == 54
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), prior_path]}
    regressions, late, inset = [], [], []
    for episode in prior['episodes']:
        profile, version = episode['profile'], episode['version']
        if version not in ['v17', 'handoff', 'short', 'v18']: continue
        if profile == 'known_full_s23_clean_demo_12000036':
            search = episode['searches'][0]
            regressions.append({
                'job': episode['job'], 'success': episode['success'], 'steps': episode['steps'],
                'carry_search_start': search['start_step'], 'search_finish': search['finish_step'],
                'planning_work': search['actual_trace_work'], 'planning_calls': search['planning_calls'],
                'selected_candidate': search['selected_candidate'],
                'phase_transition_events': [e for e in episode['phase_transitions'] if e.get('to') in ['CARRY', 'PLACE', 'RELEASE']],
                'first_submitted_place_step': episode['first_place_step'],
                'first_submitted_release_step': episode['first_release_step'],
                'segment_steps': [{k: segment[k] for k in ['segment', 'first_step', 'last_step', 'observed_steps',
                                                         'minimum_actual_joint_margin_rad', 'hold_false_steps']}
                                  for segment in search['segments']],
                'first_execution_guard': search['selected_route_execution']['first_guard_or_failure_event'],
                'original_short_candidate_reasons': [(o['candidate'], o['reason']) for o in search['options']],
            })
        for search in episode['searches']:
            if search.get('selected_candidate') == 'current_rotation_inset':
                inset.append({'job': episode['job'], 'search_start': search['start_step'],
                              'search_finish': search['finish_step'], 'work': search['actual_trace_work'],
                              'calls': search['planning_calls'], 'episode_success': episode['success'],
                              'episode_steps': episode['steps'], 'route_lifecycle': search['route_lifecycle'],
                              'first_submitted_place_step': episode['first_place_step'],
                              'reference_success': episode['comparison_to_same_stage_v17']['success_pair'][0],
                              'reference_steps': episode['comparison_to_same_stage_v17']['step_pair'][0]})
        if profile not in ['regression_6000005', 'clearance_profile_6000005'] or version not in ['handoff', 'v18']:
            continue
        path = STAGE/episode['job']/'trace.jsonl'
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
        rows = [json.loads(line) for line in path.read_text(encoding='utf8').splitlines()]
        actual, count, maximum, runs = [], 0, 0, []
        for row in rows:
            recovery = row['recovery']
            if recovery.get('carry_segment') != 'direct_transport': continue
            pose = recovery['mixed_pose']
            ready = bool(pose['position_error_m'] < .009 and pose['orientation_error_rad'] < .08 and recovery['stable_hold'])
            count = count+1 if ready else 0
            maximum = max(maximum, count)
            if ready:
                if runs and runs[-1][-1] == row['step']-1: runs[-1].append(row['step'])
                else: runs.append([row['step']])
            actual.append({'step': row['step'], 'position_error_m': pose['position_error_m'],
                           'orientation_error_rad': pose['orientation_error_rad'], 'stable_hold': recovery['stable_hold'],
                           'strict_ready': ready, 'derived_consecutive_ready': count,
                           'joint_positions': row['joint_positions'],
                           'submitted_action': row['submitted_action']})
        search = episode['searches'][0]
        schedule = search['selected_schedule']
        assert search['selected_candidate'] == 'current_exact' and len(actual) == 41
        assert maximum == 3 and count == 1 and actual[-1]['step'] == 400
        assert episode['first_place_step'] is None and episode['first_release_step'] is None
        late.append({'job': episode['job'], 'same_start_profile_duplicate': True,
                     'first_changed_command_step': episode['comparison_to_same_stage_v17']['first_changed_submitted_action']['step'],
                     'first_changed_observation_step': episode['comparison_to_same_stage_v17']['first_changed_state_before_step'],
                     'carry_start': episode['first_carry_step'],
                     'v17_carry_start': episode['comparison_to_same_stage_v17']['reference_first_carry_step'],
                     'search_start': search['start_step'], 'search_finish': search['finish_step'],
                     'work': search['actual_trace_work'], 'calls': search['planning_calls'],
                     'selected': search['selected_candidate'], 'selected_schedule': schedule,
                     'execution': search['execution_actual_hold_and_joints'],
                     'strict_ready_runs': runs, 'maximum_consecutive_ready': maximum,
                     'final_derived_consecutive_ready': count,
                     'derived_count_note': 'Computed from saved position <9mm, angle <.08rad, stable_hold. No private controller replay.',
                     'remaining_episode_steps': 0, 'placement_started': False, 'release_started': False,
                     'original_reserved_placement_steps': schedule['placement_minimum_steps'],
                     'original_reserved_release_steps': schedule['release_reserved_steps'],
                     'task_success': episode['success'], 'actual_direct_transport_rows': actual,
                     'interpretation': 'Existing current_exact was validated after upstream earlier CARRY. Actual transport never maintained five strict ready frames; neither PLACE nor RELEASE began. Static selection is not execution success.'})
    by_version = {item['job'].split('_', 1)[0]: item for item in regressions}
    assert by_version['short']['planning_work']-by_version['v17']['planning_work'] == 73
    assert by_version['short']['planning_calls']-by_version['v17']['planning_calls'] == 4
    assert by_version['short']['carry_search_start'] == by_version['v17']['carry_search_start'] == 276
    assert all(r['selected_candidate'] == 'outward_15_inset' for r in regressions)
    assert all(r['first_execution_guard'] is None for r in regressions)
    assert len(inset) == 4 and len(late) == 4
    out = {'source_sha256': sources, 'new_physical_episodes': 0, 'new_controller_replays': 0, 'new_ik_searches': 0,
           'regression_12000036': regressions, 'new_inset_actual_selections': inset, '6000005_tracking': late,
           'findings': [
               '12000036: short-only uses the same initial carry state and selects the same outward_15_inset route, but an unsuccessful new candidate costs 73 work and four control steps. Identical 5/17/55/28-stage durations shift PLACE and RELEASE four steps later and consume the original zero-slack success window.',
               '12000036 full: upstream handoff adds seven steps before CARRY, then short-route search adds four planning steps. PLACE begins eleven steps later, and RELEASE is not reached by 400. This is actual closed-loop delay, not the separate old route@330 static rejection.',
               '6000005: handoff and full enter CARRY 15 steps earlier, allowing the already-existing current_exact route to be selected. The new inset is never attempted there. Forty-one executed transport steps maintain grasp/joint protection but never five consecutive arrival frames.',
               'The new inset is selected four times across short/full: two duplicate executions of demo87 accelerate an existing success 300 to 283; two 12000011 second attempts improve progress but still fail at 400. There are no newly recovered successful profiles.',
               'Next-step evidence supports bounded candidate scheduling that protects existing route budgets, and separately observed near-goal settling. It does not support lowering arrival/guard thresholds, accepting budget-profile safety bypasses, or claiming generalization.'
           ],
           'limits': ['Known diagnostic cases, repeated profile/start data; no independent confirmation.',
                      'Consecutive-ready counts are derived from saved inputs, not newly simulated trajectories.',
                      'A phase-transition event and the first submitted command in that phase differ by one control step. Both are explicitly labeled.',
                      'Reserved schedule steps are controller heuristics, not physical completion guarantees.']}
    assert all(sha(ROOT/path) == digest for path, digest in sources.items())
    with (RUN/'analysis/smoke_a_route_findings.json').open('x', encoding='utf8') as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'regression_profiles': len(regressions), 'new_inset_selections': len(inset),
                      '6000005_guarded_tracking_executions': len(late), 'new_physical_episodes': 0}))


if __name__ == '__main__': main()
