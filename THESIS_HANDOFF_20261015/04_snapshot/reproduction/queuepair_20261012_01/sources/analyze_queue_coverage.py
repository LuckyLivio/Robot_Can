"""Analyze a paired queue-coverage probe without changing models or test results."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch

from common import ROOT
from world_model import WorldModel, score, target_score, rank_metrics


def load_model(path):
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    cfg = checkpoint['config']
    model = WorldModel(cfg['dim'], cfg['width'], cfg.get('future_only', False))
    model.load_state_dict(checkpoint['state_dict']); model.eval()
    if not all(torch.isfinite(t).all() for t in model.state_dict().values()):
        raise ValueError(f'Non-finite model: {path}')
    return model, checkpoint


def branch_metrics(model, data):
    n, k, h, _ = data['a'].shape
    xx = np.repeat(data['x'][:, None], k, axis=1).reshape(n*k, -1)
    aa = data['a'].reshape(n*k, h, 7)
    yy = data['y'].reshape(n*k, h, -1)
    labels = data['labels'].reshape(n*k, h, 2)
    predictions, readouts = [], []
    with torch.no_grad():
        for start in range(0, n*k, 64):
            y, r = model(torch.from_numpy(xx[start:start+64]), torch.from_numpy(aa[start:start+64]))
            predictions.append(y.numpy()); readouts.append(r)
    predicted = np.concatenate(predictions)
    logits = torch.cat(readouts)
    ranks = rank_metrics(score(logits).numpy(), target_score(torch.from_numpy(labels)).numpy(), n, k)
    eef = np.linalg.norm(predicted[:, :, :3]-yy[:, :, :3], axis=-1)*1000
    obj = np.linalg.norm(predicted[:, :, 16:19]-yy[:, :, 16:19], axis=-1)*1000
    probs = logits.sigmoid().numpy()
    return {**ranks, 'eef_mean_error_mm_by_horizon': eef.mean(0).tolist(),
            'object_mean_error_mm_by_horizon': obj.mean(0).tolist(),
            'progress_mae': float(np.abs(probs[:, :, 0]-labels[:, :, 0]).mean()),
            'risk_brier': float(np.square(probs[:, :, 1]-labels[:, :, 1]).mean())}


def paired(a, b):
    aa = {row['demo']: row for row in a['records']}
    bb = {row['demo']: row for row in b['records']}
    if set(aa) != set(bb) or len(aa) != 30 or len(a['records']) != 30 or len(b['records']) != 30:
        raise ValueError('Expected the same 30 unique dev demos')
    shared = ('policy', 'policy_checkpoint', 'split', 'delay', 'noise', 'steps')
    if any(a['args'][key] != b['args'][key] for key in shared):
        raise ValueError('Unmatched closed-loop evaluation parameters')
    return {'a_only_success': [name for name in aa if aa[name]['success'] and not bb[name]['success']],
            'b_only_success': [name for name in aa if bb[name]['success'] and not aa[name]['success']],
            'both_success': sum(aa[name]['success'] and bb[name]['success'] for name in aa),
            'both_failure': sum(not aa[name]['success'] and not bb[name]['success'] for name in aa)}


def plot_report(report, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels = {'previous':'Previous WM', 'zero':'Rollout / zero queue',
              'real':'Rollout / real queue', 'k2':'BC shift k=2'}
    colors = {'previous':'#89939e', 'zero':'#db8a33', 'real':'#178b83', 'k2':'#435064'}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    order = ['previous', 'zero', 'real', 'k2']
    values = [report['closed_loop_dev'][key]['successes'] for key in order]
    bars = axes[0].bar(range(4), values, color=[colors[key] for key in order], width=.65)
    axes[0].set_xticks(range(4), [labels[key].replace(' / ', '\n') for key in order], fontsize=9)
    axes[0].set_ylim(0, 32); axes[0].set_yticks(range(0, 31, 5))
    axes[0].set_ylabel('Successful development episodes (out of 30)')
    axes[0].bar_label(bars, labels=[f'{value}/30' for value in values], padding=4)
    axes[0].set_title('Closed-loop task performance')
    for key in ('previous', 'zero', 'real'):
        errors = report['shared_real_queue_dev_branch_metrics'][key]['object_mean_error_mm_by_horizon']
        axes[1].plot(range(1, len(errors)+1), errors, marker='o', markersize=4, color=colors[key], label=labels[key])
    axes[1].set_xlabel('Prediction horizon (control steps)')
    axes[1].set_ylabel('Mean object position error (mm)')
    axes[1].set_title('Same real-queue development branches')
    axes[1].legend(frameon=False, fontsize=9)
    for ax in axes:
        ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Queue coverage probe | one training seed (17) | development data only', fontsize=12)
    fig.savefig(out/'queue_coverage_probe.png', dpi=180)
    fig.savefig(out/'queue_coverage_probe.pdf')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--reference-model', default='fixed_20261011_234708_859_full')
    args = parser.parse_args()
    out = ROOT/'reproduction'/args.tag/'analysis'
    if out.exists():
        raise FileExistsError(out)
    torch.set_num_threads(2)
    datasets = {}
    dataset_checks = {}
    for split in ('train', 'dev'):
        datasets[split] = {}
        for mode in ('real', 'zero'):
            path = ROOT/'data'/f'branches_{split}_{args.tag}_{mode}.npz'
            with np.load(path, allow_pickle=False) as data:
                datasets[split][mode] = {key: data[key].copy() for key in data.files}
        a, b = datasets[split]['real'], datasets[split]['zero']
        for key in ('x', 'parent', 'point', 'commands'):
            if not np.array_equal(a[key], b[key]):
                raise ValueError(f'Paired anchors differ: {split}/{key}')
        if np.any(b['queue']):
            raise ValueError('Zero queue condition contains a nonzero queue')
        if set(a['parent']) & set(json.loads((ROOT/'data/splits.json').read_text())['sealed_test']):
            raise ValueError('Unexpected sealed-test parent')
        for mode, data in datasets[split].items():
            if not all(np.isfinite(data[key]).all() for key in ('x', 'a', 'y', 'labels', 'queue')):
                raise ValueError('Non-finite branch data')
            targets = target_score(torch.from_numpy(data['labels'].reshape(-1, 8, 2))).numpy().reshape(-1, 4)
            dataset_checks[f'{split}_{mode}'] = {
                'groups': len(data['x']), 'parents': len(set(data['parent'])),
                'nonzero_queue_groups': int(np.any(data['queue'] != 0, axis=(1, 2)).sum()),
                'groups_with_score_range_over_025': int((np.ptp(targets, axis=1) > .025).sum()),
                'risk_positive_groups': int(np.any(data['labels'][..., 1] > 0, axis=(1, 2)).sum())}
    models, checkpoints = {}, {}
    for mode in ('real', 'zero'):
        models[mode], checkpoints[mode] = load_model(ROOT/'models'/f'{args.tag}_{mode}_s17'/'model.pt')
    models['previous'], checkpoints['previous'] = load_model(ROOT/'models'/args.reference_model/'model.pt')
    for field in ('mean', 'scale'):
        if not torch.equal(getattr(models['real'], field), getattr(models['zero'], field)):
            raise ValueError('Paired model normalization differs')
    for key in ('seed','method','width','updates','batch','lr','rank_weight','risk_weight','future_only'):
        if checkpoints['real']['config'][key] != checkpoints['zero']['config'][key]:
            raise ValueError(f'Unmatched training parameter: {key}')
    offline = {mode: branch_metrics(model, datasets['dev']['real']) for mode, model in models.items()}
    results = {}
    for mode in ('real', 'zero'):
        paths = list((ROOT/'reproduction'/args.tag/mode).glob('delay_wm_dev_*.json'))
        if len(paths) != 1:
            raise ValueError('Expected one matched dev result per queue condition')
        results[mode] = json.loads(paths[0].read_text())
        if results[mode]['status'] != 'complete':
            raise ValueError('Incomplete evaluation')
    previous = ROOT/'models'/args.reference_model
    results['previous'] = json.loads((previous/'delay_wm_dev_d2_shift_fbshift_fbi2_gm0.02_score.json').read_text())
    results['k2'] = json.loads((previous/'delay_bc_shift_dev_d2_k2.json').read_text())
    closed = {}
    for name, result in results.items():
        successes = sum(bool(r['success']) for r in result['records'])
        if abs(successes/len(result['records']) - result['success_rate']) > 1e-8:
            raise ValueError('Incorrect saved success rate')
        closed[name] = {'successes': successes, 'episodes': len(result['records']),
                        'success_rate': result['success_rate'],
                        'selected_step': checkpoints[name]['selected_step'] if name in checkpoints else None,
                        'demo_105': next(r for r in result['records'] if r['demo'] == 'demo_105'),
                        'demo_179': next(r for r in result['records'] if r['demo'] == 'demo_179')}
    comparisons = {f'{a}_vs_{b}': paired(results[a], results[b]) for a, b in
                   [('real','zero'), ('real','previous'), ('real','k2'), ('zero','k2')]}
    report = {'scope': 'development-only paired single-training-seed probe; no test-set or promotion',
              'paired_conditions': 'same rollout states/parents/points/commands/normalization/training recipe; real vs zero pending queue',
              'dataset_checks': dataset_checks, 'shared_real_queue_dev_branch_metrics': offline,
              'closed_loop_dev': closed, 'paired_comparisons': comparisons,
              'checkpoint_selected_steps': {name: ck['selected_step'] for name, ck in checkpoints.items()},
              'limitations': ['One training seed, not a multi-seed advantage claim.',
                              'The previous model also differs in anchor distribution; only real-vs-zero is the paired queue intervention.',
                              'BC-shift rollout anchors do not cover all states visited by the WM controller.',
                              'Dev branch metrics use the same real-queue futures for all models.',
                              'Evaluation success, not lower offline prediction error, determines control utility.']}
    lines = ['真实队列训练覆盖对照：开发集诊断', '',
             '两组使用同一批闭环起点、候选命令、归一化和训练配置，仅改变分支起始队列。',
             '训练20条父轨迹/160组；开发分支8条父轨迹/64组；闭环开发评估30个共同起点。',
             '各组仅训练seed17，未运行sealed_test，未替换已有模型。', '', '闭环结果：']
    for name, r in closed.items():
        lines.append(f"{name}: {r['successes']}/{r['episodes']}；保存检查点step={r['selected_step']}；demo105={r['demo_105']['success']}；demo179={r['demo_179']['success']}")
    lines.extend(['', '同一真实队列开发分支上的两步位置预测误差：'])
    for name, metrics in offline.items():
        lines.append(f"{name}: 末端 {metrics['eef_mean_error_mm_by_horizon'][1]:.2f} mm；物体 {metrics['object_mean_error_mm_by_horizon'][1]:.2f} mm；排序遗憾 {metrics['mean_regret']:.6f}")
    for name, pair in comparisons.items():
        lines.append(f"{name}: 前者独胜 {pair['a_only_success']}；后者独胜 {pair['b_only_success']}")
    lines.extend(['', '解释：旧模型与新模型还存在起点分布变化，不能把二者差异全部归因于队列。',
                  '只有新real与新zero是配对队列对照。离线误差下降不自动代表闭环成功率上升。',
                  '本报告是开发诊断，不能宣称多种子稳定提升或封存测试结论。', ''])
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    out.mkdir()
    (out/'analysis.json').write_text(encoded, encoding='utf-8')
    (out/'diagnosis.txt').write_text('\n'.join(lines), encoding='utf-8')
    with (out/'comparison.csv').open('x', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['condition','dev_successes','episodes','selected_step','eef_h2_mm','object_h2_mm','mean_regret'])
        writer.writeheader()
        for name, row in closed.items():
            metrics = offline.get(name, {})
            writer.writerow({'condition':name,'dev_successes':row['successes'],'episodes':row['episodes'],
                             'selected_step':row['selected_step'],
                             'eef_h2_mm':metrics.get('eef_mean_error_mm_by_horizon',[None,None])[1],
                             'object_h2_mm':metrics.get('object_mean_error_mm_by_horizon',[None,None])[1],
                             'mean_regret':metrics.get('mean_regret')})
    plot_report(report, out)
    print('\n'.join(lines), flush=True)


if __name__ == '__main__':
    main()
