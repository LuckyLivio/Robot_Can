"""Update active guides only; immutable experiment reports and handoff stay untouched."""
from pathlib import Path
import json,csv,html,re
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
AUD='reproduction/project_audit_20261015_01'
LATEST='reproduction/progress_v11_20261015_01/demo/index.html'
modified=[]
def put(name,text):
    p=ROOT/name
    if p.exists():assert (RUN/'before'/name).is_file(),name
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.strip()+'\n',encoding='utf8');modified.append(name)
def old(name):return (RUN/'before'/name).read_text(encoding='utf8')

def main():
    put('STATUS.md',f'''# 项目当前状态（2026-10-15审查版）

冻结展示主线为v5；最新开发候选为v11，未采用。当前完整结论见[全项目检查报告]({AUD}/REPORT.md)，逐项见[清单]({AUD}/CHECKLIST.csv)。

- 原世界模型：三种子开发1800回合、独立确认840回合；Full联合增益为+4.72个百分点，排序相对Plain的独立优势仍不确定。
- 补充持续性、真值短期排序、H/K共900回合，已经完成，不是缺项。
- v5：开发236/240、独立原生确认464/480；两次原生确认不能跨批直接相减。
- v6—v10保留全部探索、失败与消融；未过门槛的阶段不启动下一阶段属于按协议停止。
- v11：小测试9、消融148、开发240，共397次执行；已知箱沿380步完成，开发235/240低于v6的236/240，未进入独立确认。
- v7早期pilot_a有序列化中断，后续pilot_b已完整重启148回合；不把3份running结果算成完整实验。

本轮全仓文件/数据/权重/视频/统计检查通过，已更新活动文档和导航；未新增训练或仿真。旧代码、权重、结果、写作包与失败记录保留。

待办：持物等待分支的状态切换；当前设备以外的干净安装验收；最新迁移增补包；更直接的相关工作阅读、正式论文和学校格式。详见[分优先级计划]({AUD}/IMPROVEMENT_PLAN.md)。单任务、低维真值、固定BC与有限延迟范围继续如实限定。

当前[前端]({LATEST})；最新[只读检查入口]({AUD}/verify.py)。历史根文档的原样备份在本轮before目录。''')
    put('PROGRAM_GUIDE.md',f'''# 当前项目运行与模块指南

更新：2026-10-15。项目根为 `C:\\Users\\Livio\\Desktop\\robot_can`，PyCharm解释器为 `.venv\\Scripts\\python.exe`。

## 先看成果

```powershell
Set-Location 'C:\\Users\\Livio\\Desktop\\robot_can'
& '.\\.venv\\Scripts\\python.exe' -m http.server 8766 --bind 127.0.0.1
```

保持终端运行，打开 **http://127.0.0.1:8766/** 。根入口自动跳到[v11当前展示]({LATEST})。若端口已有本项目服务，直接使用。前端是静态文件服务，不会运行机器人或训练。

全项目[审查页面]({AUD}/index.html)与[分类导航](WORKSPACE/index.html)另行提供。当前展示保留v5主结果，v11仅作为未采用候选。

## 只读完整性检查

```powershell
& '.\\.venv\\Scripts\\python.exe' -X utf8 -B reproduction\\project_audit_20261015_01\\verify.py
```

验证审查前10,146个登记文件：授权改动的活动文档按before原样备份核对，其他文件在原位置核对；另验当前交付清单。不训练、不创建环境、不物理回放。历史verify绑定当时根文档，可能因后续授权文档更新失败；不要改旧manifest或删除结果绕过检查。

## 环境与模型

```powershell
& '.\\.venv\\Scripts\\python.exe' -m pip check
```

当前版本、CUDA和主权重前向已核对，见[环境指南](ENVIRONMENT_GUIDE.md)。`requirements-repro.txt`是旧建议，不是当前可移植锁文件。看已有视频无需重装仿真环境。

## 模块与入口选择

| 模块 | 用途 |
|---|---|
| common.py | 数据/23维观测、BC加载、控制器和传感器状态恢复 |
| collect_rollout_branches.py | 同历史/同FIFO候选采集 |
| world_model.py / train_world.py | 残差动力学、进展/失抓头、排序；根训练入口为历史入口 |
| reproduction/multiseed_20261012_01/train_suite.py | 匹配三种子与公平训练 |
| reproduction/confirmation_20261012_01/ | 冻结世界模型确认协议与结果 |
| reproduction/recovery_v5_20261012_01/ | 当前冻结恢复主线与精确状态重跑包装 |
| reproduction/improvement_v6_… 至 v11_… | 分离候选与负结果，不能自动视为已采用 |
| reproduction/progress_v11_20261015_01/demo/ | 当前展示、历史视频和v11新视频 |

33个根Python入口包含旧探索路线。不要逐个按默认参数运行来“验收整个项目”：例如evaluate_delay默认候选数、门限与冻结主协议不同。旧任务JSON含本机命令路径，迁移时需新包装器处理，保留旧协议。

完整v5重跑命令在[v5 README](reproduction/recovery_v5_20261012_01/README.md)。这些命令会仿真且拒绝覆盖；只读审查不执行它们。重跑必须新输出目录，已看过的起点重复执行不称独立确认。新机器方案见[调整计划]({AUD}/IMPROVEMENT_PLAN.md)。''')
    put('PROJECT_AUDIT.md',f'''# 全项目适用性与完整度评估（2026-10-15）

**主实验资产完整，适合以系统设计与实验分析为定位开展本科论文；尚未达到通用、稳定或无失败的机器人系统。** 学校任务书未提供，最终题目与格式需导师认可。

[详细检查报告]({AUD}/REPORT.md) · [逐项清单]({AUD}/CHECKLIST.csv) · [后续方案]({AUD}/IMPROVEMENT_PLAN.md) · [清理建议]({AUD}/CLEANUP.md)

本轮盘点10,146个Git文件，检查891份Python、3983份JSON、1358份JSONL/2335802行、684个权重路径及全部受管理图像/视频。重新核对主线2640条记录和42项置信区间；环境、BC与6个世界模型前向通过。全量原始文件哈希、各项机器凭据见报告目录。

发现并处理：活动文档/旧前端/历史校验入口混用；迁移包范围未突出；导航未覆盖v6—v11。旧文档原样备份，旧实验未改。v7中断pilot_a已有完整pilot_b替代，不计作主实验遗漏。

当前主要缺口：v11继承的持物等待状态转换；世界模型开发泛化与排序增益不稳定；目标电脑干净安装未验证；旧写作包不含v6—v11；正式论文与学校格式未完成。v11开发235/240低于v6的236/240，主版本仍v5（确认464/480）。

检查不是对所有历史运行路径的形式化证明；本轮未新增训练、闭环实验或物理重演。可再生缓存约38KB、Git临时对象约2.68MiB只是清理候选，原始轨迹/权重/失败记录不是垃圾。''')
    put('EVIDENCE_INDEX.md',f'''# 当前成果与版本索引（2026-10-15）

[当前展示]({LATEST}) · [当前校验]({AUD}/verify.py) · [全仓审查]({AUD}/REPORT.md) · [结果](RESULTS.md) · [贡献](CONTRIBUTIONS.md) · [统计](STATISTICS.md)

| 阶段 | 完成情况与使用边界 | 权威入口 |
|---|---|---|
| 数据/队列/真值/评分诊断 | 开发与机制定位，非独立确认 | [队列](reproduction/queuepair_20261012_01/)、[真值](reproduction/candidate_truth_20261012_01/)、[校准](reproduction/headcal_20261012_01/) |
| 三种子公平消融 | 60组1800开发回合 | [报告](reproduction/multiseed_20261012_01/analysis/report.txt) |
| 原世界模型确认 | 840回合、60起点，无共享恢复 | [报告](reproduction/confirmation_20261012_01/analysis/report.txt) |
| 补充实验 | 持续性/oracle/H/K，900回合，已经完成 | [报告](reproduction/extensions_20261012_01/REPORT.md) |
| v1—v4 | 恢复探索、已有四组对照及负结果 | [四组汇总](reproduction/consolidation_20261012_01/FACTORIAL_REVIEW.md) |
| v5主线 | 开发236/240，确认464/480，压力12/16 | [评估](reproduction/recovery_v5_20261012_01/ASSESSMENT.md) |
| v6候选 | 开度/重复下降，开发236/240，未采用 | [报告](reproduction/improvement_v6_20261015_01/REPORT.md) |
| v7候选 | 最终30/37；pilot_a中断，pilot_b完整 | [报告](reproduction/improvement_v7_20261015_01/REPORT.md) |
| v8候选 | 两轮五路消融均未通过门槛 | [报告](reproduction/improvement_v8_20261015_01/REPORT.md) |
| v9候选 | 关节姿态与耗时；坐标系修订有记录 | [报告](reproduction/improvement_v9_20261015_01/REPORT.md) |
| v10候选 | 箱沿高度/路径，最终30/37 | [报告](reproduction/improvement_v10_20261015_01/REPORT.md) |
| v11候选 | 31/37；开发235/240；箱沿救回，整体未采用 | [报告](reproduction/improvement_v11_20261015_01/REPORT.md) |
| 图表深查 | 固定集泛化、评分敏感性与原始图替代表达 | [报告](reproduction/figures_deepcheck_20261014_01/REPORT.md) |
| 写作迁移 | c8bbe86历史包，非v11最新整包 | [当前交接说明](THESIS_HANDOFF_LATEST.md) |

所有实验目录的protocol/design/study_plan/lock保留执行前字节；负结果及未启动阶段不删除。历史报告按当时范围阅读，不拿旧“尚未完成”覆盖后来的记录。RESULTS_TABLE.csv是早期历史表，当前结果以本索引链接的配对记录为准。ADAPTIVE_PROTOCOL是另一条历史探索线。

全文件和逐结果台账：[FILE_INVENTORY]({AUD}/FILE_INVENTORY.csv)、[RESULT_LEDGER]({AUD}/RESULT_LEDGER.csv)。''')
    put('THESIS_HANDOFF_LATEST.md',f'''# 当前论文资料交接说明（2026-10-15）

旧 `THESIS_HANDOFF_20261015/` 与两份ZIP校验通过，精确对应提交c8bbe86；包括原世界模型与v5主线、40张表、19组图和详细提纲。**它不包含后续v6—v11，不能仅凭日期认为已经是最新。**

写作先读[最新审查]({AUD}/REPORT.md)、[当前贡献](CONTRIBUTIONS.md)、[当前结果](RESULTS.md)、[当前提纲](THESIS_OUTLINE.md)，再使用[旧详细提纲](THESIS_HANDOFF_20261015/01_outline/THESIS_OUTLINE_REVISED.md)和图表；以各自批次/分母为准。

旧包里的652份gzip与本地两个ZIP被Git本机排除，不随克隆提供；原始JSONL在主仓库原路径。克隆可以获取旧包非压缩资料，完整包校验需要另外复制FULL ZIP或gzip目录。不要把Git克隆中的旧包称为完整日志独立包。

本次新增审查文件夹可作为最新文字增补；v6—v11原始数据仍在各reproduction目录，没有重打包覆盖旧ZIP。后续建立单独增补发行包、验证新设备，再开始正式写作，具体见[计划]({AUD}/IMPROVEMENT_PLAN.md)。

本轮没有论文正文。''')
    put('ENVIRONMENT_GUIDE.md',f'''# 当前环境、冻结版本与新设备说明

更新：2026-10-15。PyCharm使用项目 `.venv\\Scripts\\python.exe`。本轮实测Python3.10.9、torch2.14.1+cu130、NumPy1.26.4、robosuite1.5.1、MuJoCo3.3.0、h5py3.11.0、SciPy1.15.3。pip check通过；RTX5080 Laptop CUDA可用且小张量计算通过；BC及Full/Plain各三种子在一个保存观测上前向通过。

[本轮环境与推理凭据]({AUD}/environment_and_inference.json) · [完整pip快照]({AUD}/environment-freeze-current.txt)。这是实际环境快照，不是已验证可在任意机器安装的锁文件。本轮没有新建环境或运行闭环机器人。

`requirements-repro.txt`保留历史安装建议，其torch2.9.1注释不是实际冻结版本。不要按旧注释降级当前环境；新设备需核对该设备系统、GPU和可用包，再在新环境验证。[新设备方案]({AUD}/IMPROVEMENT_PLAN.md)

Windows兼容记录在 `data/windows_compatibility.json`；setup_windows.py会写项目虚拟环境中的DLL/WGL配置，已工作环境看演示不需要反复执行。不把.venv直接复制到另一台电脑。

原示范来源与SHA见[data manifest](data/can_ph_lowdim_v15.manifest.json)。BC主权重为 `policy/bc_chunk_dev_v4/policy_15000.pt`，Full/Plain为 `models/multiseed_20261012_01_{{full,plain}}_s{{17,23,41}}/model.pt`。原用户model.pt存于 `models/full_future_delay2_shift_v0/model.pt`；它保留为早期模型，并非当前三种子模型。两份导入权重均与最初替换凭据的SHA一致；桌面原文件目前不在该路径，不能重新直接比对桌面副本。

前端已有视频只需标准库HTTP服务；生成新视频另需ffmpeg和渲染依赖。历史任务JSON含原机器命令路径，新机器不能原样照搬命令数组。''')
    put('DEMO_GUIDE.md',f'''# 当前成果展示与讲解顺序

更新：2026-10-15。[当前页面]({LATEST})，启动命令见[PROGRAM_GUIDE](PROGRAM_GUIDE.md)。根网址 http://127.0.0.1:8766/ 自动跳转；历史页面保留。

1. 先看最新进展：主版本v5，v11仅为候选；明确31/37诊断与235/240开发是不同批次。
2. 看v10/v11箱沿对比：同状态BC k=2、噪声0.05，v11在380步完成；20fps逐控制步回放，成功后保持终点。单个已知案例不能证明泛化。
3. 展开240开发表和持物等待失败图，解释为何v11没有采用。
4. 介绍原世界模型：D2/100ms、四候选、H8含队列前缀、k2回退。原始BC/Full/Plain六段视频固定seed17，统计包含三种子；当前重新渲染的视频为20fps。
5. 展示原840回合确认及900回合补充诊断；Full有局部收益，但不声称排序稳定击败Plain。
6. 展示v5独立确认464/480；v4/v5日志动画是观测轨迹，不是新实机/三维视频。历史v6/v8恢复视频提供Full17/23/41及BC案例，明确版本。
7. 看贡献边界、失败与[全项目检查]({AUD}/REPORT.md)。

BC k=2选预测动作块第3项，不读取真实未来。噪声0.05施加于出队的前三个归一化动作分量，不是5cm物体噪声。世界模型风险头不等于碰撞概率，门限不是校准不确定性。共享恢复是规则控制，不是新世界模型训练。

视频/轨迹都来自保存记录；不以播放插值改变成功率，未测量当前浏览器全部负载下的丢帧率，不保证真实运动无振荡。v11[回放核验](reproduction/progress_v11_20261015_01/edge_replay_validation.json)、历史[20fps核验](reproduction/progress_20261015_01/original_20fps_validation.json)。''')
    put('REPRODUCTION_PLAN.md',f'''# 当前复核与交付计划

更新：2026-10-15。主线已完成数据/权重检查、队列一致性、三种子公平消融、原世界模型确认、900回合补充、v1—v5恢复确认及v6—v11候选研究。按阶段见[EVIDENCE_INDEX](EVIDENCE_INDEX.md)。

本轮仅作全仓审查、现有统计复算和文档整理，不新增闭环实验。主版本仍v5；v11开发未达门槛，不能进入新的独立确认。

当前优先级：文档/导航统一（完成）；最新迁移增补包与目标设备验收；若继续算法改进，先修持物等待状态，再单独考虑数据覆盖与泛化。[完整计划和验收门槛]({AUD}/IMPROVEMENT_PLAN.md)

只读验收见[PROGRAM_GUIDE](PROGRAM_GUIDE.md)。旧回合重放、重新训练和新起点确认是不同任务，不能混称。全部旧协议与失败结果保留。''')
    s=old('README.md');s=f'> 全项目审查已完成：[详细报告]({AUD}/REPORT.md) · [检查清单]({AUD}/CHECKLIST.csv) · [调整计划]({AUD}/IMPROVEMENT_PLAN.md)。未新增训练或仿真。\n\n'+s
    s=s.replace('reproduction\\improvement_v11_20261015_01\\verify_integrity.py',f'reproduction\\project_audit_20261015_01\\verify.py').replace('9,787 个路径','10,146 个路径')
    s=s.replace('授权修改的根 README 和入口页面按逐字节备份验证','本轮授权更新的活动文档和分类入口按逐字节备份验证')
    s+='\n最新迁移说明：[THESIS_HANDOFF_LATEST.md](THESIS_HANDOFF_LATEST.md)。旧写作包是c8bbe86历史快照，完整包ZIP和gzip不随Git克隆提供。\n'
    put('README.md',s)
    s=old('RESULTS.md');s='> 更新说明（2026-10-15）：原主线数值不变，新增候选版本汇总见文末；主版本仍v5。\n\n'+s
    s+='''\n## 后续候选v6—v11（2026-10-15）

| 候选 | 最终已知诊断 | 开发 | 采用情况 |
|---|---:|---:|---|
| v6 | 31/37 | 236/240 | 无净增，未采用 |
| v7合用 | 30/37 | 未启动 | 未过门槛 |
| v8合用 | 30/37 | 未启动 | 未过门槛 |
| v9合用 | 30/37 | 未启动 | 未过门槛 |
| v10合用 | 30/37 | 未启动 | 未过门槛 |
| v11合用 | 31/37 | 235/240 | 未采用；箱沿局部救回，继承等待退步 |

以上为反复使用的诊断/开发条件，不是新独立确认；不替换前文v5主结果。逐组证据见[EVIDENCE_INDEX](EVIDENCE_INDEX.md)。
''';put('RESULTS.md',s)
    s=old('CONTRIBUTIONS.md');s='> 当前审查（2026-10-15）：三项主要贡献定位不变。v6—v11补充机制和失败证据，未形成新的稳定整体收益。\n\n'+s
    s+=f'\n## 后续候选的定位\n\nv11箱沿案例完成，但开发235/240低于v6的236/240；未知等待与持物状态衔接仍有缺陷。把它用于受控改进和失败分析，不称全面解决恢复。部分后续监督器读取当前7关节，BC/WM输入仍23维；不要把v5的输入说明套到所有后续版本。[创新/使用价值审查]({AUD}/REPORT.md)\n';put('CONTRIBUTIONS.md',s)
    s=old('THESIS_OUTLINE.md');s='> 2026-10-15复查：主文仍以原世界模型确认和v5恢复确认为主；v6—v11用于局部机制与负结果分析。详细旧提纲的版本边界见[当前交接说明](THESIS_HANDOFF_LATEST.md)。\n\n'+s
    s=s.replace('7. 时间救回、侧倒救回、失抓失败和角落退步；真实已有视频/日志与逐步物理回放证据。','7. 时间救回、侧倒救回、失抓失败和角落退步；真实已有视频/日志与逐步物理回放证据。\n8. 可选附录：v6—v11受控诊断、箱沿380步局部修复、235/240开发退步及持物等待状态转换。不得把11个版本列为11项独立创新。')
    s=s.replace('[当前演示](reproduction/consolidation_20261012_01/demo/index.html)',f'[当前演示]({LATEST})');put('THESIS_OUTLINE.md',s)
    s=old('STATISTICS.md');s+='\n## 2026-10-15补充口径\n\nv11的37条件是已知诊断；240开发为30起点×8种执行条件，不是240独立起点。397新执行包括小测试和消融，不包含核验回放。其决策耗时含BC/WM选择和监督器，仍不含完整物理/渲染链路；与早期仅选择器计时不可直接当等价实时基准。\n';put('STATISTICS.md',s)
    s=old('PROTOCOL.md').replace('| 最新恢复 |','| 冻结恢复主线 |');s+=f'\n## 后续候选与当前审查\n\nv6—v11各有独立协议，见[EVIDENCE_INDEX](EVIDENCE_INDEX.md)。最新[v11计划](reproduction/improvement_v11_20261015_01/protocols/PLAN.md)与[开发冻结](reproduction/improvement_v11_20261015_01/protocols/development_freeze.json)保留原字节。本轮审查不新增实验、不修改历史门槛；[当前报告]({AUD}/REPORT.md)。\n';put('PROTOCOL.md',s)
    s=old('DELAY_PROTOCOL.md');s+='\n## 后续版本输入边界（2026-10-15）\n\n上述23维为策略/世界模型输入，v5恢复也沿用这些观测。v9—v11的关节姿态验证额外读取当前7关节，BC和Full公平共享；并非新增世界模型输入或视觉感知。当前候选状态见[STATUS](STATUS.md)。\n';put('DELAY_PROTOCOL.md',s)
    s=old('SUPPLEMENTAL_RESULTS.md').replace('后续共享恢复已发展至v5','冻结共享恢复主线为v5，后续v6—v11为未采用候选');put('SUPPLEMENTAL_RESULTS.md',s)
    s=old('RELATED_WORK.md');s+='''\n## 2026-10-15直接相关研究补查

以下只补项目定位，未生成新的BibTeX或声称阅读全文：

- [Real-Time Execution of Action Chunking Flow Policies（RTC）](https://www.pi.website/download/real_time_chunking.pdf)：官方论文摘要及首页机制说明已核查；通过冻结必然执行的动作前缀、生成后续动作处理异步推理。当前固定D2、低维BC候选评分不同于流策略inpainting，但“考虑待执行前缀”本身不是首创。
- [Real-Time Robot Execution with Masked Action Chunking（REMAC）](https://arxiv.org/abs/2601.20130)：官方摘要/元信息已核查；讨论异步执行中块内不一致与前缀保持。当前系统未实现该训练机制，不与其跨平台成功率直接排名。
- [Recovery RL](https://arxiv.org/abs/2010.15920)官方摘要复核：任务与恢复策略分离已有直接相关工作；本项目规则状态机不等同于安全评论器和学习恢复策略。

正式写作仍需阅读直接相关方法与假设，不以网页核查代替完整文献工作。当前工程与诊断贡献见[全仓审查](reproduction/project_audit_20261015_01/REPORT.md)。
''';put('RELATED_WORK.md',s)
    s=old('GITHUB_UPLOAD.md').replace('.\\reproduction\\github_upload_20261015_01\\verify.py','.\\reproduction\\project_audit_20261015_01\\verify.py')
    s=s.replace('本次为上传补充 `.gitignore`，并更新 README 的当前校验入口，改前文件逐字节保存在上述目录；旧校验清单不改写。新入口映射授权修改的两个文件后核对原始资产。旧环境中已存在的 DEMO_GUIDE.md 历史差异仍会单独报告。','当前入口校验审查前10,146个受管理路径；本轮活动文档更新映射到before备份，其他旧文件保持原路径，历史清单不改写。')
    s+='\n## 当前发布边界（2026-10-15）\n\n主仓库已有v11及完整原始JSONL，受管理文件约8.99 GiB，Git对象另占约1.42 GiB。旧写作包内652份gzip和本地两份ZIP被.git/info/exclude排除，不会随克隆出现；使用完整迁移包须另外传输FULL ZIP。当前恢复主版本仍v5，v11开发未采用。[当前资料交接](THESIS_HANDOFF_LATEST.md)。\n';put('GITHUB_UPLOAD.md',s)
    s=old('DELIVERY_CHECKLIST.md');s='> 2026-10-15更新：原主线与v6—v11已全面盘点；本文区分已具备与正式交付事项。\n\n'+s
    s+=f'\n## 当前新增收尾项\n\n- [ ] 目标电脑干净安装/展示验收；当前仅单机环境与前向核对通过。\n- [ ] 新建v6—v11增补迁移包，旧c8bbe86写作包不覆盖。\n- [ ] 若继续优化，单独修持物等待，维持400步并按门槛验证；不是本轮已完成项。\n- [ ] 作者选择自有代码许可，补第三方来源清单。\n- [x] 全仓原始资产、数据格式、视频、既有统计和写作包完整性检查；活动文档/导航已统一。\n\n[详细清单]({AUD}/CHECKLIST.csv) · [优先级计划]({AUD}/IMPROVEMENT_PLAN.md)。\n';put('DELIVERY_CHECKLIST.md',s)
    s=old('PROJECT_NAVIGATION.md').replace('[原项目3,946份文件分类索引](WORKSPACE/FILE_INDEX.csv)',f'[当前审查前10,146文件索引]({AUD}/FILE_INVENTORY.csv)；[旧3,946文件快照分类](WORKSPACE/FILE_INDEX.csv)')
    s=s.replace('- [论文迁移材料](THESIS_HANDOFF_20261015/00_READ_FIRST.md)','- [当前论文交接说明](THESIS_HANDOFF_LATEST.md)；[旧迁移包](THESIS_HANDOFF_20261015/00_READ_FIRST.md)')
    s=s.replace('图表优先看迁移包的详细图注；原根THESIS_OUTLINE.md作为历史保留，新写作使用迁移包内修订提纲。','图表可参考旧迁移包的详细图注，但它不含v6—v11；当前根THESIS_OUTLINE与最新交接说明补充候选版本边界。')
    s=f'> [全项目审查与清理/调整计划]({AUD}/REPORT.md) · [审查网页]({AUD}/index.html)\n\n'+s;put('PROJECT_NAVIGATION.md',s)
    for folder in ['01_code','02_documents','03_experiments','04_data_weights','05_visualization']:
        name=f'WORKSPACE/{folder}/README.md';s=old(name)
        s=s.replace('reproduction/consolidation_20261012_01/demo/index.html',LATEST).replace('原机器人与证据展示，需要HTTP服务','当前v11进展与冻结主线展示，需要HTTP服务')
        s+='\n\n当前版本补充：[全项目审查](../../'+AUD+'/REPORT.md) · [最新交接说明](../../THESIS_HANDOFF_LATEST.md) · [候选v11](../../reproduction/improvement_v11_20261015_01/REPORT.md)。旧迁移包为c8bbe86快照，不含后续候选。\n';put(name,s)
    s=old('WORKSPACE/index.html').replace('../reproduction/consolidation_20261012_01/demo/index.html','../'+LATEST).replace('原机器人与证据展示，需要HTTP服务','当前机器人与证据展示，需要HTTP服务')
    s=s.replace('<section><h2>源码与模块</h2>',f'<section><h2>当前审查与版本</h2><p>冻结主线v5；v11开发235/240，未采用。旧迁移包为c8bbe86快照。</p><a href="../{AUD}/index.html">打开全仓检查清单与计划</a> · <a href="../THESIS_HANDOFF_LATEST.md">最新交接说明</a></section><section><h2>源码与模块</h2>')
    s=s.replace('10月12日原提纲，保留作历史','当前提纲与候选边界').replace('写论文优先使用的修订提纲','c8bbe86详细提纲，结合当前增补使用');put('WORKSPACE/index.html',s)
    put('WORKSPACE/README.md','''# 分类工作区入口

[网页导航](index.html) · [当前全仓报告](../reproduction/project_audit_20261015_01/REPORT.md) · [当前资料交接](../THESIS_HANDOFF_LATEST.md)

仅增加分类入口，不搬移旧代码、权重或结果。FILE_INDEX.csv对应旧3946文件快照；当前审查前的10146文件清单在审查目录。主版本v5、候选v11分别标注。
''')
    with (RUN/'document_changes.json').open('x',encoding='utf8') as f:json.dump({'updated_or_added':modified,'historical_experiment_files_modified':0},f,ensure_ascii=False,indent=2)
    print('Updated/added',len(modified),'active documents/navigation files')
if __name__=='__main__':main()
