"""Run the predeclared real-vs-zero-queue training comparison on development data.

Independent collection shards run in local subprocesses. Training uses the
existing architecture/loss/checkpoint rule and only evaluates the dev split.
Every dataset, model, log and result has a fresh name; nothing is promoted.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

from common import ROOT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def invoke(arguments, log, label):
    command = [sys.executable, '-B', '-u', *arguments]
    with log.open('x', encoding='utf-8') as handle:
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace',
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        for line in process.stdout:
            handle.write(line); handle.flush()
            print(f'[{label}] {line.rstrip()}', flush=True)
        if process.wait():
            raise RuntimeError(f'{label} failed; see {log}')


def combine(tag, split, shards, count):
    split_names = json.loads((ROOT/'data/splits.json').read_text())[split][:count]
    for mode in ('real', 'zero'):
        pieces, metadata = [], []
        for shard in shards:
            path = ROOT/'data'/f'branches_{split}_{shard}_{mode}.npz'
            with np.load(path, allow_pickle=False) as data:
                pieces.append({key: data[key].copy() for key in data.files})
            meta = json.loads(path.with_suffix('.json').read_text())
            if meta['status'] != 'complete' or meta['npz_sha256'] != sha(path):
                raise RuntimeError(f'Incomplete or changed shard: {path}')
            metadata.append(meta)
        arrays = {key: np.concatenate([piece[key] for piece in pieces]) for key in pieces[0]}
        parents = list(dict.fromkeys(arrays['parent'].tolist()))
        if parents != split_names:
            raise RuntimeError(f'Wrong parent order/split in {split}')
        out = ROOT/'data'/f'branches_{split}_{tag}_{mode}.npz'
        with out.open('xb') as handle:
            np.savez_compressed(handle, **arrays)
        meta = {'status': 'complete', 'action_semantics': 'executed_after_fifo',
                'input': 'PRIVILEGED_STATE_DIAGNOSTIC', 'queue_mode': mode,
                'anchor_source': 'closed_loop_bc_shift', 'restore_method': 'deterministic_replay_of_executed_prefix',
                'parents': parents, 'groups': len(arrays['x']), 'shards': shards,
                'shard_metadata': metadata, 'npz_sha256': sha(out),
                'checks': {key: max(m['checks'][key] for m in metadata) for key in metadata[0]['checks']}}
        with out.with_suffix('.json').open('x', encoding='utf-8') as handle:
            json.dump(meta, handle, indent=2)
    with np.load(ROOT/'data'/f'branches_{split}_{tag}_real.npz') as real, np.load(ROOT/'data'/f'branches_{split}_{tag}_zero.npz') as zero:
        for key in ('x', 'parent', 'point', 'commands'):
            if not np.array_equal(real[key], zero[key]):
                raise RuntimeError(f'Paired conditions differ in {key}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if not args.tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.tag):
        raise ValueError('Tag must contain only letters, digits, underscore or hyphen')
    if args.workers < 1:
        raise ValueError('workers must be positive')
    tag = args.tag
    out = ROOT/'reproduction'/tag
    jobs = [('train', i, 5) for i in range(0, 20, 5)] + [('dev', i, 4) for i in range(0, 8, 4)]
    for path in [out, *[ROOT/'models'/f'{tag}_{mode}_s17' for mode in ('real', 'zero')]]:
        if path.exists():
            raise FileExistsError(path)
    for split, start, _ in jobs:
        for name in (tag, f'{tag}_part{start:02d}'):
            for mode in ('real', 'zero'):
                path = ROOT/'data'/f'branches_{split}_{name}_{mode}.npz'
                if path.exists() or path.with_suffix('.json').exists():
                    raise FileExistsError(path)
    out.mkdir()
    (out/'logs').mkdir()
    protocol = {'question': 'Does training on real pending queues improve over zero queues at identical closed-loop anchors?',
                'train_parents': 20, 'dev_parents_for_branches': 8, 'points_per_parent': 8,
                'anchor_policy': 'bc_chunk_dev_v4/policy_15000.pt', 'rollout_shift': 2,
                'delay': 2, 'horizon': 8, 'candidates': 4, 'noise': 0,
                'method': 'full', 'future_only': True, 'seed': 17, 'updates': 3000,
                'batch': 16, 'width': 128, 'learning_rate': .0003, 'risk_weight': .5,
                'rank_weight': .2, 'selection_rule': 'minimum dev branch mean_regret, unchanged',
                'closed_loop_dev_episodes': 30, 'gate_margin': .02, 'fallback_index': 2,
                'sealed_test': 'not evaluated', 'promotion': 'none; this is one paired training-seed diagnostic',
                'implementation_sha256': {name: sha(ROOT/name) for name in
                    ['collect_rollout_branches.py','run_queue_coverage_probe.py','train_world.py','world_model.py','evaluate_delay.py','common.py']}}
    (out/'protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    def collect(job):
        split, start, count = job
        name = f'{tag}_part{start:02d}'
        invoke(['collect_rollout_branches.py', '--split', split, '--name', name,
                '--start', str(start), '--demos', str(count), '--points', '8'],
               out/'logs'/f'collect_{split}_{start:02d}.log', f'{split}:{start}')
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(collect, jobs))
    for split, count in [('train', 20), ('dev', 8)]:
        combine(tag, split, [f'{tag}_part{start:02d}' for sp, start, _ in jobs if sp == split], count)
    for mode in ('zero', 'real'):
        model = f'{tag}_{mode}_s17'
        invoke(['train_world.py', '--method', 'full', '--dataset', f'{tag}_{mode}',
                '--run', model, '--seed', '17', '--updates', '3000', '--batch', '16',
                '--width', '128', '--lr', '.0003', '--rank-weight', '.2', '--risk-weight', '.5', '--future-only'],
               out/'logs'/f'train_{mode}.log', f'train:{mode}')
        invoke(['evaluate_delay.py', '--method', 'wm', '--model', model,
                '--policy', 'bc_chunk_dev_v4', '--policy-checkpoint', 'policy_15000.pt',
                '--split', 'dev', '--episodes', '30', '--steps', '400', '--delay', '2',
                '--horizon', '8', '--candidates', '4', '--candidate-mode', 'shift',
                '--score-only', '--fallback', 'shift', '--fallback-index', '2',
                '--gate-margin', '.02', '--risk-weight', '.5', '--output-dir', str(out/mode)],
               out/'logs'/f'evaluate_{mode}.log', f'eval:{mode}')
    (out/'complete.json').write_text(json.dumps({'status':'complete','tag':tag,'protocol':protocol},indent=2),encoding='utf-8')
    print(json.dumps({'status': 'complete', 'output_dir': str(out)}), flush=True)


if __name__ == '__main__':
    main()
