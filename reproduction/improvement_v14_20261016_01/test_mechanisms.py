"""Independent v14 mechanism checks: saved inputs and synthetic branches only.

No simulator is instantiated, no new success samples are produced, and archived
traces remain immutable. Synthetic patched geometry checks validate control flow,
not a geometric/physical safety certificate.
"""
from pathlib import Path
from dataclasses import asdict, replace
from unittest.mock import patch
import argparse
import ast
import copy
import hashlib
import json
import sys
import traceback
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v14_20261016_01.recovery import recovery_controller as module
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import RecoveryController, Config
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import RecoveryController as V13, Config as C13
from reproduction.improvement_v11_20261015_01.recovery.recovery_controller import RecoveryController as V11
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS

OLD = ROOT / 'reproduction/improvement_v13_20261016_01'
TARGET = [.1975, .4025, .8]
EVENTS = ['events', 'guard_events', 'geometry_events', 'joint_events', 'edge_events',
          'wait_hold_events', 'support13_events', 'escape_events', 'planning_events', 'pose_events']


def diagnostic_without_time(info):
    return {key: value for key, value in info.items() if key != 'planning_ms'}


def replay_off():
    episodes = steps = 0
    jobs = json.loads((OLD / 'pilot_a/jobs.json').read_text(encoding='utf8'))
    for job in jobs:
        if job['version'] != 'v13':
            continue
        current = None
        for row in map(json.loads, (OLD / 'pilot_a' / job['id'] / 'trace.jsonl').open(encoding='utf8')):
            x = np.array(row['state_before'], np.float32)
            if row['demo'] != current:
                current = row['demo']
                episodes += 1
                previous = np.zeros(7, np.float32)
                cfg = job['config']
                parent = V13(TARGET, .8, x, job['enabled'], C13(**cfg))
                child = RecoveryController(TARGET, .8, x, job['enabled'], Config(**cfg, trajectory_tracking=False, descent_clearance=False))
            for controller in [parent, child]:
                controller.set_joint_positions(row['joint_positions'])
                if job.get('force_recovery_at') == row['step']:
                    controller.start_attempt('diagnostic_forced_start', x)
            proposal = np.array(row['original_proposal'], np.float32)
            a, ai = parent.choose(x, proposal, previous)
            b, bi = child.choose(x, proposal, previous)
            np.testing.assert_array_equal(a, b)
            submitted = a.copy()
            # Diagnostic grasp-loss cases inject opening after choose().
            # Preserve the exact raw parent/child equality above; compare the
            # archived submitted command only after that documented injection.
            if row['fault_injected']:
                submitted[6] = -1.
            np.testing.assert_allclose(submitted, row['submitted_action'], rtol=0, atol=1e-7)
            assert diagnostic_without_time(ai) == diagnostic_without_time(bi)
            assert child.clock == parent.clock == row['step']
            assert 0 <= child.attempts <= 2
            for name in EVENTS:
                assert getattr(parent, name) == getattr(child, name), (job['id'], current, row['step'], name)
            assert child.tracking14_events == child.clearance14_events == []
            previous = np.array(row['executed_action'], np.float32)
            steps += 1
    assert episodes == 50, episodes
    return {'episodes': episodes, 'steps': steps, 'actions_exact': True,
            'diagnostics_exact_except_measured_planning_time': True, 'inherited_events_exact': True}


def saved_snapshots(condition, demo, wanted):
    """Get v14/off controllers immediately before selected archived input rows."""
    directory = OLD / 'confirmation' / ('v13_' + condition)
    job = json.loads((directory / 'result.json').read_text(encoding='utf8'))['job']
    controller = None
    previous = np.zeros(7, np.float32)
    prior_x = None
    prior_q = None
    found = {}
    for row in map(json.loads, (directory / 'trace.jsonl').open(encoding='utf8')):
        if row['demo'] != demo:
            continue
        x = np.array(row['state_before'], np.float32)
        if controller is None:
            controller = RecoveryController(TARGET, .8, x, True, Config(**job['config'], trajectory_tracking=False, descent_clearance=False))
        controller.set_joint_positions(row['joint_positions'])
        if row['step'] in wanted:
            candidate = copy.deepcopy(controller)
            candidate.cfg = replace(candidate.cfg, trajectory_tracking=True, descent_clearance=True)
            candidate.last_observed = None if prior_x is None else prior_x.copy()
            candidate.last_joints = None if prior_q is None else prior_q.copy()
            found[row['step']] = (candidate, copy.deepcopy(row), previous.copy())
        action, _ = controller.choose(x, np.array(row['original_proposal'], np.float32), previous)
        np.testing.assert_allclose(action, row['submitted_action'], rtol=0, atol=1e-7)
        previous = np.array(row['executed_action'], np.float32)
        prior_x = x.copy()
        prior_q = np.array(row['joint_positions'], float)
    assert set(found) == set(wanted)
    return found


