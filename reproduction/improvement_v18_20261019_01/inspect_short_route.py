"""Explain v17 short-route rejection using saved inputs and bounded static probes.

No physics, training, success-dependent runtime logic or old-source edit.
Changed endpoint/orientation probes are different routes, not evidence that an
unconverged IK result for the original exact target was a false rejection.
"""
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch
import argparse
import copy
import hashlib
import json
import math
import sys
import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
OLD = ROOT/'reproduction/improvement_v17_20261019_01'
STAGE = OLD/'smoke_a'
from reproduction.improvement_v17_20261019_01.recovery import carry_search as module17
from reproduction.improvement_v17_20261019_01.recovery.recovery_controller import RecoveryController as V17, Config as C17
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import RecoveryController as V15, Config as C15
from reproduction.improvement_v15_20261016_01.recovery.carry_path import _stage
from reproduction.improvement_v9_20261015_01.recovery.kinematics import fk


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def serial(value):
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, dict): return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [serial(v) for v in value]
    return value


def source_paths(jobs):
    paths = [Path(__file__), STAGE/'jobs.json', STAGE/'completed.json', STAGE/'started.json',
             OLD/'analysis/smoke_a_carry_diagnosis.json', OLD/'analysis/smoke_a_budget_reference.json']
    for number in range(6, 18):
        for directory in (ROOT/'reproduction').glob(f'improvement_v{number}_*/recovery'):
            paths.extend(p for p in directory.iterdir() if p.suffix in ['.py', '.json'])
    paths += list((ROOT/'reproduction/recovery_v5_20261012_01').glob('*.py'))
    for job in jobs:
        paths.extend(STAGE/job['id']/name for name in ['result.json', 'trace.jsonl'])
    return sorted(set(paths))


def snapshot(controller, x, q):
    return {'clock': controller.clock, 'attempt': controller.attempts, 'x': np.asarray(x, float).copy(),
            'q': np.asarray(q, float).copy(), 'rotation': controller.goal_rotation.copy(),
            'offset': controller.held_offset.copy(), 'target': controller.target.copy(),
            'floor': controller.floor, 'carry_clearance_m': controller.cfg.carry_clearance_m}


def capture(job, finish_at):
    """Replay only saved observations up to the last required snapshot."""
    rows = list(map(json.loads, (STAGE/job['id']/'trace.jsonl').open(encoding='utf8')))
    cls, cfg = (V15, C15) if job['version'] == 'budget' else (V17, C17)
    c = cls([.1975, .4025, .8], .8, np.asarray(rows[0]['state_before'], np.float32),
            job.get('enabled', True), cfg(**job['config']))
    inputs = []
    class Captured(module17.CarryPathSearch):
        def __init__(self, controller, x, q):
            inputs.append(snapshot(controller, x, q))
            super().__init__(controller, x, q)
    previous = np.zeros(7, np.float32)
    controls = 0
    with patch.object(module17, 'CarryPathSearch', Captured):
        for row in rows:
            x, q = np.asarray(row['state_before'], np.float32), np.asarray(row['joint_positions'], float)
            c.set_joint_positions(q)
            if job.get('force_recovery_at') == row['step']:
                c.start_attempt('diagnostic_forced_start', x)
            action, info = c.choose(x, np.asarray(row['original_proposal'], np.float32), previous)
            if row['fault_injected']: action[6] = -1.
            np.testing.assert_array_equal(action, row['submitted_action'])
            # Wall-clock measurements are not controller state.
            a = {k: v for k, v in info.items() if k != 'planning_ms'}
            b = {k: v for k, v in row['recovery'].items() if k != 'planning_ms'}
            assert serial(a) == b, (job['id'], row['step'], 'diagnostics differ')
            previous = np.asarray(row['executed_action'], np.float32)
            controls += 1
            if job['version'] == 'budget' and row['recovery']['mode'] == 'CARRY':
                inputs.append(snapshot(c, x, q))
                break
            if row['step'] >= finish_at:
                break
    return inputs, {'job': job['id'], 'saved_input_controller_steps': controls,
                    'actions_and_non_timing_diagnostics_exact': True,
                    'physical_episodes': 0}, rows


def controller(first, synthetic_clock=None):
    cfg = SimpleNamespace(carry_clearance_m=first['carry_clearance_m'], joint_solution_margin_rad=.04,
                          ik_iterations_per_target=48, horizon_steps=400, delay=2,
                          max_delta_m=.035, max_rotation_rad=.15)
    return SimpleNamespace(cfg=cfg, floor=first['floor'], target=np.asarray(first['target']),
                           goal_rotation=np.asarray(first['rotation']), held_offset=np.asarray(first['offset']),
                           clock=first['clock'] if synthetic_clock is None else synthetic_clock)


