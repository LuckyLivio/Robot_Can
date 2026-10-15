"""Same-history candidate audit: dynamics, state readout, and task completion.

Development-only diagnostics. Frozen deployed weights and scoring are not edited.
Each intervention reconstructs the simulator AND controller by replaying history.
"""
import argparse
from collections import deque
import csv
import hashlib
import json
from pathlib import Path
import time

import h5py
import numpy as np
import torch

from common import ROOT, DATA, make_env, pack_obs, restore_demo, load_policy, ChunkPolicy
from collect_rollout_branches import branch, error, replay, signature
from world_model import WorldModel, score, target_score


def write_json(path, value):
    with path.open('x', encoding='utf-8') as file:
        json.dump(value, file, indent=2, allow_nan=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate(scores, margin=.02, fallback=2):
    best = int(np.argmax(scores))
    return fallback if best != fallback and float(scores[best]-scores[fallback]) < margin else best


def imagine(model, state, commands, queue, horizon=8):
    sequences = np.stack([np.concatenate([queue, np.repeat(c[None], horizon, 0)])[:horizon]
                          for c in commands]).astype(np.float32)
    with torch.no_grad():
        future, logits = model(torch.from_numpy(np.repeat(state[None], len(commands), 0)),
                               torch.from_numpy(sequences))
        scores = score(logits, .5).numpy()
    return future.numpy(), logits.sigmoid().numpy(), scores, sequences


def continue_branch(env, demo, prefix, anchor, command, policy, model, mode, limit=400):
    checks = replay(env, demo, prefix, anchor)
    pending = deque(action.copy() for action in anchor['queue'])
    state = anchor['x'].copy()
    states, actions, submitted, selections, stages = [], [], [], [], []
    success = False
    for local_step in range(limit-len(prefix)):
        forced = local_step < (8 if mode == 'hold8_bc' else 1)
        if forced:
            new_action, selected = command.copy(), -1
        else:
            base = policy.best(torch.from_numpy(state[None]))[0].numpy()
            selected = 2
            if mode == 'once_wm':
                _, _, scores, _ = imagine(model, state, base[:4], np.asarray(pending, np.float32))
                selected = gate(scores)
            new_action = base[selected].copy()
        pending.append(new_action)
        action = np.clip(pending.popleft(), -1, 1)
        obs, *_ = env.step(action)
        state = pack_obs(obs)
        states.append(state.copy()); actions.append(action.copy())
        submitted.append(new_action.copy()); selections.append(selected)
        stages.append(np.asarray(env.staged_rewards()))
        success = bool(env._check_success())
        if success:
            break
    return {'success': success, 'end_step': len(prefix)+len(states),
            'ever_grasped_after_anchor': bool(np.any(np.asarray(stages)[:, 1] > .3)),
            'peak_stage_after_anchor': float(np.max(stages)),
            'final_object_position': state[16:19].tolist(),
            'final_stages': stages[-1].tolist()}, {
                'states': np.asarray(states), 'actions': np.asarray(actions),
                'submitted': np.asarray(submitted), 'selections': np.asarray(selections),
                'stages': np.asarray(stages)}, checks


def choose_anchors(traces):
    chosen = []
    for name, rows in traces.items():
        overrides = [r for r in rows if r['overrode_fallback'] and r['step'] <= 393]
        if not overrides:
            raise ValueError(f'No override anchors in {name}')
        choices = [('first_override', overrides[0])]
        if name != 'demo_105':
            choices.append(('largest_predicted_advantage', max(overrides, key=lambda r: r['selected_advantage'])))
            holding = [r for r in overrides if r['stages_before'][1] > .3]
            if holding:
                choices.append(('first_override_while_grasping', holding[0]))
        unique = {}
        for reason, row in choices:
            unique.setdefault(row['step'], {'demo': name, 'step': row['step'], 'reasons': []})['reasons'].append(reason)
        chosen.extend(sorted(unique.values(), key=lambda item: item['step']))
    return chosen


def main(args):
    directory = Path(args.output_dir).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    source_result = Path(args.trace_result).resolve()
    source = json.loads(source_result.read_text(encoding='utf-8'))
    cfg = source['args']
    required = {'split': 'dev', 'method': 'wm', 'delay': 2, 'horizon': 8, 'candidates': 4,
                'candidate_mode': 'shift', 'fallback': 'shift', 'fallback_index': 2,
                'gate_margin': .02, 'risk_weight': .5, 'noise': 0., 'score_only': True, 'steps': 400}
    if source['status'] != 'complete' or any(cfg.get(k) != v for k, v in required.items()):
        raise ValueError('Audit requires the frozen noise-free dev configuration')
    names = ['demo_97', 'demo_179', 'demo_105']
    dev = json.loads((ROOT/'data/splits.json').read_text())['dev']
    if any(n not in dev or n not in source['trace_files'] for n in names):
        raise ValueError('All diagnostic parents must be in dev and present in the source traces')
    traces = {n: [json.loads(line) for line in (source_result.parent/source['trace_files'][n]).read_text().splitlines()]
              for n in names}
    anchors = choose_anchors(traces)
    model_path = ROOT/'models'/cfg['model']/'model.pt'
    policy_path = ROOT/'policy'/cfg['policy']/cfg['policy_checkpoint']
    torch.set_num_threads(2)
    policy = load_policy(policy_path)
    if type(policy) is not ChunkPolicy:
        raise ValueError('This diagnostic requires the stateless MLP policy; history policies need replayed policy state')
    ck = torch.load(model_path, map_location='cpu', weights_only=True)
    if not ck['config'].get('future_only'):
        raise ValueError('True-state readout substitution requires a future_only head')
    model = WorldModel(ck['config']['dim'], ck['config']['width'], True)
    model.load_state_dict(ck['state_dict']); model.eval()
    provenance_paths = [source_result, model_path, policy_path, DATA, ROOT/'data/splits.json',
                        ROOT/'diagnose_candidate_truth.py', ROOT/'common.py', ROOT/'world_model.py',
                        ROOT/'collect_rollout_branches.py', ROOT/'collect_branches.py', ROOT/'evaluate_delay.py']
    provenance_paths += [source_result.parent/p for p in source['trace_files'].values()]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in provenance_paths}
    write_json(directory/'protocol.json', {
        'status': 'frozen_before_counterfactual_rollouts', 'source_args': cfg, 'anchors': anchors,
        'anchor_rule': 'Failed real-vs-k2 dev demos 97 and 179: first override, maximum predicted override advantage, first override while grasping. Successful demo105: first override. Deduplicate; step<=393.',
        'short_truth': 'Eight executed steps, same pending FIFO, candidate submitted repeatedly. Exact model input match.',
        'true_state_readout': 'Replace predicted states with actual states in the unchanged future_only head.',
        'continuations': {'once_bc': 'Submit candidate once, then original BC k=2 each step.',
                          'hold8_bc': 'Submit same candidate eight times, then original BC k=2.',
                          'once_wm': 'Submit candidate once, then unchanged deployed WM controller.'},
        'budget': '400 total steps from initial demo, including replayed prefix; stop on success.',
        'limitations': 'Selected dev failure cases, one checkpoint, deterministic noise-free conditional continuations; no population success-rate estimate or sealed-test tuning.',
        'sha256': hashes})
    checks = {}

    def check(key, value, tolerance=1e-7):
        checks[key] = max(checks.get(key, 0.), float(value))
        if value > tolerance:
            raise RuntimeError(f'{key} failed: {value}')

    previous = json.loads((ROOT/'reproduction/queuepair_20261012_01/real'/source_result.name).read_text())
    before = {r['demo']: r for r in previous['records']}
    for row in source['records']:
        for key in ('success', 'steps', 'peak_stage_reward', 'ever_grasped', 'selection_counts'):
            if row[key] != before[row['demo']][key]:
                raise RuntimeError('Traced run differs from completed queue coverage evaluation')
    check('trace_vs_previous_result', 0)
    results, baselines = [], {}
    started = time.perf_counter()
    env = make_env(False)
    try:
      with h5py.File(DATA, 'r') as file:
        for name in names:
            demo = file['data'][name]
            state = pack_obs(restore_demo(env, demo))
            base = policy.best(torch.from_numpy(state[None]))[0].numpy()
            initial = {'x': state, 'signature': signature(env), 'stages': np.asarray(env.staged_rewards()),
                       'queue': np.zeros((2, 7), np.float32)}
            summary, trajectory, _ = continue_branch(env, demo, [], initial, base[2], policy, model, 'once_bc')
            baselines[name] = (summary, trajectory)
            print(json.dumps({'baseline': name, **summary}), flush=True)
        for spec in anchors:
            name, step = spec['demo'], spec['step']
            rows, demo = traces[name], file['data'][name]
            row = rows[step-1]
            prefix = [np.asarray(r['executed_action'], np.float32) for r in rows[:step-1]]
            obs = restore_demo(env, demo)
            for action, expected in zip(prefix, rows):
                obs, *_ = env.step(action)
                check('trace_prefix_states', error(pack_obs(obs), expected['state_after']))
            anchor = {'x': pack_obs(obs), 'signature': signature(env),
                      'stages': np.asarray(env.staged_rewards()), 'queue': np.asarray(row['queue_before'], np.float32)}
            check('trace_anchor_state', error(anchor['x'], row['state_before']))
            check('trace_anchor_stages', error(anchor['stages'], row['stages_before']))
            pending = deque([np.zeros(7, np.float32) for _ in range(2)])
            for earlier in rows[:step-1]:
                pending.append(np.asarray(earlier['submitted_action'], np.float32))
                check('trace_fifo_actions', error(np.clip(pending.popleft(), -1, 1), earlier['executed_action']))
            check('trace_anchor_queue', error(pending, anchor['queue']))
            commands = policy.best(torch.from_numpy(anchor['x'][None]))[0].numpy()[:4]
            check('trace_candidates', error(commands, row['candidate_actions']))
            predicted, probabilities, predicted_scores, sequences = imagine(model, anchor['x'], commands, anchor['queue'])
            check('trace_predictions', error(predicted, row['predicted_states']))
            check('trace_scores', error(predicted_scores, row['learned_scores']))
            check('trace_model_sequences', error(sequences, row['model_sequences']))
            check('trace_selection', abs(gate(predicted_scores)-row['selected']))
            grouped = []
            for k, command in enumerate(commands):
                actual, recovered = branch(env, demo, prefix, anchor, anchor['queue'], command, 8)
                for key, value in recovered.items():
                    check('replay_'+key, value)
                check('matched_prediction_actions', error(actual['a'], sequences[k]))
                grouped.append(actual)
            for k in reversed(range(4)):
                reverse, _ = branch(env, demo, prefix, anchor, anchor['queue'], commands[k], 8)
                for key in ('a', 'y', 'labels'):
                    check('reverse_order_'+key, error(reverse[key], grouped[k][key]))
                check('common_fifo_states', error(grouped[k]['y'][:2], grouped[0]['y'][:2]))
                check('common_fifo_labels', error(grouped[k]['labels'][:2], grouped[0]['labels'][:2]))
            truth = np.stack([r['y'] for r in grouped])
            labels = np.stack([r['labels'] for r in grouped])
            with torch.no_grad():
                true_state_logits = model.labels((torch.from_numpy(truth)-model.mean)/model.scale)
                true_state_scores = score(true_state_logits, .5).numpy()
                true_state_probabilities = true_state_logits.sigmoid().numpy()
                true_scores = target_score(torch.from_numpy(labels), .5).numpy()
            selected = row['selected']
            result = {**spec, 'selected': selected, 'fallback': 2, 'initial_stages': anchor['stages'].tolist(),
                      'predicted_scores': predicted_scores.tolist(), 'true_state_readout_scores': true_state_scores.tolist(),
                      'true_short_scores': true_scores.tolist(),
                      'predicted_advantage_vs_k2': float(predicted_scores[selected]-predicted_scores[2]),
                      'true_state_readout_advantage_vs_k2': float(true_state_scores[selected]-true_state_scores[2]),
                      'true_advantage_vs_k2': float(true_scores[selected]-true_scores[2]),
                      'raw_winners': {'predicted': int(predicted_scores.argmax()), 'true_state_readout': int(true_state_scores.argmax()),
                                      'true_short': int(true_scores.argmax())},
                      'gated_winners': {'predicted': gate(predicted_scores), 'true_state_readout': gate(true_state_scores),
                                        'true_short': gate(true_scores)},
                      'candidates': []}
            arrays = {'predicted_states': predicted, 'true_states': truth, 'predicted_labels': probabilities,
                      'true_labels': labels, 'true_state_readout_labels': true_state_probabilities,
                      'executed_sequences': sequences, 'commands': commands, 'queue': anchor['queue'], 'anchor': anchor['x']}
            for k in range(4):
                candidate = {'k': k, 'predicted_score': float(predicted_scores[k]),
                             'true_state_readout_score': float(true_state_scores[k]), 'true_short_score': float(true_scores[k]),
                             'eef_error_mm_by_horizon': (np.linalg.norm(predicted[k, :, :3]-truth[k, :, :3], axis=1)*1000).tolist(),
                             'object_error_mm_by_horizon': (np.linalg.norm(predicted[k, :, 16:19]-truth[k, :, 16:19], axis=1)*1000).tolist(),
                             'predicted_progress_mae': float(np.abs(probabilities[k, :, 0]-labels[k, :, 0]).mean()),
                             'true_state_progress_mae': float(np.abs(true_state_probabilities[k, :, 0]-labels[k, :, 0]).mean()),
                             'predicted_max_risk': float(probabilities[k, :, 1].max()),
                             'true_state_max_risk': float(true_state_probabilities[k, :, 1].max()),
                             'true_max_risk': float(labels[k, :, 1].max()), 'continuations': {}}
                for mode in ('once_bc', 'hold8_bc', 'once_wm'):
                    outcome, trajectory, recovered = continue_branch(env, demo, prefix, anchor, commands[k], policy, model, mode)
                    for key, value in recovered.items():
                        check('replay_'+key, value)
                    if mode == 'once_wm' and k == selected:
                        tail = rows[step-1:]
                        check('deployed_continuation_states', error(trajectory['states'], [r['state_after'] for r in tail]))
                        check('deployed_continuation_actions', error(trajectory['actions'], [r['executed_action'] for r in tail]))
                        check('deployed_continuation_success', abs(int(outcome['success'])-int(tail[-1]['success_after'])))
                    if mode == 'once_bc' and k == 2 and 'first_override' in spec['reasons']:
                        baseline_summary, baseline_trajectory = baselines[name]
                        for key in ('states', 'actions'):
                            check('first_override_k2_baseline_'+key, error(trajectory[key], baseline_trajectory[key][step-1:]))
                        check('first_override_k2_baseline_success', abs(int(outcome['success'])-int(baseline_summary['success'])))
                    if mode == 'hold8_bc':
                        n = min(8, len(trajectory['states']))
                        check('hold8_short_truth', error(trajectory['states'][:n], truth[k, :n]))
                    candidate['continuations'][mode] = outcome
                    for key, value in trajectory.items():
                        arrays[f'k{k}_{mode}_{key}'] = value
                result['candidates'].append(candidate)
            name_root = f'{name}_step{step:03d}'
            with (directory/f'{name_root}.npz').open('xb') as output:
                np.savez_compressed(output, **arrays)
            write_json(directory/f'{name_root}.json', result)
            results.append(result)
            print(json.dumps({'anchor_complete': name_root, 'selected': selected, 'predicted_scores': result['predicted_scores'],
                              'true_scores': result['true_short_scores'], 'elapsed_s': time.perf_counter()-started}), flush=True)
    finally:
        env.close()
    payload = {'status': 'complete', 'source': str(source_result.relative_to(ROOT)), 'checks': checks,
               'baselines': {n: summary for n, (summary, _) in baselines.items()}, 'anchors': results,
               'elapsed_s': time.perf_counter()-started, 'sha256': hashes}
    write_json(directory/'results.json', payload)
    export(directory, payload)


