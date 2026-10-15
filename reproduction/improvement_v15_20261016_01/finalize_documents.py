"""Update only the nine backed-up active entry documents after verified results."""
from pathlib import Path
import hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];REL=RUN.relative_to(ROOT).as_posix()
DOCS=['README.md','index.html','STATUS.md','DEMO_GUIDE.md','RESULTS.md','EVIDENCE_INDEX.md','PROJECT_NAVIGATION.md','THESIS_HANDOFF_LATEST.md','PROGRAM_GUIDE.md']
START=f"""```powershell
Set-Location 'C:\\Users\\Livio\\Desktop\\robot_can'
& '.\\.venv\\Scripts\\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\\Users\\Livio\\Desktop\\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/{REL}/index.html** 。已有8766服务时直接打开，无需再启动；终端保持运行，Ctrl+C停止。
"""
if __name__=='__main__':
    summary=json.loads((RUN/'SUMMARY.json').read_text(encoding='utf8'))
    assert summary['status']=='smoke_gate_failed_not_adopted'
    stage=summary['latest_stage'];result=json.loads((RUN/'analysis'/f'{stage}.json').read_text())
    assert not result['outcome_gate_passed'] and summary['completed_evaluation_executions']==45
    verification=json.loads((RUN/'analysis'/f'{stage}_verification.json').read_text())
    physics=json.loads((RUN/'analysis'/f'{stage}_physics.json').read_text())
    assert verification['passed'] and physics['passed']
    old=json.loads((RUN/'before_manifest.json').read_text())
    for name in DOCS:
        assert hashlib.sha256((RUN/'before'/name).read_bytes()).hexdigest()==old[name]
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==old[name],'Do not overwrite an unexpected concurrent document edit'
    headline='v15已完成45次五组小测试：v14 / 仅搬运A / 仅分段B / 仅预算C / 完整v15为6/9、3/9、6/9、7/9、4/9。小测试未通过，v15未采用。'
    boundary='9个条件包含8个标准条件和1个复用6000005起点的预算配置profile，不能当作9个独立起点。标准条件下完整v15为3/8、父v14为6/8；预算专用profile为v15成功、父版失败。'
    links=f'[本轮完整报告]({REL}/REPORT.md) · [v15前端]({REL}/index.html) · [执行前协议]({REL}/protocols/PLAN.md) · [v14原报告](reproduction/improvement_v14_20261016_01/REPORT.md)'
    finding='预算模块单独运行救回时间不足案例且未损失旧成功；搬运模块的局部IK误拒和转向耗时导致三个旧成功退步，两个主难例仍未完成。因此不替换既有正式成果，不进入470次消融、两版各240次开发或1440次全新起点确认。'
    (ROOT/'README.md').write_text(f'''# CAN LAB · 机器人世界模型与恢复控制

本项目研究延迟控制下的罐体抓取搬运：冻结BC策略产生候选，世界模型预测并评分，恢复控制器处理失抓、支撑姿态和路径约束。当前使用特权状态仿真，不等同于视觉输入或实机验证。

## 当前状态（2026-10-16）

**{headline}**

{boundary}

{finding} v14及全部旧代码、权重和结果保留。本轮未训练，也未写论文。

{links}

## 启动前端

{START}

页面展示真实五组结果、三目标完成情况、未执行阶段与可下载图表。v15没有新增机器人视频；页面链接的v14视频明确标注历史版本，不冒充本轮成果。

## 导航

- [分类导航](PROJECT_NAVIGATION.md)
- [环境与运行指南](PROGRAM_GUIDE.md)
- [项目状态](STATUS.md)
- [结果索引](RESULTS.md)
- [证据索引](EVIDENCE_INDEX.md)
- [前端演示指南](DEMO_GUIDE.md)
- [写作材料交接](THESIS_HANDOFF_LATEST.md)
- [本轮目录与核验命令]({REL}/README.md)
- [此前README原样快照]({REL}/before/README.md)
''',encoding='utf8')
    (ROOT/'STATUS.md').write_text(f'''# 当前项目状态

**{headline}**

{boundary}

{finding}

{links}

| 检查项 | 本轮状态 |
|---|---|
| 小测试和局部五组消融 | 45次完整执行，原始正负结果全部保留 |
| 保存输入动作/FIFO/噪声回放 | {verification['episodes']}回合、{verification['controls']}步通过 |
| 物理回放 | {physics['episodes']}回合、{physics['steps']}步通过；不新增统计样本 |
| 继承参数 | 97项默认值不变，400步、D2、最多两次及原保护保留 |
| 470次已知条件消融 | 未运行 |
| 开发对照 | v14/v15各240次，共480次；未运行 |
| 全新起点确认 | 1440次计划未运行，起点未生成，未冻结用于确认 |
| 采用 | 完整v15未采用，既有主成果不替换 |
| 泛化训练 / 论文正文 | 均未进行 |

下一步应先缩短经过核验的持物转向路径，解决局部终点IK对旧成功的误拒，再处理箱沿执行跟踪。预算模块的局部改善需要更广对照，尚不能宣称泛化提升。

[此前状态原样快照]({REL}/before/STATUS.md)
''',encoding='utf8')
    (ROOT/'DEMO_GUIDE.md').write_text(f'''# 前端与演示指南

{START}

先看未通过门槛和五组对照，再看三个目标与未执行阶段，最后查看图表CSV和原始结果。主卡片统计8个标准条件，预算专用profile在卡片底部单列。

本轮没有新增v15机器人视频。页面中的[v14原始对比演示](reproduction/improvement_v14_20261016_01/index.html#demo)属于历史v14记录，不能用来声称v15完成任务。仅打开网页不会启动新训练或控制实验。

{links}

[此前演示指南快照]({REL}/before/DEMO_GUIDE.md)
''',encoding='utf8')
    (ROOT/'PROGRAM_GUIDE.md').write_text(f'''# 项目运行指南（当前入口）

**{headline}**

沿用现有 `.venv\\Scripts\\python.exe`，在PyCharm选择它作为解释器。权重与依赖无需替换。

## 启动前端

{START}

## 核验与实验

{finding}

[本轮README]({REL}/README.md)提供只读核验命令。[执行前协议]({REL}/protocols/PLAN.md)定义阶段顺序。`protocols/pilot_jobs.json`是已准备的470次作业，不是实验结果。开发冻结脚本同时检查结果、机制、保存输入和物理核验；本轮小测试失败，不能绕过它生成开发或确认结果。

{links}

早期数据、训练和历史运行步骤保留在[此前指南原样快照]({REL}/before/PROGRAM_GUIDE.md)，请按对应版本使用。
''',encoding='utf8')
    for name,title in [('RESULTS.md','实验结果索引'),('EVIDENCE_INDEX.md','证据索引'),('PROJECT_NAVIGATION.md','项目分类导航'),('THESIS_HANDOFF_LATEST.md','写作材料交接状态')]:
        historical=(RUN/'before'/name).read_text(encoding='utf8')
        extra=('既有跨设备写作包属于此前封存材料，不包含本轮v15。以后写作可把本轮作为消融与失败分析，不得写成已确认的总体提升；本轮不更新论文正文。' if name=='THESIS_HANDOFF_LATEST.md' else '')
        header=f'''# {title} · 当前入口

**{headline}**

{boundary}

{finding}

{links}

{extra}

[本轮逐条件配对表]({REL}/analysis/{stage}_pairs.csv) · [图表与来源]({REL}/figures/CATALOG.json) · [完整度检查]({REL}/verify_integrity.py)

## 历史内容（以下按各自版本和时间解释）

'''
        (ROOT/name).write_text(header+historical,encoding='utf8')
    (ROOT/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={REL}/index.html"><title>CAN LAB · v15诊断</title><a href="{REL}/index.html">打开v15实验报告（未采用）</a></html>',encoding='utf8')
    with (RUN/'document_changes.json').open('x',encoding='utf8') as f:json.dump({'updated':DOCS},f,indent=2)
    print('Updated exactly nine previously backed-up active entries.')
