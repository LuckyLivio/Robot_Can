"""Compare frozen-head calibration, continuation control and original dev runs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from common import ROOT
from calibrate_score_head import model_from_checkpoint, write_json
from world_model import score, target_score


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save_csv(path, rows):
    with path.open('x', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def gate(scores):
    chosen = int(np.argmax(scores))
    return 2 if chosen != 2 and float(scores[chosen]-scores[2]) < .02 else chosen


def main(args):
    directory = ROOT/'reproduction'/args.tag
    output = directory/'analysis'
    output.mkdir(exist_ok=False)
    training = read(directory/'training_complete.json')
    protocol = read(directory/'protocol.json')
    if training['status'] != 'complete':
        raise ValueError('Training did not complete')
    torch.set_num_threads(2)
    base_model = protocol['args']['base_model']
    names = {'original': base_model, **{arm: entry['model'] for arm, entry in training['arms'].items()}}
    checkpoints = {arm: torch.load(ROOT/'models'/name/'model.pt', map_location='cpu', weights_only=True)
                   for arm, name in names.items()}
    models = {arm: model_from_checkpoint(ck, 'cpu') for arm, ck in checkpoints.items()}
    original_state = checkpoints['original']['state_dict']
    weight_checks = {}
    for arm in ('control', 'calibrated'):
        changed = [name for name, value in checkpoints[arm]['state_dict'].items()
                   if not torch.equal(value, original_state[name])]
        if not changed or any(not name.startswith('labels.') for name in changed):
            raise RuntimeError(f'Unexpected changed tensors: {arm}, {changed}')
        logs = read(ROOT/'models'/names[arm]/'log.json')
        best = min(logs, key=lambda row: row['dev']['predicted']['rank']['mean_regret'])
        if checkpoints[arm]['selected_step'] != best['step']:
            raise RuntimeError('Checkpoint choice does not follow the frozen rule')
        weight_checks[arm] = {'changed_tensors': changed, 'selected_step_verified': best['step']}
    for filename, expected in training['source_sha256'].items():
        if hashlib.sha256((ROOT/filename).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Source changed after calibration protocol: {filename}')
    # Verify exactly identical predicted states on every existing train/dev branch.
    prediction_checks = {}
    with torch.no_grad():
      for split in ('train', 'dev'):
        with np.load(ROOT/'data'/f"branches_{split}_{protocol['args']['dataset']}.npz") as z:
            x, actions = torch.from_numpy(z['x']), torch.from_numpy(z['a'])
        n, k = actions.shape[:2]
        maximum = 0.
        for start in range(0, n, 32):
            end = min(start+32, n)
            xb = x[start:end, None].expand(-1,k,-1).reshape((end-start)*k,-1)
            ab = actions[start:end].flatten(0,1)
            expected = models['original'](xb,ab)[0]
            for arm in ('control','calibrated'):
                actual = models[arm](xb,ab)[0]
                maximum = max(maximum, float((actual-expected).abs().max()))
                if not torch.equal(actual,expected):
                    raise RuntimeError('State predictions changed under head-only calibration')
        prediction_checks[split] = {'groups': n, 'max_state_difference': maximum}
    result_name = 'delay_wm_dev_d2_shift_fbshift_fbi2_gm0.02_score.json'
    paths = {'original': Path(args.reference_result).resolve(),
             'control': directory/'control'/result_name, 'calibrated': directory/'calibrated'/result_name,
             'k2': ROOT/'models/fixed_20261011_234708_859_full/delay_bc_shift_dev_d2_k2.json'}
    runs = {arm: read(path) for arm,path in paths.items()}
    dev_names = read(ROOT/'data/splits.json')['dev']
    for arm,run in runs.items():
        if run.get('status','complete') != 'complete' or [r['demo'] for r in run['records']] != dev_names:
            raise ValueError('Incomplete or mismatched dev episode set')
        if run['args']['split'] != 'dev' or run['args']['delay'] != 2 or run['args']['noise'] != 0:
            raise ValueError('Incorrect evaluation condition')
        if len(run['records']) != 30 or len(set(r['demo'] for r in run['records'])) != 30:
            raise ValueError('Expected exactly 30 unique dev episodes')
        if arm != 'k2':
            for key in ('policy','policy_checkpoint','steps','delay','horizon','candidates','candidate_mode','fallback','fallback_index','gate_margin','score_only','risk_weight'):
                if run['args'][key] != runs['original']['args'][key]:
                    raise ValueError(f'Evaluation argument changed: {arm}/{key}')
    indexed = {arm: {r['demo']:r for r in run['records']} for arm,run in runs.items()}
    summary = {}
    for arm,run in runs.items():
        records = run['records']
        total_steps = sum(r['steps'] for r in records)
        override_steps = sum(r['steps']-r['selection_counts'].get('2',0) for r in records) if arm!='k2' else 0
        offline = training['original']['dev'] if arm=='original' else training['arms'][arm]['offline_metrics']['dev'] if arm!='k2' else None
        summary[arm] = {'success': sum(r['success'] for r in records), 'episodes': len(records),
                        'success_rate': sum(r['success'] for r in records)/len(records),
                        'failed_demos': [r['demo'] for r in records if not r['success']],
                        'total_steps': total_steps, 'override_fraction_per_executed_step': override_steps/total_steps,
                        'selected_step': checkpoints[arm]['selected_step'] if arm!='k2' else None,
                        'dev_offline': offline}
    pairs = {}
    for other in ('original','control','k2'):
        pairs['calibrated_vs_'+other] = {
            'calibrated_only_success': [n for n in dev_names if indexed['calibrated'][n]['success'] and not indexed[other][n]['success']],
            'reference_only_success': [n for n in dev_names if not indexed['calibrated'][n]['success'] and indexed[other][n]['success']]}
    episode_rows = []
    for name in dev_names:
        entry = {'demo': name}
        for arm in runs:
            entry[arm+'_success'] = indexed[arm][name]['success']
            entry[arm+'_steps'] = indexed[arm][name]['steps']
        episode_rows.append(entry)
    save_csv(output/'episode_comparison.csv', episode_rows)
    # Post-hoc rescoring of already collected dev counterfactuals; never used for training or selection.
    diagnostic = ROOT/'reproduction/candidate_truth_20261012_01/audit'
    previous = read(diagnostic/'results.json')
    diagnostic_rows, diagnostic_summary = [], {arm:[] for arm in models}
    with torch.no_grad():
      for anchor in previous['anchors']:
        name,step = anchor['demo'],anchor['step']
        with np.load(diagnostic/f'{name}_step{step:03d}.npz') as z:
            xb = torch.from_numpy(np.repeat(z['anchor'][None],4,axis=0))
            ab = torch.from_numpy(z['executed_sequences'])
            truth_states = torch.from_numpy(z['true_states'])
            truth_labels = torch.from_numpy(z['true_labels'])
            saved_prediction = z['predicted_states']
        truth_scores = target_score(truth_labels,.5).numpy()
        for arm,model in models.items():
            future,logits = model(xb,ab)
            if not np.array_equal(future.numpy(),saved_prediction):
                raise RuntimeError('Original anchor state prediction is no longer identical')
            predicted = score(logits,.5).numpy()
            real = score(model.labels((truth_states-model.mean)/model.scale),.5).numpy()
            diagnostic_summary[arm].append({'demo':name,'step':step,'selected':gate(predicted),
                                            'true_state_selected':gate(real),
                                            'predicted_score_mae':float(np.abs(predicted-truth_scores).mean()),
                                            'true_state_score_mae':float(np.abs(real-truth_scores).mean())})
            for k in range(4):
                diagnostic_rows.append({'demo':name,'step':step,'arm':arm,'k':k,
                                        'predicted_score':float(predicted[k]),'real_state_head_score':float(real[k]),
                                        'truth_score':float(truth_scores[k]),'selected':gate(predicted)==k})
    save_csv(output/'old_anchor_rescoring.csv',diagnostic_rows)
    diagnostic_aggregate = {
        arm: {'predicted_score_mae': float(np.mean([r['predicted_score_mae'] for r in rows])),
              'true_state_score_mae': float(np.mean([r['true_state_score_mae'] for r in rows])),
              'changed_selections_vs_original': sum(r['selected'] != old['selected'] for r,old in zip(rows,diagnostic_summary['original']))}
        for arm,rows in diagnostic_summary.items()}
    write_json(output/'old_anchor_summary.json',diagnostic_aggregate)
    analysis = {'status':'complete','summary':summary,'paired_comparisons':pairs,
                'weight_checks':weight_checks,'prediction_checks':prediction_checks,
                'old_anchor_rescoring':diagnostic_summary,
                'note':'Old-anchor rescoring is offline and does not imply the new controller visits those same states.',
                'input_sha256':{path.relative_to(ROOT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in paths.values()}}
    write_json(output/'analysis.json',analysis)
    labels = {'original':'校准前模型','control':'只续训评分头（对照）','calibrated':'加入真实状态监督校准','k2':'BC k=2'}
    lines = ['评分头校准开发集对照报告','',
             f"结果：校准前 {summary['original']['success']}/30，对照 {summary['control']['success']}/30，校准后 {summary['calibrated']['success']}/30，BC k=2 {summary['k2']['success']}/30。",
             '本次仅更新评分头3330个参数。其余83991个参数和归一化缓冲区不变，全部160组训练分支及64组开发分支的状态预测逐元素完全一致。',
             '保持原来的候选展开、评分公式、0.02门限、动作执行方式、BC权重和数据划分。没有将上次7个开发诊断点加入训练。','',
             '实验规则：两组都从相同原模型出发，使用相同seed17、相同批次索引、相同3000步预算、Adam lr=0.0003、batch16。',
             '对照只继续原评分头监督；校准组额外加入真实未来状态上的进度BCE+0.5风险BCE，权重1。原预测状态监督与0.2排序损失保留。',
             '按原规则选择预测分数的开发分支排序遗憾最小的检查点；相同时选最早。闭环成功率和旧诊断点不参与选点。',
             f"实际选中：对照第{summary['control']['selected_step']}步，校准第{summary['calibrated']['selected_step']}步（两组训练预算相同，选中的步数可以不同）。",'',
             '开发分支离线指标（64组/8条父轨迹，不是64个独立任务）：']
    for arm in ('original','control','calibrated'):
        offline = summary[arm]['dev_offline']
        lines.append(f"{labels[arm]}：预测状态评分MAE={offline['predicted']['score_mae']:.6f}；真实状态评分MAE={offline['real']['score_mae']:.6f}；真实状态风险Brier={offline['real']['risk_brier']:.6f}；部署路径排序遗憾={offline['predicted']['rank']['mean_regret']:.8f}。")
    lines += ['','30个相同开发起点的配对变化：']
    for other in ('original','control','k2'):
        pair=pairs['calibrated_vs_'+other]
        lines.append(f"校准模型 vs {labels[other]}：校准独胜={pair['calibrated_only_success']}；参照独胜={pair['reference_only_success']}。")
    lines += ['','重点回合：']
    for name in ('demo_105','demo_124','demo_97','demo_179'):
        lines.append(name+'：'+'；'.join(f"{labels[arm]}={'成功' if indexed[arm][name]['success'] else '失败'}@{indexed[arm][name]['steps']}" for arm in runs))
    lines += ['','解释与边界：',
              '上次固定的7个诊断起点（28候选）重评分：']
    for arm,values in diagnostic_aggregate.items():
        lines.append(f"{labels[arm]}：预测链评分MAE={values['predicted_score_mae']:.6f}，真实状态评分MAE={values['true_state_score_mae']:.6f}，相对原模型改变候选选择的起点数={values['changed_selections_vs_original']}/7。")
    lines += ['这组针对失败状态的局部指标与64组开发分支指标不同，应同时报告；不能只用整体平均下降宣称关键失败已修复。',
              '离线评分误差下降与闭环成功率应分别判断。真实状态评分头的改善，不会自动纠正冻结的状态预测偏差或重复动作规划近似。',
              '这是一个训练种子、一个固定底座、一个开发集上的对照结果；单回合的变化不能证明稳定或泛化提升。',
              '旧诊断点重评分仅比较相同历史状态上的分数；新控制器轨迹会变化，不能把离线选项变化直接当成整条任务被救回。',
              '未改动候选展开或执行方式；未运行封存测试；没有将新权重替换为默认模型。原权重和全部历史结果保留。',
              '本轮结果只支持本轮配置的结论，不根据开发闭环结果追选其他训练检查点。','',
              '文件：episode_comparison.csv 为全部30回合；old_anchor_rescoring.csv 为旧28个候选的前后重评分；analysis.json 为原始分析。']
    with (output/'diagnosis.txt').open('x',encoding='utf-8') as file:
        file.write('\n'.join(lines)+'\n')
    plot(output,summary,indexed,dev_names,labels)
    print(json.dumps({'summary':summary,'pairs':pairs,'checks':prediction_checks}),flush=True)


def plot(output,summary,indexed,dev_names,labels):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    plt.rcParams['font.family']=['Microsoft YaHei','DejaVu Sans']
    plt.rcParams['axes.unicode_minus']=False
    fig=plt.figure(figsize=(13,8),layout='constrained')
    grid=fig.add_gridspec(2,2,height_ratios=[1.15,1])
    ax=fig.add_subplot(grid[0,0]); bx=fig.add_subplot(grid[0,1]); cx=fig.add_subplot(grid[1,:])
    arms=list(summary)
    colors=['#8c9bad','#dfaa59','#429d87','#537fb4']
    bars=ax.bar(range(4),[summary[a]['success'] for a in arms],color=colors)
    ax.set(ylim=(0,33),xticks=range(4),xticklabels=['校准前','续训对照','真实状态校准','BC k=2'],ylabel='成功回合数',title='完整开发集：相同30个起点')
    for bar,arm in zip(bars,arms):
        ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.4,f"{summary[arm]['success']}/30",ha='center',fontsize=12)
    ax.grid(axis='y',alpha=.2)
    for offset,kind,label,color in [(-.18,'predicted','输入预测状态','#597fa9'),(.18,'real','输入真实状态','#399b82')]:
        values=[summary[a]['dev_offline'][kind]['score_mae'] for a in arms[:3]]
        drawn=bx.bar(np.arange(3)+offset,values,.34,label=label,color=color)
        for bar,value in zip(drawn,values):bx.text(bar.get_x()+bar.get_width()/2,value+.002,f'{value:.4f}',ha='center',fontsize=9)
    bx.set(ylim=(0,.15),xticks=range(3),xticklabels=['校准前','续训对照','真实状态校准'],ylabel='评分绝对误差（越低越好）',title='同一批64组开发分支的评分误差')
    bx.legend(fontsize=9);bx.grid(axis='y',alpha=.2)
    values=np.asarray([[int(indexed[a][name]['success']) for name in dev_names] for a in arms])
    cx.imshow(values,cmap=ListedColormap(['#efc4bb','#b1d9ca']),vmin=0,vmax=1,aspect='auto')
    for i,arm in enumerate(arms):
        for j,name in enumerate(dev_names):cx.text(j,i,'✓' if indexed[arm][name]['success'] else '×',ha='center',va='center',fontsize=11)
    cx.set(xticks=range(30),xticklabels=[n.split('_')[1] for n in dev_names],yticks=range(4),yticklabels=[labels[a] for a in arms],xlabel='开发回合编号（demo ID）',title='逐回合比较：绿色成功，红色失败')
    cx.tick_params(axis='x',labelsize=8)
    fig.suptitle('仅校准评分头：状态预测、候选与执行逻辑保持不变',fontsize=16)
    fig.supxlabel('单种子开发诊断｜检查点按预先固定的离线规则选择｜未运行封存测试',fontsize=10)
    fig.savefig(output/'head_calibration.png',dpi=170)
    fig.savefig(output/'head_calibration.pdf')
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag',required=True)
    parser.add_argument('--reference-result',default=str(ROOT/'reproduction/queuepair_20261012_01/real/delay_wm_dev_d2_shift_fbshift_fbi2_gm0.02_score.json'))
    main(parser.parse_args())
