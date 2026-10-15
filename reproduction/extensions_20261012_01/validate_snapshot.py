"""Compare native snapshots with full executed-history reconstruction."""
import sys, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import h5py, numpy as np, torch
from common import DATA, make_env, load_policy, restore_demo, pack_obs
from collect_rollout_branches import signature, branch, error, replay
from snapshot import true_branches
from collections import deque


def main():
    torch.set_num_threads(2)
    policy = load_policy(ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt')
    env = make_env(False)
    checks = []
    started = time.perf_counter()
    with h5py.File(DATA) as data:
        for name, noise in [('demo_105', 0.), ('demo_97', .05), ('demo_179', .05)]:
            demo = data['data'][name]
            obs = restore_demo(env, demo)
            queue = deque([np.zeros(7, np.float32) for _ in range(2)])
            prefix = []
            rng = np.random.default_rng(70000 + int(name.split('_')[1]))
            for step in range(280):
                x = pack_obs(obs)
                base = policy.best(torch.from_numpy(x[None]))[0].numpy()
                if step in [0, 40, 80, 120, 180, 240, 279]:
                    anchor = {'x': x.copy(), 'signature': signature(env),
                              'stages': np.asarray(env.staged_rewards()).copy()}
                    before = time.perf_counter()
                    ys, labels = true_branches(env, list(queue), base[:4], 8)
                    elapsed = time.perf_counter() - before
                    restore_error = error(signature(env), anchor['signature'])
                    reverse_y, reverse_l = true_branches(env, list(queue), base[:4], 8, [3, 2, 1, 0])
                    maxima = {'restored_signature': restore_error,
                              'reverse_y': error(ys, reverse_y), 'reverse_labels': error(labels, reverse_l)}
                    for k in range(4):
                        result, _ = branch(env, demo, prefix, anchor, list(queue), base[k], 8)
                        maxima[f'history_y_{k}'] = error(ys[k], result['y'])
                        maxima[f'history_labels_{k}'] = error(labels[k], result['labels'])
                    replay(env, demo, prefix, anchor)
                    assert max(maxima.values()) <= 1e-7, maxima
                    row = {'demo': name, 'noise': noise, 'step': step,
                           'stages': anchor['stages'].tolist(), 'max_error': max(maxima.values()),
                           'branch_seconds': elapsed}
                    checks.append(row)
                    print(json.dumps(row), flush=True)
                queue.append(base[2].copy())
                action = queue.popleft()
                if noise:
                    action[:3] += rng.normal(0, noise, 3)
                action = np.clip(action, -1, 1)
                prefix.append(action.copy())
                obs, *_ = env.step(action)
    env.close()
    result = {'passed': True, 'checks': checks, 'branches_compared': 4 * len(checks),
              'max_error': max(c['max_error'] for c in checks), 'elapsed_s': time.perf_counter() - started}
    out = Path(__file__).parent/'snapshot_validation.json'
    with out.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)


if __name__ == '__main__':
    main()
