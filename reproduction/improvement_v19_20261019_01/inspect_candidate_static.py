"""Saved-state admission/candidate-cost checks. No physical or control rollout."""
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import argparse
import copy
import json
import sys
import numpy as np

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v18_20261019_01.inspect_short_route import controller, serial, sha, read
from reproduction.improvement_v18_20261019_01.inspect_short_route_static import validate
from reproduction.improvement_v17_20261019_01.recovery.carry_search import CarryPathSearch as V17
from reproduction.improvement_v19_20261019_01.recovery import carry_search as runtime


def execute(first, cls=runtime.CarryPathSearch):
    c = controller(first)
    before = c.clock
    s = cls(c, first['x'], first['q'])
    assert c.clock == before
    if cls is runtime.CarryPathSearch:
        assert len(s.options) == 4
        assert s.options[0][0] == 'current_exact' and s.options[1][0] == 'current_rotation_inset'
    calls = []
    while not s.done:
        before = c.clock
        s.advance(16)
        assert c.clock == before
        assert s.last_work <= 16 and s.last_geometry_work <= 4
        calls.append({'clock': c.clock, 'work': s.last_work, 'geometry': s.last_geometry_work})
        if not s.done: c.clock += 1
    assert s.work <= 384 and s.calls <= 24
    assert all(r['iterations'] <= 48 for o in s.receipts for r in o['path_ik'])
    if cls is runtime.CarryPathSearch:
        for option in s.receipts:
            if option['candidate'] == 'current_rotation_inset':
                assert option['candidate_work'] <= 48
                if not option['admission']['admitted']:
                    assert option['candidate_work'] == 1 and not option['path_ik'] and not option['geometry']
                    assert not option['accepted'] and option['status'] == 'unknown'
    old = s.work, s.calls, len(s.receipts), s.status
    for _ in range(3): s.advance(16)
    assert old == (s.work, s.calls, len(s.receipts), s.status)
    return s, calls


def optional_fixture(first, original):
    """Mechanism fixture: a real, prior exact-route receipt from this state."""
    c = controller(first)
    s = runtime.CarryPathSearch(c, first['x'], first['q'])
    s.receipts = [copy.deepcopy(original)]
    s.index = 1
    s._start_option()
    return c, s


