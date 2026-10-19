"""Update only nine backed-up active entries from verified v18 results."""
from pathlib import Path
import hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];REL=RUN.relative_to(ROOT).as_posix()
DOCS=['README.md','index.html','STATUS.md','DEMO_GUIDE.md','RESULTS.md','EVIDENCE_INDEX.md','PROJECT_NAVIGATION.md','THESIS_HANDOFF_LATEST.md','PROGRAM_GUIDE.md']
START=f"""```powershell
Set-Location 'C:\\Users\\Livio\\Desktop\\robot_can'
& '.\\.venv\\Scripts\\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\\Users\\Livio\\Desktop\\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/{REL}/index.html** 。已有 8766 服务时直接打开；终端保持运行，Ctrl+C 停止。
"""
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))
if __name__=='__main__':
    s=read(RUN/'SUMMARY.json')
    # This publication template is deliberately limited to a completed smoke
    # rejection. A passing stage must get a report matching the stages run.
    assert s['status']=='smoke_gate_failed_not_adopted' and s['completed_evaluation_executions']==54
    assert s['all_completed_stage_audits_passed'] and not s['adopted']
    old=read(RUN/'before_manifest.json')
    for name in DOCS:
        assert sha(RUN/'before'/name)==old[name]
        assert sha(ROOT/name)==old[name],('Concurrent entry edit',name)
    stage=s['latest_stage'];v=s['latest_complete_variants']
    order=['v16','v17','budget','handoff','short','v18']
    labels=['实际 v16','实际 v17','原预算候选','仅衔接修复','仅短路线修复','完整 v18']
    scores='、'.join(f'{label} {v[key]["success"]}/{v[key]["episodes"]}' for key,label in zip(order,labels))
    headline=f'v18 已完成六组共 54 回合小测试及单项消融：{scores}。未通过预定门槛，完整 v18 未采用。'
    boundary='每组 9 个条件包括 8 个标准条件和 1 个复用 6000005 起点的 clearance-only 配置，只有 8 个不同起点。两个单项修复分别加在完整 v17 上；预算候选仍为原 v15 仅预算 C，保护条件不同，仅用于成功数参考。54 次执行不是 54 个独立起点。'
    finding='本轮实现下降指令连续衔接，以及原朝向、内移端点的直接路线候选。组件和静态认证通过不等于整回合成功。未绕过小测试门槛：564 次扩展诊断、三版各 240 次开发（共 720 次）及 1440 次全新起点确认均未运行，未生成新确认起点。保留 v17、预算候选及全部旧代码、权重和结果。未做泛化训练，未写论文。'
    links=f'[完整报告]({REL}/REPORT.md) · [v18 前端]({REL}/index.html) · [执行前协议]({REL}/protocols/PLAN.md) · [v17 原报告](reproduction/improvement_v17_20261019_01/REPORT.md)'
    common=f'**{headline}**\n\n{boundary}\n\n{finding}\n\n{links}\n'
    diagnoses='\n\n'.join(f'**{x["title"]}**：{x["finding"]} 下一步：{x["next_step"]}' for x in s['diagnostic_findings'])
    mechanisms=read(RUN/'analysis/mechanisms_a.json')
    (ROOT/'README.md').write_text(f'''# CAN LAB · 机器人世界模型与恢复控制

本项目研究延迟控制下的罐体抓取搬运：冻结 BC 策略产生候选，世界模型预测并评分，恢复控制器处理失抓、支撑姿态和路径约束。当前使用特权状态仿真，不等同于视觉输入或实机验证。

## 当前状态（2026-10-19）

{common}
## 启动前端

{START}

页面包含六组实际结果、目标完成情况、失败诊断、未执行阶段及可下载图表。本轮没有新增机器人视频，页面中的 v14 视频明确标注为历史版本。

## 导航

- [项目分类导航](PROJECT_NAVIGATION.md)
- [环境与运行指南](PROGRAM_GUIDE.md)
- [项目状态](STATUS.md)
- [实验结果](RESULTS.md) · [证据索引](EVIDENCE_INDEX.md)
- [前端演示指南](DEMO_GUIDE.md)
- [写作材料交接](THESIS_HANDOFF_LATEST.md)
- [本轮目录与核验命令]({REL}/README.md)
- [此前 README 原样快照]({REL}/before/README.md)
''',encoding='utf8')
    (ROOT/'STATUS.md').write_text(f'''# 当前项目状态

{common}
| 检查项 | 本轮状态 |
|---|---|
| 小测试与单项消融 | 54 回合完整执行，保留所有正负结果 |
| 关闭新功能精确回放 | 9 个 profile 精确复现实际 v17，详见机制回执 |
| 组件与静态检查 | 四份执行前回执通过并绑定源码 |
| 保存输入审计 | {s['action_replay_controls']} 控制步通过 |
| 物理回放 | {s['physical_replay_episodes']} 回合、{s['physical_replay_steps']} 步通过，不增加样本 |
| 继承参数 | 106 项不变，新增两开关；400 步、D2、保护阈值保持 |
| 扩展 / 开发 / 确认 | 564 / 720 / 1440 回合未运行；未生成确认起点 |
| 采用 / 训练 / 论文 | 完整 v18 未采用；未训练，未写论文 |

## 诊断及后续方案

{diagnoses}

[此前状态原样快照]({REL}/before/STATUS.md)
''',encoding='utf8')
    (ROOT/'DEMO_GUIDE.md').write_text(f'''# 前端与演示指南

{START}

先看六组结果及预定门槛，再核对三个目标、逐条件表和失败诊断。主卡片统计 8 个标准条件，clearance-only 配置单列。图表采用分类比较，不用折线暗示这些无序案例之间存在连续趋势。

本轮没有新增 v18 视频。[v14 原始演示](reproduction/improvement_v14_20261016_01/index.html#demo)属于历史版本，不能作为 v18 成功证据。打开页面不会运行训练或实验。

{links}

[此前指南快照]({REL}/before/DEMO_GUIDE.md)
''',encoding='utf8')
    (ROOT/'PROGRAM_GUIDE.md').write_text(f'''# 项目运行指南（当前入口）

{common}
沿用 `.venv\\Scripts\\python.exe`，在 PyCharm 中选择它作为解释器。

## 启动前端

{START}

## 核验和实验

[本轮 README]({REL}/README.md)提供核验命令。[正式协议]({REL}/protocols/PLAN.md)锁定阶段门槛；登记作业不代表执行。小测试失败，不进入开发或独立确认。

早期训练、数据和历史命令保存在[此前指南快照]({REL}/before/PROGRAM_GUIDE.md)，按对应版本使用。
''',encoding='utf8')
    for name,title in [('RESULTS.md','实验结果索引'),('EVIDENCE_INDEX.md','证据索引'),('PROJECT_NAVIGATION.md','项目分类导航'),('THESIS_HANDOFF_LATEST.md','写作材料交接状态')]:
        extra=('此前写作包未包含 v18。本轮结果可作为探索与失败分析，不能写为总体改进或独立确认通过。本轮未写论文或改写提纲。' if name=='THESIS_HANDOFF_LATEST.md' else '')
        header=f'''# {title} · 当前入口

{common}
{extra}

[逐条件配对表]({REL}/analysis/{stage}_pairs.csv) · [图表及来源]({REL}/figures/CATALOG.json) · [完整度核验]({REL}/verify_integrity.py)

## 历史内容（按各自版本与时间解释）

'''
        (ROOT/name).write_text(header+(RUN/'before'/name).read_text(encoding='utf8'),encoding='utf8')
    (ROOT/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={REL}/index.html"><title>CAN LAB · v18 诊断</title><a href="{REL}/index.html">打开 v18 实验报告（未采用）</a></html>',encoding='utf8')
    with (RUN/'document_changes.json').open('x',encoding='utf8') as stream:json.dump({'updated':DOCS},stream,indent=2)
    print('Updated exactly nine backed-up entry documents.')
