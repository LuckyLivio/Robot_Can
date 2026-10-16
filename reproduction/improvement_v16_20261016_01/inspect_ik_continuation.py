"""Saved-input diagnostics only: no simulator or new physical episodes.

Reference-success trajectories explain the old controller's acceptance region;
they are never supplied to the path search. Planning receives only the first
CARRY observation, observed joints, and the exact original controller targets.
"""
from pathlib import Path
from dataclasses import fields
from types import SimpleNamespace
import argparse
import hashlib
import json
import math
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import RecoveryController, Config
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK, LIMITS

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
STAGE = RUN.parent/'improvement_v15_20261016_01/smoke_a'
CASES = ['known_bc_k2_clean_demo_12000011',
         'known_full_s23_clean_demo_12000036',
         'known_full_s23_noise005_demo_12000021',
         'known13_bc_k2_noise005_demo_13000021']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def serial(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


def load(case):
    folder = STAGE/('v14_'+case)
    result = json.loads((folder/'result.json').read_text(encoding='utf8'))
    rows = list(map(json.loads, (folder/'trace.jsonl').open(encoding='utf8')))
    assert result['status'] == 'complete' and len(rows) == result['records'][0]['steps']
    cfg = Config(**{key: value for key, value in result['job']['config'].items()
                    if key in {field.name for field in fields(Config)}})
    controller = RecoveryController([.1975, .4025, .8], .8,
                                    np.asarray(rows[0]['state_before'], np.float32), True, cfg)
    previous = np.zeros(7, np.float32)
    first = None
    observations = []
    for row in rows:
        x = np.asarray(row['state_before'], np.float32)
        q = np.asarray(row['joint_positions'], float)
        before = controller.mode
        controller.set_joint_positions(q)
        action, _ = controller.choose(x, np.asarray(row['original_proposal'], np.float32), previous)
        previous = np.asarray(row['executed_action'], np.float32)
        # The controller replay validates interpretation of saved original data.
        np.testing.assert_array_equal(action, row['submitted_action'])
        if controller.mode == 'CARRY' and first is None:
            first = {'step': row['step'], 'x': x.astype(float).copy(), 'q': q.copy(),
                     'rotation': controller.goal_rotation.copy(),
                     'offset': controller.held_offset.copy(), 'target': controller.target.copy(),
                     'floor': controller.floor, 'carry_clearance_m': cfg.carry_clearance_m}
        if before in ['CARRY', 'PLACE'] or controller.mode in ['CARRY', 'PLACE']:
            observations.append({'step': row['step'], 'before': before, 'after': controller.mode,
                                 'eef': x[:3].astype(float), 'can': x[16:19].astype(float),
                                 'object_xy_error_m': float(np.linalg.norm(x[16:18]-controller.target[:2])),
                                 'orientation_error_rad': float(np.linalg.norm(Rotation.from_matrix(
                                     controller.goal_rotation @ Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec())),
                                 'joint_margin_rad': float(np.min(np.minimum(q-LIMITS[:, 0], LIMITS[:, 1]-q)))})
    assert first is not None
    evidence = {'case': case, 'success': result['records'][0]['success'], 'steps': len(rows),
                'saved_input_replay_actions_exact': True, 'source_result_sha256': digest(folder/'result.json'),
                'source_trace_sha256': digest(folder/'trace.jsonl'), 'first_carry': first,
                'transport_minimum_actual_joint_margin_rad': min(o['joint_margin_rad'] for o in observations),
                'transport_maximum_actual_orientation_error_rad': max(o['orientation_error_rad'] for o in observations),
                'transitions': [o for o in observations if o['before'] != o['after']]}
    return first, evidence


def continuation(first, carry, place, spacing, ik_type=IK):
    q = first['q'].copy()
    start = first['x'][:3].copy()
    receipts = []
    work = 0
    for label, goal in [('carry', carry), ('place', place)]:
        count = max(1, math.ceil(float(np.linalg.norm(goal-start))/spacing))
        for index, point in enumerate(np.linspace(start, goal, count+1)[1:]):
            ik = ik_type(q, point, first['rotation'], 48)
            while not ik.done:
                ik.advance(1)
                work += 1
            receipt = ik.receipt()
            receipts.append({'stage': label, 'index': index+1, 'targets_in_stage': count,
                             'point': point, **receipt})
            if not receipt['success'] or receipt['limit_margin_rad'] < .04:
                return {'status': 'unknown', 'spacing_m': spacing, 'work': work,
                        'reason': 'local_ik_unconverged' if not receipt['success'] else 'joint_margin_unconfirmed',
                        'receipts': receipts}
            q = ik.q.copy()
        start = goal.copy()
    return {'status': 'validated_ik_only', 'spacing_m': spacing, 'work': work, 'receipts': receipts}


def endpoint_trials(first):
    target = first['target'][:2]
    directions = {'current_side': first['x'][16:18]-target,
                  'robot_side': np.array([-.5, -.1])-target}
    trials = []
    for direction_name, direction in directions.items():
        direction = direction/max(np.linalg.norm(direction), 1e-12)
        for radius in [0., .025, .035, .04]:
            xy = target+direction*radius
            carry = np.r_[xy, first['floor']+first['carry_clearance_m']]+first['offset']
            for dz in [.085, .095]:
                place = np.r_[xy, first['floor']+dz]+first['offset']
                trial = continuation(first, carry, place, .04)
                trials.append({'direction': direction_name, 'radius_m': radius, 'place_height_above_floor_m': dz,
                               'carry_goal': carry, 'place_goal': place, **trial})
    return trials


def helper_checks(prior):
    from .recovery.carry_search import CarryPathSearch, MAX_WORK, MAX_ADVANCE_CALLS
    from reproduction.improvement_v15_20261016_01.recovery.carry_path import _translation, _rotation_samples, _rotation_sample
    checks = []
    for evidence in prior['evidence']:
        first = evidence['first_carry']
        controller = SimpleNamespace(
            floor=first['floor'], target=np.asarray(first['target']),
            cfg=SimpleNamespace(carry_clearance_m=first['carry_clearance_m'],
                                joint_solution_margin_rad=.04, ik_iterations_per_target=48),
            goal_rotation=np.asarray(first['rotation']), held_offset=np.asarray(first['offset']))
        search = CarryPathSearch(controller, first['x'], first['q'])
        calls = []
        while not search.done:
            search.advance(16)
            calls.append({'work': search.last_work, 'geometry': search.last_geometry_work})
            assert search.last_work <= 16 and search.last_geometry_work <= 4
        assert search.calls <= MAX_ADVANCE_CALLS and search.work <= MAX_WORK
        before = (search.work, search.calls, len(search.receipts), search.status)
        for _ in range(3):
            assert search.advance(16)
        assert (search.work, search.calls, len(search.receipts), search.status) == before
        assert search.last_work == 0
        for receipt in search.receipts:
            assert all(item['iterations'] <= 48 for item in receipt['path_ik'])
            if not receipt['accepted']:
                assert receipt['status'] == 'unknown'
        chosen = search.chosen
        if chosen is not None:
            assert search.status == 'validated'
            accepted = next(receipt for receipt in search.receipts if receipt['accepted'])
            assert all(item['success'] and item['limit_margin_rad'] >= .04 for item in accepted['path_ik'])
            assert all(item['accepted'] for item in accepted['geometry'])
            np.testing.assert_array_equal(chosen['carry_goal'], chosen['stages'][-1]['goal'])
            np.testing.assert_array_equal(chosen['place_goal'], chosen['placement']['goal'])
            np.testing.assert_array_equal(chosen['placement']['start'], chosen['carry_goal'])
            carry_object = chosen['carry_goal']-chosen['held_offset']
            place_object = chosen['place_goal']-chosen['held_offset']
            assert np.linalg.norm(carry_object[:2]-controller.target[:2]) < .045
            assert np.linalg.norm(place_object[:2]-controller.target[:2]) < .05
            assert place_object[2] < controller.floor+.10
            # Recheck every full segment from the returned executable stages,
            # independent of the search's task queue and receipt bookkeeping.
            for stage in chosen['stages']+[chosen['placement']]:
                if stage['kind'] == 'translate':
                    assert _translation(search.envelope, stage['start'], stage['goal'], stage['rotation'], search.gap)['accepted']
                else:
                    for rotation, hand_bound, can_bound in _rotation_samples(
                            search.envelope, stage['start_rotation'], stage['rotation'], search.gap):
                        assert _rotation_sample(search.envelope, stage['start'], rotation,
                                                search.gap, hand_bound, can_bound)['accepted']
        # A deliberately tiny per-call allowance exercises the same hard
        # call budget. Repeated calls after exhaustion never restart a search.
        bounded = CarryPathSearch(controller, first['x'], first['q'])
        while not bounded.done:
            bounded.advance(1)
        assert bounded.calls <= 24 and bounded.work <= 24
        if bounded.chosen is None:
            assert bounded.status == 'unknown'
        old_work = bounded.work
        bounded.advance(16)
        assert bounded.work == old_work
        checks.append({'case': evidence['case'], 'first_carry_step': first['step'],
                       'status': search.status, 'work': search.work, 'calls': search.calls,
                       'calls_detail': calls, 'chosen': chosen, 'receipts': search.receipts,
                       'post_completion_idempotent': True, 'tiny_slice_budget_status': bounded.status,
                       'tiny_slice_budget_calls': bounded.calls})
    return {'new_physical_episodes': 0, 'new_controller_replays': 0,
            'script_sha256': digest(__file__), 'helper_sha256': digest(RUN/'recovery/carry_search.py'),
            'input_receipt_sha256': digest(RUN/'analysis/ik_continuation_a.json'),
            'all_budget_and_geometry_checks_passed': True, 'cases': checks,
            'limits': {'max_work_per_control_step': 16, 'max_geometry_work_per_control_step': 4,
                       'max_planning_control_steps': 24, 'max_total_work': 384,
                       'max_ik_iterations_per_target': 48, 'minimum_joint_margin_rad': .04,
                       'minimum_geometry_margin_m': .001},
            'limitations': ['All inputs are already-known diagnostics, not independent confirmation.',
                            'Static path validation does not prove closed-loop completion or OSC joint-branch tracking.',
                            'No safety or task success thresholds were relaxed.',
                            'Three old successes need a different certified pose/endpoint; their original precise-pose paths were not shown feasible.',
                            'The same-attempt outcome cache is the central controller responsibility.']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='ik_continuation_a.json')
    parser.add_argument('--helper', action='store_true', help='Use the saved first-CARRY inputs; no repeated controller replay.')
    args = parser.parse_args()
    destination = RUN/'analysis'/args.output
    assert not destination.exists(), 'Do not overwrite prior diagnostic receipts.'
    if args.helper:
        prior = json.loads((RUN/'analysis/ik_continuation_a.json').read_text(encoding='utf8'))
        output = helper_checks(prior)
        with destination.open('x', encoding='utf8') as handle:
            json.dump(serial(output), handle, ensure_ascii=False, indent=2, allow_nan=False)
        print(json.dumps([{'case': case['case'], 'status': case['status'], 'work': case['work'],
                           'calls': case['calls'], 'chosen': case['chosen']['candidate'] if case['chosen'] else None}
                          for case in output['cases']], indent=2))
        return
    evidence = []
    for case in CASES:
        first, item = load(case)
        carry = np.r_[first['target'][:2], first['floor']+first['carry_clearance_m']]+first['offset']
        place = np.r_[first['target'][:2], first['floor']+.085]+first['offset']
        item['original_endpoint_continuation'] = [continuation(first, carry, place, spacing)
                                                 for spacing in [.08, .04, .02, .01]]
        item['task_acceptance_region_trials'] = endpoint_trials(first)
        evidence.append(item)
        print(json.dumps({'case': case, 'saved_success': item['success'],
                          'original_validated': [t['spacing_m'] for t in item['original_endpoint_continuation']
                                                 if t['status'] == 'validated_ik_only'],
                          'region_validated': [{k: t[k] for k in ['direction', 'radius_m', 'place_height_above_floor_m', 'work']}
                                               for t in item['task_acceptance_region_trials']
                                               if t['status'] == 'validated_ik_only']}, ensure_ascii=False), flush=True)
    output = {'new_physical_episodes': 0, 'saved_input_replays': len(CASES), 'script_sha256': digest(__file__),
              'evidence': evidence, 'thresholds': {'ik_iterations_per_target': 48, 'joint_margin_rad': .04,
                                                'ik_position_m': .004, 'ik_orientation_rad': .04},
              'limitations': ['Static local IK success is not closed-loop task success or collision safety.',
                              'Nonconvergence means unknown, not proven unreachable.',
                              'Region trials preserve the old task acceptance predicate but alter the commanded goal.',
                              'An accepted region target must be both certified and executed at the identical position.']}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf8') as handle:
        json.dump(serial(output), handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(destination)


if __name__ == '__main__':
    main()
