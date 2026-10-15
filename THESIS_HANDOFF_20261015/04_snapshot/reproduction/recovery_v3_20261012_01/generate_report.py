"""Render a factual engineering report from completed, verified results only."""
import json,datetime
from collections import Counter
from setup_study import ROOT,RUN,write,digest
def read(p):return json.loads((RUN/p).read_text(encoding='utf8'))
def main():
    summary=read('analysis_confirmation/summary.json');diagnosis=read('diagnosis_confirmation.json');valid=read('confirmation_state_validation.json')
    jobs=read('confirmation/jobs.json');rr={j['id']:read(f"confirmation/{j['id']}/result.json")['records'] for j in jobs}
    results={(j['version'],j['method'],j['seed'],j['noise']):rr[j['id']] for j in jobs}
    versions=['disabled','v1','v2','v3'];labels=['无恢复','v1','v2','v3']
    counts=lambda v,m,s,n:sum(r['success'] for r in results[v,m,s,n])
    totals={v:sum(counts(v,m,s,n) for n in [0.,.05] for m,s in [('bc_k2',None),('full',17),('full',23),('full',41)]) for v in versions}
    geometry=read('confirmation_state_validation.json')['geometry_starts'];gresults={v:{r['demo']:r for r in read(f'geometry_confirmation/{v}_geometry/result.json')['records']} for v in ['v2','v3']}
    gr=[]
    for kind in dict.fromkeys(r['kind'] for r in geometry):
        names=[r['name'] for r in geometry if r['kind']==kind]
        gr.append({'kind':kind,'starts':len(names),'v2_successes':sum(gresults['v2'][n]['success'] for n in names),'v3_successes':sum(gresults['v3'][n]['success'] for n in names),
                   'rescues':[n for n in names if gresults['v3'][n]['success'] and not gresults['v2'][n]['success']],
                   'regressions':[n for n in names if gresults['v2'][n]['success'] and not gresults['v3'][n]['success']]})
    write(RUN/'geometry_comparison.json',gr)
    mechanisms={}
    for v in versions[1:]:
        allrows=[r for j in jobs if j['version']==v for r in rr[j['id']]]
        failures=[r for r in allrows if not r['success']]
        timeout=Counter(e['from'] for r in allrows for e in r['events'] if e['reason']=='phase_timeout')
        lastphase=Counter((r['events'][-1]['from'] if r['events'] else 'NORMAL') for r in failures)
        losses=[r for r in allrows if any(e['reason']=='observed_grasp_loss' for e in r['events'])]
        mechanisms[v]={'phase_timeout_events':dict(timeout),'failure_last_event_source':dict(lastphase),'loss_trigger_runs':len(losses),'loss_trigger_successes':sum(r['success'] for r in losses),
          'intervened_runs':sum(r['attempts']>0 for r in allrows),'mean_steps_capped':sum(r['steps'] for r in allrows)/len(allrows)}
    write(RUN/'mechanism_summary.json',mechanisms)
    receipts={stage:read(f'validation_{stage}.json') for stage in ['dev_a','dev_b','dev_c','confirmation','geometry_confirmation']}
    assert all(r['passed'] for r in receipts.values())
    before=read('before_manifest.json')
    for p,sha in before.items():assert (ROOT/p).is_file() and digest(ROOT/p)==sha,p
    for p,sha in read('confirmation_lock.json')['sha256'].items():assert digest(ROOT/p)==sha,p
    text=['# v3 对齐与箱格碰撞改进：实验报告','',f"生成时间：{datetime.datetime.now(datetime.timezone.utc).isoformat()}。本报告是工程实验记录，不是论文。",'',
      '## 结论与保存状态','',f"本轮完成三轮开发对照、冻结后的 1920 回合原生起点独立确认，以及 32 回合独立几何压力测试。v3 在本批原生确认中为 {totals['v3']}/480，v2 为 {totals['v2']}/480；较 v2 救回 {summary['rescues_vs_v2']} 回合，新增失败 {summary['regressions_vs_v2']} 回合。每个版本的 480 是执行回合数，仅来自 60 个共享起点，不能当作 480 个独立样本。",'',
      f"本轮所有改动在 `reproduction/recovery_v3_20261012_01/`。检查前存在的 {len(before)} 个项目文件 SHA-256 均不变，包含 v1、v2、现有权重及结果。没有重新训练、替换或删除权重，没有更改根目录控制代码，没有撰写论文。",'',
      '## 修改与诊断','',
      '- 对齐：等价抓取 yaw 使用固定中性扇区，避免只按末端最短转角选择导致腕部顶限位；时限按当前位置/姿态误差设置为 70–110 步；只在高处对齐时允许平移增量范数达到 0.05 m（原环境动作界限内）。',
      '- 直立角落：同时考虑两面墙的间隙，选择斜向夹爪朝向、约 0.060 m 预开口及每轴 0.006 m 内侧偏置。',
      '- 侧倒靠墙：根据已知掌部跨度与箱格几何，使掌部向格内倾斜，最大 35°，降低掌部撞墙造成的下降超时。',
      '- 共享控制器仍只读 23 维状态历史和固定任务几何；关节限位和真实接触只用于事后诊断。BC 与 Full 使用完全相同的恢复逻辑。D=2 队列不清空、400 步预算、两次恢复上限、原权重与原 Full 评分保持不变。',
      '- 同一已知开发状态的分支诊断：旧 yaw 在 110 步后仍约 6.89 cm / 0.305 rad 偏差；等价 yaw=0 在第 85 步满足对齐条件。这是机制证据，不是新的独立成功回合。',
      '- 角落两例初版接触计数从 116/115 降至 0/0；最终较快对齐版相应为 2/0，并完成任务。只在控制边界采样接触，不能声称整个物理轨迹绝对无碰撞。',
      '', '详细开发记录与未通过的版本见 [DEVELOPMENT_NOTES.md](DEVELOPMENT_NOTES.md)、各 `pilot_*` 和 `dev_*` 目录。','',
      '## 开发集与冻结','',
      '| 版本 | 成功 / 240 | 相对 v2 的救回 / 新增失败 | 是否通过预登记门槛 |','|---|---:|---:|---|']
    for stage in ['dev_a','dev_b','dev_c']:
        s=read(f'analysis_{stage}/summary.json');p=read(f'promotion_{stage}.json');text.append(f"| {stage} | {s['v3_successes']} | {s['rescues_vs_v2']} / {s['regressions_vs_v2']} | {'通过' if p['passed'] else '未通过'} |")
    text+=['','门槛在首次 v3 运行前登记：总成功至少 232/240；相对 v2 新增失败不超过 2；BC clean/noise 均至少 28/30；Full clean 至少 84/90、noise 至少 89/90。反复使用开发集会产生选择偏差，因此开发成绩不作为最终泛化证据。',
      '',f"最终冻结后才生成 60 个新原生起点（seeds 626101201–626101260，demo_6000000–6000059）。与 {valid['old_initial_states_compared']} 个既有原生/数据初始状态无重复；逆序重新生成状态完全一致；保存的 XML 重新载入观测误差小于 1e-5。所有起点保留，没有按结果筛选。噪声由 70000+demo 编号固定生成。",'',
      '## 全新原生起点确认','', '| 条件 | 方法 | 无恢复 | v1 | v2 | v3 |','|---|---|---:|---:|---:|---:|']
    for noise in [0.,.05]:
        for method,seed in [('bc_k2',None),('full',17),('full',23),('full',41)]:
            text.append('| '+('无噪声' if noise==0 else '噪声 0.05')+' | '+('BC k=2' if method=='bc_k2' else f'Full s{seed}')+' | '+' | '.join(f'{counts(v,method,seed,noise)}/60' for v in versions)+' |')
    text+=['','| 版本 | 合计执行成功 / 480 |','|---|---:|']+[f'| {label} | {totals[v]}/480 |' for v,label in zip(versions,labels)]
    text+=['','![原生起点成功率](analysis_confirmation/success_comparison.png)','','## 配对统计与解释','','以 60 个起点为重采样单位，Full 的三个固定训练种子先在每个起点内平均；20000 次配对 bootstrap，随机种子 20261014。以下区间为描述性 95% bootstrap 区间，未做多重比较修正，也不包含训练种子总体不确定性。','',
      '| 条件 | 比较 | 成功率差（百分点） | 95% 区间 |','|---|---|---:|---:|']
    for noise,label in [('clean','无噪声'),('noise005','噪声 0.05')]:
        for key,title in [('bc_v3_minus_v2','BC: v3 − v2'),('full_v3_minus_v2','Full: v3 − v2'),('v3_full_minus_bc','v3: Full − BC')]:
            x=summary['statistics'][noise][key];lo,hi=x['ci95'];text.append(f"| {label} | {title} | {100*x['estimate']:+.2f} | [{100*lo:+.2f}, {100*hi:+.2f}] |")
    text+=['','Full 与 BC 的差异必须看上表及区间，不能因为总成功率较高就声称世界模型稳定胜出。恢复改进是共享的手工反馈控制改进，没有改善或再训练世界模型权重。','',
      '## 独立几何压力测试','', '另用 16 个新原生 reset 种子和独立姿态随机源生成起点，v2/v3 同样在第 80 步强制进入恢复，基础提议固定为静止张爪。这用于隔离恢复机构的能力，不是自然 BC/Full 策略的成功率，不计入上面的 480 回合。','',
      '| 初始几何 | v2 | v3 | 救回 / 新增失败 |','|---|---:|---:|---:|']
    for r in gr:text.append(f"| {r['kind']} | {r['v2_successes']}/{r['starts']} | {r['v3_successes']}/{r['starts']} | {len(r['rescues'])} / {len(r['regressions'])} |")
    text+=['','## 剩余问题与干预代价','',f"原生确认仍有 {480-totals['v3']} 个失败执行回合，事后分类：`{diagnosis['failure_categories']}`。逐例位置、事件、救回和退步清单在 `diagnosis_confirmation.json`。不要将跨策略、跨噪声或跨训练种子的同一起点重复失败当作独立环境样本。",'',
      '| 控制版本 | ALIGN 阶段超时事件 | DESCEND 阶段超时事件 | 发生干预的回合 | 检测到失抓后成功 / 触发回合 | 含失败的平均步数 |','|---|---:|---:|---:|---:|---:|']
    for v in ['v1','v2','v3']:
        m=mechanisms[v];text.append(f"| {v} | {m['phase_timeout_events'].get('ALIGN',0)} | {m['phase_timeout_events'].get('DESCEND',0)} | {m['intervened_runs']} | {m['loss_trigger_successes']}/{m['loss_trigger_runs']} | {m['mean_steps_capped']:.2f} |")
    text+=['','阶段超时是事件数，一回合可能有两次；失抓触发集合随控制器改变，并非相同样本上的配对成功率。并行运行的决策耗时不能当作严格的实时性能比较。',
      '', 'v3 仍没有在线避障规划、关节可达性求解、物体落出工作区后的重置机制或视觉估计鲁棒性。固定中性 yaw 和几何近似只是有限场景下的工程规则；不能保证任意角落、任意倒伏姿态都能恢复。进一步工作应先按失败事件区分接近路径、壁面间隙和剩余时间预算，再在新开发夹具上设计最小改动，不能继续在本批确认集上调参后仍称其为独立测试。',
      '', '## 完整度与本科毕设适用性','',
      '本轮已形成可审查的闭环：原因诊断 → 保留失败的原型 → 预登记开发门槛 → 通过门槛后冻结 → 全新起点的公平对照 → 配对不确定性分析 → 全轨迹验证和剩余故障记录。它可作为本科毕业设计的实验与工程部分，建议定位为“基于世界模型候选决策与状态反馈恢复的机器人搬运系统”。学校没有提供正式任务书或评分细则，因此这不是对毕业合格的保证。',
      '', '现有证据支持有边界的工程改进与系统实现；不能把工作描述为端到端视觉机器人、真实机器人验证、任意环境鲁棒控制，或已经证明世界模型全面优于 BC。仍应保留最强 BC k=2 基线、失败案例和区间估计。按本次要求，暂不撰写论文。',
      '', '## 验证与文件入口','',
      '- `study_plan.json`：先验门槛和新种子；`promotion_*.json`：每次开发决策。',
      '- `freeze_before_states.json` / `confirmation_lock.json`：冻结时点、代码/数据/权重哈希。',
      '- `confirmation/`、`geometry_confirmation/`：每回合结果与逐步动作/状态日志。',
      '- `analysis_confirmation/`：逐回合 CSV、配对统计、PNG/SVG 图。',
      '- `validation_*.json`：每一步的控制器、队列、噪声、计数及抽样 MuJoCo 完整轨迹回放检查。',
      '- `delivery_validation.json`：交付时再次确认既有文件与冻结输入未变化。',
      '- `README.md`：在当前 PyCharm 虚拟环境中查看和复核的命令。','']
    with (RUN/'REPORT.md').open('x',encoding='utf8') as f:f.write('\n'.join(text))
    for p in RUN.glob('*.py'):compile(p.read_text(encoding='utf8'),str(p),'exec')
    write(RUN/'delivery_validation.json',{'passed':True,'old_files_unchanged':len(before),'frozen_inputs_unchanged':True,
       'verified_executed_episodes':sum(r['episodes'] for r in receipts.values()),'verified_control_steps':sum(r['controls_checked'] for r in receipts.values()),
       'physical_replays':[r for v in receipts.values() for r in v['physical_replays']],
       'summary_totals':totals,'v3_rescues_vs_v2':summary['rescues_vs_v2'],'v3_regressions_vs_v2':summary['regressions_vs_v2'],
       'geometry_summary':gr,'report_sha256':digest(RUN/'REPORT.md'),'receipts_sha256':{s:digest(RUN/f'validation_{s}.json') for s in receipts}})
    print(json.dumps({'totals':totals,'rescues':summary['rescues_vs_v2'],'regressions':summary['regressions_vs_v2'],'geometry':gr},indent=2))
if __name__=='__main__':main()
