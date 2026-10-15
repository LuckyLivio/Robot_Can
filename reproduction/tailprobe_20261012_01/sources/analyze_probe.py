"""Compare frozen full-dev rollouts and audit previously fixed dev anchors."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
RUN=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from evaluate_candidate_rollout import imagine,load_frozen,write_json
from world_model import target_score

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))
def csv_write(path,rows):
    with path.open('x',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

protocol=read(RUN/'protocol.json')
for source,digest in protocol['source_sha256'].items():
    assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest()==digest,source
old=ROOT/'reproduction/headcal_20261012_01/calibrated/delay_wm_dev_d2_shift_fbshift_fbi2_gm0.02_score.json'
baseline=ROOT/'models/fixed_20261011_234708_859_full/delay_bc_shift_dev_d2_k2.json'
files={'repeat':RUN/'repeat/results.json','bc_tail':RUN/'bc_tail/results.json','bc_k2':baseline,'previous_calibrated':old}
payloads={key:read(path) for key,path in files.items()}
records={key:{r['demo']:r for r in payload['records']} for key,payload in payloads.items()}
names=protocol['parents']
for key,rows in records.items():
    assert list(rows)==names and len(rows)==30,key
    assert payloads[key].get('status','complete')=='complete',key
fields=('success','steps','peak_stage_reward','ever_grasped','selection_counts')
for name in names:
    for field in fields:
        assert records['repeat'][name][field]==records['previous_calibrated'][name][field],(name,field)
trace_fields=('state_before','state_after','queue_before','base_chunk','candidate_actions','submitted_action','executed_action',
              'model_sequences','predicted_states','predicted_progress','predicted_risk','learned_scores',
              'selected','raw_selected','raw_advantage','selected_advantage','stages_before','stages_after','success_after')
original=read(RUN/'original_reference/delay_wm_dev_d2_shift_fbshift_fbi2_gm0.02_score.json')
assert original['status']=='complete'
integration={'full_dev_previous_results_exact':True,'traces':{},'planning_checks':read(RUN/'planning_verification.json')['count']}
for name in protocol['trace_parents']:
    original_rows=[json.loads(line) for line in (RUN/'original_reference'/original['trace_files'][name]).read_text().splitlines()]
    new_rows=[json.loads(line) for line in (RUN/'repeat/traces'/f'{name}.jsonl').read_text().splitlines()]
    assert len(original_rows)==len(new_rows)
    for a,b in zip(original_rows,new_rows):
        for field in trace_fields:
            assert a[field]==b[field],(name,a['step'],field)
    integration['traces'][name]={'steps':len(new_rows),'compared_fields':len(trace_fields),'max_absolute_error':0.}

out=RUN/'analysis';out.mkdir(exist_ok=False)
rows=[]
for name in names:
    row={'demo':name}
    for key in ('bc_k2','repeat','bc_tail'):
        for field in ('success','steps','ever_grasped','peak_stage_reward'):
            row[f'{key}_{field}']=records[key][name][field]
    rows.append(row)
csv_write(out/'episode_comparison.csv',rows)
summaries={}
for key in ('bc_k2','repeat','bc_tail'):
    values=list(records[key].values());total_steps=sum(r['steps'] for r in values)
    summaries[key]={'success':sum(r['success'] for r in values),'episodes':30,
                    'mean_steps_failures_capped_400':float(np.mean([r['steps'] for r in values])),
                    'total_steps':total_steps}
    if key!='bc_k2':
        summaries[key]['pooled_override_fraction']=sum(r['steps']*r['fraction_override'] for r in values)/total_steps
        summaries[key]['step_weighted_mean_decision_ms']=sum(r['steps']*r['mean_decision_ms'] for r in values)/total_steps
paired={}
for ref in ('repeat','bc_k2'):
    wins=[n for n in names if records['bc_tail'][n]['success'] and not records[ref][n]['success']]
    losses=[n for n in names if not records['bc_tail'][n]['success'] and records[ref][n]['success']]
    paired[ref]={'bc_tail_only_success':wins,'reference_only_success':losses,
                 'success_difference':len(wins)-len(losses),'paired_n':len(names)}

# Post-result explanation only: these seven anchors were fixed in an earlier
# diagnostic. They are not training samples or hyperparameter-selection data.
torch.set_num_threads(2);model,policy,_=load_frozen()
anchor_rows=[];anchor_summary=[]
with torch.no_grad():
    for path in sorted((ROOT/'reproduction/candidate_truth_20261012_01/audit').glob('*.npz')):
        data=np.load(path);meta=read(path.with_suffix('.json'))
        plans={mode:imagine(model,policy,data['anchor'],data['queue'],data['commands'],mode) for mode in ('repeat','bc_tail')}
        truth=[];actual_actions=[];actual_submissions=[];labels=[]
        for k in range(4):
            # There is no task success within these first 8 steps. Thus the
            # original label definition is exactly max(stage), plus lost grasp.
            assert len(data[f'k{k}_once_bc_states'])>8
            stages=data[f'k{k}_once_bc_stages'][:8]
            labels.append(np.stack([stages.max(1),np.asarray((meta['initial_stages'][1]>.3)&(stages[:,1]<.3),float)],-1))
            truth.append(data[f'k{k}_once_bc_states'][:8]);actual_actions.append(data[f'k{k}_once_bc_actions'][:8])
            actual_submissions.append(data[f'k{k}_once_bc_submitted'][:8])
        truth=np.asarray(truth);actual_actions=np.asarray(actual_actions);actual_submissions=np.asarray(actual_submissions)
        true_score=target_score(torch.as_tensor(np.asarray(labels),dtype=torch.float32),.5).numpy()
        exact_actions_future,_=model(torch.from_numpy(np.repeat(data['anchor'][None],4,0)),torch.from_numpy(actual_actions))
        for k in range(4):
            r={'anchor':path.stem,'k':k,'repeat_selected':plans['repeat']['selected']==k,'bc_tail_selected':plans['bc_tail']['selected']==k,
               'repeat_predicted_score':float(plans['repeat']['scores'][k]),'bc_tail_predicted_score':float(plans['bc_tail']['scores'][k]),
               'real_once_bc_h8_score':float(true_score[k]),'real_once_bc_success':meta['candidates'][k]['continuations']['once_bc']['success'],
               'real_once_bc_end_step':meta['candidates'][k]['continuations']['once_bc']['end_step'],
               'bc_tail_submission_mae':float(np.abs(plans['bc_tail']['submitted'][k].numpy()[1:]-actual_submissions[k,1:]).mean()),
               'bc_tail_eef_error_mm':float(np.linalg.norm(plans['bc_tail']['future'][k,:,:3].numpy()-truth[k,:,:3],axis=-1).mean()*1000),
               'bc_tail_object_error_mm':float(np.linalg.norm(plans['bc_tail']['future'][k,:,16:19].numpy()-truth[k,:,16:19],axis=-1).mean()*1000),
               'actual_action_model_eef_error_mm':float(np.linalg.norm(exact_actions_future[k,:,:3].numpy()-truth[k,:,:3],axis=-1).mean()*1000),
               'actual_action_model_object_error_mm':float(np.linalg.norm(exact_actions_future[k,:,16:19].numpy()-truth[k,:,16:19],axis=-1).mean()*1000)}
            anchor_rows.append(r)
        anchor_summary.append({'anchor':path.stem,'repeat_selected':plans['repeat']['selected'],'bc_tail_selected':plans['bc_tail']['selected'],
                               'real_once_bc_success_by_k':[c['continuations']['once_bc']['success'] for c in meta['candidates']],
                               'real_once_bc_h8_scores':true_score.tolist()})
csv_write(out/'old_anchor_rollouts.csv',anchor_rows)
anchor_metrics={'changed_selections':sum(r['repeat_selected']!=r['bc_tail_selected'] for r in anchor_summary),'anchor_count':len(anchor_summary),
                'bc_tail_score_mae_vs_real_once_bc_h8':float(np.mean([abs(r['bc_tail_predicted_score']-r['real_once_bc_h8_score']) for r in anchor_rows])),
                'anchors':anchor_summary,
                'note':'Old fixed development anchors. BC-tail error includes mismatched imagined actions; actual-action model error conditions on recorded real executed actions. Neither is an independent additive decomposition.'}
for field in ('bc_tail_submission_mae','bc_tail_eef_error_mm','bc_tail_object_error_mm','actual_action_model_eef_error_mm','actual_action_model_object_error_mm'):
    anchor_metrics[field]=float(np.mean([r[field] for r in anchor_rows]))
result={'summaries':summaries,'paired':paired,'integration':integration,'old_anchor_diagnostic':anchor_metrics,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files.values()},
        'decision':'continue_to_separately_registered_aligned_data_probe' if paired['repeat']['success_difference']>0 else 'stop_frozen_BC_tail_branch_no_dev_success_gain',
        'limitations':protocol['limitations']}
write_json(out/'analysis.json',result)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,3,figsize=(14,4.6),layout='constrained')
keys=('bc_k2','repeat','bc_tail');titles=['Fixed BC k=2','WM repeat','WM BC tail'];colors=['#6f8194','#408bad','#d28148']
values=[summaries[k]['success'] for k in keys]
axes[0].bar(titles,values,color=colors)
for i,v in enumerate(values):axes[0].text(i,v+.4,f'{v}/30',ha='center')
axes[0].set(ylim=(0,32),ylabel='Successful episodes',title='Same 30 development starts')
image=np.array([[int(records[k][n]['success']) for n in names] for k in keys])
axes[1].imshow(image,cmap='RdYlGn',vmin=0,vmax=1,aspect='auto')
axes[1].set(yticks=range(3),yticklabels=titles,xticks=[0,4,9,14,19,24,29],xticklabels=[1,5,10,15,20,25,30],
            xlabel='Development episode index',title='Paired outcomes: green=success')
latencies=[summaries[k]['step_weighted_mean_decision_ms'] for k in ('repeat','bc_tail')]
axes[2].bar(['WM repeat','WM BC tail'],latencies,color=colors[1:])
for i,v in enumerate(latencies):axes[2].text(i,v+.04,f'{v:.2f} ms',ha='center')
axes[2].set(ylim=(0,max(latencies)*1.2),ylabel='Planner time per decision (ms)',title='CPU / 2 threads / sequential runs')
fig.suptitle('Frozen calibrated WM | D=2, H=8, margin=0.02 | development probe only')
fig.savefig(out/'rollout_comparison.png',dpi=180);fig.savefig(out/'rollout_comparison.pdf');plt.close(fig)

lines=['固定模型候选展开对照：开发集报告','',
       '只改变预测中的后续动作生成：repeat重复当前候选；bc_tail只提交一次候选，之后根据预测状态计算BC k=2动作。',
       '两种方式在真实环境中都只提交一次动作，然后每次观测重新规划。模型、评分头、门限、BC、初始状态和预算完全相同。',
       '本轮没有训练，没有打开封存测试，也没有替换默认模型。','',
       f"时序检查通过 {integration['planning_checks']} 项；旧30回合的成功、步数、阶段奖励、抓取和选择计数全部精确复现。",
       f"原评估器与新repeat评估器在4条完整轨迹共{sum(r['steps'] for r in integration['traces'].values())}步、每步{len(trace_fields)}项字段完全一致。",'']
for key in keys:
    s=summaries[key];lines.append(f"{key}: {s['success']}/30；失败记400步的平均步数 {s['mean_steps_failures_capped_400']:.2f}。")
    if key!='bc_k2':lines.append(f"  全步骤加权覆盖基线比例 {s['pooled_override_fraction']:.2%}；规划耗时 {s['step_weighted_mean_decision_ms']:.3f} ms。")
lines.extend(['','配对比较：'])
for ref,pair in paired.items():lines.append(f"bc_tail vs {ref}：bc_tail独胜={pair['bc_tail_only_success']}；参照独胜={pair['reference_only_success']}；净变化={pair['success_difference']}回合。")
lines.extend(['','重点回合：'])
for n in protocol['trace_parents']:
    lines.append(n+'：'+'；'.join(f"{k}={'成功' if records[k][n]['success'] else '失败'}@{records[k][n]['steps']}" for k in keys))
lines.extend(['','旧7个固定开发诊断起点（不用于训练或选参）：',
              f"候选选择变化 {anchor_metrics['changed_selections']}/7；BC-tail分数对真实once-BC短期分数MAE={anchor_metrics['bc_tail_score_mae_vs_real_once_bc_h8']:.6f}。",
              f"BC-tail未来动作MAE={anchor_metrics['bc_tail_submission_mae']:.6f}；预测轨迹末端执行器/物体平均误差={anchor_metrics['bc_tail_eef_error_mm']:.2f}/{anchor_metrics['bc_tail_object_error_mm']:.2f} mm。",
              f"将实际执行动作交给WM时，末端执行器/物体平均误差={anchor_metrics['actual_action_model_eef_error_mm']:.2f}/{anchor_metrics['actual_action_model_object_error_mm']:.2f} mm。",
              'BC-tail误差包含策略在错误预测状态上产生不同后续动作的影响；不能把它全称为动力学误差。上述两个误差不构成独立可加的因果分解。'])
for r in anchor_summary:lines.append(f"  {r['anchor']}：repeat k={r['repeat_selected']} -> bc_tail k={r['bc_tail_selected']}；真实一次动作后接BC的成功=[{', '.join(map(str,r['real_once_bc_success_by_k']))}]。")
lines.extend(['','结论与边界：',result['decision'],
              '模型在重复动作数据上训练；本实验只回答冻结该模型时换展开方式是否有效，不能证明用匹配数据重新训练也无效。',
              '即使BC-tail近似更接近一次提交的语义，未来BC控制仍不等于实际未来WM重规划。',
              '这是一个模型种子和已经多次查看的开发集，不能据此宣称稳定泛化提升；成功回合或平均步数也不能替代完整成功率。',
              '固定BC k=2必须继续保留为强基线。旧封存测试已参与历史分析，后续需要另外预先锁定确认实验。',
              '耗时仅覆盖规划阶段，含候选推演额外BC调用，不含两组共有的初始BC推理、环境步进和JSON日志；不是端到端实时性能承诺。'])
(out/'diagnosis.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'summaries':summaries,'paired':paired,'integration':integration,'decision':result['decision'],'anchors':anchor_metrics},ensure_ascii=False))
