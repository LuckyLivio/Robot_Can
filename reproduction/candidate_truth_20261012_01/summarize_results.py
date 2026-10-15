"""Render the completed candidate audit without rerunning any simulation."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(directory):
    audit = directory/'audit'
    data = json.loads((audit/'results.json').read_text(encoding='utf-8'))
    if data['status'] != 'complete' or max(data['checks'].values()) > 1e-7:
        raise ValueError('Only a completed validated audit can be summarized')
    anchors = data['anchors']
    indexed = {(a['demo'], a['step']): a for a in anchors}
    metrics = {
        'anchor_count': len(anchors), 'candidate_count': sum(len(a['candidates']) for a in anchors),
        'continuation_count': sum(len(c['continuations']) for a in anchors for c in a['candidates']),
        'unsupported_margin_at_selected_anchors': sum(a['true_advantage_vs_k2'] < .02 for a in anchors),
        'reversed_advantage_at_selected_anchors': sum(a['true_advantage_vs_k2'] < 0 for a in anchors),
        'score_mae_predicted': float(np.mean([abs(c['predicted_score']-c['true_short_score']) for a in anchors for c in a['candidates']])),
        'score_mae_head_on_real_states': float(np.mean([abs(c['true_state_readout_score']-c['true_short_score']) for a in anchors for c in a['candidates']])),
        'population_inference': False,
    }
    with (audit/'summary_metrics.json').open('x', encoding='utf-8') as file:
        json.dump(metrics, file, indent=2)
    text = [
        '同状态四候选反事实诊断（开发集）',
        '',
        '结论：同时存在状态预测偏差、任务评分头偏差，以及重复动作规划与单步干预之间的效果差异。',
        '当前证据不能证明只改一个评分公式或门限就能修复整个项目，也不能证明世界模型没有作用。',
        '',
        '一、实验范围和公平性',
        '模型：queuepair_20261012_01_real_s17；原 BC 权重；D=2，H=8，4候选，回退k=2，门限0.02，无噪声。',
        '开发失败回合97、179各3个检查点，成功回合105的首次干预作为参照。规则在真实分支执行前写入protocol.json。',
        '共7个同状态起点、28个短期候选分支、84次条件续接，并将28个短期分支逆序重跑。',
        '从回合起点重放全部已执行动作，恢复物理状态、控制器和待执行队列。四候选使用同一历史。',
        f"{len(data['checks'])}项校验全部通过，最大误差={max(data['checks'].values()):g}；原WM选择的续接完整复现原日志，首次干预点的k=2+BC续接完整复现BC基线。",
        '全部结果仅为开发集诊断，没有运行封存测试，没有更新任何模型权重。',
        '',
        '二、三个分数各是什么意思',
        '预测分数：预测未来状态，再经原评分头得到进度/失抓风险，代入原公式。',
        '真实状态读出分数：把真实未来状态代入同一个评分头，检验状态正确时它能否正确读出任务进度与风险。',
        '真实短期分数：真实仿真的进度/失抓标签代入同一个公式。',
        '公式为末步进度 + 0.5×平均进度 − 0.5×最大失抓风险；总分不是成功概率，允许超过1或小于0。',
        '这里的风险仅指起点已抓住物体而分支中失抓，不是一般任务失败概率。',
        '真实短期分支严格匹配模型输入的8个实际执行动作；不能把不同动作序列造成的差异算成预测误差。',
        '',
        '三、关键证据',
        '1. demo97，第35步：模型选择k=3，预测相对k=2优势+0.023083；真实优势−0.003088。',
        '   将真实状态送入评分头后，该相对优势为−0.000077，原来的过门限优势消失。这个点的错误相对优势与预测状态有关。',
        '2. demo179，第45步：模型选择k=0；只提交一次后由同一个BC接管，k=0失败，k=1/2/3全部成功。',
        '   k=0预测分1.068029，真实短期分0.005934；k=2分别为1.034635和0.007807。',
        '   即使输入真实未来状态，k=0/k=2评分仍高达0.933262/0.989174，说明任务读出也有明显偏差。',
        '3. demo97，第90步：四候选的真实风险均为1，真实总分约−0.405；真实状态评分头仍给0.505～0.567。',
        '   所以仅提高状态预测精度不足以保证正确评分。该点四候选在三种续接下均失败，不能声称换一个候选即可救回。',
        '4. demo97，第58步：k=0连续提交8次后由BC接管，100步成功；只提交一次再由BC接管，400步失败。',
        '   k=2只提交一次再由BC接管则113步成功。当前重复动作下的8步评分，不能直接代表单次命令的最终效果。',
        '5. demo105，第70步：k=0真实短期分0.475441，高于k=2的0.059469；一次k=0+BC在131步成功，k=2+BC在278步成功。',
        '   这是有效干预的正面例子。但真实状态评分头反而偏好k=2（0.871290比0.457493），说明预测与评分误差存在抵消现象。',
        '',
        '四、门限与归因的边界',
        f"这7个刻意选取的干预点中，{metrics['unsupported_margin_at_selected_anchors']}个的真实短期优势未达到0.02；{metrics['reversed_advantage_at_selected_anchors']}个的优势方向反了。这不是总体错误率估计。",
        f"28个候选的分数MAE：原预测链={metrics['score_mae_predicted']:.6f}；真实状态送入评分头={metrics['score_mae_head_on_real_states']:.6f}。",
        '真实状态替换不会自动修好评分；评分头是与预测状态联合训练的，这种替换是诊断干预，不能把误差严格分成彼此独立的贡献百分比。',
        '在这7个起点中，真实8步最高分候选没有出现“连续提交8次+BC失败、但另一个候选成功”的反例；不能据此宣称公式本身已被证伪。',
        '但真实8步最高分并不总对应“只提交一次+BC/WM”的成功候选。已验证的是有限时域代理目标与实际续接效果之间存在差异。',
        '后期97/90、179/109、179/160在本实验的四候选与三种续接下全失败，不代表物理上绝对不可恢复，只说明当前候选和续接方式未找到恢复路径。',
        '97/35和179/45即使只把这一次命令改为k=2、以后仍由原WM决定，也仍失败，因此不能声称只修正第一次干预就足够。',
        '',
        '五、下一步最小验证方向（本次尚未实施）',
        '1. 先做评分头校准对照：加入真实未来状态上的进度/风险监督，保留预测状态上的监督；检查失抓、抓取和低进度状态的分数。',
        '2. 单独对齐候选的规划与训练标签：以“一次候选干预，再由固定BC接管”为明确分支语义，比较原重复动作方案；不要同时改多个因素。',
        '3. 在未用于调试的训练父轨迹收集更多抓取边界与失抓分支，保留demo105这类有效干预，先做全30开发回合检查。',
        '4. 修复成立后再冻结方案，做3个训练种子、k=2/Direct/Plain对照，再按冻结方案评价封存测试。历史测试结果已查看，应如实记录；若需要严格未见的最终测试，应另设不参与调参的新测试起点。',
        '以上是待验证修复假设，尚不能保证成功率提升；旧模型和原始结果继续保留。',
        '',
        '六、全部候选结果',
        '列：k | 预测分 | 真实状态读出分 | 真实短期分 | 一次+BC | 连续8次+BC | 一次+WM',
        '成功/失败后数字为从原回合起点计的结束步数；每条分支总预算均为400步。',
    ]
    for a in anchors:
        text.append(f"\n{a['demo']} 第{a['step']}步，原WM选择k={a['selected']}，原因={','.join(a['reasons'])}")
        for c in a['candidates']:
            outcomes = [f"{'成功' if c['continuations'][m]['success'] else '失败'}@{c['continuations'][m]['end_step']}"
                        for m in ('once_bc','hold8_bc','once_wm')]
            text.append(f"{c['k']} | {c['predicted_score']:.6f} | {c['true_state_readout_score']:.6f} | {c['true_short_score']:.6f} | " + ' | '.join(outcomes))
    text.extend(['', '数据入口：results.json、candidate_comparison.csv、每个起点的JSON/NPZ、protocol.json。',
                 '图表：overview.png/pdf为关键案例；candidate_truth.png/pdf为全部7个检查点。'])
    with (audit/'diagnosis.txt').open('x', encoding='utf-8') as file:
        file.write('\n'.join(text)+'\n')
    plt.rcParams['font.family'] = ['Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), constrained_layout=True)

    def bars(ax, anchor, title):
        x = np.arange(4)
        for offset, key, label, color in [(-.25,'predicted_scores','原模型预测','#3977b7'),
                                         (0,'true_state_readout_scores','真实状态→原评分头','#df9734'),
                                         (.25,'true_short_scores','仿真真实短期分数','#389e82')]:
            ax.bar(x+offset, anchor[key], width=.24, label=label, color=color)
        ax.set(xticks=x, xticklabels=[f'k={k}' for k in range(4)], ylabel='分数（不是成功概率）', title=title)
        ax.axhline(0, color='black', linewidth=.7); ax.grid(axis='y', alpha=.2)
        ax.legend(fontsize=8, loc='best')

    def outcomes(ax, anchor, modes, title):
        labels = {'once_bc':'一次命令 + BC接管', 'hold8_bc':'连续8次命令 + BC接管', 'once_wm':'一次命令 + WM接管'}
        values = np.asarray([[int(c['continuations'][m]['success']) for c in anchor['candidates']] for m in modes])
        ax.imshow(values, cmap=matplotlib.colors.ListedColormap(['#f2c5bd','#bbe0d1']), vmin=0, vmax=1, aspect='auto')
        for y,m in enumerate(modes):
            for k,c in enumerate(anchor['candidates']):
                result = c['continuations'][m]
                ax.text(k,y,f"{'成功' if result['success'] else '失败'}\n{result['end_step']}步",ha='center',va='center',fontsize=11)
        ax.set(xticks=np.arange(4), xticklabels=[f'k={k}' for k in range(4)], yticks=np.arange(len(modes)),
               yticklabels=[labels[m] for m in modes], title=title)
        ax.tick_params(axis='y', labelsize=9)
    bars(axes[0,0], indexed['demo_179',45], '① 同状态：模型偏好k=0，真实短期分数偏好k=2\ndemo179，第45步')
    outcomes(axes[0,1], indexed['demo_179',45], ['once_bc','once_wm'], '② 相同一次干预，不同后续控制方式\ndemo179，第45步')
    bars(axes[1,0], indexed['demo_97',90], '③ 输入真实未来状态，评分仍明显偏高\ndemo97，第90步（四候选均失抓）')
    outcomes(axes[1,1], indexed['demo_97',58], ['once_bc','hold8_bc'], '④ 提交一次与提交8次的后果不同\ndemo97，第58步')
    fig.suptitle('同状态四候选诊断：预测、评分与真实后果', fontsize=17)
    fig.supxlabel('仅开发集定点诊断｜原权重与原评分规则｜总预算400步｜另有demo105的有效干预参照，详见报告', fontsize=10)
    for suffix in ('png','pdf'):
        output = audit/f'overview.{suffix}'
        if output.exists():
            raise FileExistsError(output)
        fig.savefig(output, dpi=170)
    plt.close(fig)
    print(json.dumps(metrics))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, default=Path(__file__).resolve().parent)
    main(parser.parse_args().run_dir.resolve())
