"""Write the integrated documentation after verifying archived root originals."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
STAMP='2026-10-12 成果整合版；旧根文档见 reproduction/consolidation_20261012_01/previous_documents/'
DOCS={
'README.md':'''# 动作延迟下的机器人抓取搬运与失败恢复

Panda在PickPlaceCan仿真中抓取罐子并放入目标箱。本项目实现动作块BC、动作条件世界模型候选评分、真实FIFO延迟和共享恢复，开展公平对照与失败分析。当前输入为含物体真值的23维状态，D=2、20 Hz、400步；演示图像仅用于展示。

建议定位：**考虑动作延迟的机器人抓取搬运与失败恢复系统设计及实验分析**。工程与实验基础已具备，未证明世界模型稳定优于强BC、全面恢复、纯视觉或真机安全。

## 统一入口

- [成果展示](reproduction/consolidation_20261012_01/demo/index.html)：原机器人视频、世界模型主结果、v5结果与已有日志的交互轨迹。
- [实验索引](EVIDENCE_INDEX.md)、[全项目评估](PROJECT_AUDIT.md)、[全部结果口径](RESULTS.md)。
- [运行与复核](PROGRAM_GUIDE.md)、[环境说明](ENVIRONMENT_GUIDE.md)。
- [贡献与资产来源](CONTRIBUTIONS.md)、[相关工作核查](RELATED_WORK.md)、[更新提纲](THESIS_OUTLINE.md)、[交付清单](DELIVERY_CHECKLIST.md)。

## 三条证据线

| 证据线 | 实际完成 | 结论 |
|---|---|---|
| 世界模型主线 | 三种子公平训练/消融1800开发回合，冻结后840确认回合 | 原确认Full相对BC有正向趋势，排序独立增益仍不充分 |
| 补充诊断 | 持续性、短期oracle、H=1/3、K=1/2/8；88任务900回合 | 真实短期评分也未全面完成任务，预测误差不是唯一瓶颈 |
| 共享恢复 | v1—v5；最新v5新增3464回合 | v5确认464/480，v4为457/480；救回7次集中于2个起点，区间包含零 |

各阶段使用不同数据/起点，不能拼接成同批对照或按所有回合当独立样本。v5下BC为干净60/60、噪声58/60；Full为176/180、170/180，不能把整体96.67%称作世界模型单独成功率。

## 保存与版本

本整合版只更新根文档、新本地前端和既有数据的描述性分析，**新增策略回合为0**；原代码、权重、结果、图片与旧页面保持原样。13份旧根文档已归档。旧verify脚本绑定历史根文档，当前校验入口改为本整合目录verify.py；不修改旧清单来伪造历史证明。

旧make_figures.py、RESULTS_TABLE.csv、figures与探索分支保留为历史资产，不作当前主结果入口。论文正文、正式学校格式和导师审核尚未完成。
''',
'STATUS.md':'''# 项目当前状态

## 已完成

- 数据/父轨迹划分、BC、世界模型、分支与FIFO一致性修复。
- 三种子匹配训练、公平开发消融及原生新起点确认。
- 持续性弱预测、真值短期候选排序、H=1/3与候选数量补充实验；并非缺项。
- 共享抓持确认/失抓恢复、长期无进展、对齐/角落和预算/侧倒模块v1—v5。
- v5开发门槛通过后冻结，并完成全新60原生起点及16几何起点确认。
- 成果文档和展示入口整合、贡献边界、8篇选定相关工作与官方元数据BibTeX。
- v2/v3已有同起点四组对照的新描述性汇总；不是新增实验。

## 当前结论

原世界模型确认：BC干净85.00%、噪声81.67%；Full90.00%、86.11%。v5确认：组合464/480，v4为457/480；差+1.46个百分点，配对95%区间[0,4.17]。不同轮次起点不同，不计算跨轮因果增幅。

最新v5没有证明世界模型超越强BC。窄格侧倒、滑移和角落退步仍有失败；完整记录见[RESULTS](RESULTS.md)和[v5评估](reproduction/recovery_v5_20261012_01/ASSESSMENT.md)。

## 尚未完成

正式论文正文、学校模板/引用格式、导师审阅、答辩材料和目标电脑交付验证。最新v5起点上的关闭恢复对照尚未运行；整个项目并非没有四组对照，旧v2/v3已具备。

纯视觉、真机、多任务、跨电脑干净安装和充分跨延迟泛化未完成。它们是否需要，取决于确定的题目范围，不能自动成为当前本科毕设的必补项。

本整合阶段未训练、仿真或更换权重；新增统计与轨迹图只读已有结果。未来方案见[后续候选](reproduction/consolidation_20261012_01/FOLLOWUP_PLAN.md)。
''',
'RESULTS.md':'''# 当前实验结果：按阶段分别解释

## A. 世界模型原生确认（无共享恢复）

60个新起点，BC固定一个权重，Full/Plain各三个训练种子；14任务840回合，共享起点与扰动。

| 方法 | 干净 | 噪声0.05 |
|---|---|---|
| BC k=2 | 51/60，85.00% | 49/60，81.67% |
| Full | 54/54/54，每种子60；90.00% | 52/52/51，每种子60；86.11% |
| Plain | 53/53/53，每种子60；88.33% | 50/51/50，每种子60；83.89% |

Full−BC：干净+5.00个百分点，[0,11.67]；噪声+4.44，[0,10.00]。预登记等权综合+4.72，[0.56,10.28]；Full−Plain综合+1.94，[-0.56,6.11]。这是有边界的正向证据，不代表全部条件显著或排序模块已确立。原表：[确认报告](reproduction/confirmation_20261012_01/analysis/report.txt)。

## B. 补充开发诊断

88任务900回合，30个已知开发起点。短期oracle为干净25/30、噪声25/30；BC为25/30、24/30。持续性、H=1、K=1全回退k=2。D=2时H=1看不到新候选执行。K=8新增候选超出k=0…3训练支持，不能当纯计算量消融。详见[补充报告](reproduction/extensions_20261012_01/REPORT.md)。

## C. v5共享恢复独立确认

另一批60个新起点，每版两条件×BC/Full三种子=480次执行，五版共2400回合。与A不是同批起点。

| 版本 | BC干净 /60 | BC噪声 /60 | Full干净 /180 | Full噪声 /180 | 合计 /480 |
|---|---:|---:|---:|---:|---:|
| v2 | 59 | 57 | 173 | 168 | 457 |
| v4 | 59 | 57 | 173 | 168 | 457 |
| 仅时间 | 60 | 58 | 175 | 170 | 463 |
| 仅侧倒 | 59 | 57 | 174 | 168 | 458 |
| v5组合 | 60 | 58 | 176 | 170 | 464 |

v5−v4预定执行混合差+1.46个百分点，[0,4.17]；7次救回、0退步，集中在2个起点。相对v2救回8次、退步1次。v5比时间单项仅多一次执行成功，不宣称组合具有稳定附加优势。v5 BC干净100%、噪声96.67%；Full分别97.78%、94.44%，均值低于BC。

v5仍有16次失败、7个起点；6次物体低于恢复高度、4次失抓后耗尽尝试、6次其他尝试耗尽。15次是五版共同失败。几何压力试验另外16起点，v2/v4/T/S/v5为8/11/12/11/12，不并入原生成功率。详见[v5评估](reproduction/recovery_v5_20261012_01/ASSESSMENT.md)。

## D. 有无恢复的贡献

v2/v3已经在同批起点比较BC、Full、BC+恢复、Full+恢复。新[四组描述性分析](reproduction/consolidation_20261012_01/FACTORIAL_REVIEW.md)显示恢复同时帮助两类方法，不能将其全部收益归世界模型。最新v5缺少该批的关闭恢复组，不能借用旧轮次。

所有种子均报告。开发、不同确认批次、事后诊断和演示不合并；原始数据与输出未改。当前界限见[贡献](CONTRIBUTIONS.md)与[统计](STATISTICS.md)。
''',
'STATISTICS.md':'''# 统计单位与解释边界

## 单位和指标

成功为400步内首次达到既有环境成功判定；失败完整执行400步。平均步数将失败按400截断；只看成功回合平均会有选择偏差。

每轮确认有60个配对环境起点，多种模型种子/噪声共用这些起点。840/1440/1920/2400是执行数量，不是同等数量的独立环境样本。不同确认轮次保持分开；BC只有一个固定权重，不能复制为三个训练模型。

## 已有原统计与新描述性分析

| 分析 | 方法 | 解释范围 |
|---|---|---|
| 原世界模型确认 | 20000次训练种子/起点配对交叉bootstrap，seed2026101203；两条件综合预登记等权 | 只有3个训练种子，有限起点与离散差值；逐项描述性区间 |
| v5确认 | 20000次配对起点bootstrap，seed20261016；Full三固定种子起点内平均 | 不覆盖任意重训的不确定性；8执行预定混合中Full占6项、BC占2项，不是两类方法等权 |
| 本阶段旧v2/v3四组分析 | 20000次配对起点bootstrap，seed2026101207；Full起点内平均 | 事后新增描述性分析，未产生新实验或新独立确认 |

以上均无多重比较校正。区间接触零不证明无效；退化[0,0]不证明总体等价；少数救回起点不支持普遍结论。不同统计方案的区间不可不加说明地互换。

## 关键结果

原Full−BC等权综合+4.72个百分点，[0.56,10.28]；Full−Plain综合+1.94，[-0.56,6.11]。v5−v4预定执行混合+1.46，[0,4.17]。保持各阶段原协议、原随机种子和原结果，不为统一文档重算或替换历史区间。

决策日志计时通常不含完整BC前向/总控制环，且受并行负载影响，不当实时性基准。压力测试是人工几何分层且每类仅4起点；接触按20Hz控制时刻采样，不是全部物理子步。轨迹演示为事后选例，不追加至主统计。

原统计：[原确认](reproduction/confirmation_20261012_01/analysis/paired_comparisons.csv)、[v5](reproduction/recovery_v5_20261012_01/analysis_confirmation/summary.json)、[新四组分析](reproduction/consolidation_20261012_01/factorial_analysis.json)。
''',
'PROJECT_AUDIT.md':'''# 全项目适用性与完整度评估

## 判断

项目具备本科毕业设计的工程与实验基础，适合“系统设计与实验分析”定位。尚不是正式完成的毕业论文，也没有证明显著、稳定或通用性能突破。学校任务书/评分要求未提供，最终范围需导师确认。

## 当前证据链

| 阶段 | 已完成资产 | 说明 |
|---|---|---|
| 主线数据与分支 | 200示范，140/30/30父轨迹；训练20父轨迹160组、开发8父轨迹64组 | 相关分支继承父轨迹；旧sealed已查看 |
| 三种子 | 15训练任务、18选点权重、60评估1800回合 | 75登记任务完成；预算/初始化/批次配对 |
| 原生世界模型确认 | 14任务840回合，60新起点 | BC与Full/Plain三种子、两条件 |
| 补充诊断 | 88任务900回合 | 持续性、短期oracle、H=1/3与K扫描已完成 |
| 恢复v1—v5 | 独立目录、开发/消融、成功和负结果 | v3确认未整体改善；v4自身门槛未通过，后来作为v5对照运行 |
| 最新v5 | 两轮小测试264、开发720、原生确认2400、压力80；合计3464新回合 | 612613控制步验收、45次物理回放均属既有记录 |
| 本整合阶段 | 根文档归档与统一、选定文献、旧四组汇总、前端与日志轨迹 | 新策略回合0；未重训/仿真/更改算法 |

## 已修正文档缺项

原根文档中持续性、真值排序、H=1/候选数量“未完成”已过时；这些实验在extensions目录完成。已有v2/v3四组对照也已汇总：缺的是最新v5同批关闭恢复组，并非整个项目没有该对照。

当前展示包含原世界模型视频与结果、v5表/压力结果、真实已有日志的交互轨迹。日志轨迹图不是新的三维机器人视频；未为了展示重新运行策略。

## 剩余缺陷与影响

| 缺陷 | 对当前交付的影响 | 下一步 |
|---|---|---|
| 世界模型独立贡献不稳定，排序证据不足 | 限制优越性/创新表述，不否定系统实现工作量 | 结合原确认、已有四组与负结果诚实分析 |
| 侧倒窄格、角落碰撞、滑移仍失败 | 不能宣称全面恢复；可作为失败分析 | 实际开度/整段路径余量、抓持保持分别验证 |
| 单任务、低维真值、单固定BC与固定延迟 | 泛化范围有限 | 明确范围；跨任务/视觉/真机视导师要求扩展 |
| 环境单机配置、历史脚本入口多 | 新电脑一键恢复尚未验证 | 按环境指南与提交清单整理，不直接运行全部旧脚本 |
| 正文、完整文献比较与学校格式未完成 | 正式论文交付缺项 | 已提供更新提纲、来源、引用和贡献边界；后续写作需另行开展 |

历史文档和旧页面保持原样，各版本数值有对应起点、协议、哈希和记录，不能借“整合”隐藏退步。先收束证据与交付，不为毕业自动无限迭代恢复版本。

## 验收口径

本阶段验证既有文件的内容哈希、登记结果条数、文档/前端链接、引用元数据和浏览器交互。原模型前向、物理/控制器/FIFO检查沿用已有运行凭据，不称本阶段重新跑过。当前清单与验证入口在 [PROGRAM_GUIDE](PROGRAM_GUIDE.md)。
''',
'PROGRAM_GUIDE.md':'''# 当前项目运行与模块指南

工作目录 `C:\\Users\\Livio\\Desktop\\robot_can`；PyCharm解释器沿用 `.venv\\Scripts\\python.exe`。环境版本与兼容说明见[ENVIRONMENT_GUIDE](ENVIRONMENT_GUIDE.md)。

## 先看成果

当前[展示页面](reproduction/consolidation_20261012_01/demo/index.html)包含原始视频、v5结果和日志轨迹。用PowerShell启动静态服务：

```powershell
Set-Location 'C:\\Users\\Livio\\Desktop\\robot_can'
& '.\\.venv\\Scripts\\python.exe' -m http.server 8766 --bind 127.0.0.1
```

浏览器打开 `http://127.0.0.1:8766/reproduction/consolidation_20261012_01/demo/index.html`。这是文件服务，不训练或运行机器人。若端口已经由项目文件服务使用，复用该服务。

## 当前只读完整性复核

```powershell
& '.\\.venv\\Scripts\\python.exe' -X utf8 -B reproduction\\consolidation_20261012_01\\verify.py
```

该入口按本阶段清单验证：旧根文档对应归档副本、其他原文件保持原位，新文档/前端/分析哈希不变；不调用环境、模型、训练或物理回放。旧review/v5验收脚本绑定历史根文档，根文档已授权更新，直接调用可能提示根文档变动。旧验收记录保留，不修改其清单。

## 实验复核/重跑入口

当前查看成果不需要重新训练。v5逐步/物理核验与另开目录完整重跑命令见[v5 README](reproduction/recovery_v5_20261012_01/README.md)；它们会执行仿真，需主动选择。最新根文档已更新，如其旧全项目保护检查提示根文档变动，先用当前verify核对归档，不删除结果或改历史保护清单。

各实验原脚本仍在原目录，重跑应在新的副本/输出目录进行，并重新登记。prepare生成器、统计图脚本常为排他写入，不能删除旧产物强行运行。不得把已看过的起点重复运行称新的独立确认。

## 模块

| 模块 | 作用 |
|---|---|
| common.py | 环境/数据、23维观测、控制器/传感器恢复、BC加载 |
| train_policy.py / ChunkPolicy | 混合密度动作块BC；当前冻结权重沿用 |
| collect_rollout_branches.py | 完整历史回放、真实队列同状态分支采集 |
| world_model.py / train_world.py | GRU残差状态预测、进度/抓持丢失头、组内排序 |
| evaluate_delay.py | 原世界模型候选门限与延迟闭环 |
| extensions/evaluate.py | 持续性、短期oracle、H/K开发诊断 |
| recovery_v5/recovery_controller.py / clearance.py | 共享恢复状态机与固定夹爪几何筛选 |
| consolidation/build_evidence.py | 读取已有结果统计和轨迹；没有策略运行 |
| consolidation/demo | 静态前端，读取既有结果与视频 |

根目录33个原Python脚本未改动；旧探索资产见原[模块清单](reproduction/review_20261012_01/module_inventory.json)，不要逐个运行默认参数来代替当前复核。
''',
'DEMO_GUIDE.md':'''# 成果展示与讲解顺序

最新页面：[consolidation/demo/index.html](reproduction/consolidation_20261012_01/demo/index.html)。静态服务命令见[PROGRAM_GUIDE](PROGRAM_GUIDE.md)。旧Apple页面、视频和结果原样保留。

## 建议展示顺序

1. 首页“先预测后果，再决定动作”：解释100ms延迟、四候选与H=8（含两步队列前缀）；点选四步流程。线条是机制示意，不是实测预测轨迹。
2. 原始机器人视频默认展示干净Full独胜：Full成功133步，BC和Plain未完成400步；切换噪声、共同成功和共同未完成。六段视频固定种子17，事后按类别最小编号选择，不当代表性随机样本。
3. 世界模型总体结果：干净Full90%对BC85%；预设两条件等权差+4.72个百分点，95%配对区间[0.56,10.28]。排序独立贡献和逐条件区间有边界，不用独胜视频证明全面优势。
4. 预测诊断：开发集物体位置RMSE降低32.8%是相对状态保持弱基线；三方法完整误差同时展示，Plain位置误差更低。开发父起点已参与选择，不当作独立泛化。
5. 论文改进与贡献：延迟一致的预测闭环、面向任务的候选评分、有限预算的共享恢复；分别说明实现证据和贡献边界，不宣称世界模型首创。
6. 恢复结果与交互轨迹：切换时间救回、侧倒救回和失抓失败；查看既有末端/罐体观测和阶段。这层收益单独报告。
7. 证据与交付：原始结果、已有四组分析、贡献表、相关工作与剩余失败。

## 日志轨迹图的性质

新增三例读取已有v5原始trace：demo_10000029的BC干净时间救回；demo_10000012的Full s41干净侧倒救回；demo_11000013的几何失抓失败。选择在结果已知后进行，覆盖两类救回和失败；不是新测试、三维渲染或实机视频。较早成功序列结束后保持最后观测，另一方法可继续到400步。

轨迹图显示末端/物体XY和高度、控制步与阶段；视频的相机画面只来自原始无共享恢复实验。页面明确区分，不能把老视频贴成v5机器人运行成果。

## 讲解要点

k=2是BC预测动作块第3项，不读取真实未来。2步FIFO意味着新命令稍后执行。风险头监督为特定抓持丢失标签，不是全部失败/碰撞概率；门限不是校准不确定性。共享恢复用规则状态机，不是新世界模型训练。

噪声0.05加在前三个归一化出队动作分量，不是5cm物体位置噪声。成功/失败沿用400步判定；不能把短暂抓起写成终局成功。

媒体来源：[原媒体清单](reproduction/release_20261012_01/demo/media_manifest.json)；日志来源与SHA：[本阶段evidence](reproduction/consolidation_20261012_01/evidence.json)。本阶段不生成新的机器人视频。
''',
'PROTOCOL.md':'''# 研究协议、范围与版本索引

本文为事后文档整合，不是追溯性预注册。真正执行前的protocol/design/study_plan/lock保留在各实验目录，禁止改写。

范围：PickPlaceCan、Panda、23维含物体真值状态、20Hz、D=2、400步。当前从世界模型辅助候选选择扩展到共享失败恢复；两类贡献分别分析。

| 证据线 | 原登记 |
|---|---|
| 三种子匹配训练/开发 | [multiseed protocol](reproduction/multiseed_20261012_01/protocol.json) |
| 原世界模型确认 | [design](reproduction/confirmation_20261012_01/design.json)、[lock](reproduction/confirmation_20261012_01/lock.json) |
| 补充诊断 | [extensions protocol](reproduction/extensions_20261012_01/protocol.json) |
| 最新恢复 | [v5 study_plan](reproduction/recovery_v5_20261012_01/study_plan.json)、[freeze](reproduction/recovery_v5_20261012_01/freeze_before_states.json)、[lock](reproduction/recovery_v5_20261012_01/confirmation_lock.json) |
| 本阶段整合 | [before_manifest](reproduction/consolidation_20261012_01/before_manifest.json)，不新增策略实验 |

主线训练/开发按父轨迹隔离；保留强BC k=2及全部种子，不挑确认表现最好的种子。旧sealed和全部既有确认已查看，不能继续冒充未见数据。人工压力测试与原生初始化、开发与确认、重复物理回放与新策略回合分开。

持续性、短期oracle、H=1/候选数补充已经完成；原协议的纯视觉/真机/多任务等扩展未完成。已有v2/v3四组对照见[新描述性汇总](reproduction/consolidation_20261012_01/FACTORIAL_REVIEW.md)，不算追加确认。

若改算法，另建目录并在运行前固定开发推进标准、配置、种子与统计方案，通过后冻结再生成新起点。后续候选草案不算已执行登记，见[FOLLOWUP_PLAN](reproduction/consolidation_20261012_01/FOLLOWUP_PLAN.md)。
''',
'DELAY_PROTOCOL.md':'''# 动作延迟下的世界模型与共享恢复：当前方法

## 输入、时序与BC

23维：末端位置/四元数、两指位置、物体相对及绝对状态，含物体真值。BC为宽度512、5混合分量的动作块策略，输出8×7动作。k=2选第3个预测动作，不是读取真实未来。权重固定。

20Hz、D=2 FIFO，名义100ms。队列初始两条全零动作；提交命令后执行队首、取新观测再规划。出队动作前三个归一化分量加σ=0/0.05噪声并clip，不把新命令直接执行或清空队列。

## 世界模型与选择

候选为BC k=0/1/2/3；序列由真实待执行前缀加重复候选组成，H=8。GRU宽128，h=init(z)，h'=GRU([z,a],h)，z'=z+0.1delta(h')。87321参数；冻结Full/Plain评分头只读预测归一化状态。它是低维残差动力学，不是视觉潜变量模型或已实现部分可观测记忆控制。

J=p末步+0.5mean(p)−0.5max(r)。最佳非k=2且J差<0.02时回退k=2。p为进度，r标签为初始抓持后失去抓持且未成功，不是普遍碰撞/安全概率。训练Full=MSE+BCE进度+0.5BCE风险+0.2排序；Plain只去排序。排序阈值0.025，温度0.1。

训练种子17/23/41，基础3000更新、batch16组、Adam0.0003；250步开发选点。评分头续训/校准各另加3000更新。真实奖励/成功信号用于离线标签与评价，部署不查询候选真实未来。

## 共享恢复

BC/Full提议先经过同一个观测历史恢复状态机，再提交到同一FIFO。抓持确认依赖指间距、相对运动和抬升跟随；失抓、持物/接近停滞可接管。v2增加长期无进展和抓取方向；v4增加等价方向切换与区域约束角落；v5新增剩余预算安排和侧倒夹爪间隙。

规则控制读取23维观测历史和固定场景目标/几何，不额外查询奖励、成功、接触或机械臂关节真值来选动作。夹爪几何筛选未包含整臂轨迹、全部跟踪误差或抓持稳定性保证。T包括多项内部安排，当前是模块整体消融。至多两次尝试，总400步。

## 评价与证据

各阶段分别统计，原始840回合主线与v5新2400回合不是同批起点。已有v2/v3四组对照和v5组件消融见[结果](RESULTS.md)、[统计](STATISTICS.md)、[贡献](CONTRIBUTIONS.md)。局部成功率改善不等于世界模型本身预测能力增强。
''',
'REPRODUCTION_PLAN.md':'''# 复现与交付阶段计划

## 已完成研究链

原数据/权重检查与环境配置；分支恢复/FIFO一致性修复；同状态真实后果和评分诊断；三种子匹配训练/消融；冻结原生确认；补充持续性/oracle/H/K；共享恢复v1—v5与独立确认。证据分阶段见[EVIDENCE_INDEX](EVIDENCE_INDEX.md)。

## 本阶段实际工作

归档13份根文档，整合结果/状态/协议/提纲，核查8篇官方引用及部分方法，汇总旧v2/v3四组对照，制作基于既有视频/日志的本地展示。没有新增策略回合、重训权重或更改控制算法。当前完整性验证见[PROGRAM_GUIDE](PROGRAM_GUIDE.md)。

## 接下来

先确认题目与贡献范围，按交付清单整理提交版本和正式文稿。若需要算法研究，再按[候选方案](reproduction/consolidation_20261012_01/FOLLOWUP_PLAN.md)定位实际开度/路径与滑移问题，单项小测试、开发消融、达标后冻结，用新起点确认。

旧实验、当前成果复核、另一批独立确认和正式论文交付不是同一任务。不要为展示重新跑所有模型，或者把重复执行已有确认称新的测试。
''',
'SUPPLEMENTAL_RESULTS.md':'''# 补充实验：已完成，保留开发口径

持续性弱预测、真实短期候选排序、H=1/3、K=1/2/8已补齐：88登记任务、900回合，30个已知开发起点。原结果、权重与诊断保留。详见[原报告](reproduction/extensions_20261012_01/REPORT.md)。

短期oracle干净/噪声均25/30；BC为25/30、24/30。真值短期后果并未解决全部任务，不能把oracle叫长期成功的数学上界。持续性和H=1等回退至k=2；K=8新增候选超出训练支持，未稳定改善。

后续共享恢复已发展至v5，详情见[统一结果](RESULTS.md)与[v5评估](reproduction/recovery_v5_20261012_01/ASSESSMENT.md)。本阶段只是整合原补充结果，没有重复运行900回合。
''',
'THESIS_OUTLINE.md':'''# 本科论文提纲：动作延迟下的机器人抓取搬运与失败恢复

建议题目：**考虑动作延迟的机器人抓取搬运与失败恢复系统设计及实验分析**。本页为更新的结构与证据映射，不是论文正文。实际题目、篇幅和模板需导师/学校确认。

## 问题与贡献

RQ1：含物体真值的低维状态、固定延迟下，世界模型辅助选择何时有益、何时不优于强BC？RQ2：真实队列/状态恢复、短期评分与终局成功为何需要分别核验？RQ3：共享恢复在有限预算内带来什么收益与失败边界？

贡献见[CONTRIBUTIONS](CONTRIBUTIONS.md)；相关工作见[RELATED_WORK](RELATED_WORK.md)。不预设所有研究问题必须得到正面答案。

## 第一章 绪论

任务、固定延迟与执行扰动的范围；三项问题与系统/实验贡献。明确单任务低维仿真，没有真机或纯视觉结论。

## 第二章 相关工作与基础

公共示范学习与动作分块；学习动力学与有限候选规划；决策相关训练目标；任务/恢复策略分离；几何抓取余量。按输入、预测对象、选择方式、恢复方式及验证范围比较8篇已核查入口，继续补更直接的延迟与抓取恢复文献。数据和框架注明来源。

## 第三章 系统、数据与复现一致性

PickPlaceCan/Panda/OSC_POSE；23维观测；200父轨迹140/30/30划分；训练20父轨迹160组、开发8父轨迹64组。真实D=2 FIFO与噪声位置；控制器缓存与观测刷新；完整历史回放分支采集及顺逆序一致性。

## 第四章 世界模型候选评分

BC混合密度动作块；k=2含义；四候选与H=8队列前缀；GRU残差动力学及未来状态评分头；Full/Plain/Direct等训练目标与匹配预算；门限及风险标签边界。H=1看不到新命令，K=8训练支持与部署集合不一致作为敏感性解释。

## 第五章 抓持确认与共享恢复

观测历史抓持/失抓判据；持物/接近长期无进展；恢复阶段、有限尝试；等价方向和合法区域；T剩余预算安排、S固定夹爪间隙。明确这是规则控制器，权重未改变；T内部尚未逐个分离，S不保证路径全程无碰撞与稳定抓持。

## 第六章 实验与结果

1. 环境版本、数据、种子、更新/参数/选点和公平性。
2. 三种子开发消融与原世界模型840回合确认，开发/确认分表；保留Full不稳定、排序/校准负结果。
3. 900回合补充诊断：持续性、短期oracle、H/K及离线预测误差。
4. 恢复版本过程：v3负结果、v4自身门槛未通过、v5开发达标后冻结。
5. v5新确认464/480对v4 457/480；7救回来自2起点，差+1.46，[0,4.17]。BC/Full分别报告，压力测试分开。
6. 已有v2/v3同起点四组分析，注明当前是旧数据的事后描述性分析；不拼成v5关闭恢复组。
7. 时间救回、侧倒救回、失抓失败和角落退步；真实已有视频/日志与逐步物理回放证据。

## 第七章 讨论与局限

原确认Full正向趋势与恢复后强BC结果并存；世界模型和恢复收益分别解释。单任务真值状态、固定BC、训练数据覆盖、3固定世界模型种子、60起点相关执行、小样本区间、静态几何近似、滑移/格外失败和单机复现。没有普遍安全、视觉、跨任务或真机结论。

## 第八章 总结与展望

回顾系统、一致性修复、受控分析和局部恢复收益。未来从实际开度/整段路径余量、稳定抓持入手；新版本预登记，另批确认。正式稿不以“未来必能提高”替代证据。

## 图表与原始证据

| 内容 | 来源 |
|---|---|
| 原世界模型三种子开发/确认 | [开发](reproduction/multiseed_20261012_01/analysis/report.txt)、[确认](reproduction/confirmation_20261012_01/analysis/report.txt) |
| 补充预测/时域/候选/短期oracle | [extensions报告与图](reproduction/extensions_20261012_01/REPORT.md) |
| v5主表/效应区间/压力 | [v5评估与图](reproduction/recovery_v5_20261012_01/ASSESSMENT.md) |
| 已有四组分析 | [汇总表](reproduction/consolidation_20261012_01/FACTORIAL_REVIEW.md)、[数值JSON](reproduction/consolidation_20261012_01/factorial_analysis.json) |
| 选定文献 | [对照](RELATED_WORK.md)、[官方元数据BibTeX](reproduction/consolidation_20261012_01/references_verified.bib) |
| 原始视频与新日志图 | [当前演示](reproduction/consolidation_20261012_01/demo/index.html)、[来源SHA](reproduction/consolidation_20261012_01/evidence.json) |

文字、图表和结论应能回到上述原始数据；不同确认批次不得直接相减或合并为独立样本。
''',
'ENVIRONMENT_GUIDE.md':'''# 冻结实验环境与提交说明

PyCharm沿用项目 `.venv\\Scripts\\python.exe`，工作目录项目根。已有实验快照：Python3.10.9、torch2.14.1+cu130、NumPy1.26.4、robosuite1.5.1、MuJoCo3.3.0，完整字段在[environment.json](reproduction/review_20261012_01/environment.json)、[已安装版本](reproduction/review_20261012_01/environment-freeze.txt)。本整合阶段没有重新测试CUDA、运行模型或重装依赖。

`requirements-repro.txt`保留的是旧安装建议，其torch2.9.1注释不是实际冻结版本，不应据此降级当前环境。完整版本快照也不是已验证的跨电脑离线安装包。

Windows兼容记录在 `data/windows_compatibility.json`。`setup_windows.py`仅面向当前项目虚拟环境，复制MuJoCo DLL并设置WGL相关宏；它有写入，不要在已工作的环境中为“看演示”反复执行。新电脑需要根据其系统单独确认，不能直接复制`.venv`当完整安装方案。

数据：[来源和SHA](data/can_ph_lowdim_v15.manifest.json)。BC：[冻结路径](policy/bc_chunk_dev_v4/policy_15000.pt)。Full/Plain：models/multiseed_20261012_01_{full,plain}_s{17,23,41}/model.pt。原学习权重在本阶段不变。

提交副本建议包含源码、必要权重、数据下载校验与划分、协议/配置、主结果/验证记录、演示与文档；虚拟环境和IDE缓存不当作研究成果。先整理清单，后续在目标演示电脑做独立安装/展示验证。
''',
'EVIDENCE_INDEX.md':'''# 统一成果与版本索引

## 当前入口

[展示](reproduction/consolidation_20261012_01/demo/index.html) · [结果](RESULTS.md) · [贡献](CONTRIBUTIONS.md) · [统计](STATISTICS.md) · [相关工作](RELATED_WORK.md) · [交付清单](DELIVERY_CHECKLIST.md)

## 研究过程

| 目录/版本 | 作用 | 当前使用方式 |
|---|---|---|
| queuepair / candidate_truth / headcal / tailprobe | 一致性、同状态真值、评分校准与续接探索 | 开发诊断，不作新独立确认 |
| multiseed_20261012_01 | 15训练任务、18权重、60开发评估 | 三种子公平消融，全部种子保留 |
| confirmation_20261012_01 | 原世界模型14任务840回合 | 无共享恢复的原确认；60起点 |
| extensions_20261012_01 | 88任务900回合 | 持续性、短期oracle、H/K已完成 |
| recovery_20261012_01（v1） | 抓持/失抓、持物停滞 | 原240回合开发改善，仍有失败 |
| recovery_v2_20261012_01 | 长期无进展、侧倒与几何恢复 | 开发和独立确认，含关闭恢复对照 |
| recovery_v3_20261012_01 | 对齐/角落探索 | 确认未整体超过v2，负结果保留 |
| recovery_v4_20261012_01 | 等价方向切换、区域约束 | 自身开发推进门槛未通过；作为v5冻结参考后来被评价 |
| recovery_v5_20261012_01 | T时间、S侧倒间隙及组合 | 最新完成开发/冻结/新确认，局部改善不代表全面恢复 |
| release / review | 原视频、旧文档与Apple页面 | 历史展示保持原样 |
| consolidation_20261012_01 | 本次成果与文献整合、旧四组统计、新前端 | 不新增策略/训练回合 |

每个实验目录内的protocol/design/study_plan/lock、result/trace与validation为原始证据，目录中的旧评估按当时进度解释。不能因当前结果更新而改写过去门槛或负结果。

## 新增分析与可查资产

[已有四组对照](reproduction/consolidation_20261012_01/FACTORIAL_REVIEW.md)、[整合数据](reproduction/consolidation_20261012_01/evidence.json)、[文献元数据](reproduction/consolidation_20261012_01/references_metadata.json)、[BibTeX](reproduction/consolidation_20261012_01/references_verified.bib)、[未来草案](reproduction/consolidation_20261012_01/FOLLOWUP_PLAN.md)。

13份本次修改前根文档位于[previous_documents](reproduction/consolidation_20261012_01/previous_documents/)。旧make_figures.py与RESULTS_TABLE.csv等不作当前主表。原ADAPTIVE_PROTOCOL是另一条探索线，不能混入本轮确认。
'''
}
def main():
 before=json.loads((RUN/'before_manifest.json').read_text(encoding='utf-8-sig'));changed=[];created=[]
 for name,text in DOCS.items():
  p=ROOT/name
  if name in before:
   archived=RUN/'previous_documents'/name
   assert hashlib.sha256(archived.read_bytes()).hexdigest()==before[name]
   assert hashlib.sha256(p.read_bytes()).hexdigest()==before[name],name
   changed.append(name)
  else:
   assert not p.exists(),name;created.append(name)
  p.write_text(text.strip()+'\n\n版本：'+STAMP+'\n',encoding='utf8')
 (RUN/'document_changes.json').write_text(json.dumps({'changed_root_documents':changed,'created_root_documents':created,
  'preserved_root_documents':['ADAPTIVE_PROTOCOL.md'],'algorithm_changes':[],'new_policy_episodes':0},ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'changed':changed,'new':created,'algorithms_modified':False},ensure_ascii=False))
if __name__=='__main__':main()
