"""Publish the audited v20 outcome to nine verbatim-backed-up active entries."""
from pathlib import Path
import hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];REL=RUN.relative_to(ROOT).as_posix()
DOCS=['README.md','index.html','STATUS.md','DEMO_GUIDE.md','RESULTS.md','EVIDENCE_INDEX.md','PROJECT_NAVIGATION.md','THESIS_HANDOFF_LATEST.md','PROGRAM_GUIDE.md']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
if __name__=='__main__':
    s=read(RUN/'SUMMARY.json')
    assert s['all_completed_stage_audits_passed']
    assert s['status']=='smoke_gate_failed_not_adopted' and not s['adopted'], 'Update publication wording for any other verified outcome before publishing'
    assert s['completed_evaluation_executions']==54
    before=read(RUN/'before_manifest.json')
    for name in DOCS:assert sha(ROOT/name)==sha(RUN/'before'/name)==before[name],name
    labels={'v17':'实际 v17','v19':'实际 v19','budget':'原预算候选','directional':'仅 A 方向衔接','braking':'仅 B 延迟制动','v20':'完整 v20'}
    variants=s['latest_complete_variants'];stage=s['latest_stage']
    score='；'.join(f'{label} {variants[key]["success"]}/{variants[key]["episodes"]}' for key,label in labels.items())
    links=f'[本轮完整报告]({REL}/REPORT.md) · [v20 前端]({REL}/index.html) · [正式协议]({REL}/protocols/PLAN.md) · [v19 原报告](reproduction/improvement_v19_20261019_01/REPORT.md)'
    common=f'''**v20 已完成六组共54回合小测试与消融，未通过预定门槛，未采用。**

{score}。

每组9个条件共用8个不同物理起点：8个标准条件与1个复用6000005起点的clearance专用配置。A、B及组合均基于完整v19；原预算候选保护不同，仅作成功数参考。54回合不是54个独立起点，这组困难案例成功率不能当作项目总体成功率。

保持400步、真实D2 FIFO、原保护阈值与成功定义。564回合扩展诊断、三版各240回合开发对照（合计720）及1440回合独立确认均未运行，未生成新确认起点。保留v19、预算候选与全部旧代码、权重和结果。未做泛化训练，未写论文。

{links}
'''
    start=f'''```powershell
Set-Location 'C:\\Users\\Livio\\Desktop\\robot_can'
& '.\\.venv\\Scripts\\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\\Users\\Livio\\Desktop\\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/{REL}/index.html** 。已有8766服务时直接打开，不重复启动；服务终端保持运行，Ctrl+C停止。根地址会跳转到本轮前端。
'''
    (ROOT/'README.md').write_text(f'''# CAN LAB · 机器人世界模型与恢复控制

项目研究延迟控制下的罐体抓取搬运：冻结BC策略提供动作候选，世界模型预测评分，恢复控制器处理失抓、支撑姿态及受约束搬运。目前使用特权状态仿真，尚无视觉输入或实机验证。

## 当前状态（2026-10-19）

{common}
## 启动前端

{start}
页面包含六组实际结果、预定门槛、逐条件证据和分类图表。本轮没有新拍的v20机器人视频，历史演示按其真实版本标注。

## 导航

- [分类导航](PROJECT_NAVIGATION.md) · [环境与运行指南](PROGRAM_GUIDE.md)
- [项目状态](STATUS.md) · [结果索引](RESULTS.md) · [证据索引](EVIDENCE_INDEX.md)
- [演示指南](DEMO_GUIDE.md) · [写作材料交接](THESIS_HANDOFF_LATEST.md)
- [本轮目录和核验命令]({REL}/README.md)
- [此前README原样快照]({REL}/before/README.md)
''',encoding='utf8')
    findings='\n\n'.join(f'**{x["title"]}**：{x["finding"]} 下一步：{x["next_step"]}' for x in s['diagnostic_findings'])
    (ROOT/'STATUS.md').write_text(f'''# 当前项目状态

{common}
| 检查项 | 本轮状态 |
|---|---|
| 小测试与消融 | 54回合完整执行，正负结果全部保留 |
| 新开关全关 | 9个profile、3423控制步精确复现实际v19 |
| 执行前检查 | 四项当前源码绑定回执通过 |
| 保存输入逐步审计 | {s['action_replay_controls']}控制步通过 |
| 物理回放 | {s['physical_replay_episodes']}回合、{s['physical_replay_steps']}步；不增加样本 |
| 配置与预算 | 111项继承值不变；新加2开关，400步、D2 |
| 后续阶段 | 扩展、开发、采用冻结、确认未开始 |
| 训练与论文 | 未训练、未写论文 |

## 实际诊断与后续方向

{findings}

[此前状态快照]({REL}/before/STATUS.md)
''',encoding='utf8')
    (ROOT/'DEMO_GUIDE.md').write_text(f'''# 前端与演示指南

{start}
先看六组配对结果与门槛，再看逐条件表、消融和失败诊断。标准8条件与复用起点的clearance配置分列；无序案例不连成折线。

本轮没有新v20视频。[历史v14演示](reproduction/improvement_v14_20261016_01/index.html#demo)不能作为v20成功证据。前端不会启动实验或训练。

{links}

[此前指南快照]({REL}/before/DEMO_GUIDE.md)
''',encoding='utf8')
    (ROOT/'PROGRAM_GUIDE.md').write_text(f'''# 项目运行指南（当前入口）

{common}
PyCharm沿用 `.venv\\Scripts\\python.exe` 解释器。

## 启动前端

{start}
## 核验和实验

[本轮README]({REL}/README.md)提供核验命令。[协议]({REL}/protocols/PLAN.md)锁定条件和门槛；作业登记不等于执行。小测试未通过，不启动开发和独立确认。

早期训练、数据与历史命令保留在[此前指南快照]({REL}/before/PROGRAM_GUIDE.md)，按对应版本使用。
''',encoding='utf8')
    for name,title in [('RESULTS.md','实验结果索引'),('EVIDENCE_INDEX.md','证据索引'),('PROJECT_NAVIGATION.md','项目分类导航'),('THESIS_HANDOFF_LATEST.md','写作材料交接状态')]:
        extra='已有写作包未纳入v20。本轮是已知难例上的探索与失败分析，不能表述为普遍提升或独立确认通过。未写论文、未改提纲。' if name=='THESIS_HANDOFF_LATEST.md' else ''
        header=f'''# {title} · 当前入口

{common}
{extra}

[逐条件配对表]({REL}/analysis/{stage}_pairs.csv) · [图表与来源]({REL}/figures/CATALOG.json) · [完整度核验]({REL}/verify_integrity.py)

## 历史内容（按各自版本和时间解释）

'''
        (ROOT/name).write_text(header+(RUN/'before'/name).read_text(encoding='utf8'),encoding='utf8')
    (ROOT/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={REL}/index.html"><title>CAN LAB · v20诊断</title><a href="{REL}/index.html">打开v20实验报告（未采用）</a></html>',encoding='utf8')
    with (RUN/'document_changes.json').open('x',encoding='utf8') as f:json.dump({'updated':DOCS},f,indent=2)
    print('Updated exactly nine backed-up active documents.')
