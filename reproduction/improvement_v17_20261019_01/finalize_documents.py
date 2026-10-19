"""Publish verified v17 findings to the nine backed-up active entry files."""
from pathlib import Path
import hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];REL=RUN.relative_to(ROOT).as_posix()
DOCS=['README.md','index.html','STATUS.md','DEMO_GUIDE.md','RESULTS.md','EVIDENCE_INDEX.md','PROJECT_NAVIGATION.md','THESIS_HANDOFF_LATEST.md','PROGRAM_GUIDE.md']
START=f"""```powershell
Set-Location 'C:\\Users\\Livio\\Desktop\\robot_can'
& '.\\.venv\\Scripts\\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\\Users\\Livio\\Desktop\\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/{REL}/index.html** 。已有 8766 服务时直接打开，无需再次启动；终端保持运行，Ctrl+C 停止。
"""
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    s=json.loads((RUN/'SUMMARY.json').read_text(encoding='utf8'))
    assert s['status']=='smoke_gate_failed_not_adopted' and s['completed_evaluation_executions']==63
    assert s['all_completed_stage_audits_passed'] and not s['adopted']
    old=json.loads((RUN/'before_manifest.json').read_text())
    for name in DOCS:
        assert sha(RUN/'before'/name)==old[name]
        assert sha(ROOT/name)==old[name],('Concurrent document edit',name)
    stage=s['latest_stage'];v=s['latest_complete_variants']
    order=['v15','v16','budget','route','edge','held','v17']
    labels=['v15','v16','原预算候选','路径单项','箱沿单项','持物单项','完整 v17']
    scores='、'.join(f'{label} {v[key]["success"]}/{v[key]["episodes"]}' for key,label in zip(order,labels))
    headline=f'v17 已完成七组共 63 次小测试：{scores}。未通过预定门槛，完整 v17 未采用。'
    boundary='每组 9 个条件包括 8 个标准条件和 1 个复用 6000005 起点的 clearance-only 父配置 profile，只有 8 个不同起点；不得将 63 次执行视为 63 个独立样本。三个单项修复分别加在完整 v16 上，预算候选仍为原 v15 仅预算 C。'
    finding='公共路径复用、短路线和反馈控制已实现并接受闭环检验；组件检查通过不等于整回合成功。预算候选的 7/9 仅表示任务成功，其中两个成功条件在 CARRY/PLACE 阶段低于现行 0.04 rad 关节余量，不能整体回退采用。658 次扩展消融、v15/v16/v17 各 240 次开发（共 720 次）及 1440 次全新起点确认均未运行。保留预算候选，既有主成果不替换。'
    links=f'[完整报告]({REL}/REPORT.md) · [v17 前端]({REL}/index.html) · [执行前协议]({REL}/protocols/PLAN.md) · [v16 原报告](reproduction/improvement_v16_20261016_01/REPORT.md)'
    diagnoses='\n\n'.join(f'**{x["title"]}**：{x["finding"]} 下一步：{x["next_step"]}' for x in s['diagnostic_findings'])
    common=f'**{headline}**\n\n{boundary}\n\n{finding}\n\n{links}\n'
    (ROOT/'README.md').write_text(f'''# CAN LAB · 机器人世界模型与恢复控制

本项目研究延迟控制下的罐体抓取搬运：冻结 BC 策略产生候选，世界模型预测并评分，恢复控制器处理失抓、支撑姿态和路径约束。当前使用特权状态仿真，不等同于视觉输入或实机验证。

## 当前状态（2026-10-19）

{common}
保留 v16 及全部旧代码、权重和结果。本轮没有泛化训练，没有写论文。

## 启动前端

{START}

页面展示真实七组结果、目标完成情况、失败诊断、未执行阶段和可下载图表。本轮没有新增 v17 机器人视频；页面中的 v14 视频链接明确标注为历史版本。

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
| 小测试及单项消融 | 63 次完整执行，所有正负结果保留 |
| 关闭功能精确回放 | 9 个 profile、3,485 步复现实际 v16 |
| 当前组件检查 | components_c 共 19 组通过；静态两个 static_b 通过 |
| 实际保存输入审计 | {s['action_replay_controls']} 控制步通过 |
| 物理回放 | {s['physical_replay_episodes']} 回合、{s['physical_replay_steps']} 步通过，不增加样本 |
| 继承参数 | 103 项不变；400 步、D2 和保护阈值保持 |
| 已知条件扩展消融 | 658 次已登记，未运行 |
| 开发对照 | 三版各 240 次，共 720 次；未运行 |
| 独立确认 | 1440 次计划未运行，未生成全新起点，未冻结用于确认 |
| 采用 / 训练 / 论文 | 完整 v17 未采用；未训练，未写论文 |

## 诊断与后续方案

{diagnoses}

[此前状态原样快照]({REL}/before/STATUS.md)
''',encoding='utf8')
    (ROOT/'DEMO_GUIDE.md').write_text(f'''# 前端与演示指南

{START}

先查看七组结果与未通过门槛，再看三个目标和失败诊断，最后核对 CSV、原始结果与未执行阶段。主卡片统计 8 个标准条件，clearance-only profile 单列。

本轮没有新增 v17 视频。[v14 原始机器人演示](reproduction/improvement_v14_20261016_01/index.html#demo)属于历史版本，不能用于声称 v17 完成任务。打开页面不会运行训练或实验。

{links}

[此前演示指南快照]({REL}/before/DEMO_GUIDE.md)
''',encoding='utf8')
    (ROOT/'PROGRAM_GUIDE.md').write_text(f'''# 项目运行指南（当前入口）

{common}
沿用 `.venv\\Scripts\\python.exe`，在 PyCharm 中选择它作为解释器；不替换权重或旧环境。

## 启动前端

{START}

## 核验与实验

[本轮 README]({REL}/README.md)提供只读核验命令。阶段顺序由[执行前协议]({REL}/protocols/PLAN.md)锁定，登记作业不代表已执行。小测试失败，不绕过门槛进入开发或确认。

早期训练、数据与历史运行命令保留在[此前指南快照]({REL}/before/PROGRAM_GUIDE.md)，按对应版本使用。
''',encoding='utf8')
    for name,title in [('RESULTS.md','实验结果索引'),('EVIDENCE_INDEX.md','证据索引'),('PROJECT_NAVIGATION.md','项目分类导航'),('THESIS_HANDOFF_LATEST.md','写作材料交接状态')]:
        extra=('此前跨设备写作包不包含本轮 v17。v17 可用于探索和失败分析，不能写为已确认总体提升。本轮未更新论文正文或提纲。' if name=='THESIS_HANDOFF_LATEST.md' else '')
        header=f'''# {title} · 当前入口

{common}
{extra}

[逐条件配对表]({REL}/analysis/{stage}_pairs.csv) · [图表及来源]({REL}/figures/CATALOG.json) · [完整度核验]({REL}/verify_integrity.py)

## 历史内容（以下按各自版本与时间解释）

'''
        (ROOT/name).write_text(header+(RUN/'before'/name).read_text(encoding='utf8'),encoding='utf8')
    (ROOT/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={REL}/index.html"><title>CAN LAB · v17 诊断</title><a href="{REL}/index.html">打开 v17 实验报告（未采用）</a></html>',encoding='utf8')
    with (RUN/'document_changes.json').open('x',encoding='utf8') as f:json.dump({'updated':DOCS},f,indent=2)
    print('Updated exactly nine backed-up entry documents.')
