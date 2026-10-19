"""Compact, source-bound v20 trace findings; no controller or physics execution."""
from pathlib import Path
import hashlib
import json

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
ORDER = ['v17', 'v19', 'budget', 'directional', 'braking', 'v20']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def compact(case):
    keep = ['job', 'version', 'condition', 'demo', 'comparison_profile', 'success', 'steps',
            'first_carry_clock', 'first_place_clock', 'first_release_clock',
            'final_command_mode', 'final_next_mode', 'braking20_triggered_events',
            'braking20_applied_events', 'braking20_rejected_or_replaced_events',
            'braking20_overlap_with_settling19']
    out = {key: case[key] for key in keep}
    out['held_stages'] = [{key: stage[key] for key in [
        'phase', 'first_control', 'last_control', 'controls', 'ready_control_spans',
        'maximum_consecutive_ready', 'last_consecutive_ready', 'last_position_error_m',
        'last_angle_error_rad', 'braking20_controls']} for stage in case['held_pose_segments']]
    out['release_tails'] = [{key: value for key, value in tail.items() if key != 'actual_tail'}
                            for tail in case['release_tails']]
    return out


def braking_window(case):
    controls = case['held_pose_controls']
    ready = [row for row in controls if row['strict_arrival_predicate']]
    first_ready = ready[0]['control_step'] if ready else None
    after = [row for row in controls if first_ready is not None and row['control_step'] >= first_ready]
    return {
        'job': case['job'], 'first_ready_control': first_ready,
        'largest_position_error_after_first_ready_m': max((r['position_error_m'] for r in after), default=None),
        'bias_control_window': [{
            'control_step': r['control_step'], 'position_error_m': r['position_error_m'],
            'orientation_error_rad': r['orientation_error_rad'], 'bias_m': r['bias_m'],
            'observed_motion_m': r['observed_motion_m'], 'ready': r['strict_arrival_predicate'],
            'consecutive_ready': r['consecutive_strict_arrival'],
            'capture_axes': (r['target_band_braking'] or {}).get('capture_brake_axes'),
            'integral_pause_axes': (r['target_band_braking'] or {}).get('integral_pause_axes'),
            'inside_position_ball': (r['target_band_braking'] or {}).get('inside_original_position_ball'),
            'old_crossing_axes': (r['integral_pause'] or {}).get('integral_brake_axes'),
            'submitted_translation': r['submitted_action'][:3],
            'executed_translation_before_noise': r['executed_before_noise'][:3],
            'executed_translation_after_noise': r['executed_action'][:3],
        } for r in controls if r['control_step'] >= 382],
    }


