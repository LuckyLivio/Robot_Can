"""Analyze every registered confirmation result; never select or modify a model."""
import csv,hashlib,json,sys,datetime
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from prepare_states import write

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save_csv(path,rows):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    design=read(RUN/'design.json');lock=read(RUN/'lock.json');jobs=read(RUN/'jobs.json')
    for relative,sha in lock['input_sha256'].items():assert digest(ROOT/relative)==sha,relative
    assert read(RUN/'validation.json')['passed'] and read(RUN/'state_validation.json')['passed']
    out=RUN/'analysis'
    if out.exists() and any(out.iterdir()):raise FileExistsError(out)
    out.mkdir(exist_ok=True)
    names=design['state_names'];seeds=design['seeds'];conditions=list(design['conditions']);N=len(names)
    results={};records=[];per_seed=[];source_hashes={};traces={};noise_checks=0
    with h5py.File(RUN/'starts.hdf5','r') as states:
        for job in jobs:
            done=read(RUN/'completed'/f"{job['id']}.json")
            assert done['status']=='complete'
            for relative,sha in done['outputs'].items():assert digest(ROOT/relative)==sha,relative
            p=ROOT/job['outputs'][0];r=read(p);a=r['args']
            assert r['status']=='complete' and len(r['records'])==N
            assert r['resolved_demos']==names and [x['demo'] for x in r['records']]==names
            assert r['provenance']['confirmation_lock_sha256']==digest(RUN/'lock.json')
            assert r['provenance']['execution_started_at']>lock['locked_at']
            for k,v in {'split':'confirmation','steps':400,'delay':2,'horizon':8,'candidates':4,
                        'fallback_index':2,'gate_margin':.02,'risk_weight':.5,'score_only':True,
                        'candidate_mode':'shift','noise':job['noise']}.items():assert a[k]==v,(job['id'],k)
            method,seed,condition=job['method'],job['seed'],job['condition']
            expected_model=f'multiseed_20261012_01_{method}_s{seed}' if method!='bc_k2' else 'multiseed_20261012_01_full_s17'
            assert a['model']==expected_model
            assert a['method']==('bc_shift' if method=='bc_k2' else 'wm')
            assert a['shift_index']==2
            key=(method,seed,condition);assert key not in results;results[key]=r
            source_hashes[job['outputs'][0]]=digest(p)
            steps=sum(x['steps'] for x in r['records'])
            per_seed.append({'method':method,'seed':seed,'condition':condition,'success':sum(x['success'] for x in r['records']),
                'episodes':N,'success_percent':100*np.mean([x['success'] for x in r['records']]),
                'mean_steps_failures_capped_400':np.mean([x['steps'] for x in r['records']]),
                'pooled_override_percent':100*sum(x['steps']*x.get('fraction_override',0) for x in r['records'])/steps,
                'decision_ms_parallel_execution_not_latency_benchmark':sum(x['steps']*x['mean_decision_ms'] for x in r['records'])/steps,
                'source':job['outputs'][0]})
            for x in r['records']:
                assert 1<=x['steps']<=400 and sum(x['selection_counts'].values())==x['steps']
                assert x['success'] or x['steps']==400
                if method=='bc_k2':assert x['selection_counts']=={'2':x['steps']}
                records.append({'method':method,'seed':seed,'condition':condition,
                    **{k:x[k] for k in ('demo','success','steps','ever_grasped','peak_stage_reward')},
                    'fraction_override':x.get('fraction_override'),'source':job['outputs'][0]})
            # First two starts were selected for tracing before confirmation.
            for name,relative in r['trace_files'].items():
                rows=[json.loads(line) for line in (p.parent/relative).read_text().splitlines()]
                assert len(rows)==next(x['steps'] for x in r['records'] if x['demo']==name)
                initial=np.asarray(rows[0]['state_before']);traces.setdefault(name,[]).append(initial)
                assert np.max(np.abs(initial-states['data'][name]['initial_observation'][:]))<1e-5
                previous_queue=[np.zeros(7,np.float32) for _ in range(2)]
                noise=states['data'][name]['execution_noise'][:]
                for i,row in enumerate(rows):
                    assert np.array_equal(np.asarray(row['queue_before'],np.float32),np.asarray(previous_queue))
                    previous_queue.append(np.asarray(row['submitted_action'],np.float32))
                    executed=previous_queue.pop(0)
                    assert np.array_equal(executed,np.asarray(row['executed_action_before_noise'],np.float32))
                    if job['noise']:executed[:3]+=noise[i]
                    assert np.array_equal(np.clip(executed,-1,1),np.asarray(row['executed_action'],np.float32))
                    noise_checks+=1
    assert len(results)==14 and len(records)==840
    for name,values in traces.items():
        assert len(values)==14 and all(np.array_equal(values[0],v) for v in values)

    def matrix(method,condition):
        if method=='bc_k2':
            y=np.array([x['success'] for x in results[(method,None,condition)]['records']],float)
            return np.repeat(y[None],3,axis=0)
        return np.array([[x['success'] for x in results[(method,s,condition)]['records']] for s in seeds],float)
    rng=np.random.default_rng(2026101203);B=20000
    si=rng.integers(0,3,(B,3));ii=rng.integers(0,N,(B,N))
    def ci(values):
        sample=values[si[:,:,None],ii[:,None,:]].mean((1,2))
        return np.quantile(sample,[.025,.975])*100
    def values(method,condition):
        return np.mean([matrix(method,c) for c in conditions],axis=0) if condition=='joint_equal_weight' else matrix(method,condition)
    methods=['bc_k2','full','plain'];summary=[];paired=[];paired_seed=[]
    for condition in [*conditions,'joint_equal_weight']:
        for method in methods:
            y=values(method,condition);lo,hi=ci(y)
            counts=[int(row.sum()) for row in y] if condition!='joint_equal_weight' else [None]*3
            summary.append({'method':method,'condition':condition,'independent_initial_states':N,
                'world_model_training_seeds':0 if method=='bc_k2' else 3,
                'success_s17_or_fixed_bc':counts[0],'success_s23':counts[1] if method!='bc_k2' else None,
                'success_s41':counts[2] if method!='bc_k2' else None,'mean_success_percent':100*y.mean(),
                'seed_sd_pp':100*y.mean(1).std(ddof=1) if method!='bc_k2' else None,
                'paired_crossed_bootstrap_low_percent':lo,'paired_crossed_bootstrap_high_percent':hi})
        for left,right in [('full','bc_k2'),('plain','bc_k2'),('full','plain')]:
            a,b=values(left,condition),values(right,condition);d=a-b;lo,hi=ci(d)
            paired.append({'left':left,'right':right,'condition':condition,'mean_difference_pp':100*d.mean(),
                'paired_crossed_bootstrap_low_pp':lo,'paired_crossed_bootstrap_high_pp':hi,
                'seed17_difference_pp':100*d[0].mean(),'seed23_difference_pp':100*d[1].mean(),'seed41_difference_pp':100*d[2].mean()})
            if condition!='joint_equal_weight':
                for i,seed in enumerate(seeds):
                    wins=[n for j,n in enumerate(names) if d[i,j]>0];losses=[n for j,n in enumerate(names) if d[i,j]<0]
                    paired_seed.append({'left':left,'right':right,'condition':condition,'seed':seed,
                        'left_only_success':len(wins),'right_only_success':len(losses),
                        'difference_pp':100*d[i].mean(),'left_only_ids':';'.join(wins),'right_only_ids':';'.join(losses)})
    save_csv(out/'episodes.csv',records);save_csv(out/'per_seed.csv',per_seed)
    save_csv(out/'summary.csv',summary);save_csv(out/'paired_comparisons.csv',paired)
    save_csv(out/'paired_per_seed.csv',paired_seed)
    # Sample composition is reported descriptively, not used for filtering.
    with h5py.File(ROOT/'data/can_ph_lowdim_v15.hdf5','r') as f:
        old=np.stack([d['states'][0] for d in f['data'].values()])
    with h5py.File(RUN/'starts.hdf5','r') as f:
        new=np.stack([f['data'][n]['states'][0] for n in names])
    distribution={'old_n':len(old),'new_n':len(new),'old_can_xy_min':old[:,31:33].min(0).tolist(),
        'old_can_xy_max':old[:,31:33].max(0).tolist(),'new_can_xy_min':new[:,31:33].min(0).tolist(),
        'new_can_xy_max':new[:,31:33].max(0).tolist(),
        'note':'Flat-state positions31:34 are the can free-joint position in the locked model. Summary only; no data filtered.'}
    write(out/'initial_distribution.json',distribution)
    validation={'passed':True,'complete_jobs':14,'episode_records':840,'independent_initial_states':N,
        'original_inputs_still_match_lock':True,'execution_started_after_lock':True,
        'traced_starts_identical_across_all14_jobs':True,'exact_queue_and_paired_noise_checks_steps':noise_checks,
        'all_registered_rows_retained':True}
    write(out/'result_validation.json',validation)
    write(out/'analysis.json',{'analyzed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'summary':summary,'paired':paired,'source_sha256':source_hashes,'bootstrap_replicates':B,
        'bootstrap_seed':2026101203,'validation':validation})
    # Publication-oriented, exportable figures; plotted directly from JSON-derived values.
    labels={'bc_k2':'BC k=2','full':'Full','plain':'Plain (no rank)'}
    colors={'bc_k2':'#53687E','full':'#247BA0','plain':'#D68A35'}
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    fig,axs=plt.subplots(1,2,figsize=(11.6,5.1),sharey=True)
    for ax,condition in zip(axs,conditions):
        for i,method in enumerate(methods):
            row=next(r for r in summary if r['method']==method and r['condition']==condition)
            mean=row['mean_success_percent'];lo=row['paired_crossed_bootstrap_low_percent'];hi=row['paired_crossed_bootstrap_high_percent']
            ax.bar(i,mean,color=colors[method],alpha=.8,width=.60)
            ax.errorbar(i,mean,yerr=[[max(0,mean-lo)],[max(0,hi-mean)]],fmt='none',color='black',capsize=5)
            y=matrix(method,condition).mean(1)*100
            if method!='bc_k2':ax.scatter(np.array([i-.13,i,i+.13]),y,c='white',edgecolors='black',s=34,zorder=3)
            counts=[int(v) for v in matrix(method,condition).sum(1)]
            caption=f'{counts[0]}/60' if method=='bc_k2' else '/'.join(map(str,counts))+' of 60'
            ax.text(i,3,f'{mean:.1f}%\n{caption}',ha='center',va='bottom',fontsize=10,color='black')
        ax.set_xticks(range(3),[labels[m] for m in methods]);ax.set_ylim(0,105)
        ax.set_title('Clean execution' if condition=='clean' else 'Execution noise: SD 0.05')
        ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    axs[0].set_ylabel('Success within 400 steps (%)')
    fig.suptitle('Prospectively locked confirmation: 60 fresh initial states',fontsize=15)
    fig.text(.5,.015,'Dots: training seeds 17 / 23 / 41. Whiskers: descriptive paired crossed bootstrap 95% intervals. Fixed BC evaluated once per condition.',ha='center',fontsize=8.7)
    fig.tight_layout(rect=(0,.06,1,.95));fig.savefig(out/'confirmation_success.png',dpi=180);fig.savefig(out/'confirmation_success.pdf');plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5.6));rows=[r for r in paired if r['condition']!='joint_equal_weight']
    for i,row in enumerate(rows):
        d=row['mean_difference_pp'];lo=row['paired_crossed_bootstrap_low_pp'];hi=row['paired_crossed_bootstrap_high_pp']
        ax.errorbar(d,i,xerr=[[d-lo],[hi-d]],fmt='o',color='#247BA0' if row['condition']=='clean' else '#D68A35',capsize=4)
        ax.text(hi+.7,i,f'{d:+.1f} [{lo:+.1f}, {hi:+.1f}]',va='center',fontsize=9)
    ax.axvline(0,color='black',linestyle='--',linewidth=1)
    ax.set_yticks(range(len(rows)),[f"{labels[r['left']]} − {labels[r['right']]} | {'clean' if r['condition']=='clean' else 'noise'}" for r in rows]);ax.invert_yaxis()
    ax.set_xlabel('Paired success-rate difference (percentage points)')
    lo=min(r['paired_crossed_bootstrap_low_pp'] for r in rows);hi=max(r['paired_crossed_bootstrap_high_pp'] for r in rows)
    ax.set_xlim(min(lo-3,-5),max(hi+19,15));ax.grid(axis='x',alpha=.2)
    ax.set_title('Confirmation effects with paired 95% bootstrap intervals')
    fig.text(.5,.015,'60 initial states × 3 matched training seeds; 20,000 crossed resamples. Conditions share the same initial states. Intervals are descriptive.',ha='center',fontsize=8.7)
    fig.tight_layout(rect=(0,.05,1,1));fig.savefig(out/'paired_effects.png',dpi=180);fig.savefig(out/'paired_effects.pdf');plt.close(fig)
    # Compare dev and confirmation descriptively, without pooling them.
    dev=[]
    with (ROOT/'reproduction/multiseed_20261012_01/analysis/summary.csv').open(encoding='utf-8-sig') as f:dev=list(csv.DictReader(f))
    comparisons=[]
    for r in summary:
        if r['condition']=='joint_equal_weight':continue
        d=next(x for x in dev if x['method']==r['method'] and float(x['noise'])==design['conditions'][r['condition']])
        comparisons.append({'method':r['method'],'condition':r['condition'],'dev_initial_states':30,
            'dev_success_percent':float(d['mean_success_percent']),'confirmation_initial_states':60,
            'confirmation_success_percent':r['mean_success_percent'],
            'descriptive_change_pp':r['mean_success_percent']-float(d['mean_success_percent'])})
    save_csv(out/'dev_vs_confirmation.csv',comparisons)
    lines=['独立确认实验报告','',
        '范围：冻结 BC k=2、Full 和 Plain；Full/Plain 各含训练种子17、23、41。没有再训练、校准、调门限或按确认表现选种子。',
        '预登记60个原生随机初始状态，各在干净与执行位置噪声标准差0.05下评估，14组/840条完整回合。独立起点为60个，不是840个独立任务。',
        '状态生成：同一HDF5 env_args、robosuite1.5.1 PickPlaceCan原生位置采样器，机器人关节高斯初始化标准差0.02。没有预热或按结果筛选。',
        '噪声：每起点固定一个400×3序列，所有方法使用相同逐步噪声；干净和加噪也共享起点。每条件仅一个噪声实现，不能推广至所有噪声。',
        '冻结时间(UTC)：'+lock['locked_at'],
        '参数：400步，延迟D=2，H=8，4个候选k=0/1/2/3，回退k=2，门限0.02，风险权重0.5，学习评分，单步执行后重规划。',
        '输入：含物体真实状态的23维仿真低维输入，不是纯视觉，也未验证真机。',
        '', '结果（每种子分母60；BC只运行一个固定权重）：']
    for r in summary:
        if r['condition']=='joint_equal_weight':continue
        counts=str(r['success_s17_or_fixed_bc']) if r['method']=='bc_k2' else f"{r['success_s17_or_fixed_bc']}/{r['success_s23']}/{r['success_s41']}"
        lines.append(f"{r['condition']} | {labels[r['method']]} | 成功数 {counts} | 平均{r['mean_success_percent']:.2f}% | 95%区间[{r['paired_crossed_bootstrap_low_percent']:.2f},{r['paired_crossed_bootstrap_high_percent']:.2f}]%")
    lines+=['','配对差异（百分点，括号内为描述性95%区间）：']
    for r in paired:
        lines.append(f"{r['condition']} | {labels[r['left']]} − {labels[r['right']]}: {r['mean_difference_pp']:+.2f} [{r['paired_crossed_bootstrap_low_pp']:+.2f},{r['paired_crossed_bootstrap_high_pp']:+.2f}]")
    lines+=['','统计规则：20,000次交叉配对bootstrap，同时重采样训练种子轴与初始状态轴，同一状态抽样用于所有模型和条件。固定BC共享，不当作三个独立训练结果。联合结果先对两个预设条件等权平均再重采样。',
        '区间是有限样本的描述性不确定范围，不是等效性检验或所有比较的同时置信区间。只有3个训练种子，种子泛化估计较粗；不得把跨零解释成证明无效。',
        '', '验证：60个原生状态可按种子逐个精确重生成，与原200个初始状态无精确重复；两组另外的QA起点反向40步重放误差为0。',
        '新评估调用的是字节相同的历史评估核心；在旧开发轨迹530步中所有字段（计时除外）完全一致。',
        f'正式结果28份预选轨迹（头两个起点×14组），共{noise_checks}步FIFO与噪声逐值核对，初始观测跨所有控制器完全一致。',
        'XML保存存在微小数值舍入；所有控制器读同一保存XML。新旧环境按名称对齐的已有物体/几何/站点参数差异均不超过1e-6；原生环境额外目标标记禁用碰撞。不能宣称生成分布与人工示范采集经验分布完全等同。',
        '', '本轮不合并旧开发/历史sealed_test结果来增加样本数；它们参与过方法开发。本轮新起点是冻结方法后的确认用途，评估完成后也不能再称为未见数据。',
        '文件索引：design.json登记生成种子与规则；lock.json记录执行前文件哈希；starts.hdf5含XML/状态/完整噪声；evaluations含全部原始JSON和预选逐步轨迹；completed含各输出哈希。',
        'analysis/summary.csv、per_seed.csv、paired_comparisons.csv、paired_per_seed.csv及episodes.csv提供全部统计。图由原始JSON生成，PNG/PDF可用于论文。']
    (out/'report.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'summary':summary,'paired':paired,'validation':validation},indent=2),flush=True)

if __name__=='__main__':main()