def call_once(controller, row, previous):
    before = controller.clock
    action, info = controller.choose(np.array(row['state_before'], np.float32),
                                     np.array(row['original_proposal'], np.float32), previous)
    assert controller.clock == before + 1
    assert controller.clock <= 400 and controller.attempts <= 2
    assert np.all(np.isfinite(action)) and np.max(np.abs(action)) <= 1.000001
    json.dumps(info, allow_nan=False)
    return action, info


def targeted_checks():
    lean = saved_snapshots('bc_k2_noise005', 'demo_13000021', [207, 260, 365, 370])
    wall = saved_snapshots('full_s41_noise005', 'demo_13000022', [365, 371, 372])
    checks = []
    for collection in [lean, wall]:
        for step, (controller, row, previous) in collection.items():
            call_once(copy.deepcopy(controller), row, previous)
            checks.append({'kind': 'saved_input_one_decision_clock_budget', 'demo': row['demo'], 'step': step})

    controller, row, previous = copy.deepcopy(lean[260])
    x = np.array(row['state_before'], np.float32)
    controller.cfg = replace(controller.cfg, descent_clearance=False)
    controller.motion[:3] = [.004, -.002, .001]
    controller.motion[3:] = [.01, -.02, .01]
    controller.goal_rotation = controller.edge_plan['rotation'].copy()
    goal = controller.edge_plan['above']
    parent = copy.deepcopy(controller)
    parent.cfg = replace(parent.cfg, trajectory_tracking=False)
    plain = parent.pose_action(x, goal, 0.)
    damped = controller.pose_action(x, goal, 0.)
    assert not np.array_equal(plain[:3], damped[:3])
    assert np.linalg.norm(damped[:3] * .05) <= controller.cfg.max_delta_m + 1e-8
    assert np.linalg.norm(damped[3:6] * .5) <= controller.cfg.max_rotation_rad + 1e-8
    assert controller.clock == parent.clock, 'pose_action must not advance clock'
    before = controller.clock
    action, _ = V11.edge_action(controller, x)
    assert controller.clock == before + 1
    assert any(e['event'] == 'observed_motion_damping' for e in controller.tracking14_events)
    checks.append({'kind': 'explicit_v11_dispatch_reaches_v14_pose_action', 'passed': True})

    controller, row, previous = copy.deepcopy(lean[365])
    controller.cfg = replace(controller.cfg, descent_clearance=False)
    x = np.array(row['state_before'], np.float32)
    before, attempts = controller.clock, controller.attempts
    assert controller.joint_replan(x)
    assert controller.clock == before and controller.attempts == attempts
    assert controller.edge_plan is None and controller.edge_search is not None
    assert controller.tracking_replans[attempts] == 1
    assert np.min(np.minimum(controller.joints-LIMITS[:,0], LIMITS[:,1]-controller.joints)) < controller.cfg.joint_warning_rad
    checks.append({'kind': 'joint_warning_current_joint_replan_no_clock_or_attempt_reset', 'passed': True})

    controller, row, previous = copy.deepcopy(lean[365])
    # Below the warning margin alone does not imply an imminent .04rad breach.
    controller.joints = np.mean(LIMITS, axis=1)
    controller.last_joints = controller.joints.copy()
    controller.joints[0] = LIMITS[0,0]+.15
    controller.last_joints[0] = LIMITS[0,0]+.152
    assert not controller.joint_replan(np.array(row['state_before'], np.float32))
    assert not controller.tracking_replans
    checks.append({'kind': 'joint_warning_without_forecast_breach_keeps_checked_path', 'passed': True})

    controller, row, previous = copy.deepcopy(lean[365])
    controller.cfg = replace(controller.cfg, descent_clearance=False)
    controller.tracking_replans[controller.attempts] = controller.cfg.tracking_max_replans
    action, info = call_once(controller, row, previous)
    assert controller.mode == 'POSE_WAIT' and controller.edge_plan is None
    assert controller.events[-1]['reason'] == 'v14_joint_warning_no_untried_path'
    checks.append({'kind': 'joint_replan_limit_false_branch_waits_and_ticks_once', 'passed': True})

    # Synthetic positive/negative branch tests use a real saved DESCEND pose,
    # but patched local-margin results; these do not certify real feasibility.
    controller, row, previous = copy.deepcopy(wall[365])
    x = np.array(row['state_before'], np.float32)
    assert controller.mode == 'DESCEND'
    controller.cfg = replace(controller.cfg, trajectory_tracking=False)
    before = controller.clock
    with patch.object(module, 'sweep_margin', return_value=.002), patch.object(module, 'object_margin', side_effect=[.0035, .004, .004]):
        controller.recenter_start(x)
    assert controller.recenter is not None and controller.recenter_ik is not None
    assert controller.clock == before
    call_once(controller, row, previous)
    checks.append({'kind': 'synthetic_recenter_accepted_then_bounded_ik_ticks_once', 'passed': True})

    controller, row, previous = copy.deepcopy(wall[365])
    controller.cfg = replace(controller.cfg, trajectory_tracking=False)
    with patch.object(module, 'sweep_margin', return_value=.0009), patch.object(module, 'object_margin', side_effect=[.0035, .004, .004]):
        controller.recenter_start(np.array(row['state_before'], np.float32))
    assert controller.recenter is None
    assert controller.clearance14_events[-1]['accepted'] is False
    checks.append({'kind': 'synthetic_below_1mm_box_margin_rejected', 'passed': True})

    controller, row, previous = copy.deepcopy(wall[365])
    controller.cfg = replace(controller.cfg, trajectory_tracking=False)
    with patch.object(module, 'sweep_margin', return_value=.002), patch.object(module, 'object_margin', return_value=.0029):
        controller.recenter_start(np.array(row['state_before'], np.float32))
    assert controller.recenter is None
    assert controller.clearance14_events[-1]['accepted'] is False
    checks.append({'kind': 'synthetic_below_3mm_planned_can_margin_rejected', 'passed': True})

    # Refuse recenter before the inherited feasibility, aperture and movement
    # guards. Values are chosen to isolate the tighter 12mm movement bound
    # below the separate inherited 15mm pose-change threshold.
    for kind in ['unknown_feasibility', 'unsettled_gap', 'moved_12_1mm', 'too_open']:
        controller, row, previous = copy.deepcopy(wall[365])
        x = np.array(row['state_before'], np.float32)
        assert controller.recenter_eligible(x), 'saved positive pose must satisfy unchanged guards'
        if kind == 'moved_12_1mm':
            x[16:19] = controller.plan_anchor[:3]
            x[16] += .0121
            assert not controller.pose_changed(x)
        elif kind == 'too_open':
            aperture = controller.approach_gap + controller.cfg.aperture_tolerance_m + .003
            x[7], x[8] = aperture/2, -aperture/2
        with patch.object(controller, 'refresh_feasibility', return_value='unknown' if kind == 'unknown_feasibility' else 'feasible'), \
             patch.object(controller, 'gap_ready', return_value=kind != 'unsettled_gap'), \
             patch.object(module, 'sweep_margin', return_value=.002), \
             patch.object(module, 'object_margin', return_value=.0035):
            assert not controller.recenter_eligible(x)
            controller.recenter_start(x)
        assert controller.recenter is None and not controller.recenter_counts
        checks.append({'kind': 'recenter_rejects_' + kind, 'passed': True})

    controller, row, previous = copy.deepcopy(wall[365])
    x = np.array(row['state_before'], np.float32)
    with patch.object(module, 'object_margin', return_value=.004), patch.object(module, 'sweep_margin') as sweep:
        controller.recenter_start(x)
    assert controller.recenter is None and not controller.recenter_counts
    assert not sweep.called
    checks.append({'kind': 'adequate_live_clearance_does_not_recenter_for_lateral_motion_alone', 'passed': True})

    # An imposed prior velocity deliberately points away from the endpoint.
    # The submitted command must still stay inside the exact checked segment,
    # with no rotation/gripper increment and no perpendicular translation.
    controller, row, previous = copy.deepcopy(wall[365])
    x = np.array(row['state_before'], np.float32)
    direction = np.array([1., 2., -1.]); direction /= np.linalg.norm(direction)
    center = x[:3] + direction*.005
    controller.recenter = {'goal': center.copy(), 'rotation': Rotation.from_quat(x[3:7]).as_matrix(),
                           'axis': controller.edge_plan['rotation'][:,2].copy(), 'anchor': x[16:23].copy()}
    controller.recenter_ik = None
    controller.motion[:3] = -direction*.02
    controller.motion[3:] = [.03, -.04, .05]
    before = controller.clock
    with patch.object(controller, 'recenter_eligible', return_value=True), \
         patch.object(module, 'sweep_margin', return_value=.002) as sweep, \
         patch.object(module, 'object_margin', return_value=.004):
        action, info = controller.recenter_action(x)
    assert controller.clock == before+1 and info['mode'] == 'PATH_RECENTER'
    np.testing.assert_array_equal(action[3:], np.zeros(4))
    command = action[:3]*.05
    assert np.linalg.norm(np.cross(command, center-x[:3])) < 1e-9
    assert np.dot(command, center-x[:3]) >= 0
    assert np.linalg.norm(command) <= np.linalg.norm(center-x[:3])+1e-9, 'command may not overshoot the certified segment endpoint'
    np.testing.assert_array_equal(sweep.call_args.args[0], x[:3])
    np.testing.assert_array_equal(sweep.call_args.args[1], center)
    checks.append({'kind': 'recenter_command_zero_rotation_collinear_and_inside_certified_segment', 'passed': True})

    # Preserve strict 9mm / .08rad arrival and five consecutive observations.
    for distance, angle, accepted in [(.0089, .079, True), (.0091, .0, False), (.001, .081, False)]:
        controller, row, previous = copy.deepcopy(wall[365])
        x = np.array(row['state_before'], np.float32)
        rotation = Rotation.from_quat(x[3:7]).as_matrix()
        controller.edge_plan['rotation'] = Rotation.from_rotvec([angle, 0, 0]).as_matrix() @ rotation
        goal = controller.grasp_target(x)
        axis = controller.edge_plan['rotation'][:,2]
        x[:3] = goal-axis*.04
        controller.recenter = {'goal': x[:3]+np.array([distance, 0, 0]), 'rotation': rotation.copy(),
                               'axis': axis.copy(), 'anchor': x[16:23].copy()}
        controller.recenter_ik = None
        controller.motion[:] = 0
        with patch.object(controller, 'recenter_eligible', return_value=True), \
             patch.object(controller, 'gap_ready', return_value=True), \
             patch.object(module, 'sweep_margin', return_value=.002), \
             patch.object(module, 'object_margin', return_value=.004):
            for index in range(controller.cfg.delay+3):
                controller.recenter_action(x)
                if index < controller.cfg.delay+2 or not accepted:
                    assert controller.recenter is not None
        assert (controller.recenter is None) == accepted
        checks.append({'kind': 'recenter_arrival_threshold_and_five_frames', 'distance_m': distance, 'angle_rad': angle, 'accepted': accepted})

    controller, row, previous = copy.deepcopy(wall[365])
    x = np.array(row['state_before'], np.float32)
    controller.recenter = {'goal': x[:3].copy(), 'rotation': Rotation.from_quat(x[3:7]).as_matrix(),
                           'axis': controller.edge_plan['rotation'][:,2].copy(), 'anchor': x[16:23].copy()}
    controller.recenter_ik = None
    controller.age = controller.cfg.stage_timeout
    call_once(controller, row, previous)
    assert controller.recenter is None and controller.mode == 'POSE_WAIT'
    checks.append({'kind': 'recenter_preserves_70_step_phase_timeout', 'passed': True})

    controller, row, previous = copy.deepcopy(wall[365])
    controller.cfg = replace(controller.cfg, trajectory_tracking=False, descent_clearance=False)
    call_once(controller, row, previous)
    assert controller.tracking14_events == controller.clearance14_events == []
    checks.append({'kind': 'both_flags_disabled_no_new_mechanism_events', 'passed': True})
    return checks


