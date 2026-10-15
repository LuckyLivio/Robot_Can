"""Paired multiseed development analysis; no model selection from outcomes."""
import csv
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
import numpy as np
from train_suite import write_json

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def csv_save(path,rows):
    with path.open('x',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

LABELS={'bc_k0':'BC k=0','bc_k1':'BC k=1','bc_k2':'BC k=2','full':'Full','plain':'No rank',
        'direct':'Direct (matched)','prediction_only':'Prediction only','head_control':'Head continuation',
        'calibrated':'Head calibrated','no_risk_score':'Full: no risk term','no_gate':'Full: no gate','horizon4':'Full: H=4'}
CHINESE={'bc_k0':'固定BC k=0','bc_k1':'固定BC k=1','bc_k2':'固定BC k=2','full':'Full',
         'plain':'无排序Plain','direct':'参数匹配Direct','prediction_only':'只预测+物理代价',
         'head_control':'评分头续训对照','calibrated':'评分头校准','no_risk_score':'Full去掉风险评分',
         'no_gate':'Full去掉门限','horizon4':'Full预测时域4'}
ORDER=list(LABELS)
protocol=read(RUN/'protocol.json');jobs=read(RUN/'jobs.json');seeds=protocol['seeds'];names=protocol['demos']
assert read(RUN/'validation.json')['passed'] and read(RUN/'training_verification.json')['passed']
for relative,digest in protocol['source_sha256'].items():assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest,relative
out=RUN/'analysis'
if out.exists() and any(out.iterdir()):raise FileExistsError('Refusing to overwrite populated analysis directory')
out.mkdir(exist_ok=True)
results={};all_rows=[];source_hashes={};seed_rows=[]
for job in jobs:
    done=read(RUN/'completed'/f"{job['id']}.json")
    for relative,digest in done['output_sha256'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest,relative
    if job['phase']!='evaluate':continue
    path=ROOT/job['outputs'][0];payload=read(path);args=payload['args']
    assert payload['status']=='complete' and payload['resolved_demos']==names
    assert [r['demo'] for r in payload['records']]==names and len(payload['records'])==30
    assert args['split']=='dev' and args['model']==job['model'] and args['noise']==job['noise']
    for key in ('horizon','risk_weight','gate_margin'):assert args[key]==job[key]
    for key,expected in [('delay',2),('steps',400),('candidates',4),('fallback_index',2)]:assert args[key]==expected
    key=(job['method'],job['seed'],job['noise']);assert key not in results
    results[key]=payload
    source_hashes[job['outputs'][0]]=hashlib.sha256(path.read_bytes()).hexdigest()
    records=payload['records'];steps=sum(r['steps'] for r in records)
    overrides=sum(r['steps']*r.get('fraction_override',0.) for r in records)
    seed_rows.append({'method':job['method'],'seed':job['seed'],'noise':job['noise'],'success':sum(r['success'] for r in records),
                      'episodes':30,'mean_steps_failures_capped_400':sum(r['steps'] for r in records)/30,
                      'pooled_override_fraction':overrides/steps if job['seed'] is not None else None,
                      'parallel_run_mean_decision_ms':sum(r['steps']*r['mean_decision_ms'] for r in records)/steps,
                      'source':job['outputs'][0]})
    for record in records:
        assert 1<=record['steps']<=400 and sum(record['selection_counts'].values())==record['steps']
        all_rows.append({'method':job['method'],'seed':job['seed'],'noise':job['noise'],
                         **{k:record[k] for k in ('demo','success','steps','ever_grasped','peak_stage_reward')},
                         'fraction_override':record.get('fraction_override'),'source':job['outputs'][0]})
assert len(results)==60 and len(all_rows)==1800

# Deterministic baseline reproduction is checked against an earlier complete
# clean run. It is reused only as a verification target, never for model selection.
old=read(ROOT/'models/fixed_20261011_234708_859_full/delay_bc_shift_dev_d2_k2.json')
for a,b in zip(results[('bc_k2',None,0.)]['records'],old['records']):
    for key in ('demo','success','steps','peak_stage_reward','ever_grasped'):assert a[key]==b[key],key
    # Historical baseline JSON predates selection-count logging. Verify the
    # current fixed-shift invariant independently instead of inventing old data.
    assert a['selection_counts']=={'2':a['steps']}

def matrix(method,noise):
    if method.startswith('bc_'):
        values=np.asarray([r['success'] for r in results[(method,None,noise)]['records']],float)
        return np.repeat(values[None],3,axis=0)
    return np.asarray([[r['success'] for r in results[(method,seed,noise)]['records']] for seed in seeds],float)

# Identical resampled seed/parent indices for each paired difference preserve
# the pairing. The same parent resample is used across all resampled seeds.
rng=np.random.default_rng(20261012);B=20000
seed_indices=rng.integers(0,3,size=(B,3));parent_indices=rng.integers(0,30,size=(B,30))
def crossed_ci(values):
    draws=values[seed_indices[:,:,None],parent_indices[:,None,:]].mean((1,2))
    return [float(v) for v in np.quantile(draws,[.025,.975])]

summary=[]
usage=[]
for noise in (0.,.05):
    for method in ORDER:
        values=matrix(method,noise);counts=values.sum(1);rates=values.mean(1);lo,hi=crossed_ci(values)
        summary.append({'method':method,'noise':noise,'train_seeds':0 if method.startswith('bc_') else 3,
                        'success_s17':int(counts[0]),'success_s23':None if method.startswith('bc_') else int(counts[1]),
                        'success_s41':None if method.startswith('bc_') else int(counts[2]),'episodes_per_seed':30,
                        'mean_success_percent':float(rates.mean()*100),
                        'seed_sample_sd_pp':None if method.startswith('bc_') else float(rates.std(ddof=1)*100),
                        'crossed_bootstrap_ci_low_percent':lo*100,'crossed_bootstrap_ci_high_percent':hi*100})
        if not method.startswith('bc_'):
            selected_rows=[r for r in seed_rows if r['method']==method and r['noise']==noise]
            only_k2=all(set(r['selection_counts']).issubset({'2'}) for seed in seeds for r in results[(method,seed,noise)]['records'])
            usage.append({'method':method,'noise':noise,'mean_per_seed_override_fraction':float(np.mean([r['pooled_override_fraction'] for r in selected_rows])),
                          'all_three_seeds_selected_k2_at_every_step':only_k2})
comparisons=[('full','bc_k2'),('plain','bc_k2'),('direct','bc_k2'),('prediction_only','bc_k2'),
             ('head_control','bc_k2'),('calibrated','bc_k2'),('full','plain'),('full','direct'),
             ('calibrated','head_control'),('calibrated','full'),('head_control','full'),
             ('full','no_risk_score'),('full','no_gate'),('full','horizon4'),('full','prediction_only')]
paired=[];paired_seed=[]
for noise in (0.,.05):
    for left,right in comparisons:
        a,b=matrix(left,noise),matrix(right,noise);difference=a-b;lo,hi=crossed_ci(difference)
        row={'left':left,'right':right,'noise':noise,'mean_difference_pp':float(difference.mean()*100),
             'crossed_bootstrap_ci_low_pp':lo*100,'crossed_bootstrap_ci_high_pp':hi*100,
             'delta_success_s17':int(difference[0].sum()),'delta_success_s23':int(difference[1].sum()),
             'delta_success_s41':int(difference[2].sum()),'distinct_parents':30,'training_seeds':3}
        paired.append(row)
        for i,seed in enumerate(seeds):
            d=difference[i];draws=d[parent_indices].mean(1);ci=np.quantile(draws,[.025,.975])
            wins=[n for j,n in enumerate(names) if d[j]>0];losses=[n for j,n in enumerate(names) if d[j]<0]
            paired_seed.append({'left':left,'right':right,'noise':noise,'seed':seed,'wins':len(wins),'losses':len(losses),
                                'difference_pp':float(d.mean()*100),'paired_parent_ci_low_pp':float(ci[0]*100),
                                'paired_parent_ci_high_pp':float(ci[1]*100),'left_only_success':';'.join(wins),
                                'right_only_success':';'.join(losses)})

csv_save(out/'episodes.csv',all_rows);csv_save(out/'per_seed.csv',seed_rows);csv_save(out/'summary.csv',summary)
csv_save(out/'paired_comparisons.csv',paired);csv_save(out/'paired_per_seed.csv',paired_seed)
csv_save(out/'controller_usage.csv',usage)
training=read(RUN/'training_verification.json')
model_rows=[];head_rows=[]
for item in training['selected']:
    method,seed=item['method'],item['seed']
    is_head=method in ('control','calibrated')
    metrics=item['dev_metrics']
    base=next(r for r in training['selected'] if r['seed']==seed and r['method']=='full')
    model_rows.append({'method':method,'seed':seed,'parameters':item['parameters'],
                       'effective_trainable_parameters_this_phase':3330 if is_head else (83991 if method=='prediction_only' else item['parameters']),
                       'base_update_budget':3000,'extra_head_update_budget':3000 if is_head else 0,
                       'base_selected_step':base['selected_step'] if is_head else item['selected_step'],
                       'head_selected_step':item['selected_step'] if is_head else None,
                       'selected_dev_regret':None if method=='prediction_only' else metrics['mean_regret'],
                       'selected_dev_normalized_state_mse':base['dev_metrics']['normalized_state_mse'] if is_head else metrics.get('normalized_state_mse'),
                       'minibatch_sha256':item['minibatch_sha256']})
for seed in seeds:
    directory=ROOT/'reproduction'/f'{RUN.name}_head_s{seed}'
    completion=read(directory/'training_complete.json')
    metrics={'base_full':completion['original']['dev']}
    metrics.update({arm:completion['arms'][arm]['offline_metrics']['dev'] for arm in ('control','calibrated')})
    for arm,value in metrics.items():
        head_rows.append({'seed':seed,'arm':arm,'predicted_score_mae':value['predicted']['score_mae'],
                          'true_state_score_mae':value['real']['score_mae'],'true_state_risk_brier':value['real']['risk_brier'],
                          'predicted_score_regret':value['predicted']['rank']['mean_regret']})
csv_save(out/'model_metadata.csv',model_rows);csv_save(out/'head_calibration_offline.csv',head_rows)
data_stats={}
for split in ('train','dev'):
    with np.load(ROOT/'data'/f'branches_{split}_{protocol["dataset"]}.npz') as data:
        progress=data['labels'][...,0];risk=data['labels'][...,1]
        scores=progress[:,:,-1]+.5*progress.mean(-1)-.5*risk.max(-1)
        gap=abs(scores[:,:,None]-scores[:,None,:]);mask=np.triu(np.ones((4,4),bool),1)[None]
        data_stats[split]={'groups':len(scores),'risk_positive_steps':int((risk>0).sum()),'branch_steps':risk.size,
                           'nontrivial_rank_pairs':int(((gap>.025)&mask).sum()),'possible_rank_pairs':len(scores)*6,
                           'groups_with_score_spread_over_0025':int((scores.max(1)-scores.min(1)>.025).sum())}
write_json(out/'data_statistics.json',data_stats)
write_json(out/'analysis.json',{'status':'complete','seed_order':seeds,'dev_parent_order':names,'summary':summary,
          'paired_comparisons':paired,'paired_per_seed':paired_seed,'source_sha256':source_hashes,
          'model_metadata':model_rows,'head_calibration_offline':head_rows,'data_statistics':data_stats,
          'controller_usage':usage,
          'offline_metrics_sha256':hashlib.sha256((RUN/'offline/metrics.json').read_bytes()).hexdigest(),
          'verification':{'completed_evaluation_jobs':len(results),'episode_records':len(all_rows),
                          'old_clean_BC_k2_exact_reproduction':True,'registered_sources_unchanged':True},
          'statistics':{'bootstrap_replicates':B,'bootstrap_seed':20261012,'method':'Crossed resampling of training-seed and parent-episode axes, paired across compared methods.',
                        'warning':'Three training seeds, fixed BC and fixed branch data, repeatedly inspected development parents. No independent-sample claim for 1800 records; no unseen-test/generalization inference. Intervals are descriptive, not multiplicity-adjusted.'}})

# Figures are generated directly from the complete raw-result aggregation.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,2,figsize=(15,8.5),layout='constrained',sharey=True)
colors=['#3366a3','#d28535','#279879']
for ax,noise in zip(axes,(0.,.05)):
    for y,method in enumerate(ORDER):
        s=next(r for r in summary if r['method']==method and r['noise']==noise)
        mean=s['mean_success_percent'];low=s['crossed_bootstrap_ci_low_percent'];high=s['crossed_bootstrap_ci_high_percent']
        ax.plot([low,high],[y,y],color='#9b9b9b',lw=2,zorder=1)
        ax.scatter([mean],[y],marker='D',color='black',s=28,zorder=3)
        if method.startswith('bc_'):
            ax.text(101,y,f"{s['success_s17']}/30",va='center',fontsize=9)
        else:
            for i,seed in enumerate(seeds):
                value=s[f'success_s{seed}']/30*100
                ax.scatter([value],[y+(i-1)*.15],color=colors[i],s=24,zorder=2,label=f'seed {seed}' if y==3 else None)
            ax.text(101,y,' / '.join(str(s[f'success_s{seed}']) for seed in seeds),va='center',fontsize=9)
    ax.set(yticks=range(len(ORDER)),yticklabels=[LABELS[k] for k in ORDER],xlim=(0,121),xticks=range(0,101,20),
           xlabel='Success (%) | right: successes per 30',title='Clean execution' if noise==0 else 'Position noise std=0.05')
    ax.grid(axis='x',alpha=.2);ax.set_ylim(len(ORDER)-.5,-.5)
axes[0].legend(loc='lower left',fontsize=9)
fig.suptitle('Matched three-seed development suite | mean + individual seeds + descriptive 95% intervals\nBC is fixed; right-hand counts follow seed order 17 / 23 / 41',fontsize=13)
fig.savefig(out/'multiseed_success.png',dpi=180);fig.savefig(out/'multiseed_success.pdf');plt.close(fig)

selected_pairs=[('full','bc_k2'),('calibrated','bc_k2'),('calibrated','head_control'),('full','plain'),('full','direct'),
                ('full','no_risk_score'),('full','no_gate'),('full','horizon4')]
fig,axes=plt.subplots(1,2,figsize=(15,6.5),layout='constrained',sharey=True)
for ax,noise in zip(axes,(0.,.05)):
    for y,(left,right) in enumerate(selected_pairs):
        row=next(r for r in paired if (r['left'],r['right'],r['noise'])==(left,right,noise))
        ax.plot([row['crossed_bootstrap_ci_low_pp'],row['crossed_bootstrap_ci_high_pp']],[y,y],color='#9b9b9b',lw=2)
        ax.scatter([row['mean_difference_pp']],[y],color='black',marker='D',s=30,zorder=3)
        for i,seed in enumerate(seeds):ax.scatter([row[f'delta_success_s{seed}']/30*100],[y+(i-1)*.15],color=colors[i],s=24)
    ax.axvline(0,color='gray',ls='--');ax.grid(axis='x',alpha=.2)
    ax.set(yticks=range(len(selected_pairs)),yticklabels=[f'{LABELS[a]} minus {LABELS[b]}' for a,b in selected_pairs],
           xlabel='Paired success difference (percentage points)',title='Clean' if noise==0 else 'Noise 0.05')
    ax.set_ylim(len(selected_pairs)-.5,-.5)
fig.suptitle('Paired effects across all three seeds | positive values favor the first method',fontsize=13)
fig.savefig(out/'paired_effects.png',dpi=180);fig.savefig(out/'paired_effects.pdf');plt.close(fig)

lines=['三个训练种子与公平消融：完整开发集评估','',
       '本报告由全部原始JSON生成，没有挑选最优种子。每种方法按17、23、41固定顺序报告。',
       '完成12个基础模型训练和6个评分头续训/校准模型，共18个选定权重；60组闭环评估，共1800条回合记录。',
       '1800条记录来自相同30个开发父轨迹的重复配对评估，并不是1800个独立任务。没有运行sealed_test或新确认集。','',
       '实验一致性：',
       '所有基础方法使用相同真实队列分支数据：训练20父轨迹/160组、开发8父轨迹/64组。BC权重固定。',
       '三个训练种子全部重新训练。独立批次生成器保证同一种子所有架构看到完全相同的3000x16组索引；因此不能将旧版单种子结果直接视为本轮同一次训练。',
       'Full、Plain和只预测模型初始张量一致，参数87321；Direct参数87364，相差43个（约0.05%），数据和更新数一致，但计算量并非完全相同。',
       '基础训练3000次更新；评分头两组在相同Full底座上各额外3000次更新，主校准比较是校准组对续训对照。不能忽略额外预算直接归因于校准。',
       'model_metadata.csv记录实际可训练参数：评分头阶段为3330。原校准器的config从基础模型继承部分元数据，其中顶层trainable_parameters是基础模型值；实际冻结状态已逐张量验证，应以校准协议和此表为准。',
       '只预测模型按开发状态MSE选择检查点，部署时彻底忽略随机评分头；采用已有物理代价，其门限单位不同，是无标签控制器诊断，不是严格的评分尺度单因素消融。',
       '去风险项、去门限、H=4均使用同一Full权重；去风险项只去掉部署评分中的风险惩罚，并未去掉训练风险监督。','']
for noise in (0.,.05):
    lines.append('无噪声：' if noise==0 else '位置动作噪声标准差0.05：')
    for method in ORDER:
        s=next(r for r in summary if r['method']==method and r['noise']==noise)
        counts=str(s['success_s17']) if method.startswith('bc_') else '/'.join(str(s[f'success_s{seed}']) for seed in seeds)
        sd='' if s['seed_sample_sd_pp'] is None else f"；种子标准差{s['seed_sample_sd_pp']:.2f}个百分点"
        lines.append(f"  {CHINESE[method]}：成功数{counts}（每次30回合）；均值{s['mean_success_percent']:.2f}%{sd}。")
    lines.append('')
lines.extend(['配对效应（左方法减右方法，三种子/父轨迹交叉自助法描述性95%区间）：'])
for row in paired:
    lines.append(f"  noise={row['noise']:g}, {CHINESE[row['left']]} - {CHINESE[row['right']]}：{row['mean_difference_pp']:+.2f}个百分点，区间[{row['crossed_bootstrap_ci_low_pp']:+.2f}, {row['crossed_bootstrap_ci_high_pp']:+.2f}]；各种子成功数差{row['delta_success_s17']:+d}/{row['delta_success_s23']:+d}/{row['delta_success_s41']:+d}。")
lines.extend(['','统计与结论边界：',
              '排序信号有限：训练160组中28组的候选真实评分差超过0.025；开发64组中11组超过该值。约90%的成对比较未进入原排序损失。这是后续数据改进的依据，但不能由此单独断言因果。',
              '所有差异均按相同父轨迹配对；同时重采样训练种子和父轨迹轴。固定BC只评估一次/条件，不将其复制成三个独立基线。',
              '仅3个训练种子，区间估计本身有限；多个消融属于探索性描述，未做多重检验校正，且开发集已经多次用于分析。',
              '结果只能支持这一固定BC、固定分支数据和开发集上的稳定性/消融判断，不等价于未见任务泛化或真机性能。',
              '并行闭环运行的决策耗时保存在per_seed.csv，仅作运行记录，不能作为严格公平的速度基准。',
              '下一步需先冻结论文主张，再在单独预先锁定、未用于开发的新初始状态上确认；历史sealed_test已被查看，不能再次称为完全未见。',
              '项目仍是使用物体真值的23维状态诊断；论文正文、旧文档统一、最终机器人演示及独立确认实验不因本轮完成而自动完成。','',
              '文件：summary.csv为全方法汇总；per_seed.csv为60组原始汇总；episodes.csv为1800条回合；paired_per_seed.csv包含逐种子独胜/独败轨迹。'])
for row in usage:
    if row['all_three_seeds_selected_k2_at_every_step']:
        lines.append(f"注意：{CHINESE[row['method']]}在noise={row['noise']:g}的三个种子中全程选择k=2，当前门限下行为退化为固定BC。其成功率不能证明预测模块本身提高了控制效果。")
(out/'report.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'complete':True,'summary':summary,'paired':paired},ensure_ascii=False),flush=True)
