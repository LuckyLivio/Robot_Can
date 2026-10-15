import argparse
from collections import deque
import json
from pathlib import Path
import time

import h5py
import numpy as np

from common import ROOT, DATA, OBS_KEYS, make_env, pack_obs, restore_demo
from collect_branches import future_labels


def max_error(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise RuntimeError('Non-finite state or observation in restoration check.')
    return float(np.max(np.abs(a - b)))


def geometry_error(obs):
    from robosuite.utils import transform_utils as T

    x = pack_obs(obs)
    relative = T.pose_in_A_to_pose_in_B(
        T.pose2mat((x[16:19], x[19:23])),
        T.pose_inv(T.pose2mat((x[:3], x[3:7]))),
    )
    observed = T.pose2mat((x[9:12], x[12:16]))
    # Compare rotation matrices, since q and -q represent the same orientation.
    return max_error(relative, observed)


def controller_snapshot(env):
    values = []
    for robot in env.robots:
        for controller in robot.part_controllers.values():
            error = max_error(controller.joint_pos, env.sim.data.qpos[controller.qpos_index])
            if getattr(controller, 'ref_name', None) is not None:
                error = max(error, max_error(
                    controller.ref_pos, env.sim.data.get_site_xpos(controller.ref_name)))
            if error > 1e-8:
                raise RuntimeError(f'Controller cache does not match restored state: {error}')
            for key in ('initial_joint', 'joint_pos', 'joint_vel', 'ref_pos',
                        'ref_ori_mat', 'goal_pos', 'goal_ori', 'goal_qvel'):
                value = getattr(controller, key, None)
                if value is not None:
                    values.append(np.asarray(value).reshape(-1).copy())
    return np.concatenate(values)


def rollout(env, demo, index, commands, xml=False, delay=2):
    obs = restore_demo(env, demo, index, xml=xml)
    initial = pack_obs(obs)
    controllers = controller_snapshot(env)
    geometry = geometry_error(obs)
    initial_grasp = bool(env.staged_rewards()[1] > .3)
    queue = deque([np.zeros(7, np.float32) for _ in range(delay)], maxlen=delay + 1)
    states, observations, labels, actions = [], [], [], []
    for command in commands:
        queue.append(command)
        executed = queue.popleft()
        actions.append(executed.copy())
        obs, *_ = env.step(executed)
        observations.append(pack_obs(obs))
        states.append(env.sim.get_state().flatten().copy())
        labels.append(future_labels(env, initial_grasp))
    expected = np.concatenate([np.zeros((delay, 7)), commands], axis=0)[:len(commands)]
    if max_error(actions, expected) != 0:
        raise RuntimeError('FIFO action alignment failed.')
    return {'initial': initial, 'controllers': controllers, 'geometry': geometry,
            'states': np.asarray(states), 'obs': np.asarray(observations),
            'labels': np.asarray(labels)}


def check_branches(env, demo, index):
    commands = [np.repeat(demo['actions'][index + k][None], 8, axis=0) for k in range(4)]
    forward = [rollout(env, demo, index, command) for command in commands]
    errors = {
        'initial_repeat_max_error': max(max_error(r['initial'], forward[0]['initial']) for r in forward),
        'controller_repeat_max_error': max(max_error(r['controllers'], forward[0]['controllers']) for r in forward),
        'geometry_max_error': max(r['geometry'] for r in forward),
        'zero_prefix_max_error': max(max_error(r[key][:2], forward[0][key][:2])
                                     for r in forward for key in ('states', 'obs', 'labels')),
    }
    for mode, order in [('reverse', range(3, -1, -1)), ('xml', range(4))]:
        error = 0.
        for k in order:
            repeated = rollout(env, demo, index, commands[k], xml=(mode == 'xml'))
            errors['geometry_max_error'] = max(errors['geometry_max_error'], repeated['geometry'])
            for key in ('initial', 'controllers', 'states', 'obs', 'labels'):
                error = max(error, max_error(repeated[key], forward[k][key]))
        errors[f'{mode}_repeat_max_error'] = error
    if max(errors.values()) > 1e-5:
        raise RuntimeError(f'Branch restoration check failed at {index}: {errors}')
    return {'index': index, **errors}


def main(report_path=None):
    if report_path is not None:
        report_path = ROOT / report_path
        if report_path.exists():
            raise FileExistsError(f'Refusing to overwrite smoke report: {report_path}')
    start = time.perf_counter()
    env = make_env(False)
    report = {'mode': 'STATE_DIAGNOSTIC', 'replays': [],
              'compatibility_only': ['initial_max_error', '40_step_max_error']}
    try:
        with h5py.File(DATA, 'r') as file:
            for name in ['demo_0', 'demo_1']:
                demo = file['data'][name]
                obs = restore_demo(env, demo)
                ref = np.concatenate([demo['obs'][k][0] for k in OBS_KEYS])
                initial = max_error(pack_obs(obs), ref)
                # Logged relative poses can contain the old reset cache. Keep their
                # mismatch visible, but validate physical fields and geometry separately.
                direct = np.r_[0:9, 16:23]
                direct_error = max_error(pack_obs(obs)[direct], ref[direct])
                geometry = geometry_error(obs)
                if direct_error > 1e-3 or geometry > 1e-5:
                    raise RuntimeError(f'Initial physical observation mismatch: {name}')
                controller_snapshot(env)
                errors = []
                for t in range(min(40, len(demo['actions']))):
                    obs, *_ = env.step(demo['actions'][t])
                    ref = np.concatenate([demo['next_obs'][k][t] for k in OBS_KEYS])
                    errors.append(max_error(pack_obs(obs), ref))
                checks = [check_branches(env, demo, t)
                          for t in sorted({20, min(90, len(demo['actions']) - 8)})]
                row = {'demo': name, 'initial_max_error': initial,
                       'initial_direct_max_error': direct_error, 'initial_geometry_max_error': geometry,
                       '40_step_max_error': max(errors), 'branch_checks': checks}
                report['replays'].append(row)
                print(json.dumps(row), flush=True)
    finally:
        env.close()
    report.update(checks_passed=True, elapsed_s=time.perf_counter() - start)
    # Default is read-only. Explicit reports are created exclusively, never overwritten.
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open('x', encoding='utf-8') as output:
            json.dump(report, output, indent=2)
    print(json.dumps({'checks_passed': True, 'elapsed_s': report['elapsed_s'],
                      'report': str(report_path) if report_path is not None else None}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, help='Optional new JSON path; existing files are refused.')
    main(parser.parse_args().report)