def export(directory, payload):
    rows = []
    for anchor in payload['anchors']:
        for c in anchor['candidates']:
            row = {'demo': anchor['demo'], 'step': anchor['step'], 'k': c['k'], 'selected': c['k'] == anchor['selected']}
            row.update({key: c[key] for key in ('predicted_score', 'true_state_readout_score', 'true_short_score',
                                               'predicted_progress_mae', 'true_state_progress_mae',
                                               'predicted_max_risk', 'true_state_max_risk', 'true_max_risk')})
            for mode, outcome in c['continuations'].items():
                row[mode+'_success'] = outcome['success']; row[mode+'_end_step'] = outcome['end_step']
            rows.append(row)
    with (directory/'candidate_comparison.csv').open('x', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    n = len(payload['anchors'])
    fig, axes = plt.subplots(n, 2, figsize=(13, 3.1*n), constrained_layout=True)
    for i, anchor in enumerate(payload['anchors']):
        ax, bx = axes[i]
        x = np.arange(4)
        for values, label, marker in ((anchor['predicted_scores'], 'Predicted score', 'o'),
                                     (anchor['true_state_readout_scores'], 'Head on real future states', 's'),
                                     (anchor['true_short_scores'], 'Simulator short-horizon score', '^')):
            ax.plot(x, values, marker=marker, label=label)
        ax.axvline(anchor['selected'], color='gray', alpha=.3)
        ax.set(title=f"{anchor['demo']}, step {anchor['step']} (chosen k={anchor['selected']})",
               xticks=x, xlabel='Candidate k', ylabel='Score (higher is better)')
        ax.grid(alpha=.2)
        if i == 0:
            ax.legend(fontsize=8)
        outcomes = np.asarray([[int(c['continuations'][mode]['success']) for c in anchor['candidates']]
                               for mode in ('once_bc', 'hold8_bc', 'once_wm')])
        bx.imshow(outcomes, cmap=plt.cm.RdYlGn, vmin=0, vmax=1, aspect='auto', alpha=.7)
        for mode_index, mode in enumerate(('once_bc', 'hold8_bc', 'once_wm')):
            for k, candidate in enumerate(anchor['candidates']):
                outcome = candidate['continuations'][mode]
                bx.text(k, mode_index, f"{'Success' if outcome['success'] else 'Fail'}\nstep {outcome['end_step']}", ha='center', va='center', fontsize=9)
        bx.set(xticks=x, yticks=[0, 1, 2], yticklabels=['One command + BC k2', 'Eight commands + BC k2', 'One command + WM'],
               xlabel='Candidate k', title='Conditional task outcome (same total budget: 400)')
    fig.suptitle('Same-history counterfactual audit | dev only, noise=0, frozen real-queue WM', fontsize=14)
    fig.savefig(directory/'candidate_truth.png', dpi=160)
    fig.savefig(directory/'candidate_truth.pdf')
    plt.close(fig)
    print(json.dumps({'complete': str(directory), 'anchors': n, 'max_check_error': max(payload['checks'].values())}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace-result', required=True)
    parser.add_argument('--output-dir', required=True)
    main(parser.parse_args())
