"""Refresh nine backed-up active entry points after the final assessment."""
from pathlib import Path
import json,re
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
P='reproduction/improvement_v13_20261016_01'

if __name__=='__main__':
    s=json.loads((RUN/'SUMMARY.json').read_text(encoding='utf8'));headline=s['headline']
    d=json.loads((RUN/'analysis/confirmation.json').read_text());n={v:r['success'] for v,r in d['variants'].items()}
    banner=f'> **v13更新（2026-10-16）**：{headline} [报告]({P}/REPORT.md) · [前端]({P}/index.html)。旧代码、权重、结果保留。\n\n'
    link=f'[v13完整报告]({P}/REPORT.md)'
    current=f'''本轮完整阶段共{s['completed_evaluation_executions']}次评估执行，另保留中断批次的17个完成单任务与2个不完整任务。没有泛化训练或论文正文。正式v5冻结证据继续保留；v13与v6/v12的本批比较不能直接证明优于另批v5。

| 阶段 | 结果 | 证据边界 |
|---|---|---|
| 最终小测试 | v12 3/6、S 5/6、R 3/6、v13 6/6 | 已知诊断 |
| 四组消融 | v12 32/50、S 40/50、R 32/50、v13 41/50 | 50执行条件，复用部分起点 |
| 开发 | v6/v12/v13均236/240，无新增退步 | 30固定起点×8条件；没有提高成功率 |
| 独立确认 | v6 {n['v6']}/480、v12 {n['v12']}/480、v13 {n['v13']}/480 | 本轮冻结后60个新起点×8条件，按起点配对统计 |
'''
    startup='''```powershell
Set-Location 'C:\\Users\\Livio\\Desktop\\robot_can'
& '.\\.venv\\Scripts\\python.exe' -m http.server 8766 --bind 127.0.0.1
```

保持终端运行，打开 **http://127.0.0.1:8766/** 。根入口自动跳到v13。已有该端口服务时直接打开，不必重复启动。关闭服务按`Ctrl+C`；另用端口时命令和网址一起修改。
'''
    verify=f'''```powershell
& '.\\.venv\\Scripts\\python.exe' -X utf8 -B {P}/verify_integrity.py
```

只读检查本轮前10982个登记路径、9份活动文档的原样备份、当前交付清单及开发/确认冻结锁。不会训练或仿真。旧verify绑定当时根文档，可能因后续授权更新而提示差异；不要改旧manifest或删除结果绕过检查。
'''
    docs={}
    docs['README.md']=f'''# 动作延迟下的机器人抓取搬运与失败恢复

Panda机械臂在PickPlaceCan仿真中抓取罐子并放入目标箱。BC生成动作块，世界模型预测并评分候选，FIFO执行器施加真实动作延迟；共享恢复控制器处理抓持确认、无进展、失抓和重新搬运。

实验使用含物体真值位置/姿态的23维状态，恢复器另读当前7关节角与固定任务几何。主要协议为20Hz、D=2、400步、最多两次抓取尝试；不是纯视觉或真机实验。

## 在PyCharm启动前端

{startup}

[直接打开v13](http://127.0.0.1:8766/{P}/index.html) · [历史完整展示](reproduction/progress_v11_20261015_01/demo/index.html) · [v12结果](reproduction/improvement_v12_20261015_01/index.html)。

前端是静态HTML/CSS/JavaScript，不需要npm或Node.js。必须在项目根目录启动HTTP服务；启动服务不会运行训练或机器人仿真。视频和曲线均来自保存实验。根路径只出现文件列表通常意味着入口文件缺失或启动了别的目录，请检查工作目录。

## 最新评估

{current}

{link}列出全部失败、统计区间、门槛及核验。v13新增侧倒箱沿/斜靠支撑资格检查，以及长等待后最多一次受检撤退重规划。S同时包含新支撑家族的路径入口；R单独没有提高已知成功数，不能夸大其独立效果。

## 模块与资料

| 入口 | 作用 |
|---|---|
| `common.py` | 创建环境、恢复数据状态、加载BC和打包观测 |
| `train_policy.py`、`policy/` | 动作块BC训练与冻结权重 |
| `collect_rollout_branches.py` | 同状态、历史和延迟队列下采集候选分支 |
| `world_model.py`、`train_world.py`、`models/` | 状态预测与评分训练、冻结权重和历史结果 |
| `evaluate_delay.py` | BC/世界模型延迟闭环评估 |
| `reproduction/extensions_20261012_01/` | 持续性、真值短期排序、H/K实验 |
| `reproduction/recovery_v5_20261012_01/` | 原冻结恢复主线与独立确认 |
| `reproduction/improvement_v6_…`至`improvement_v12_…` | 历史改进、消融与负结果 |
| `{P}/` | 本轮控制器、源码快照、原始轨迹、统计、图表和前端 |
| `data/` | 数据、划分和来源校验 |
| `WORKSPACE/` | 分类导航，原始路径保留 |

[运行指南](PROGRAM_GUIDE.md) · [环境说明](ENVIRONMENT_GUIDE.md) · [结果](RESULTS.md) · [证据索引](EVIDENCE_INDEX.md) · [项目导航](PROJECT_NAVIGATION.md) · [演示讲解](DEMO_GUIDE.md) · [当前状态](STATUS.md)。

## 环境和完整性检查

PyCharm解释器使用`C:\\Users\\Livio\\Desktop\\robot_can\\.venv\\Scripts\\python.exe`。已有环境可以继续使用；显式指定解释器不受终端`(base)`前缀影响。

```powershell
& '.\\.venv\\Scripts\\python.exe' -c "import sys; print(sys.executable); print(sys.version)"
& '.\\.venv\\Scripts\\python.exe' -m pip check
```

{verify}

仿真重跑命令见[本轮README]({P}/README.md)，使用新的阶段目录，不能覆盖既有输出。重复旧起点只算复核，不是新的独立确认。

## 图表、迁移与项目边界

本轮5张图提供600dpi PNG、矢量PDF/SVG、CSV及源哈希，见[图表解释]({P}/FIGURE_GUIDE.md)。平台是等待，折点是原始控制/状态切换；曲线不平滑，成功后按真实终点结束。两段新视频为20fps逐步物理回放。此前36张论文图仍保留在[旧图表包](reproduction/paper_quality_20261015_01/FIGURE_CATALOG.md)。

换设备请使用同步后的完整Git项目。旧ZIP不含v12/v13，单独复制v13目录也缺少继承模块和权重。详见[跨设备说明](THESIS_HANDOFF_LATEST.md)。

项目具备本科毕设的工程与实验材料，仍有恢复失败、规划耗时峰值和有限泛化范围；不能宣称世界模型稳定优于强BC、任意物体泛化或真机安全。正式学校要求、论文正文和答辩仍需另行完成。本轮未写论文。

当前README更新于2026-10-16；修改前原样文件在`{P}/before/README.md`。所有旧算法、权重、结果及历史页面保留。
'''
    docs['PROGRAM_GUIDE.md']=f'''# 项目运行与模块指南

更新：2026-10-16。项目根`C:\\Users\\Livio\\Desktop\\robot_can`，解释器`.venv\\Scripts\\python.exe`。

## 1. 展示已有成果

{startup}

最新页面：[v13]({P}/index.html)。展示包含最终小测试、四组消融、240开发、1440配对确认、两段同起点视频和五张新图。历史v12及完整世界模型/v5展示从页面导航进入。

## 2. 不运行实验的完整性核验

{verify}

## 3. 本轮实验复核入口

冻结代码在`{P}/recovery/`，各阶段同时保存source快照。原始结果和trace位于smoke_a/c/d/e、pilot_a、dev_a、confirmation；smoke_b为保留的中断记录。

新的重复执行目录示例：

```powershell
& '.\\.venv\\Scripts\\python.exe' -X utf8 -B {P}/run_batch.py --stage smoke_repeat_01 --jobs protocols/smoke_jobs.json --workers 4
& '.\\.venv\\Scripts\\python.exe' -X utf8 -B {P}/verify_run.py --stage smoke_repeat_01
& '.\\.venv\\Scripts\\python.exe' -X utf8 -B {P}/verify_physics.py --stage smoke_repeat_01
```

完整开发/确认重复可分别使用`protocols/dev_jobs.json`、`protocols/confirmation_jobs.json`，阶段名必须未存在。重复执行改变本轮交付目录后，交付清单不会自动覆盖新增文件；原封存资料继续有效，新增复核应单独登记。不要再次运行原确认生成器或覆盖原analysis。重复旧起点不是新的独立确认。

## 4. 算法和数据流

`common.py`创建仿真并读取23维真值状态 → 冻结BC输出动作块 → BC k=2固定选第三项或Full对四个候选评分 → 共享恢复监督器按可行性/抓持证据选择动作 → D2 FIFO出队并施加动作噪声 → 仿真一步并记录。成功标签只用于评估终止，不参与控制选择。

恢复器额外使用当前7关节角和已知几何。S为支撑识别加新候选路径；R为长等待有界撤退/重规划。控制器不因未知可行性默认下降。400步包括规划等待和恢复，时钟不会重置。

## 5. 环境、历史与迁移

[环境指南](ENVIRONMENT_GUIDE.md)保留实际版本和兼容说明。`requirements-repro.txt`是旧建议，不是当前完整可移植锁文件。看视频无需重装仿真环境。

[完整结果](RESULTS.md) · [证据索引](EVIDENCE_INDEX.md) · {link} · [旧v5README](reproduction/recovery_v5_20261012_01/README.md)。旧代码依赖和历史结果不得删掉。本轮没有训练或论文；换设备使用完整仓库，详见[交接说明](THESIS_HANDOFF_LATEST.md)。
'''
    docs['STATUS.md']=f'''# 项目当前状态（2026-10-16 v13）

{current}

{link}提供主要配对区间、逐条件退步/救回和失败列表。完成执行不等于性能门槛通过，不能把已知诊断收益当成独立泛化收益。

- 原世界模型：三种子公平开发1800回合、独立确认840回合，历史结论见[结果](RESULTS.md)。
- 持续性、真值短期排序、H/K补充900回合已经完成。
- v5原冻结主线、v6—v12全部改进和负结果保留。本轮没有删除或替换旧权重。
- v13所有完整阶段决策核验和规定物理回放完成；前端视频、图表与完整性检查分别保留回执。
- 没有泛化训练，没有论文正文；跨设备干净安装/真机验证仍未完成。

待改进：剩余几何/路径不可行与失抓后的可达性、400步内的恢复余量、规划峰值耗时；先按失败首个分歧做诊断，不直接放松可行性阈值。后续修改应放新目录并使用另一批未查看确认起点。

[当前前端]({P}/index.html) · [只读完整性检查]({P}/verify_integrity.py) · [图表解释]({P}/FIGURE_GUIDE.md) · [历史全仓审查](reproduction/project_audit_20261015_01/REPORT.md)。
'''
    docs['DEMO_GUIDE.md']=f'''# 演示启动与讲解顺序

{startup}

1. 打开[v13页面]({P}/index.html)，先说明400步、D2、20Hz及冻结权重。
2. 核对四阶段结果。小测试和消融是已知诊断；开发30起点；独立确认60新起点，每个起点八个关联条件。
3. 播放“斜靠物体”对比：Full s23、噪声0.05；v13在391步完成，时间余量仍窄。再播放“侧倒箱沿”：BC k=2干净；v13在291步完成。这两例预先选自已知失败，不能替代确认统计。
4. 看独立确认表、配对区间及报告。按门槛如实讲解救回和新增失败，不只展示成功视频。
5. 阅读[曲线解释]({P}/FIGURE_GUIDE.md)：等待平台、抬升/放置高度变化、开度折点均为原始轨迹；图不平滑、成功终点不延长。
6. 从顶部进入[v12历史成果](reproduction/improvement_v12_20261015_01/index.html)及[完整世界模型/v5展示](reproduction/progress_v11_20261015_01/demo/index.html)。不同批起点不得直接比较成功数。

BC k=2选动作块第三项，不读取真实未来；噪声0.05作用在出队动作前三个归一化分量，不是5厘米物体位置噪声。S/R共享恢复不是世界模型训练。输入是真值状态，支撑筛查不等于全臂安全证明。

两段新视频为960×660、20fps、421帧，每个控制步一帧，成功后保持终点便于对照；已做保存动作物理回放、全文件解码和浏览器播放检查。没有用视频插值掩盖动作振荡，也没有验证任意设备负载下的无丢帧性能。
'''
    # Historical scientific reports remain intact under an explicit dated section.
    for name in ['RESULTS.md','EVIDENCE_INDEX.md','PROJECT_NAVIGATION.md']:
        old=(RUN/'before'/name).read_text(encoding='utf8')
        old=re.sub(r'^> \*\*v12更新[^\n]*\n\n','',old)
        old=old.replace('本轮','该历史阶段').replace('当前展示','历史展示').replace('当前校验','历史校验')
        if name=='RESULTS.md':prefix=f'# 实验结果总览（更新至v13）\n\n{current}\n{link}，配对原始记录见[{P}/analysis/confirmation_pairs.csv]({P}/analysis/confirmation_pairs.csv)。恢复控制与世界模型收益分别评价。\n'
        elif name=='EVIDENCE_INDEX.md':prefix=f'''# 当前证据索引

[v13前端]({P}/index.html) · {link} · [当前校验]({P}/verify_integrity.py) · [图表目录]({P}/figures/CATALOG.json)。

| 本轮内容 | 权威记录 |
|---|---|
| 执行前门槛 | [PLAN]({P}/protocols/PLAN.md) |
| 完整与中断执行台账 | [inventory]({P}/analysis/execution_inventory.json) |
| 小测试及四组消融 | [smoke_e]({P}/analysis/smoke_e.json)、[pilot_a]({P}/analysis/pilot_a.json) |
| 240开发 | [dev_a]({P}/analysis/dev_a.json) |
| 60新起点、1440配对执行 | [统计]({P}/analysis/confirmation.json)、[配对CSV]({P}/analysis/confirmation_pairs.csv) |
| 冻结与初态复核 | [锁]({P}/protocols/confirmation_lock.json)、[初态]({P}/analysis/confirmation_state_validation.json) |
| 剩余失败与耗时 | [diagnosis]({P}/analysis/confirmation_diagnosis.json) |
| 历史v12 | [报告](reproduction/improvement_v12_20261015_01/REPORT.md) |
'''
        else:prefix=f'''# 项目总导航

- 最新实现、结果和视频：[{P}/]({P}/README.md)。
- 直接查看：[v13前端]({P}/index.html)；总报告：{link}。
- 启动与复核：[README](README.md)、[PROGRAM_GUIDE](PROGRAM_GUIDE.md)、[DEMO_GUIDE](DEMO_GUIDE.md)。
- 全阶段证据：[EVIDENCE_INDEX](EVIDENCE_INDEX.md)、[RESULTS](RESULTS.md)。
- 跨设备：[THESIS_HANDOFF_LATEST](THESIS_HANDOFF_LATEST.md)。旧包不含v12/v13，使用完整同步项目。
- 旧路径未移动；分类入口仍在[WORKSPACE](WORKSPACE/index.html)。
'''
        docs[name]=prefix+'\n## 历史记录（截至2026-10-15；按原批次解释）\n\n'+old
    docs['THESIS_HANDOFF_LATEST.md']=f'''# 跨设备资料交接（2026-10-16）

最新资料为{link}及其源数据、五张新图和两段视频。本轮没有论文正文，也没有改写旧论文提纲；后续写作需将本轮结论和负结果补入相应实验章节，不能沿用旧提纲中停在v11/v12的状态描述。

**旧ZIP不包含v12和v13。换设备请使用同步后的完整Git项目，或完整复制robot_can项目（虚拟环境需在新设备重新配置）。只复制v13目录无法运行继承的v5—v12模块，也缺少数据与冻结权重。** GitHub入口：https://github.com/LuckyLivio/Robot_can 。

| 内容 | 路径 |
|---|---|
| 本轮整体评估 | [{P}/REPORT.md]({P}/REPORT.md) |
| 最新实现与原始轨迹 | `{P}/recovery/`、各阶段`result.json`与`trace.jsonl` |
| 配对数据与统计 | `{P}/analysis/confirmation_pairs.csv`、`confirmation.json` |
| 新图、图注、CSV | [图表说明]({P}/FIGURE_GUIDE.md)、`{P}/figures/` |
| 视频与回放验证 | `{P}/demo/`、`analysis/demo_replay_*.json` |
| 旧详细提纲与36张图 | [提纲](reproduction/paper_quality_20261015_01/THESIS_OUTLINE_REVIEWED.md)、[图目录](reproduction/paper_quality_20261015_01/FIGURE_CATALOG.md) |
| 原始迁移包 | [说明](reproduction/portable_delivery_20261015_01/README.md) |

旧迁移包的本机移位、标准库环境和前端检查属于历史验收，不能声称新设备已经验证。新设备先按[环境指南](ENVIRONMENT_GUIDE.md)配置，再按[运行指南](PROGRAM_GUIDE.md)检查；使用`verify_integrity.py`做字节核验。当前完整成果以v13报告为准，旧包只作历史资料。

写作边界：60独立起点不等于480独立样本；共享恢复收益不归因于世界模型；真值状态不等于视觉感知；不同确认批次不直接拼接。旧v5冻结证据和所有失败结果保留。本科毕设工程材料已较完整，论文论证、学校格式和答辩准备尚需完成。
'''
    expected=json.loads((RUN/'document_changes.json').read_text())['updated']
    assert set(docs)==set(expected)-{'index.html'}
    for name,body in docs.items():
        assert (RUN/'before'/name).is_file();(ROOT/name).write_text(banner+body,encoding='utf8')
    (ROOT/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={P}/index.html"><title>CAN LAB</title><a href="{P}/index.html">打开v13成果页面</a></html>',encoding='utf8')
    readme=f'''# v13：侧倒箱沿、斜靠支撑与有界重规划

{headline}

[整体评估](REPORT.md) · [前端](index.html) · [执行前协议](protocols/PLAN.md) · [图表解释](FIGURE_GUIDE.md) · [执行台账](analysis/execution_inventory.json)。

全部旧代码、权重和结果保留；400步、20Hz、D2、最多两次抓取尝试不变。没有泛化训练和论文正文。v13继承v5—v12，迁移时需要完整项目。

在robot_can根目录的PyCharm PowerShell终端启动：

{startup}

直达：http://127.0.0.1:8766/{P}/index.html 。

## 只读完整性检查

{verify}

## 重复复核（会运行仿真）

运行器拒绝覆盖已有目录。使用新阶段名，例如：

```powershell
& '.\\.venv\\Scripts\\python.exe' -X utf8 -B {P}/run_batch.py --stage smoke_repeat_01 --jobs protocols/smoke_jobs.json --workers 4
& '.\\.venv\\Scripts\\python.exe' -X utf8 -B {P}/verify_run.py --stage smoke_repeat_01
& '.\\.venv\\Scripts\\python.exe' -X utf8 -B {P}/verify_physics.py --stage smoke_repeat_01
```

开发与确认的已锁任务分别是`protocols/dev_jobs.json`和`protocols/confirmation_jobs.json`。重复旧确认起点只算复核，不能算另一批独立实验。不要覆盖旧分析、源码快照、清单或冻结锁。

五张图有600dpi PNG、PDF/SVG、CSV和来源SHA256；两个20fps视频逐保存动作物理回放。验证记录在`validation/`。中断的smoke_b及所有未通过迭代保留，不计作完整阶段通过证据。旧写作ZIP不含本轮，请使用同步后的完整仓库。
'''
    (RUN/'README.md').write_text(readme,encoding='utf8');print('Updated 9 active entry points and v13 README; prior bytes remain in before/.')