class Probe(module17.CarryPathSearch):
    """One explicitly named diagnostic route with original finite limits."""
    def __init__(self, c, x, q, probe):
        self.probe = probe
        super().__init__(c, x, q)

    def _start_option(self):
        if not self._ordered:
            self.options = [next(o for o in self.options if o[0] == 'current_exact')]
        super()._start_option()
        if self.probe == 'original_exact_waypoint_02':
            # Same complete mixed geometry. Only the IK continuation spacing
            # changes from <=4 cm to <=2 cm; target tolerances stay unchanged.
            tasks = [t for t in self.tasks if t[0] != 'ik']
            for stage in self.stages+[self.placement]:
                angle = np.linalg.norm(Rotation.from_matrix(stage['rotation']@stage['start_rotation'].T).as_rotvec())
                count = max(1, math.ceil(np.linalg.norm(stage['goal']-stage['start'])/.02), math.ceil(angle/.08))
                rv = Rotation.from_matrix(stage['rotation']@stage['start_rotation'].T).as_rotvec()
                for i in range(1, count+1):
                    f = i/count
                    tasks.append(('ik', stage, stage['start']+(stage['goal']-stage['start'])*f,
                                  Rotation.from_rotvec(rv*f).as_matrix()@stage['start_rotation']))
            self.tasks = tasks

    def _route(self, option):
        if self.probe not in ['original_rotation_inset', 'observed_rotation_inset']:
            return super()._route(option)
        rotation = self.original_rotation.copy() if self.probe == 'original_rotation_inset' else self.start_rotation.copy()
        offset = self.envelope.held_offset(rotation)
        radial = np.array([-.5, -.1])-self.target[:2]
        radial /= np.linalg.norm(radial)
        xy = self.target[:2]+.035*radial
        carry = np.r_[xy, self.carry_height]+offset
        place = np.r_[xy, self.floor+.095]+offset
        stage = _stage('direct_transport', 'translate', self.x[:3].copy(), carry, self.start_rotation, rotation)
        placement = _stage('placement_validation', 'translate', carry, place, rotation, rotation)
        return {'name': 'current_exact', 'rotation': rotation, 'offset': offset, 'short': True,
                'stages': [stage], 'placement': placement}


def run_probe(first, name, synthetic_clock=None):
    c = controller(first, synthetic_clock)
    s = Probe(c, first['x'], first['q'], name)
    calls = []
    while not s.done:
        s.advance(16)
        calls.append({'clock': c.clock, 'work': s.last_work, 'geometry_work': s.last_geometry_work})
        assert s.last_work <= 16 and s.last_geometry_work <= 4
        if not s.done: c.clock += 1
    assert s.calls <= 24 and s.work <= 384
    assert all(r['iterations'] <= 48 for o in s.receipts for r in o['path_ik'])
    if s.chosen:
        assert all(r['success'] and r['limit_margin_rad'] >= .04 for o in s.receipts for r in o['path_ik'])
        assert all(r['accepted'] and r['hand_margin_m'] >= .001 and r['carried_can_margin_m'] >= .001 for o in s.receipts for r in o['geometry'])
        np.testing.assert_array_equal(s.chosen['carry_goal'], s.chosen['stages'][-1]['goal'])
        np.testing.assert_array_equal(s.chosen['place_goal'], s.chosen['placement']['goal'])
    return {'probe': name, 'synthetic_clock': synthetic_clock, 'observed_clock': first['clock'],
            'status': s.status, 'work': s.work, 'calls': s.calls, 'call_work': calls,
            'chosen': s.chosen, 'receipts': s.receipts,
            'claim': 'Different target/rotation route' if 'inset' in name else 'Same exact goal with changed continuation spacing' if '02' in name else 'Original exact route',
            'closed_loop_validation': False}


