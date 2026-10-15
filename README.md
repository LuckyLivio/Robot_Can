> 当前 v10 箱沿接近实验正在核验，旧成果完整保留。前端入口：<http://127.0.0.1:8766/>。新结果与状态见 [v10 报告](reproduction/improvement_v10_20261015_01/REPORT.md)。

# 动作延迟下的机器人抓取搬运与失败恢复

Panda 机械臂在 PickPlaceCan 仿真中抓取罐子并放入目标箱。本项目实现动作块行为克隆（BC）、世界模型候选动作评分、真实 FIFO 动作延迟，以及抓持确认和失败恢复控制。

实验采用含物体位置与姿态真值的 23 维状态观测，控制频率 20 Hz，主要协议为 D=2、每回合最多 400 步。前端用于展示已有实验视频、结果和日志轨迹。

## 前端启动：在 PyCharm 终端执行

打开项目 `C:\Users\Livio\Desktop\robot_can`，在 PyCharm 底部 Terminal 中使用 PowerShell：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1
```

保持终端运行，在浏览器打开：

**[打开前端：http://127.0.0.1:8766/](http://127.0.0.1:8766/)**

项目根入口会自动跳转到最新整合版。也可以[直接打开成果页面](http://127.0.0.1:8766/reproduction/progress_v10_20261015_01/demo/index.html)。

当前整合版包含 v10 的实验状态、20 fps 历史机器人视频、世界模型与 v5 冻结主结果，以及 v6/v8 同起点历史恢复对比。恢复演示提供 Full 的 17、23、41 三个种子和 BC 退步案例；候选未达标也如实展示。

这是静态 HTML/CSS/JavaScript 前端，不需要 npm、Node.js 或额外前端依赖。启动命令只提供本地文件服务；训练和机器人仿真有独立入口。请通过 HTTP 地址访问，使数据与视频按项目路径加载。

- 停止服务：在服务终端按 `Ctrl+C`。
- 端口已占用：先打开上面的地址；已有项目服务可直接使用。另开服务时将命令中的 `8766` 改为 `8767`，访问地址也改为 `8767`。
- 页面打不开：检查工作目录、启动报错以及终端是否仍在运行。
- 数据或视频无法加载：必须在 `robot_can` 根目录启动服务，不能只在 `demo` 子目录启动。

历史页面仍保留：

| 页面 | 地址 |
|---|---|
| 当前整合版，推荐 | http://127.0.0.1:8766/reproduction/progress_v10_20261015_01/demo/index.html |
| review 历史版 | http://127.0.0.1:8766/reproduction/review_20261012_01/demo/index.html |
| release 历史版 | http://127.0.0.1:8766/reproduction/release_20261012_01/demo/index.html |

## PyCharm 环境

项目解释器选择：

```text
C:\Users\Livio\Desktop\robot_can\.venv\Scripts\python.exe
```

已有虚拟环境和依赖可以直接使用。以下命令显式使用项目解释器，即使终端显示 `(base)` 也不影响：

```powershell
& '.\.venv\Scripts\python.exe' -c "import sys; print(sys.executable); print(sys.version)"
& '.\.venv\Scripts\python.exe' -m pip check
```

环境快照、Windows 兼容说明和新电脑安装注意事项见 [ENVIRONMENT_GUIDE.md](ENVIRONMENT_GUIDE.md)。旧安装建议与实际冻结版本可能不同，沿用当前已工作的环境即可。

## 主要模块

| 文件或目录 | 作用 |
|---|---|
| `common.py` | 创建环境、读取数据、打包观测、加载 BC、恢复仿真状态 |
| `train_policy.py` | 训练动作块 BC 策略 |
| `collect_rollout_branches.py` | 同状态、同历史、同延迟队列的候选动作分支采集 |
| `world_model.py`、`train_world.py` | 状态预测、进度和失抓评分、候选排序 |
| `evaluate_delay.py` | 动作延迟下的 BC 与世界模型闭环评估 |
| `reproduction/extensions_20261012_01/` | 持续性、真值短期排序、预测长度及候选数量实验 |
| `reproduction/recovery_v5_20261012_01/` | v5 恢复控制、消融、独立确认和失败分析 |
| `reproduction/progress_v10_20261015_01/demo/` | 当前进度与成果展示前端 |
| `reproduction/improvement_v9_20261015_01/` | 关节姿态检查与规划耗时消融，旧结果保留 |
| `data/` | 数据、划分与来源校验 |
| `policy/`、`models/` | 策略和世界模型权重、实验结果 |

BC 提供候选动作，世界模型预测并评分，执行器通过 FIFO 队列模拟延迟。共享恢复控制器监测抓持与无进展状态，必要时接管重新抓取、搬运和放置。世界模型与共享恢复的收益分别评价。

## 当前实验结果

本轮 v9 的关节可达性与规划耗时结果见 [v9 完整报告](reproduction/improvement_v9_20261015_01/REPORT.md)。新监督器额外读取七个关节角度，BC 和 Full 公平共享；原策略/世界模型输入仍为 23 维。未达到门槛的候选不会替换下列冻结主结果。

完整世界模型主实验、补充诊断及恢复实验见 [RESULTS.md](RESULTS.md) 和 [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md)。不同阶段的起点与条件不能直接拼接成同一批对照。

已冻结的主线恢复实验：

| 版本 | 开发集成功 /240 | 独立原生确认成功 /480 | 几何压力成功 /16 |
|---|---:|---:|---:|
| v2 | 229 | 457 | 8 |
| v4 | 231 | 457 | 11 |
| 仅时间预算 | 234 | 463 | 12 |
| 仅侧倒间隙 | 233 | 458 | 11 |
| **组合 v5** | **236** | **464** | **12** |

原生确认使用 60 个新起点，每版执行 BC、Full 三个固定训练种子和两种噪声条件，共 480 回合；统计单位仍为起点。几何压力测试使用另外 16 个起点，单独统计。

v5 相对 v4 救回 7 次执行且没有新增失败，但收益集中于两个起点；总体提升 1.46 个百分点，95% 起点配对区间为 [0, 4.17]。v5 下 BC 干净/噪声为 60/60、58/60，Full 为 176/180、170/180。这支持局部恢复改善，尚未证明世界模型稳定优于强 BC 或全面解决抓取恢复。

详见 [v5 整体评估与图表](reproduction/recovery_v5_20261012_01/ASSESSMENT.md)。

## 文件完整性与实验重跑

检查已有成果和本次 README 更新：

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction\improvement_v9_20261015_01\verify_integrity.py
```

