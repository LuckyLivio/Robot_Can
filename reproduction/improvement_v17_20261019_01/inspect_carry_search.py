"""v17 static search mechanisms using saved inputs; no new physics episodes."""
from pathlib import Path
from types import SimpleNamespace
from dataclasses import fields
import argparse
import copy
import hashlib
import json
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v17_20261019_01.recovery.carry_search import CarryPathSearch
from reproduction.improvement_v16_20261016_01.recovery.carry_search import CarryPathSearch as OldSearch
from reproduction.improvement_v16_20261016_01.recovery.pose_servo import _hand_box_translation_envelope
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import RecoveryController as V16, Config as C16
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import RecoveryController as V15, Config as C15

RUN = Path(__file__).resolve().parent
OLD = RUN.parent/'improvement_v16_20261016_01'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def serial(x):
    if isinstance(x, np.ndarray): return x.tolist()
    if isinstance(x, np.generic): return x.item()
    if isinstance(x, dict): return {k: serial(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [serial(v) for v in x]
    return x


def controller(first, clock=None):
    cfg = SimpleNamespace(carry_clearance_m=first['carry_clearance_m'], joint_solution_margin_rad=.04,
                          ik_iterations_per_target=48, horizon_steps=400, delay=2, max_delta_m=.035,
                          max_rotation_rad=.15)
    return SimpleNamespace(cfg=cfg, floor=first['floor'], target=np.asarray(first['target']),
                           goal_rotation=np.asarray(first['rotation']), held_offset=np.asarray(first['offset']),
                           clock=int(first['step'] if clock is None else clock))


def capture(job_id):
    folder = OLD/'smoke_a'/job_id
    result = json.loads((folder/'result.json').read_text(encoding='utf8'))
    assert result['status'] == 'complete'
    rows = list(map(json.loads, (folder/'trace.jsonl').open(encoding='utf8')))
    cls, config = (V15, C15) if job_id.startswith('v15_') else (V16, C16)
    job = result['job']
    cfg = config(**{k: v for k, v in job['config'].items() if k in {f.name for f in fields(config)}})
    c = cls([.1975, .4025, .8], .8, np.asarray(rows[0]['state_before'], np.float32), True, cfg)
    previous = np.zeros(7, np.float32)
    for row in rows:
        x = np.asarray(row['state_before'], np.float32)
        q = np.asarray(row['joint_positions'])
        c.set_joint_positions(q)
        if job.get('force_recovery_at') == row['step']:
            c.start_attempt('diagnostic_forced_start', x)
        action, _ = c.choose(x, np.asarray(row['original_proposal'], np.float32), previous)
        if row['fault_injected']: action[6] = -1.
        np.testing.assert_array_equal(action, row['submitted_action'])
        previous = np.asarray(row['executed_action'], np.float32)
        if c.mode == 'CARRY':
            return {'step': row['step'], 'x': x.astype(float), 'q': q.copy(),
                    'rotation': c.goal_rotation.copy(), 'offset': c.held_offset.copy(),
                    'target': c.target.copy(), 'floor': c.floor, 'carry_clearance_m': cfg.carry_clearance_m}, {
                        'job': job_id, 'saved_input_replay_steps': row['step'], 'submitted_actions_exact': True,
                        'result_sha256': sha(folder/'result.json'), 'trace_sha256': sha(folder/'trace.jsonl')}
    raise AssertionError('No CARRY input in '+job_id)


def run_search(first, cls=CarryPathSearch, clock=None):
    c = controller(first, clock)
    search = cls(c, first['x'], first['q'])
    calls = []
    while not search.done:
        search.advance(16)
        calls.append({'work': search.last_work, 'geometry_work': search.last_geometry_work, 'clock': c.clock})
        assert search.last_work <= 16 and search.last_geometry_work <= 4
        if not search.done: c.clock += 1
    assert search.calls <= 24 and search.work <= 384
    before = (search.work, search.calls, len(search.receipts), search.status)
    for _ in range(3): search.advance(16)
    assert before == (search.work, search.calls, len(search.receipts), search.status)
    return search, calls


def validate_chosen(search):
    assert all(r['iterations'] <= 48 for o in search.receipts for r in o['path_ik'])
    assert all(o['status'] == 'unknown' for o in search.receipts if not o['accepted'])
    if search.chosen is None:
        return {'route_chosen': False}
    p = search.chosen
    accepted = next(o for o in search.receipts if o['accepted'])
    assert accepted['predicted_rigid_object_goals']['accepted_original_task_region']
    assert all(r['success'] and r['limit_margin_rad'] >= .04 for r in accepted['path_ik'])
    assert all(r['accepted'] and r['hand_margin_m'] >= .001 and r['carried_can_margin_m'] >= .001 for r in accepted['geometry'])
    assert not p['preserve_current']
    np.testing.assert_array_equal(p['carry_goal'], p['stages'][-1]['goal'])
    np.testing.assert_array_equal(p['place_goal'], p['placement']['goal'])
    if p['short_original_route']:
        assert len(p['stages']) == 1 and p['stages'][0]['label'] == 'direct_transport'
        np.testing.assert_array_equal(p['rotation'], search.original_rotation)
        np.testing.assert_array_equal(p['held_offset'], search.original_offset)
        np.testing.assert_array_equal(p['carry_goal'], np.r_[search.target[:2], search.carry_height]+search.original_offset)
        np.testing.assert_array_equal(p['place_goal'], np.r_[search.target[:2], search.floor+.085]+search.original_offset)
        stage = p['stages'][0]
        rv = Rotation.from_matrix(stage['rotation'] @ stage['start_rotation'].T).as_rotvec()
        minimum = float('inf')
        # Dense product-grid check is independent of sampled arc deductions.
        # The analytical envelope is still what covers points between samples.
        for fraction in np.linspace(0, 1, 9):
            r = Rotation.from_rotvec(rv*fraction).as_matrix() @ stage['start_rotation']
            hand = _hand_box_translation_envelope(stage['start'], stage['goal'], r, search.gap)
            can = search.envelope.sweep_margin(stage['start'], stage['goal'], r)
            minimum = min(minimum, hand, can)
        assert minimum >= .001
        return {'route_chosen': True, 'short_original_targets_exact': True,
                'direct_product_grid_minimum_margin_m': minimum,
                'predicted_object_goals': accepted['predicted_rigid_object_goals']}
    return {'route_chosen': True, 'short_original_targets_exact': False,
            'predicted_object_goals': accepted['predicted_rigid_object_goals']}


class NeverHit(dict):
    def __contains__(self, key): return False


class NoReuse(CarryPathSearch):
    """Static oracle: identical algorithm, but cache reuse disabled explicitly."""
    def __init__(self, *args):
        super().__init__(*args)
        self._ik_cache = NeverHit()
        self._geometry_cache = NeverHit()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='carry_search_static_a.json')
    args = p.parse_args()
    destination = RUN/'analysis'/args.output
    assert not destination.exists()
    prior = json.loads((OLD/'analysis/ik_continuation_a.json').read_text(encoding='utf8'))
    inputs = [(e['case'], e['first_carry']) for e in prior['evidence']]
    sources = []
    for job in ['v15_regression_6000005', 'v16_regression_6000005']:
        first, source = capture(job)
        sources.append(source)
        inputs.append((job, first))
    cases = []
    for name, first in inputs:
        search, calls = run_search(first)
        validation = validate_chosen(search)
        cases.append({'name': name, 'input': first, 'status': search.status, 'work': search.work,
                      'calls': search.calls, 'calls_detail': calls, 'chosen': search.chosen,
                      'receipts': search.receipts, 'cache_stats': search.cache_stats, 'checks': validation})
        print(json.dumps({'name': name, 'status': search.status, 'work': search.work, 'calls': search.calls,
                          'candidate': search.chosen['candidate'] if search.chosen else None,
                          'short': search.chosen['short_original_route'] if search.chosen else None,
                          'cache': search.cache_stats}), flush=True)
    # Same physical saved input, explicitly synthetic earlier clock, to isolate
    # cache correctness from the separately tested late-budget rejection.
    first = inputs[-1][1]
    cached, _ = run_search(first, clock=100)
    uncached, _ = run_search(first, cls=NoReuse, clock=100)
    assert cached.status == uncached.status
    assert bool(cached.chosen) == bool(uncached.chosen)
    assert len(cached.receipts) == len(uncached.receipts)
    for left, right in zip(cached.receipts, uncached.receipts):
        assert (left['candidate'], left['reason'], left['accepted']) == (right['candidate'], right['reason'], right['accepted'])
        assert len(left['path_ik']) == len(right['path_ik'])
        for a, b in zip(left['path_ik'], right['path_ik']):
            for field in ['stage', 'point', 'success', 'iterations', 'q', 'position_error_m', 'angle_error_rad', 'limit_margin_rad']:
                assert a[field] == b[field], (field, a[field], b[field])
    if cached.chosen:
        assert cached.chosen['candidate'] == uncached.chosen['candidate']
        np.testing.assert_array_equal(cached.chosen['carry_goal'], uncached.chosen['carry_goal'])
    cached_unknowns = [r for o in cached.receipts for r in o['path_ik']
                       if r['cache_hit'] and (not r['success'] or r['limit_margin_rad'] < .04)]
    # If a shorter valid route ends the search, use exact observed prefix
    # targets from v16's real failed receipt as an isolated numerical cache
    # mechanism probe; never inject this into the production candidate family.
    probe = {'synthetic_clock_only': 100, 'same_saved_physical_input': True,
             'cached_work': cached.work, 'uncached_work': uncached.work,
             'cache_stats': cached.cache_stats, 'outcome_equal': True, 'all_raw_ik_receipts_exact_without_cache': True,
             'cached_unknown_receipts': cached_unknowns}
    assert cached.work <= uncached.work
    assert len(cached_unknowns) == 2 and cached.cache_stats['ik_work_avoided'] == 94
    assert cached_unknowns[0]['cache_key'] == cached_unknowns[1]['cache_key']
    # Fresh searches never share dictionaries; changed inputs invalidate the
    # context hash even for a one-ULP perturbation.
    base = CarryPathSearch(controller(first, 100), first['x'], first['q'])
    fresh = CarryPathSearch(controller(first, 100), first['x'], first['q'])
    assert not fresh._ik_cache and fresh._ik_cache is not base._ik_cache
    contexts = [base._context()]
    for field, index in [('x', 0), ('x', 7), ('x', 16), ('x', 19), ('q', 0), ('target', 0), ('offset', 0)]:
        changed = copy.deepcopy(first)
        changed[field] = np.asarray(changed[field], float).copy()
        changed[field].flat[index] = np.nextafter(changed[field].flat[index], np.inf)
        other = CarryPathSearch(controller(changed, 100), changed['x'], changed['q'])
        contexts.append(other._context())
    assert len(set(contexts)) == len(contexts)
    key = base._key('ik', base.q, base.x[:3], base.original_rotation, [48, .04])
    altered = base.q.copy(); altered[0] = np.nextafter(altered[0], np.inf)
    assert key != base._key('ik', altered, base.x[:3], base.original_rotation, [48, .04])
    altered_target = base.x[:3].copy(); altered_target[0] = np.nextafter(altered_target[0], np.inf)
    assert key != base._key('ik', base.q, altered_target, base.original_rotation, [48, .04])
    altered_rotation = base.original_rotation.copy(); altered_rotation[0, 0] = np.nextafter(altered_rotation[0, 0], np.inf)
    assert key != base._key('ik', base.q, base.x[:3], altered_rotation, [48, .04])
    assert key != base._key('ik', base.q, base.x[:3], base.original_rotation, [47, .04])
    assert not base.x.flags.writeable and not base.q.flags.writeable and not base.envelope.vertices.flags.writeable
    for known in [base.x, base.q, base.envelope.vertices]:
        try:
            known.flat[0] = 0.
        except ValueError:
            pass
        else:
            raise AssertionError('Search snapshot should reject mutation')
    late, _ = run_search(first, clock=399)
    assert late.chosen is None and late.status == 'unknown'
    assert late.work == 4 and all(r['reason'] == 'remaining_command_schedule_unconfirmed' for r in late.receipts)
    output = {'passed': True, 'new_physical_episodes': 0,
              'saved_parent_controller_replay_steps': sum(s['saved_input_replay_steps'] for s in sources),
              'script_sha256': sha(__file__), 'helper_sha256': sha(RUN/'recovery/carry_search.py'),
              'prior_input_receipt_sha256': sha(OLD/'analysis/ik_continuation_a.json'), 'sources': sources,
              'cases': cases, 'cache_probe': probe,
              'exact_key_perturbation_and_no_cross_search_cache': True,
              'late_budget_unknown_without_ik': {'work': late.work, 'calls': late.calls, 'receipts': late.receipts},
              'limits': {'per_target_ik': 48, 'per_control_step_work': 16, 'geometry_per_call': 4,
                         'total_work': 384, 'planning_calls': 24, 'joint_margin_rad': .04, 'box_margin_m': .001},
              'limitations': ['Known diagnostic states only; static success is not physical success or independent confirmation.',
                              'Minimum command schedule is a model of capped nominal commands and mandatory waits, not a physical lower bound.',
                              'Nominal completion estimates order candidates but do not guarantee the route finishes.',
                              'No arrival, release, grasp, aperture, geometry or joint threshold was relaxed.']}
    destination.parent.mkdir(exist_ok=True)
    with destination.open('x', encoding='utf8') as handle:
        json.dump(serial(output), handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(destination)


if __name__ == '__main__': main()
