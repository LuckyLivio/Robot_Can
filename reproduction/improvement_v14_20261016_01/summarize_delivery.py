"""Build a candid delivery report from immutable completed smoke stages."""
from pathlib import Path
import hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
if __name__=='__main__':
    stages={s:read(RUN/'analysis'/f'{s}.json') for s in ['smoke_a','smoke_b']}
    audits={s:read(RUN/'analysis'/f'{s}_verification.json') for s in stages}
    physics={s:read(RUN/'analysis'/f'{s}_physics.json') for s in stages}
    assert all(x['passed'] for x in [*audits.values(),*physics.values()])
    assert not stages['smoke_b']['outcome_gate_passed']
    for forbidden in ['pilot_a','dev_a','confirmation']:
        assert not (RUN/forbidden).exists()
    mechanism=read(RUN/'analysis/mechanisms_b.json');assert mechanism['passed']
    assert hashlib.sha256((RUN/'recovery/recovery_controller.py').read_bytes()).hexdigest()==mechanism['source_sha256']
    # C was inactive in all combined-v14 B episodes. Verify exact physical and
    # action equivalence to T, rather than crediting the combined label.
    equivalent=[]
    for j in read(RUN/'smoke_b/jobs.json'):
        if j['version']!='v14':continue
        d=read(RUN/'smoke_b'/j['id']/'result.json');assert not any(r['clearance14_events'] for r in d['records'])
        a=[json.loads(s) for s in (RUN/'smoke_b'/j['id']/'trace.jsonl').open()]
        b=[json.loads(s) for s in (RUN/'smoke_b'/j['id'].replace('v14_','track_',1)/'trace.jsonl').open()]
        assert len(a)==len(b)
        for x,y in zip(a,b):
            for key in ['demo','step','state_before','state_after','submitted_action','executed_action','success_after']:assert x[key]==y[key]
        equivalent.append(j['id'])
    summary={'status':'smoke_gate_failed_not_adopted','latest_revision':'smoke_b',
        'headline':'v14小测试未达标：斜靠首次接近和抓取已改善，搬运与箱沿耗时仍失败；未进入大规模消融、开发或独立确认。',
        'completed_evaluation_executions':sum(a['episodes'] for a in audits.values()),
        'completed_stages':{s:a['episodes'] for s,a in audits.items()},
        'action_replay_controls':sum(a['controls'] for a in audits.values()),
        'physical_replay_episodes':sum(a['episodes'] for a in physics.values()),
        'physical_replay_steps':sum(a['steps'] for a in physics.values()),
        'partial_failed_stage_episodes':0,'new_training_runs':0,'new_weights':0,
        'pilot_executions':0,'development_executions':0,'independent_confirmation_executions':0,
        'adopted':False,'frozen_for_confirmation':False,
        'mechanism_checks':len(mechanism['targeted_checks']),'inherited_config_fields_unchanged':mechanism['all_inherited_config_fields_exact'],
        'off_replay_episodes':mechanism['off_replay']['episodes'],'off_replay_steps':mechanism['off_replay']['steps'],
        'latest_complete_variants':stages['smoke_b']['variants'],
        'combined_exactly_equals_tracking_on_latest_smoke':equivalent,
        'limitations':['8 deliberately selected known conditions per variant; no generalization estimate.',
                       'Both target episodes still fail within400 steps.',
                       'Clearance-only loses one parent success and shows no episode-level gain.',
                       'Combined C is inactive on this smoke panel; outcome matches T exactly.',
                       'Hand/can segment and local IK checks are not a full-arm or physical safety proof.']}
    (RUN/'SUMMARY.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf8')
    lines=['# v14 检查报告（2026-10-16）','',
        '**结论：小测试门槛未通过，v14 保留为诊断版本，未采用。** 接近控制得到局部改善，但两个目标整回合仍失败，不应宣称成功率提升或问题已彻底修复。',
        '', '## 1. 本轮范围和保护', '',
        '新代码位于本目录，继承冻结 v13。T 增加接近末段的观测速度补偿及关节余量趋势检查；C 在已验证路径上尝试横向回正。400 步、20 Hz、D2、两次尝试、旧权重及全部 88 个继承配置字段保持不变。没有训练，没有写论文。',
        '', '## 2. 完整运行的实验', '',
        '| 修订 | v13 | 仅 T | 仅 C | v14（T+C） | 门槛 |','|---|---:|---:|---:|---:|---|']
    for s,d in stages.items():
        nums=[f"{d['variants'][v]['success']}/{d['variants'][v]['episodes']}" for v in ['v13','track','clearance','v14']]
        lines.append('| '+s+' | '+' | '.join(nums)+' | 未通过 |')
    lines += ['', '两轮各 8 个已知条件 × 4 组，共 **64 次闭环执行**。四组小测试同时提供局部消融。每轮的代码快照、失败结果和逐步记录均保留。93 条件 × 4 组的大规模消融（372 次）、240 次开发对照及 1440 次全新起点确认均**未运行**；代码只准备好入口，没有生成确认起点或冻结采用版本。',
        '', '这些起点经过历史失败分析后选入，不能把 6/8 写成总体成功率或泛化能力；相同起点的不同模型与修订也不是独立样本。',
        '', '## 3. 实际改善与剩余失败', '',
        '- **斜靠目标 BC + noise0.05 / demo13000021**：v13 第一次接近超时，第二次接近触限；v14-b 在第 258 步进入下降、269 步闭合、294 步确认抬升、311 步进入搬运。已解决该次首次接近超时；但搬运仍到 400 步未完成。持物持续，终点距箱格中心约 92.5 mm；第 358 步关节 4 观测限位余量为 −0.004203 rad（MuJoCo 软限位允许小幅越界）。剩余问题转为持物姿态下的搬运可达性，不能宣称全程关节限位已修好。',
        '- **箱沿目标 Full s41 + noise0.05 / demo13000022**：第一段旋转仍在第 231 步超时，第二次尝试又花时间重新核验姿态，400 步未完成。静态三点 IK 的可行结果不足以保证实际 OSC 沿同一关节姿态运动。',
        '- **回正模块 C**：第二轮单独使用为 5/8，损失旧 demo6000005 成功；该例回正后已完成抓取和搬运，但到第 392 步才释放，400 步时仍未成功（父版本 380 步成功）。尚无整回合救回证据。v14-b 的八个条件中 C 未触发，动作与物理状态逐步精确等于仅 T，不能把 T 的局部改善归功于 C。',
        '- **旧成功保护**：v14-b 保留本面板 v13 原有的 6 个成功；这只是小面板回归检查，不是开发或独立确认通过。',
        '', '## 4. 负结果及修订依据', '',
        'smoke_a 的回正条件过早触发，v14 只有 4/8。复查还发现回正动作与固定旋转路径证据的范围不完全一致。smoke_b 收窄为实测间隙触发，补齐原未知状态、12 mm 物体位移与开度保护；动作限定在线段内、无旋转或夹爪增量。所有早期结果保留，不能把 a 轮称为最终控制安全证明。',
        '', 'mechanisms_a.json 的失败来自测试工具未模拟 choose() 之后的诊断性开爪注入；仅修正测试工具后，mechanisms_a_harness2.json 通过。mechanisms_b.json 进一步加入修正行为检查。测试工具错误与物理实验失败分开记录。',
        '', '## 5. 核验清单', '',
        f'- [x] 最终 {summary["mechanism_checks"]} 项机制检查通过；88 个继承配置字段不变。',
        '- [x] 关闭新增功能：50 个历史案例、14,704 步动作/诊断/继承事件精确回放；b 轮复用该记录并核对关闭分支逻辑没有变化，没有虚增实验数。',
        f'- [x] 全部 64 回合、{summary["action_replay_controls"]:,} 个控制步完成保存输入、动作、D2 FIFO、噪声、终止与预算复算。',
        f'- [x] 全部 64 回合、{summary["physical_replay_steps"]:,} 步完成物理回放，前后观测、奖励阶段及成功标签精确相同；回放不计入新的成功率样本。',
        '- [x] 小测试未达标后未越过门槛运行后续大批实验；无训练、无新权重。',
        '- [ ] 372 次大规模消融：未启动。','- [ ] 240 次开发对照：未启动。','- [ ] 全新起点独立确认：未启动。',
        '', '图像、视频、网页、文档链接、旧文件哈希和 Git 同步各有单独验证；以 validation/、integrity_receipt.json 和实际远端提交为依据。',
        '', '## 6. 项目整体评估与下一步', '',
        '既有项目的代码、三种子世界模型、基线、历史消融、开发与独立确认材料继续有效；本轮没有替换它们。项目具备本科毕业设计的实验与展示基础，但不能称为完美系统、普遍优于强基线或具备完整物理安全保证。v14 目前只能作为失败定位与控制改进的探索记录，不能作为已确认的新增性能成果。',
        '', '建议下一轮先改变局部路径验证覆盖的阶段，而非继续调整同一组阻尼：',
        '1. 对斜靠抓取，规划时同时检查“抓取—抬升—搬运前段”的实际关节姿态；抓住后若需调整姿态，必须在安全高度验证携带物体包络，不能只检查空夹爪。',
        '2. 对箱沿，比较“先平移到可旋转位置，再转向接近”的有限分段路径；逐段验证旋转包络、箱体/物体间隙和当前关节 IK，保留原阈值与 400 步。',
        '3. 将 C 的旧成功退步作为必过保护案例，先排除回正占用预算与重新启动等待循环，再扩大消融；只在门槛通过后运行开发和新起点确认。',
        '', '以上属于后续方案，本轮尚未实施。',
        '', '## 7. 证据入口', '',
        '- [执行前协议](protocols/PLAN.md)','- [第二轮配对结果](analysis/smoke_b_pairs.csv)','- [第二轮门槛判定](analysis/smoke_b.json)',
        '- [机制检查](analysis/mechanisms_b.json)','- [逐步路径诊断](analysis/path_diagnosis.json)','- [前端与对比演示](index.html)','- [v13 原报告](../improvement_v13_20261016_01/REPORT.md)']
    (RUN/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps({k:summary[k] for k in ['status','completed_evaluation_executions','action_replay_controls','physical_replay_steps']}))
