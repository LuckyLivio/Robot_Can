"""Paired real/zero FIFO branches from the same closed-loop BC-shift states.

Each branch reconstructs its complete history by replaying the exact executed
action prefix from the demo initial state. No incomplete mid-rollout simulator
snapshot is used. Train/dev parents remain isolated; sealed_test is unsupported.
"""
import argparse
from collections import deque
import hashlib
import json
import time

import h5py
import numpy as np
import torch

from common import ROOT, DATA, make_env, pack_obs, restore_demo, load_policy
from collect_branches import future_labels


def error(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise RuntimeError('Invalid shape or non-finite value in replay check')
    return float(np.max(np.abs(a - b))) if a.size else 0.0


def signature(env):
    values = [env.sim.get_state().flatten().copy(), env.sim.data.ctrl.copy(),
              env.sim.data.qacc_warmstart.copy(), np.asarray([env.timestep])]
    for robot in env.robots:
        for controller in robot.part_controllers.values():
            for key in ('initial_joint', 'joint_pos', 'joint_vel', 'ref_pos',
                        'ref_ori_mat', 'goal_pos', 'goal_ori', 'goal_qvel'):
                value = getattr(controller, key, None)
                if value is not None:
                    values.append(np.asarray(value).reshape(-1).copy())
    return np.concatenate(values)


def rollout(env, demo, policy, delay, shift, steps):
    obs = restore_demo(env, demo)
    if hasattr(policy, 'reset'):
        policy.reset()
    pending = deque([np.zeros(7, np.float32) for _ in range(delay)])
    anchors, executed = [], []
    for step in range(steps):
        state = pack_obs(obs)
        base = policy.best(torch.from_numpy(state[None]))[0].numpy()
        if not 0 <= shift < len(base):
            raise ValueError('Rollout shift is outside the BC chunk')
        anchors.append({'x': state, 'base': base.copy(), 'signature': signature(env),
                        'queue': np.asarray(pending, np.float32).reshape(-1, 7).copy(),
                        'stages': np.asarray(env.staged_rewards()).copy()})
        pending.append(base[shift].copy())
        action = np.clip(pending.popleft(), -1, 1)
        executed.append(action.copy())
        obs, *_ = env.step(action)
        if env._check_success():
            return anchors, executed, True
    return anchors, executed, False


def replay(env, demo, prefix, anchor):
    obs = restore_demo(env, demo)
    for action in prefix:
        obs, *_ = env.step(action)
    checks = {'observation': error(pack_obs(obs), anchor['x']),
              'physics_controller': error(signature(env), anchor['signature']),
              'stages': error(env.staged_rewards(), anchor['stages'])}
    if max(checks.values()) > 1e-7:
        raise RuntimeError(f'History replay did not recover the anchor: {checks}')
    return checks


def branch(env, demo, prefix, anchor, queue, command, horizon):
    checks = replay(env, demo, prefix, anchor)
    pending = deque(action.copy() for action in queue)
    initial_grasp = bool(anchor['stages'][1] > .3)
    actions, states, labels = [], [], []
    for _ in range(horizon):
        pending.append(command.copy())
        action = np.clip(pending.popleft(), -1, 1)
        obs, *_ = env.step(action)
        actions.append(action.copy())
        states.append(pack_obs(obs))
        labels.append(future_labels(env, initial_grasp))
    return {'a': np.asarray(actions, np.float32), 'y': np.asarray(states, np.float32),
            'labels': np.asarray(labels, np.float32)}, checks


def main(args):
    if min(args.demos, args.points, args.horizon, args.candidates, args.steps) < 1 or args.delay < 0:
        raise ValueError('Counts must be positive and delay nonnegative')
    if args.delay >= args.horizon:
        raise ValueError('Horizon must extend beyond the common FIFO prefix')
    if '/' in args.name or '\\' in args.name or args.name in ('.', '..'):
        raise ValueError('Name must be a single dataset basename')
    names = json.loads((ROOT/'data/splits.json').read_text())[args.split]
    if args.start < 0 or args.start + args.demos > len(names):
        raise ValueError('Requested more parent demos than the split contains')
    selected = names[args.start:args.start + args.demos]
    paths = {mode: ROOT/'data'/f'branches_{args.split}_{args.name}_{mode}.npz'
             for mode in ('real', 'zero')}
    for path in paths.values():
        if path.exists() or path.with_suffix('.json').exists():
            raise FileExistsError(f'Refusing to overwrite branch data: {path}')
    torch.set_num_threads(2)
    policy_path = ROOT/'policy'/args.policy/args.policy_checkpoint
    policy = load_policy(policy_path)
    if args.candidates > policy.horizon:
        raise ValueError('More shift candidates requested than the BC chunk contains')
    arrays = {mode: {key: [] for key in ('x', 'a', 'y', 'labels', 'parent', 'point', 'queue', 'commands')}
              for mode in paths}
    checks = {'observation': 0.0, 'physics_controller': 0.0, 'stages': 0.0,
              'common_prefix_states': 0.0, 'common_prefix_labels': 0.0,
              'reverse_order_states': 0.0, 'reverse_order_labels': 0.0,
              'matched_closed_loop_prefix': 0.0, 'fifo_actions': 0.0}
    start = time.perf_counter()
    episodes = []
    env = make_env(False)
    try:
        with h5py.File(DATA, 'r') as data:
            for name in selected:
                demo = data['data'][name]
                anchors, executed, success = rollout(env, demo, policy, args.delay, args.shift_index, args.steps)
                stop = len(anchors) - args.horizon - 1
                if stop < 10 or stop - 10 + 1 < args.points:
                    raise ValueError(f'Not enough rollout points in {name}')
                indices = np.linspace(10, stop, args.points, dtype=int)
                for point_index, point in enumerate(indices):
                    anchor = anchors[point]
                    commands = anchor['base'][:args.candidates]
                    for mode, buffer in arrays.items():
                        queue = anchor['queue'] if mode == 'real' else np.zeros_like(anchor['queue'])
                        grouped = []
                        for command in commands:
                            result, replay_checks = branch(env, demo, executed[:point], anchor, queue, command, args.horizon)
                            for key, value in replay_checks.items():
                                checks[key] = max(checks[key], value)
                            expected = np.concatenate([queue, np.repeat(command[None], args.horizon, axis=0)])[:args.horizon]
                            checks['fifo_actions'] = max(checks['fifo_actions'], error(result['a'], np.clip(expected, -1, 1)))
                            grouped.append(result)
                        for result in grouped[1:]:
                            checks['common_prefix_states'] = max(checks['common_prefix_states'], error(result['y'][:args.delay], grouped[0]['y'][:args.delay]))
                            checks['common_prefix_labels'] = max(checks['common_prefix_labels'], error(result['labels'][:args.delay], grouped[0]['labels'][:args.delay]))
                        if mode == 'real' and args.delay:
                            actual = [anchors[point + offset + 1]['x'] for offset in range(args.delay)]
                            checks['matched_closed_loop_prefix'] = max(checks['matched_closed_loop_prefix'], error(grouped[0]['y'][:args.delay], actual))
                        # Check every selected point in validation runs, or the first point per parent otherwise.
                        if args.verify_all or point_index == 0:
                            for k in reversed(range(len(commands))):
                                reverse, _ = branch(env, demo, executed[:point], anchor, queue, commands[k], args.horizon)
                                checks['reverse_order_states'] = max(checks['reverse_order_states'], error(reverse['y'], grouped[k]['y']))
                                checks['reverse_order_labels'] = max(checks['reverse_order_labels'], error(reverse['labels'], grouped[k]['labels']))
                        buffer['x'].append(anchor['x']); buffer['queue'].append(queue.copy())
                        buffer['commands'].append(np.repeat(commands[:, None], args.horizon, axis=1))
                        for key in ('a', 'y', 'labels'):
                            buffer[key].append(np.stack([r[key] for r in grouped]))
                        buffer['parent'].append(name); buffer['point'].append(int(point))
                        if max(checks.values()) > 1e-7:
                            raise RuntimeError(f'Branch validation failed: {checks}')
                episodes.append({'demo': name, 'rollout_steps': len(anchors), 'success': success,
                                 'sampled_points_zero_based': indices.tolist()})
                print(json.dumps({'demo': name, 'groups_per_mode': len(arrays['real']['x']),
                                  'max_check_error': max(checks.values()),
                                  'elapsed_s': time.perf_counter()-start}), flush=True)
    finally:
        env.close()
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in [DATA, ROOT/'data/splits.json', policy_path, ROOT/'common.py',
                           ROOT/'collect_branches.py', ROOT/'collect_rollout_branches.py']}
    for mode, buffer in arrays.items():
        packed = {key: np.asarray(value, dtype=str if key == 'parent' else np.int64 if key == 'point' else np.float32)
                  for key, value in buffer.items()}
        # Exclusive creation only after the whole collection passes validation.
        with paths[mode].open('xb') as handle:
            np.savez_compressed(handle, **packed)
        meta = {'args': vars(args), 'queue_mode': mode, 'status': 'complete',
                'input': 'PRIVILEGED_STATE_DIAGNOSTIC', 'action_semantics': 'executed_after_fifo',
                'anchor_source': 'closed_loop_bc_shift', 'point_semantics': 'number_of_executed_prefix_steps',
                'restore_method': 'deterministic_replay_of_executed_prefix',
                'groups': len(buffer['x']), 'parents': selected, 'episodes': episodes,
                'checks': checks, 'reverse_checks': 'all_points' if args.verify_all else 'first_point_each_parent',
                'nonzero_queue_groups': int(np.any(packed['queue'] != 0, axis=(1, 2)).sum()),
                'source_sha256': hashes, 'npz_sha256': hashlib.sha256(paths[mode].read_bytes()).hexdigest(),
                'elapsed_s': time.perf_counter()-start}
        with paths[mode].with_suffix('.json').open('x', encoding='utf-8') as handle:
            json.dump(meta, handle, indent=2, allow_nan=False)
    print(json.dumps({'datasets': {mode: str(path) for mode, path in paths.items()}, 'checks': checks}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=['train', 'dev'], required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--demos', type=int, default=20)
    parser.add_argument('--start', type=int, default=0, help='Parent offset for independent collection shards')
    parser.add_argument('--points', type=int, default=8)
    parser.add_argument('--steps', type=int, default=400)
    parser.add_argument('--delay', type=int, default=2)
    parser.add_argument('--horizon', type=int, default=8)
    parser.add_argument('--candidates', type=int, default=4)
    parser.add_argument('--shift-index', type=int, default=2)
    parser.add_argument('--policy', default='bc_chunk_dev_v4')
    parser.add_argument('--policy-checkpoint', default='policy_15000.pt')
    parser.add_argument('--verify-all', action='store_true')
    main(parser.parse_args())