def original_rejection(option):
    path, geom = option.get('path_ik', []), option.get('geometry', [])
    last = path[-1] if path else None
    output = {'reason': option['reason'], 'status': option['status'], 'accepted': option['accepted'],
              'schedule_at_start': option['schedule_at_start'], 'schedule_at_finish': option['schedule_at_finish'],
              'predicted_rigid_object_goals': option['predicted_rigid_object_goals'],
              'carry_goal': option['carry_goal'], 'place_goal': option['place_goal'],
              'path_ik': path, 'geometry': geom,
              'last_ik_seed_q': path[-2]['q'] if len(path) > 1 else None,
              'rejection_before_geometry_and_ik': not geom and not path,
              'geometry_checks_all_passed': all(g['accepted'] for g in geom) if geom else None}
    if last:
        _, _, jac = fk(np.asarray(last['q']), True)
        singular = np.linalg.svd(np.array([1, 1, 1, .25, .25, .25])[:, None]*jac, compute_uv=False)
        output['failed_ik_weighted_jacobian_singular_values'] = singular
        output['local_solver_status_is_not_unreachability_proof'] = True
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='short_route_diagnosis_a.json')
    args = parser.parse_args()
    destination = RUN/'analysis'/args.output
    assert not destination.exists()
    assert read(STAGE/'completed.json')['source_unchanged']
    all_jobs = read(STAGE/'jobs.json')
    summary = read(OLD/'analysis/smoke_a_carry_diagnosis.json')
    selected = [j for j in all_jobs if j['version'] in ['route', 'v17'] and
                any(e['job'] == j['id'] and e.get('searches') for e in summary['episodes'])]
    budgets = [j for j in all_jobs if j['version'] == 'budget' and j['demos'] == ['demo_6000005']]
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths(selected+budgets)}
    cases, replays, budget = [], [], []
    names = ['original_exact_waypoint_04', 'original_exact_waypoint_02', 'original_rotation_inset', 'observed_rotation_inset']
    for job in selected:
        result = read(STAGE/job['id']/'result.json')['records'][0]
        finishes = [e for e in result['carry15_events'] if e['event'] == 'held_transport_search_complete']
        old = next(e for e in summary['episodes'] if e['job'] == job['id'])
        inputs, replay, _ = capture(job, max(s['start_step'] for s in old['searches']))
        replays.append(replay)
        assert len(inputs) == len(finishes) == len(old['searches'])
        for first, finish, prior_search in zip(inputs, finishes, old['searches']):
            assert first['clock'] == prior_search['start_step']
            np.testing.assert_array_equal(first['x'], prior_search['start_observation'])
            np.testing.assert_array_equal(first['q'], prior_search['start_observed_joints'])
            option = next(o for o in finish['options'] if o['candidate'] == 'current_exact')
            item = {'job': job['id'], 'snapshot': first, 'original_finish_step': finish['step'],
                    'original_rejection': original_rejection(option), 'static_probes': []}
            for name in names:
                item['static_probes'].append(run_probe(first, name))
            # Deliberately synthetic earlier clock only for the eight cases
            # rejected before any geometry/IK. This separates temporal policy
            # from local route feasibility; it is not an executable rescue.
            if not option['path_ik'] and not option['geometry']:
                item['budget_isolation_probe'] = run_probe(first, names[0], synthetic_clock=100)
            cases.append(item)
            print(json.dumps({'job': job['id'], 'clock': first['clock'], 'original': option['reason'],
                              'static': [(p['probe'], p['status'], p['work']) for p in item['static_probes']]}, ensure_ascii=False), flush=True)
    for job in budgets:
        inputs, replay, rows = capture(job, 400)
        replays.append(replay)
        first = inputs[0]
        result = read(STAGE/job['id']/'result.json')['records'][0]
        item = {'job': job['id'], 'task_success': result['success'], 'steps': result['steps'], 'snapshot': first,
                'phase_transitions': [e for e in result['events'] if e['step'] >= first['clock']-1],
                'actual_carry_place_rows': [{k: row[k] for k in ['step', 'state_before', 'joint_positions', 'submitted_action', 'recovery']}
                                           for row in rows if row['recovery']['mode'] in ['CARRY', 'PLACE']],
                'static_probes': [run_probe(first, name) for name in names]}
        budget.append(item)
        print(json.dumps({'budget_reference': job['id'], 'clock': first['clock'],
                          'static': [(p['probe'], p['status'], p['work']) for p in item['static_probes']]}, ensure_ascii=False), flush=True)
    assert len(cases) == 23
    assert all(sha(ROOT/rel) == digest for rel, digest in hashes.items()), 'A read dependency changed during diagnosis'
    counts = dict(Counter(c['original_rejection']['reason'] for c in cases))
    output = {'source_sha256': hashes, 'v17_searches_examined': len(cases), 'original_rejection_counts': counts,
              'new_physical_episodes': 0, 'new_training': False, 'saved_input_replays': replays,
              'saved_input_controller_steps': sum(r['saved_input_controller_steps'] for r in replays),
              'bounded_static_route_probes': sum(len(c['static_probes'])+int('budget_isolation_probe' in c) for c in cases)+sum(len(c['static_probes']) for c in budget),
              'cases': cases, 'budget_success_references': budget,
              'limits': {'per_target_ik_iterations': 48, 'work_per_advance': 16, 'geometry_per_advance': 4,
                         'search_work': 384, 'advance_calls': 24, 'joint_margin_rad': .04,
                         'ik_position_error_m': .004, 'ik_orientation_error_rad': .04, 'geometry_margin_m': .001},
              'limitations': ['Known saved states only; no independent evaluation and no physical route execution.',
                              'A changed terminal point or orientation is a new route, not proof of IK false rejection for the old exact target.',
                              'Budget-isolation probes use explicitly synthetic clock 100, never future simulator state.',
                              'Static reachability and nominal geometry do not prove actual joint tracking, grasp stability or completion within 400 steps.',
                              'A failed local solver stays unknown; no threshold or iteration cap is relaxed.',
                              'Budget reference successes do not authorize bypassing any current guard; only two correlated profiles of the same 6000005 start are used.']}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf8') as handle:
        json.dump(serial(output), handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'output': str(destination), 'rejections': counts,
                      'new_physical_episodes': 0, 'saved_input_controls': output['saved_input_controller_steps']}))


if __name__ == '__main__':
    main()