def main():
    source = RUN / 'analysis' / 'smoke_a_control_diagnosis.json'
    diagnosis = json.loads(source.read_text(encoding='utf8'))
    assert diagnosis['passed'] and diagnosis['selected_evaluation_executions'] == 54
    assert diagnosis['unique_start_identities'] == 8 and diagnosis['registered_profiles'] == 9
    for name, digest in diagnosis['source_sha256'].items():
        assert sha(ROOT / name) == digest, name
    cases = diagnosis['cases']
    by_id = {case['job']: case for case in cases}
    assert len(by_id) == 54
    version = {}
    for v in ORDER:
        rows = [c for c in cases if c['version'] == v]
        standard = [c for c in rows if c['comparison_profile'] == 'standard']
        clearance = [c for c in rows if c['comparison_profile'] != 'standard']
        assert len(rows) == 9 and len(standard) == 8 and len(clearance) == 1
        version[v] = dict(diagnosis['version_summary'][v],
                          standard_success=sum(c['success'] for c in standard), standard_executions=len(standard),
                          clearance_success=clearance[0]['success'], clearance_steps=clearance[0]['steps'],
                          successful_profiles=[c['job'][len(v)+1:] for c in rows if c['success']])
    delta = []
    for c in cases:
        if c['version'] not in ['braking', 'v20']:
            continue
        reference = 'v19' if c['version'] == 'braking' else 'directional'
        old = by_id[reference + c['job'][len(c['version']):]]
        delta.append({
            'variant': c['job'], 'reference': old['job'],
            'success_change': int(c['success']) - int(old['success']),
            'completion_step_change': c['steps'] - old['steps'],
            'same_failure_is_not_zero_effect': not c['success'] and not old['success'],
            'place_clock_change': None if c['first_place_clock'] is None or old['first_place_clock'] is None
                else c['first_place_clock'] - old['first_place_clock'],
            'release_clock_change': None if c['first_release_clock'] is None or old['first_release_clock'] is None
                else c['first_release_clock'] - old['first_release_clock'],
        })
    focus = lambda demo: [compact(c) for c in cases if c['demo'] == demo]
    record = {
        'passed': True, 'stage': 'smoke_a', 'scope': 'Read-only compact extraction from the original trace diagnosis.',
        'executions': 54, 'profiles': 9, 'unique_starts': 8, 'new_physical_episodes': 0,
        'new_controller_replays': 0, 'version_summary': version,
        'paired_B_effect_on_actual_outcomes': delta,
        'restored_old_success_12000036': focus('demo_12000036'),
        'terminal_failure_6000005_two_profiles': focus('demo_6000005'),
        'actual_bias_and_drift_6000005_standard': [braking_window(by_id[v + '_regression_6000005'])
                                                for v in ['v19', 'braking']],
        'no_step_gain_demo87': focus('demo_87'),
        'slower_second_attempt_12000011': focus('demo_12000011'),
        'unchanged_success_with_stage_tradeoff_side_s17': [compact(c) for c in cases if 'known_side_s17' in c['job']],
        'other_unresolved_targets': [compact(c) for c in cases if c['demo'] in [
            'demo_12000021', 'demo_13000021', 'demo_13000022']],
        'interpretation': [
            'B restores the known 12000036 success previously achieved by v17. It is not a rescue of the three registered target failures.',
            'The 12000036 CARRY stage durations remain unchanged. PLACE reaches the original release condition one control earlier, leaving one more actually executed open command before control400.',
            '6000005 B actually runs and pauses/clears integral bias, but the maximum consecutive accepted arrival observations remain three. No future controls after400 are inferred.',
            '6000005 A and full never reach CARRY; their zero B calls must be classified as upstream absence, not a failed B intervention.',
            '12000011 B delays the second-attempt clearance and reorientation; it does not reach PLACE by400 although parent v19 does. Both task outcomes remain failures.',
            'New braking20 and old settling19 receipts overlap on some identical controls. Event counts are not independent samples and must not be added.',
            'Only guarded CARRY route stages require the original five consecutive strict 9mm/0.08rad accepted observations. PLACE keeps its inherited object XY/height/age release condition; its pose streak is descriptive.',
            'An old budget-group task success does not certify compliance with the current held-object protection contract. It is a historical reference, not an admissible replacement.',
            'The clearance comparison is a second profile of the same6000005 start, not a ninth independent start. This selected small set does not establish generalization.',
        ],
        'next_step_recommendation_only': [
            'Keep the failed full version unadopted and do not advance its preregistered large-experiment gates.',
            'Separate the A upstream regression from the limited B improvement. Preserve B as a candidate, not a broadly validated default.',
            'Before proposing another rule, diagnose the actual D2 residual motion and remaining mandatory PLACE/RELEASE budget from saved6000005 controls; do not extend the400-step budget or relax five-frame confirmation.',
            'Any later narrower B candidate should explicitly retain12000036 while avoiding the slower second-attempt12000011 behavior, then pass a newly frozen small ablation before larger evaluation. No additional candidate is implemented by this receipt.',
        ],
        'verified_diagnosis_source_files': len(diagnosis['source_sha256']),
        'source_sha256': {rel(Path(__file__)): sha(Path(__file__)), rel(source): sha(source),
                          **diagnosis['source_sha256']},
    }
    path = RUN / 'analysis' / 'smoke_a_control_findings.json'
    with path.open('x', encoding='utf8') as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'passed': True, 'output': rel(path), 'executions': 54,
                      'new_physics': 0, 'source_files': len(record['source_sha256'])}))


if __name__ == '__main__':
    main()
