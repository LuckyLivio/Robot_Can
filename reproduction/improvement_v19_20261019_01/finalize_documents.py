"""Publish verified v19 status to exactly nine byte-backed-up active entries."""
from pathlib import Path
import hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];REL=RUN.relative_to(ROOT).as_posix()
DOCS=['README.md','index.html','STATUS.md','DEMO_GUIDE.md','RESULTS.md','EVIDENCE_INDEX.md','PROJECT_NAVIGATION.md','THESIS_HANDOFF_LATEST.md','PROGRAM_GUIDE.md']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
if __name__=='__main__':
    summary=read(RUN/'SUMMARY.json')
    assert summary['completed_evaluation_executions']==72 and summary['all_completed_stage_audits_passed']
    assert summary['status']=='smoke_gate_failed_not_adopted' and not summary['adopted']
    before=read(RUN/'before_manifest.json')
    for name in DOCS:assert sha(ROOT/name)==sha(RUN/'before'/name)==before[name],name
    variants=summary['latest_complete_variants'];stage=summary['latest_stage']
    labels={'v17':'实际 v17','v18':'实际 v18','budget':'原预算候选','transition':'仅 A 衔接窗口',
            'candidate':'仅 B 候选限额','settling':'仅 C 积分制动','ab':'A+B','v19':'完整 v19'}
    score='；'.join(f'{label} {variants[key]["success"]}/{variants[key]["episodes"]}' for key,label in labels.items())
    links=f'[本轮完整报告]({REL}/REPORT.md) · [v19 前端]({REL}/index.html) · [正式协议]({REL}/protocols/PLAN.md) · [v18 原报告](reproduction/improvement_v18_20261019_01/REPORT.md)'
    common=f'''**v19 已完成八组共72回合小测试与消融，未通过预定门槛，未采用。**

{score}。

每组9个条件共用8个不同物理起点：8个标准条件与1个复用6000005起点的clearance专用配置。A/B/C/AB均加在完整v18上，原预算候选保护不同，仅作成功数参考。72回合不是72个独立起点，本组困难案例成功率不能当作整个项目总体成功率。

保留400步、D2 FIFO、原保护阈值与成功定义。752次扩展诊断、三版各240次开发对照（合计720）及1440次独立确认均未运行，未生成新确认起点；保留v18、预算候选及所有旧代码、权重、结果。未做泛化训练，未写论文。

{links}
'''
    start=f'''```powershell
Set-Location 'C:\\Users\\Livio\\Desktop\\robot_can'
& '.\\.venv\\Scripts\\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\\Users\\Livio\\Desktop\\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/{REL}/index.html** 。已有8766服务时直接打开，不重复启动；服务终端保持运行，用Ctrl+C停止。
'''
    (ROOT/'README.md').write_text(f'''# CAN LAB · 机器人世界模型与恢复控制

项目研究延迟控制下的罐体抓取搬运：冻结BC策略提供动作候选，世界模型预测评分，恢复控制器处理失抓、支撑姿态及受约束的搬运。当前是特权状态仿真，尚不构成视觉输入或实机验证。

## 当前状态（2026-10-19）

{common}
## 启动前端

{start}
页面包含八组实际结果、预定门槛、逐条件证据及论文质量分类图。历史视频有独立版本标签，本轮没有新拍的v19机器人视频。

## 导航

- [分类导航](PROJECT_NAVIGATION.md) · [环境和运行指南](PROGRAM_GUIDE.md)
- [项目状态](STATUS.md) · [结果索引](RESULTS.md) · [证据索引](EVIDENCE_INDEX.md)
- [演示指南](DEMO_GUIDE.md) · [写作材料交接](THESIS_HANDOFF_LATEST.md)
- [本轮目录和核验命令]({REL}/README.md)
- [此前README原样快照]({REL}/before/README.md)
''',encoding='utf8')
    findings='\n\n'.join(f'**{x["title"]}**：{x["finding"]} 下一步：{x["next_step"]}' for x in summary['diagnostic_findings'])
    (ROOT/'STATUS.md').write_text(f'''# 当前项目状态

{common}
| 检查项 | 本轮状态 |
|---|---|
| 小测试与消融 | 72回合完整执行，保留全部正负结果 |
| 三新开关全关 | 9个profile、3429步精确复现实际v18 |
| 执行前检查 | 5项有效源码绑定回执通过；a版全关回执保留为设计历史 |
| 保存输入审计 | {summary['action_replay_controls']}控制步通过 |
| 物理回放 | {summary['physical_replay_episodes']}回合、{summary['physical_replay_steps']}步；不增加评估样本 |
| 继承配置 | 108项不变；新增3个开关，合计111项 |
| 后续阶段 | 扩展/开发/冻结/确认均未开始 |
| 采用、训练及写作 | 完整v19未采用；未训练，未写论文 |

## 实际诊断与后续方向

{findings}

[此前状态快照]({REL}/before/STATUS.md)
''',encoding='utf8')
    (ROOT/'DEMO_GUIDE.md').write_text(f'''# 前端与演示指南

{start}
先看八组实际结果、预定目标和门槛，再看逐条件表及失败诊断。主卡片统计8个标准条件，clearance专用配置单列。图表采用分类比较，不用折线连接无序案例。

本轮没有新v19视频。[历史v14演示](reproduction/improvement_v14_20261016_01/index.html#demo)不能作为v19成功证据。页面不会启动实验或训练。

{links}

[此前指南快照]({REL}/before/DEMO_GUIDE.md)
''',encoding='utf8')
    (ROOT/'PROGRAM_GUIDE.md').write_text(f'''# 项目运行指南（当前入口）

{common}
在PyCharm中沿用 `.venv\\Scripts\\python.exe` 解释器。

## 启动前端

{start}
## 核验和实验

[本轮README]({REL}/README.md)提供核验命令。[协议]({REL}/protocols/PLAN.md)锁定门槛；登记作业不代表执行。小测试未通过，不启动开发或独立确认。

早期训练、数据和历史命令保留在[此前指南快照]({REL}/before/PROGRAM_GUIDE.md)，按对应版本使用。
''',encoding='utf8')
    for name,title in [('RESULTS.md','实验结果索引'),('EVIDENCE_INDEX.md','证据索引'),('PROJECT_NAVIGATION.md','项目分类导航'),('THESIS_HANDOFF_LATEST.md','写作材料交接状态')]:
        extra='此前写作包未包含v19。本轮只能作为探索与失败分析，不能表述为普遍改善或独立确认通过。未写论文或改写提纲。' if name=='THESIS_HANDOFF_LATEST.md' else ''
        head=f'''# {title} · 当前入口

{common}
{extra}

[配对表]({REL}/analysis/{stage}_pairs.csv) · [图表及来源]({REL}/figures/CATALOG.json) · [文件完整度核验]({REL}/verify_integrity.py)

## 历史内容（按各自版本与时间解释）

'''
        (ROOT/name).write_text(head+(RUN/'before'/name).read_text(encoding='utf8'),encoding='utf8')
    (ROOT/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={REL}/index.html"><title>CAN LAB · v19诊断</title><a href="{REL}/index.html">打开v19实验报告（未采用）</a></html>',encoding='utf8')
    with (RUN/'document_changes.json').open('x',encoding='utf8') as f:json.dump({'updated':DOCS},f,indent=2)
    print('Updated exactly nine backed-up active documents.')
