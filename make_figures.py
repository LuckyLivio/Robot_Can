
"""Rebuild audited figures from recorded episodes. No training or simulation.

Original script and figures: reproduction/figures_audit_20261014_01/before/.
See figures/README.md for scope, provenance and statistical limitations.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

ROOT = Path(__file__).resolve().parent
CONF = 'reproduction/confirmation_20261012_01'
DEV = 'reproduction/multiseed_20261012_01'
SEEDS = (17, 23, 41)
COLORS = ('#2563eb', '#0d9488', '#e87924')
SOURCES = {}
DATA = {}
plt.rcParams.update({'font.family': 'sans-serif',
    'font.sans-serif': ['Microsoft YaHei', 'SimHei', 'DejaVu Sans'],
    'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.unicode_minus': False, 'pdf.fonttype': 42})


def read(rel):
    raw = (ROOT / rel).read_bytes()
    SOURCES[rel] = hashlib.sha256(raw).hexdigest()
    return raw.decode('utf-8-sig')


def load(rel):
    return json.loads(read(rel))


def records(run, count):
    """Use the episode index to locate raw JSON, and verify every indexed row."""
    rows = list(csv.DictReader(io.StringIO(read(f'{run}/analysis/episodes.csv'))))
    groups, by_source = {}, {}
    for row in rows:
        by_source.setdefault(row['source'], []).append(row)
    for source, indexed in by_source.items():
        result = load(source)
        raw = result['records']
        assert len(raw) == count and len({r['demo'] for r in raw}) == count, source
        assert len(indexed) == count and len({r['demo'] for r in indexed}) == count, source
        assert result.get('status', 'complete') == 'complete', source
        assert result['args']['delay'] == 2 and result['args']['steps'] == 400, source
        lookup = {r['demo']: r for r in raw}
        assert set(lookup) == {r['demo'] for r in indexed}, source
        first = indexed[0]
        condition = first.get('condition') or ('clean' if float(first['noise']) == 0 else 'noise005')
        seed = int(first['seed']) if first['seed'] else None
        key = (first['method'], seed, condition)
        assert key not in groups, key
        for row in indexed:
            assert row['method'] == first['method'] and row['seed'] == first['seed']
            r = lookup[row['demo']]
            assert type(r['success']) is bool and 1 <= r['steps'] <= 400
            assert r['success'] == (row['success'] == 'True') and r['steps'] == int(row['steps'])
        groups[key] = lookup
    starts = [set(g) for g in groups.values()]
    assert all(s == starts[0] for s in starts), 'Unmatched starts'
    return groups


def success_rates(groups, method, condition):
    seeds = [None] if method.startswith('bc_') else SEEDS
    return [100 * np.mean([r['success'] for r in groups[method, s, condition].values()]) for s in seeds]


def check_summary(groups, run):
    for row in csv.DictReader(io.StringIO(read(f'{run}/analysis/summary.csv'))):
        condition = row.get('condition') or ('clean' if float(row['noise']) == 0 else 'noise005')
        if condition == 'joint_equal_weight':
            actual = np.mean([success_rates(groups, row['method'], c) for c in ('clean', 'noise005')])
        else:
            actual = np.mean(success_rates(groups, row['method'], condition))
        assert np.isclose(actual, float(row['mean_success_percent'])), row


def save(fig, name, out, note):
    fig.text(.5, .015, note, ha='center', va='bottom', fontsize=9, color='#475569')
    fig.tight_layout(rect=(0, .07, 1, .96))
    fig.savefig(out / f'{name}.png', dpi=300, facecolor='white')
    fig.savefig(out / f'{name}.pdf', facecolor='white')
    plt.close(fig)


def rates_figure(groups, methods, labels, name, title, out, count):
    fig, axes = plt.subplots(1, 2, figsize=(max(10, len(methods) * 1.7), 5.1), sharey=True)
    export = []
    for ax, condition, subtitle in zip(axes, ('clean', 'noise005'), ('无噪声', '动作噪声 σ=0.05')):
        values = [success_rates(groups, m, condition) for m in methods]
        means = [np.mean(v) for v in values]
        ax.bar(range(len(methods)), means, color=['#94a3b8' if m.startswith('bc_') else '#93c5fd' for m in methods], width=.62)
        for i, (m, v) in enumerate(zip(methods, values)):
            ax.text(i, max(v) + 3, f'{np.mean(v):.1f}%', ha='center', fontsize=10)
            for j, rate in enumerate(v):
                ax.scatter(i + (j - (len(v)-1)/2)*.10, rate, color=COLORS[j], s=25, zorder=3)
            export.append({'method': m, 'condition': condition, 'seed_rates_percent': v, 'mean_percent': float(np.mean(v)), 'independent_starts': count})
        ax.set(xticks=range(len(methods)), xticklabels=labels, ylim=(0, 108), title=subtitle, ylabel='成功率（%）')
        ax.grid(axis='y', alpha=.18); ax.set_axisbelow(True)
    fig.suptitle(title, fontsize=14)
    DATA[name] = export
    save(fig, name, out, f'每条件 {count} 个共同起点；BC 固定一个权重；彩色点 = WM 训练种子 17 / 23 / 41。柱为种子均值，非独立样本置信区间。')


def paired_figures(conf, out):
    all_steps = []
    for condition, suffix, title in [('clean', 'clean', '无噪声'), ('noise005', 'noise005', '动作噪声 σ=0.05')]:
        fig, axes = plt.subplots(1, 3, figsize=(12, 4.6), sharey=True)
        data = []
        bc = conf['bc_k2', None, condition]
        for ax, seed in zip(axes, SEEDS):
            full = conf['full', seed, condition]
            counts = [0, 0, 0, 0]
            for demo in sorted(bc):
                b, w = bc[demo], full[demo]
                counts[{(True, True): 0, (False, True): 1, (True, False): 2, (False, False): 3}[b['success'], w['success']]] += 1
                if b['success'] and w['success']:
                    all_steps.append({'condition': condition, 'seed': seed, 'demo': demo, 'bc_steps': b['steps'], 'full_steps': w['steps'], 'difference': w['steps']-b['steps']})
            assert sum(counts) == len(bc)
            ax.bar(range(4), counts, color=['#94a3b8', '#0d9488', '#e87924', '#cbd5e1'])
            for i, n in enumerate(counts): ax.text(i, n+1, str(n), ha='center')
            ax.set(xticks=range(4), xticklabels=['双方\n成功', '仅 Full\n成功', '仅 BC\n成功', '双方\n失败'], ylim=(0, 65), title=f'Full 种子 {seed}', ylabel='同一起点的回合数')
            data.append({'seed': seed, 'condition': condition, 'counts': counts})
        fig.suptitle(f'独立确认 · Full 与 BC k=2 配对结果 · {title}', fontsize=14)
        DATA[f'figure_paired_{suffix}'] = data
        save(fig, f'figure_paired_{suffix}', out, '每面板同一批 60 个起点；三个面板共享起点，不能当作 180 个独立样本。未加入恢复控制。')
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
    for ax, cond, title in zip(axes, ('clean', 'noise005'), ('无噪声', '动作噪声 σ=0.05')):
        arrays = [[r['difference'] for r in all_steps if r['condition']==cond and r['seed']==s] for s in SEEDS]
        ax.boxplot(arrays, tick_labels=[f's{s}\nn={len(a)}' for s, a in zip(SEEDS, arrays)], showfliers=False)
        for i, a in enumerate(arrays, 1):
            ax.scatter(i+np.linspace(-.14, .14, len(a)), a, s=12, alpha=.5, color=COLORS[i-1])
        ax.axhline(0, color='#64748b', linestyle='--', linewidth=1)
        ax.set(title=title, xlabel='Full 训练种子 · 双方成功交集大小', ylabel='配对步数差：Full − BC k=2（步）')
        ax.grid(axis='y', alpha=.18)
    fig.suptitle('独立确认 · 同一起点、双方均成功的完成步数差', fontsize=14)
    DATA['figure_success_steps'] = all_steps
    save(fig, 'figure_success_steps', out, '负值 = Full 更快；点为全部配对观测，箱体为四分位数。条件于双方成功，不能代表全体回合效率。')


def training(out):
    fields = [('loss', '训练总损失（当前批次）'), ('prediction_loss', '训练状态预测损失（当前批次）'),
              ('ranking_loss', '训练排序损失（当前批次）'), ('mean_regret', '开发集候选评分 regret（越低越好）')]
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.3))
    export = []
    for seed, color in zip(SEEDS, COLORS):
        folder = f'models/multiseed_20261012_01_full_s{seed}'
        log, cfg, complete = load(f'{folder}/log.json'), load(f'{folder}/config.json'), load(f'{folder}/training_complete.json')
        assert cfg['method']=='full' and cfg['seed']==seed
        steps = [r['step'] for r in log]
        assert steps == sorted(set(steps)) and steps[-1] == cfg['updates']
        selected = complete['selected_step']
        assert selected == min(log, key=lambda r: r['selection_criterion'])['step']
        for ax, (field, title) in zip(axes.flat, fields):
            y = [r[field] for r in log]
            assert np.isfinite(y).all()
            ax.plot(steps, y, marker='o', ms=3, lw=1.4, color=color, label=f's{seed}')
            if field == 'mean_regret':
                ax.scatter(selected, y[steps.index(selected)], marker='*', s=150, color=color, edgecolor='white', zorder=5)
            ax.set(title=title, xlabel='优化器更新次数（step）', xlim=(0, cfg['updates']+100))
            ax.grid(alpha=.18)
        export.append({'seed': seed, 'selected_step': selected, 'records': [{k: r[k] for k in ['step']+[f[0] for f in fields]} for r in log]})
    axes[0, 0].legend(frameon=False, ncols=3)
    fig.suptitle('Full 公平训练 · 三个训练种子的原始记录', fontsize=14)
    DATA['figure_training_curves'] = export
    save(fig, 'figure_training_curves', out, '每 250 次更新记录一次；连线仅连接采样点，未平滑；星号为按开发集 regret 选择的权重。不是 epoch 均值或确认集曲线。')


def diagram(out):
    for p in [f'{CONF}/evaluator_core.py', 'world_model.py', 'collect_branches.py']: read(p)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set(xlim=(0, 12), ylim=(0, 6)); ax.axis('off')
    boxes = [(0.2, 3.6, '当前仿真状态 x_t\n23 维特权状态'), (4.25, 3.6, '固定 BC 动作块\n候选 k=0,1,2,3'),
             (8.3, 3.6, '候选想象序列\nFIFO 前缀 + 重复候选\nH=8，D=2'),
             (8.3, 1.1, 'GRU 递推未来状态\n预测进展 p 与失抓风险 r'),
             (4.25, 1.1, '评分与门控\n超过 k=2 分数至少 0.02\n否则使用 k=2'),
             (0.2, 1.1, '仅提交本次一个动作\n进入 D=2 延迟队列\n执行队首动作，再观测')]
    for x, y, label in boxes:
        ax.add_patch(FancyBboxPatch((x, y), 3.45, 1.25, boxstyle='round,pad=0.12', facecolor='#eff6ff', edgecolor='#94a3b8'))
        ax.text(x+1.725, y+.625, label, ha='center', va='center', fontsize=10)
    arrows = [((3.8,4.225),(4.1,4.225)),((7.85,4.225),(8.15,4.225)),((10.025,3.4),(10.025,2.55)),
              ((8.15,1.725),(7.85,1.725)),((4.1,1.725),(3.8,1.725)),((1.925,2.55),(1.925,3.4))]
    for a, b in arrows: ax.annotate('', xy=b, xytext=a, arrowprops={'arrowstyle':'->', 'lw':1.5, 'color':'#475569'})
    ax.text(6, .3, 'S = p(H) + 0.5 × mean(p) − 0.5 × max(r)；r 为失抓标签，不等同于所有失败概率。', ha='center', fontsize=10)
    fig.suptitle('Full 世界模型候选选择 · 独立确认配置', fontsize=14)
    DATA['figure_method_diagram'] = {'scope': 'World-model selection without shared recovery', 'delay': 2, 'horizon': 8, 'candidates': 4, 'fallback_index': 2, 'gate_margin': .02}
    save(fig, 'figure_method_diagram', out, '所有候选使用同一当前状态和真实队列前缀；滚动重规划。此图不包含后续 v1–v5 共享恢复控制，也不是纯视觉系统。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'figures')
    args = parser.parse_args(); out = args.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    conf, dev = records(CONF, 60), records(DEV, 30)
    check_summary(conf, CONF); check_summary(dev, DEV)
    rates_figure(conf, ['bc_k2','plain','full'], ['BC k=2','Plain','Full'], 'figure_success_rate', '独立确认 · 世界模型成功率（无共享恢复控制）', out, 60)
    rates_figure(dev, ['bc_k2','full','plain','direct','prediction_only','no_risk_score','no_gate'],
                 ['BC k=2','Full','Plain','Direct','仅预测','无风险评分','无门控'],
                 'figure_ablation', '公平开发集 · 三种子消融（用于分析与选择，非独立确认）', out, 30)
    paired_figures(conf, out); training(out); diagram(out)
    payload = {'sources_sha256': SOURCES, 'figures': DATA,
               'validation': {'raw_episodes_checked': sum(map(len,conf.values()))+sum(map(len,dev.values())),
                              'summary_rates_match_raw': True, 'paired_ids_equal': True, 'new_simulation_episodes': 0}}
    (out/'figure_data.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print(json.dumps(payload['validation'], ensure_ascii=False))


if __name__ == '__main__':
    main()