def reuse_off_replay(receipt):
    """Reference the full earlier replay only after verifying off dispatch AST."""
    prior_path = RUN/'analysis'/receipt
    prior = json.loads(prior_path.read_text(encoding='utf8'))
    assert prior['passed'] and prior['off_replay']['episodes'] == 50
    archived = RUN/'smoke_a/source/recovery/recovery_controller.py'
    assert hashlib.sha256(archived.read_bytes()).hexdigest() == prior['source_sha256']
    def methods(path):
        tree = ast.parse(path.read_text(encoding='utf8'))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'RecoveryController')
        return {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}
    old, current = methods(archived), methods(Path(module.__file__))
    assert ast.dump(old['__init__']) == ast.dump(current['__init__'])
    # The on-path activation expression changed in b. For both flags false,
    # each version still calls the identical parent pose_action then returns
    # it unmodified. Check the unchanged call/return guard and inactive result.
    assert ast.dump(old['pose_action'].body[0]) == ast.dump(current['pose_action'].body[0])
    assert ast.dump(old['pose_action'].body[2]) == ast.dump(current['pose_action'].body[2])
    for methods_by_name in [old, current]:
        expression = ast.Expression(methods_by_name['pose_action'].body[1].value)
        expression = ast.fix_missing_locations(expression)
        for mode in ['NORMAL', 'EDGE_ROTATE', 'EDGE_APPROACH', 'DESCEND', 'POSE_WAIT']:
            for distance in [0., .001, .06, .5]:
                namespace = {'self': SimpleNamespace(cfg=Config(trajectory_tracking=False, descent_clearance=False), mode=mode),
                             'np': np, 'goal': np.array([distance,0,0]), 'x': np.zeros(23)}
                assert not eval(compile(expression, '<off-activation>', 'eval'), {'__builtins__': {}}, namespace)
    assert ast.dump(old['choose'].body[0]) == ast.dump(current['choose'].body[0])
    return {**prior['off_replay'], 'rerun_this_receipt': False,
            'referenced_receipt': prior_path.relative_to(RUN).as_posix(),
            'referenced_receipt_sha256': hashlib.sha256(prior_path.read_bytes()).hexdigest(),
            'referenced_controller_sha256': prior['source_sha256'],
            'same_initializer_parent_pose_call_and_choose_off_dispatch_ast': True,
            'both_pose_activation_expressions_false_when_flags_disabled': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='mechanisms_a')
    parser.add_argument('--reuse-off-replay', help='Existing analysis receipt; verifies unchanged off dispatch before reusing it.')
    args = parser.parse_args()
    destination = RUN / 'analysis' / (args.output + '.json')
    assert not destination.exists(), f'Will not overwrite {destination}'
    result = {'passed': False, 'new_physical_episodes': 0,
              'source_sha256': hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()}
    error = None
    try:
        for source in list(RUN.glob('*.py')) + list((RUN/'recovery').glob('*.py')):
            ast.parse(source.read_text(encoding='utf8'))
        old_cfg, new_cfg = asdict(C13()), asdict(Config())
        assert all(new_cfg[key] == value for key, value in old_cfg.items())
        result['all_inherited_config_fields_exact'] = len(old_cfg)
        result['off_replay'] = reuse_off_replay(args.reuse_off_replay) if args.reuse_off_replay else replay_off()
        result['targeted_checks'] = targeted_checks()
        result['passed'] = True
        result['limitations'] = ['Saved-input replay and synthetic control-flow checks only.',
                                'Closed-loop success and physical clearance require subsequent smoke/ablation runs.',
                                'Inherited flipped EDGE_ROTATE overwrites rotational damping with its existing capped command.']
    except Exception:
        error = traceback.format_exc()
        result['error'] = error
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if error:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