该入口只读核对本轮开始前的 8,802 个路径，以及本轮代码、结果与前端交付清单。授权修改的根 README 和入口页面按逐字节备份验证；其他旧资产在原路径验证，不训练、不仿真。历史校验入口绑定当时的根文档，直接运行可能提示后续授权更新；不要修改旧清单来消除差异。

完整 v5 重跑、控制步骤复核和物理回放命令见 [v5 README](reproduction/recovery_v5_20261012_01/README.md)，整体运行指南见 [PROGRAM_GUIDE.md](PROGRAM_GUIDE.md)。这些实验入口会执行仿真，并检查历史根文档；如提示文档更新，先使用当前完整性检查核对归档。不要删除结果或改写旧保护清单来跳过核验。

仅展示已有成果无需重新训练。生成器与统计脚本通常禁止覆盖已有输出；重跑应在新目录执行。同一批已查看起点的重复运行不能称为新的独立确认。

## 文档导航与项目边界

| 文档 | 内容 |
|---|---|
| [PROGRAM_GUIDE.md](PROGRAM_GUIDE.md) | 运行、模块与实验入口 |
| [ENVIRONMENT_GUIDE.md](ENVIRONMENT_GUIDE.md) | 环境、兼容与权重位置 |
| [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md) | 实验证据索引 |
| [RESULTS.md](RESULTS.md) | 统一结果与统计口径 |
| [PROJECT_AUDIT.md](PROJECT_AUDIT.md) | 项目完整度与剩余工作 |
| [CONTRIBUTIONS.md](CONTRIBUTIONS.md) | 实现贡献和资产来源 |
| [RELATED_WORK.md](RELATED_WORK.md) | 相关工作核查 |
| [THESIS_OUTLINE.md](THESIS_OUTLINE.md) | 已有论文提纲 |
| [DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md) | 交付与展示清单 |