def mechanisms(first, original):
    results = []
    alterations = [
        ('original_complete_transport_placement_failure', lambda r: None, True),
        ('one_ulp_wrong_transport_endpoint', lambda r: r['path_ik'][next(i for i in range(len(r['path_ik'])-1, -1, -1)
            if r['path_ik'][i]['stage'] == 'direct_transport')]['point'].__setitem__(0, np.nextafter(r['carry_goal'][0], np.inf)), False),
        ('unknown_transport_ik', lambda r: r['path_ik'][0].update(success=False), False),
        ('transport_margin_below_004', lambda r: r['path_ik'][0].update(limit_margin_rad=.04-1e-9), False),
        ('transport_margin_exact_004', lambda r: r['path_ik'][0].update(limit_margin_rad=.04), True),
        ('mixed_geometry_rejected', lambda r: next(g for g in r['geometry'] if g['kind'] == 'mixed_geometry').update(accepted=False), False),
        ('failure_in_transport', lambda r: r['path_ik'][-1].update(stage='direct_transport'), False),
        ('search_budget_failure', lambda r: r.update(reason='bounded_search_budget_exhausted'), False),
    ]
    for name, alter, expected in alterations:
        changed = copy.deepcopy(original)
        alter(changed)
        _, s = optional_fixture(first, changed)
        result = s._admission()
        assert result['admitted'] is expected, name
        results.append({'name': name, 'admitted': result['admitted'], 'evidence': result})
    # A candidate validated exactly on work unit 48 is acceptable; a route
    # needing work unit 49 remains unknown and keeps the fallback candidates.
    for extra, expected, work in [(4, True, 47), (5, True, 48), (6, False, 48)]:
        c, s = optional_fixture(first, original)
        s.tasks[0:0] = [('schedule',)]*extra
        detail = []
        while not any(r['candidate'] == 'current_rotation_inset' for r in s.receipts):
            clock = c.clock
            s.advance(16)
            assert c.clock == clock and s.last_work <= 16 and s.last_geometry_work <= 4
            detail.append({'work': s.last_work, 'geometry': s.last_geometry_work})
            if not s.done: c.clock += 1
        receipt = next(r for r in s.receipts if r['candidate'] == 'current_rotation_inset')
        assert receipt['candidate_work'] == work and receipt['accepted'] is expected
        if not expected: assert receipt['reason'] == 'optional_candidate_work_cap_unconfirmed'
        results.append({'name': 'synthetic_charged_work_boundary', 'extra_charged_schedule_checks': extra,
                        'candidate_work': receipt['candidate_work'], 'accepted': receipt['accepted'],
                        'reason': receipt['reason'], 'call_work': detail,
                        'not_a_physical_success_or_case_specific_runtime_rule': True})
    c, s = optional_fixture(first, original)
    class SlowIK:
        def __init__(self, *args): self.done = False; self.iterations = 0
        def advance(self, n): self.iterations += n
    with patch.object(runtime, 'IK', SlowIK):
        while not any(r['candidate'] == 'current_rotation_inset' for r in s.receipts):
            old = c.clock; s.advance(16)
            assert c.clock == old and s.last_work <= 16
            c.clock += 1
    receipt = next(r for r in s.receipts if r['candidate'] == 'current_rotation_inset')
    assert receipt['candidate_work'] == 48 and receipt['reason'] == 'optional_candidate_work_cap_unconfirmed'
    assert receipt['unfinished_local_ik']['iterations_so_far'] < 48
    results.append({'name': 'unfinished_ik_at_candidate_budget_is_unknown', 'receipt': receipt})
    # Exercise the copied numerical-consumer branch with injected boundary
    # receipts; no successful route can be produced by this fixture.
    for margin, success, reason in [(.04-1e-9, True, 'local_joint_margin_unconfirmed'),
                                    (.04, True, None), (.5, False, 'local_ik_unconverged')]:
        c = controller(first)
        s = runtime.CarryPathSearch(c, first['x'], first['q'])
        stage = s.stages[0]
        s.tasks = [('ik', stage, stage['goal'], stage['rotation']), ('schedule',)]
        class FakeIK:
            def __init__(self, *args): self.done = False; self.iterations = 0
            def advance(self, n): self.done = True; self.iterations = 1
            def receipt(self):
                return {'success': success, 'iterations': 1, 'q': list(first['q']),
                        'position_error_m': 0., 'angle_error_rad': 0., 'limit_margin_rad': margin}
        with patch.object(runtime, 'IK', FakeIK): s.advance(1)
        observed = s.receipts[0]['reason'] if s.receipts else None
        assert observed == reason
        results.append({'name': 'raw_ik_margin_boundary', 'margin': margin, 'success': success, 'reason': observed})
    # Whole-search limits dominate a candidate allowance. Neither can reset
    # calls/work or grant an unvalidated route.
    for field, value in [('calls', 24), ('work', 384)]:
        c, s = optional_fixture(first, original)
        setattr(s, field, value)
        if field == 'work': s._candidate_work_start = value
        clock = c.clock
        s.advance(16)
        assert s.done and s.chosen is None and s.reason == 'bounded_search_budget_exhausted' and c.clock == clock
        results.append({'name': 'whole_search_bound_dominates', 'field': field, 'value': value})
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='candidate_static_a.json')
    output = RUN/'analysis'/p.parse_args().output
    assert not output.exists()
    old = ROOT/'reproduction/improvement_v18_20261019_01'
    prior_path, baseline_path = old/'analysis/short_route_diagnosis_a.json', old/'analysis/short_route_static_a.json'
    prior, baseline = read(prior_path), read(baseline_path)
    sources = dict(baseline['source_sha256'])
    for path in [Path(__file__), RUN/'recovery/carry_search.py', prior_path, baseline_path,
                 old/'analysis/smoke_a_route_findings.json']:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT/path) == digest for path, digest in sources.items())
    for name in ['_geometry', '_context', '_key', '_schedule', '_route']:
        assert getattr(runtime.CarryPathSearch, name) is getattr(runtime.V18Search, name)
    evidence = []
    for item in prior['cases']+prior['budget_success_references']:
        first = item['snapshot']
        s, calls = execute(first)
        reference, reference_calls = execute(first, V17)
        previous = next(x for x in baseline['cases'] if x['job'] == item['job'] and x['clock'] == first['clock'])
        check = validate(s)
        original = next((r for r in s.receipts if r['candidate'] == 'current_exact'), None)
        matching = next((r for r in reference.receipts if r['candidate'] == 'current_exact'), None)
        if original is not None and matching is not None:
            assert original['path_ik'] == matching['path_ik']
        evidence.append({'job': item['job'], 'clock': first['clock'], 'work': s.work, 'calls': s.calls,
                         'call_work': calls, 'status': s.status, 'chosen': s.chosen, 'receipts': s.receipts,
                         'checks': check, 'family': [o[0] for o in s.options],
                         'comparison_v17': {'work': reference.work, 'calls': reference.calls,
                                             'status': reference.status, 'candidate': reference.chosen['candidate'] if reference.chosen else None,
                                             'call_work': reference_calls,
                                             'original_exact_raw_path_ik_equal': original is not None and matching is not None},
                         'comparison_v18': {k: previous[k] for k in ['work', 'calls', 'status', 'chosen']}})
        print(json.dumps({'job': item['job'], 'clock': first['clock'], 'work': s.work, 'calls': s.calls,
                          'candidate': s.chosen['candidate'] if s.chosen else None,
                          'v17_work_calls': [reference.work, reference.calls],
                          'v18_work_calls': [previous['work'], previous['calls']]}), flush=True)
    demo = next(x for x in prior['cases'] if x['job'] == 'v17_held_wait_demo87')
    original = next(o for o in demo['static_probes'][0]['receipts'] if o['candidate'] == 'current_exact')
    tests = mechanisms(demo['snapshot'], original)
    late = copy.deepcopy(demo['snapshot']); late['clock'] = 399
    late_search, _ = execute(late)
    assert late_search.chosen is None and late_search.work == 4 and len(late_search.receipts) == 4
    assert late_search.receipts[1]['reason'] == 'optional_endpoint_admission_unconfirmed'
    # Exact old accepted-family behavior is checked where its original
    # snapshot remains available; this is not a physical success assertion.
    affected = next(e for e in evidence if e['job'] == 'v17_known_full_s23_clean_demo_12000036')
    assert affected['chosen']['candidate'] == 'outward_15_inset'
    assert affected['work'] == 126 and affected['calls'] == affected['comparison_v17']['calls'] == 9
    fast = next(e for e in evidence if e['job'] == 'v17_held_wait_demo87')
    assert fast['chosen']['candidate'] == 'current_rotation_inset'
    assert all(sha(ROOT/path) == digest for path, digest in sources.items())
    out = {'passed': True, 'source_sha256': sources, 'new_physical_episodes': 0,
           'new_controller_replays': 0, 'saved_states': len(evidence), 'evidence': evidence,
           'mechanism_tests': tests, 'no_helper_clock_mutation': True,
           'limits': {'candidate_count': 4, 'optional_candidate_total_work_including_admission': 48,
                      'denied_admission_work': 1, 'per_target_ik_iterations': 48, 'per_call_work': 16,
                      'per_call_geometry': 4, 'total_search_work': 384, 'search_calls': 24,
                      'joint_margin_rad': .04, 'ik_position_error_m': .004, 'ik_orientation_error_rad': .04,
                      'geometry_margin_m': .001, 'episode_steps': 400},
           'late_budget_unknown': {'work': late_search.work, 'receipts': late_search.receipts},
           'selected_counts': dict(Counter(e['chosen']['candidate'] if e['chosen'] else 'unknown' for e in evidence)),
           'tradeoffs': ['The optional family can lose previously useful partial-transport opportunities, including the known 12000011 second attempt.',
                        'An admitted optional route can still consume up to 48 work before failure; no universal preservation of old physical completion time is claimed.',
                        'Cheap admission uses only this immutable search prefix. It is not a reachability classification.',
                        'Known saved states and synthetic mechanism boundaries are not new physical success or independent confirmation.',
                        'All chosen routes still require the original live hold, joint, geometry, timeout and arrival checks.']}
    with output.open('x', encoding='utf8') as stream:
        json.dump(serial(out), stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'passed': True, 'output': str(output), 'selected_counts': out['selected_counts']}))


if __name__ == '__main__': main()
