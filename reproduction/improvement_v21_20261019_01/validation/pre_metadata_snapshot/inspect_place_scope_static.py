"""Saved-input and synthetic scope checks for v21 PLACE-only braking.

Tests the actual v21 propose17 integration. This does not choose new actions in
a simulated episode or replay the controller state machine. Historical parent
memory is supplied independently for every counterfactual proposal.
"""
from collections import Counter
from dataclasses import asdict, fields, replace
from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json
import sys

import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v19_20261019_01.recovery.recovery_controller import RecoveryController as V19, Config as C19
from reproduction.improvement_v19_20261019_01.recovery import settling as parent
from reproduction.improvement_v20_20261019_01.recovery import delay_settling as braking
from reproduction.improvement_v21_20261019_01.recovery.recovery_controller import RecoveryController as V21, Config as C21


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(x):
    if isinstance(x, dict):
        return {str(k): finite(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [finite(v) for v in x]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x) if np.isfinite(x) else None
    return x


def controller(cls, cfg, context, *, mode, enabled=True):
    x, goal, rotation, motion, state, previous, attempt, phase, held, grip = context
    c = cls([.19, .40, .8], .8, x, enabled=enabled, config=cfg)
    c.clock = 200
    c.age = 9
    c.attempts = attempt
    c.mode = mode
    c.motion = motion.copy()
    c.last_submitted17 = previous.copy() if previous is not None else None
    c.servo17['held' if held else 'edge'] = copy.deepcopy(state)
    return c


def invoke(c, context):
    x, goal, rotation, motion, state, previous, attempt, phase, held, grip = context
    immutable = finite([c.clock, c.age, c.attempts, c.mode, list(c.history), c.events,
                        c.motion, c.last_submitted17, x, goal, rotation])
    action, receipt = c.propose17(x, goal, rotation, held=held, grip=grip, phase=phase)
    assert finite([c.clock, c.age, c.attempts, c.mode, list(c.history), c.events,
                   c.motion, c.last_submitted17, x, goal, rotation]) == immutable
    assert receipt['work'] <= 16
    if receipt['accepted']:
        np.testing.assert_array_equal(action, receipt['submitted_action'])
        assert receipt['box_margin_m'] >= .001 and receipt['can_margin_m'] >= .001
        assert np.linalg.norm(receipt['position_bias_m']) <= .009 + 1e-12
        assert finite(vars(c.servo17['held' if held else 'edge'])) == finite(vars(state)), 'Uncommitted proposal changed memory'
    return action, receipt


def equivalent(actual, expected):
    np.testing.assert_array_equal(actual[0], expected[0])
    assert finite(actual[1]) == finite(expected[1])


def inspect_saved(job):
    folder = ROOT / 'reproduction/improvement_v20_20261019_01/smoke_a' / job['id']
    source, trace = folder / 'result.json', folder / 'trace.jsonl'
    saved = read(source)
    assert saved['status'] == 'complete' and saved['job'] == job
    old_cfg = C19(**job['config'])
    cfg = C21(**job['config'])
    memory = parent.ServoState()
    cases, anchor = [], None
    for line in trace.read_text(encoding='utf8').splitlines():
        row = json.loads(line)
        receipt = row['recovery'].get('mixed_pose', {})
        if not (receipt.get('held') and receipt.get('accepted') and receipt.get('state_update')):
            memory.reset()
            continue
        update = receipt['state_update']
        attempt, phase = ast.literal_eval(update['phase'])
        mode = row['recovery']['next_mode']
        context = (np.asarray(row['state_before'], np.float32), np.asarray(update['goal']),
                   np.asarray(update['rotation']), np.r_[receipt['observed_translation_per_step_m'],
                   receipt['observed_rotation_per_step_rad']], copy.deepcopy(memory),
                   np.asarray(receipt['previous_submitted_action'], np.float32), attempt, phase, True, receipt['grip_command'])
        original = invoke(controller(V19, old_cfg, context, mode=mode), context)
        equivalent(original, (np.asarray(row['submitted_action'], np.float32), receipt))
        off = invoke(controller(V21, replace(cfg, place_braking=False), context, mode=mode), context)
        equivalent(off, original)
        new = invoke(controller(V21, replace(cfg, place_braking=True), context, mode=mode), context)
        scoped = mode == 'PLACE' and phase == 'PLACE'
        if not scoped:
            equivalent(new, original)
            assert 'place21' not in new[1]
        else:
            expected = braking.propose(context[0], context[1], context[2], context[3], cfg,
                held=True, grip=context[9], state=context[4], phase=(attempt, phase),
                previous_action=context[5])
            actual_without_scope = (new[0], {k: v for k, v in new[1].items() if k != 'place21'})
            equivalent(actual_without_scope, expected)
            assert new[1]['place21']['actual_mode_at_proposal'] == 'PLACE'
            assert new[1]['place21']['phase'] == 'PLACE'
            anchor = copy.deepcopy(context)
        cases.append({'job': job['id'], 'control_step': row['step'], 'mode_at_proposal_from_saved_next_mode': mode,
                      'phase': phase, 'scope_enabled': scoped, 'B_off_exact_parent': True,
                      'non_PLACE_exact_parent': not scoped,
                      'new_action_changed': not np.array_equal(new[0], original[0]),
                      'braking_triggered': 'braking20' in new[1],
                      'work': new[1]['work'], 'place21': new[1].get('place21'),
                      'old_bias_m': original[1]['position_bias_m'], 'new_bias_m': new[1]['position_bias_m']})
        assert memory.commit(np.asarray(row['submitted_action'], np.float32), receipt)
    return cases, anchor, [source, trace]


def synthetic_checks(anchor):
    x = anchor[0].copy()
    shift = np.array([0., 0., 1.5]) - x[:3]
    x[:3] += shift
    x[16:19] += shift
    rotation = Rotation.from_quat(x[3:7]).as_matrix()
    goal = x[:3].astype(float) + [.006, -.003, .002]
    motion = np.array([.003, 0., 0., 0., 0., 0.])
    previous = np.zeros(7, np.float32)
    base_cfg = C21()
    records = []

    def context(phase='PLACE', *, attempt=1, held=True, previous_phase=None, previous_attempt=None):
        state = parent.ServoState()
        assert state.commit(previous, {'accepted': True, 'submitted_action': previous.tolist(),
            'state_update': {'phase': repr((attempt if previous_attempt is None else previous_attempt,
                                           phase if previous_phase is None else previous_phase)),
                             'held': held, 'goal': goal.tolist(), 'rotation': rotation.tolist(),
                             'bias': [.004, -.003, .002]}})
        return (x.copy(), goal.copy(), rotation.copy(), motion.copy(), state, previous.copy(),
                attempt, phase, held, 1. if held else 0.)

    scopes = [
        ('actual_PLACE', 'PLACE', 'PLACE', True, True, True, True),
        ('B_off', 'PLACE', 'PLACE', True, True, False, False),
        ('disabled_supervisor', 'PLACE', 'PLACE', False, True, True, False),
        ('unheld_PLACE', 'PLACE', 'PLACE', True, False, True, False),
        ('CARRY_mode_fake_PLACE_phase', 'CARRY', 'PLACE', True, True, True, False),
        ('RELEASE_terminal_PLACE_call', 'RELEASE', 'PLACE', True, True, True, False),
        ('PLACE_mode_CARRY_phase', 'PLACE', 'CARRY_transport', True, True, True, False),
        ('CARRY_direct', 'CARRY', 'CARRY_direct_transport', True, True, True, False),
        ('CARRY_clearance', 'CARRY', 'CARRY_clearance', True, True, True, False),
        ('CARRY_rotation', 'CARRY', 'CARRY_reorient', True, True, True, False),
        ('CARRY_transport_and_terminal', 'CARRY', 'CARRY_transport', True, True, True, False),
    ]
    for name, mode, phase, enabled, held, flag, expected_scope in scopes:
        ctx = context(phase, held=held)
        cfg = replace(base_cfg, place_braking=flag)
        c = controller(V21, cfg, ctx, mode=mode, enabled=enabled)
        actual = invoke(c, ctx)
        expected_cfg = C19(**{k: v for k, v in asdict(cfg).items() if k in {f.name for f in fields(C19)}})
        expected = invoke(controller(V19, expected_cfg, ctx, mode=mode, enabled=enabled), ctx)
        assert ('place21' in actual[1]) == expected_scope
        if not expected_scope:
            equivalent(actual, expected)
        records.append({'name': name, 'passed': True, 'place_scope': expected_scope,
                        'exact_parent': not expected_scope, 'work': actual[1]['work']})
    ctx = context()
    cfg = replace(base_cfg, terminal_settling=False)
    expected_cfg = replace(C19(), terminal_settling=False)
    equivalent(invoke(controller(V21, cfg, ctx, mode='PLACE'), ctx),
               invoke(controller(V19, expected_cfg, ctx, mode='PLACE'), ctx))
    records.append({'name': 'parent_terminal_settling_off_exact', 'passed': True})
    for name, ctx in [('phase_changed', context(previous_phase='CARRY_transport')),
                      ('attempt_changed', context(attempt=2, previous_attempt=1))]:
        actual = invoke(controller(V21, base_cfg, ctx, mode='PLACE'), ctx)
        fresh = list(copy.deepcopy(ctx)); fresh[4] = parent.ServoState()
        reference = invoke(controller(V21, base_cfg, fresh, mode='PLACE'), fresh)
        np.testing.assert_array_equal(actual[0], reference[0])
        assert actual[1]['state_reset_reason'] and actual[1]['position_bias_m'] == reference[1]['position_bias_m']
        records.append({'name': name, 'passed': True, 'reason': actual[1]['state_reset_reason']})
    ctx = context()
    action, receipt = invoke(controller(V21, base_cfg, ctx, mode='PLACE'), ctx)
    state = copy.deepcopy(ctx[4])
    assert state.commit(action, receipt)
    substituted = action.copy(); substituted[0] += np.float32(.001)
    assert not state.commit(substituted, receipt)
    assert state.goal is None and np.array_equal(state.bias, np.zeros(3))
    records.append({'name': 'helper_exact_commit_and_replaced_action_reset', 'passed': True,
                    'scope': 'ServoState contract only; final choose integration is tested separately by the central components receipt.'})
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='place_scope_static_a')
    args = parser.parse_args()
    output = RUN / 'analysis' / (args.name + '.json')
    assert not output.exists()
    stage = ROOT / 'reproduction/improvement_v20_20261019_01/smoke_a'
    assert read(stage / 'completed.json')['source_unchanged']
    jobs = [j for j in read(stage / 'jobs.json') if j['version'] == 'v19']
    assert len(jobs) == 9
    cases, anchor = [], None
    sources = [Path(__file__), stage / 'jobs.json', stage / 'completed.json']
    for job in jobs:
        found, candidate, paths = inspect_saved(job)
        cases.extend(found); sources.extend(paths)
        anchor = candidate or anchor
    assert anchor is not None
    checks = synthetic_checks(anchor)
    old, new = asdict(C19()), asdict(C21())
    assert all(new[key] == value for key, value in old.items()) and len(new) == 113 and len(old) == 111
    # No new release or PLACE dispatcher implementation: the original predicate
    # and protection-bearing placement path remain inherited unchanged.
    assert V21.placement_action16 is V19.placement_action16
    assert V21.enter is V19.enter
    for name, module in list(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if name.startswith('reproduction.') and path:
            path = Path(path).resolve()
            if path.suffix == '.py' and path.is_relative_to(ROOT): sources.append(path)
    counter = Counter((c['mode_at_proposal_from_saved_next_mode'], c['phase']) for c in cases)
    result = {
        'passed': True, 'scope': 'Actual V21.propose17 invoked on saved actual-v19 observations and parent committed memory; no choose/state-machine or physics replay.',
        'new_physical_episodes': 0, 'new_evaluation_samples': 0, 'new_controller_replays': 0,
        'source_executions': 9, 'unique_starts': 8,
        'saved_parent_action_and_receipt_reconstructions': len(cases),
        'B_off_exact_parent_proposals': len(cases),
        'B_on_outside_scope_exact_parent_proposals': sum(not c['scope_enabled'] for c in cases),
        'B_on_inside_PLACE_proposals': sum(c['scope_enabled'] for c in cases),
        'B_on_changed_actions': sum(c['new_action_changed'] for c in cases),
        'braking_triggered': sum(c['braking_triggered'] for c in cases),
        'inherited_config_fields_identical': len(old), 'total_config_fields': len(new),
        'maximum_geometry_work': max(c['work'] for c in cases),
        'scope_matrix': [{'mode': k[0], 'phase': k[1], 'proposals': value} for k, value in counter.items()],
        'checks': checks, 'cases': cases,
        'release_rule': {'inherited_placement_action16_identical': True, 'inherited_enter_identical': True,
            'condition': 'Original age>delay+5, object XY distance<0.05 and object z<floor+0.10; inherited loss and geometry/joint guards remain active.',
            'five_frame_scope': 'Five strict9mm/0.08rad frames govern held CARRY route segments. They are not a new PLACE release rule.',
            'release_transition_final_frame': 'When actual mode has already become RELEASE, phase=PLACE alone cannot enable B.'},
        'limitations': ['Saved-state proposal differences do not imply future closed-loop success or unchanged physical trajectories.',
            'Original parent memory is supplied independently; hypothetical new memory is not propagated along old observations.',
            'Final choose replacement and release-state flow are checked by separate central components, not by this helper-scope test.',
            'Same6000005 start appears in two profiles; nine source executions represent eight unique starts.'],
        'source_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(sources))},
    }
    with output.open('x', encoding='utf8') as stream:
        json.dump(finite(result), stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({k: result[k] for k in ['passed', 'saved_parent_action_and_receipt_reconstructions',
        'B_off_exact_parent_proposals', 'B_on_outside_scope_exact_parent_proposals',
        'B_on_inside_PLACE_proposals', 'B_on_changed_actions', 'braking_triggered']}))


if __name__ == '__main__':
    main()