项目具备本科毕设的工程与实验基础，建议定位为“考虑动作延迟的机器人抓取搬运与失败恢复系统设计及实验分析”。当前仍有窄格侧倒、失抓和物体掉出工作区等失败；输入不是纯视觉，未进行真机验证。论文正文与正式学校格式尚未完成。

README 更新日期：2026-10-14。更新前版本保存在 [README_before.md](reproduction/readme_update_20261014_01/README_before.md)。原算法、权重、结果与历史页面保留。

## 图表核对与重新绘制（2026-10-14）

根目录 `figures/` 的 7 组图已按原始记录更新，见 [图表说明](figures/README.md) 与 [核对报告](reproduction/figures_audit_20261014_01/REPORT.md)。原图与旧脚本完整保存在该报告目录的 `before/` 下。世界模型独立确认、开发集消融与后续 v5 恢复是不同实验，不能合并解释。

以下命令只重绘，不训练、不仿真；建议输出到新目录，避免使已冻结的图表文件哈希发生变化：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -B .\make_figures.py --output-dir .\reproduction\figures_preview
```

## GitHub 项目快照

仓库：[LuckyLivio/Robot_can](https://github.com/LuckyLivio/Robot_can)。克隆、前端与上传完整性说明见 [GITHUB_UPLOAD.md](GITHUB_UPLOAD.md)。最新图表深查及固定训练/开发集复算见 [报告](reproduction/figures_deepcheck_20261014_01/REPORT.md) 与 [图表总览](reproduction/figures_deepcheck_20261014_01/index.html)。

## 最新优化进展（2026-10-15）

当前前端增加版本状态与候选消融，根网址仍为 http://127.0.0.1:8766/ 。历史页面保持原样。

v6 开发集仍为 236/240；v7 合用诊断为 30/37，未通过保留 v6 全部成功案例的门槛。二者均未替换主版本。v8 已完成两轮五路消融，共 370 回合；每轮 v8 为 30/37、v6 为 31/37，未通过门槛，未启动开发对照。已核对实际碰撞几何并执行撤离重规划，但仍存在关节接近限位时的对齐超时和几何规划耗时问题。没有泛化训练或论文写作。

详见 [v6 报告](reproduction/improvement_v6_20261015_01/REPORT.md)、[v7 报告](reproduction/improvement_v7_20261015_01/REPORT.md) 和 [v8 预登记](reproduction/improvement_v8_20261015_01/protocols/study_plan.json)。v8 开始前的根 README 与入口保存在 `reproduction/improvement_v8_20261015_01/before/`，旧保护清单保留。

v8 历史详情：[v8 报告](reproduction/improvement_v8_20261015_01/REPORT.md) · [新前端与回放说明](reproduction/progress_20261015_01/README.md)。

## v9 进展（2026-10-15）

新增关节姿态检查和缓存/分步规划，保持400步预算。最终五路对照：v6为31/37，其余四版均为30/37；没有新增救回，未进入240回合开发集。最大策略与控制计算实测由v8的1783 ms降至v9的49 ms，不能据此保证完整实时链路。

本轮包含一次明确登记的末端坐标系验证修复，修复前记录保留，最终结论使用pilot_b。详见 [v9完整报告](reproduction/improvement_v9_20261015_01/REPORT.md) 和 [新版前端说明](reproduction/progress_v10_20261015_01/README.md)。本轮根文件改前备份在 `reproduction/improvement_v9_20261015_01/before/`。
