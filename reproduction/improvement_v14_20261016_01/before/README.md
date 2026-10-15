> **v13更新（2026-10-16）**：v13完成：开发236/240；全新60起点确认v6 445/480、v12 437/480、v13 448/480。未通过本轮对照采用门槛，保留为候选；主要配对区间未完全高于零，不能宣称总体成功率改善。 [报告](reproduction/improvement_v13_20261016_01/REPORT.md) · [前端](reproduction/improvement_v13_20261016_01/index.html)。旧代码、权重、结果保留。

# 动作延迟下的机器人抓取搬运与失败恢复

Panda机械臂在PickPlaceCan仿真中抓取罐子并放入目标箱。BC生成动作块，世界模型预测并评分候选，FIFO执行器施加真实动作延迟；共享恢复控制器处理抓持确认、无进展、失抓和重新搬运。

实验使用含物体真值位置/姿态的23维状态，恢复器另读当前7关节角与固定任务几何。主要协议为20Hz、D=2、400步、最多两次抓取尝试；不是纯视觉或真机实验。

## 在PyCharm启动前端

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1
```

保持终端运行，打开 **http://127.0.0.1:8766/** 。根入口自动跳到v13。已有该端口服务时直接打开，不必重复启动。关闭服务按`Ctrl+C`；另用端口时命令和网址一起修改。


[直接打开v13](http://127.0.0.1:8766/reproduction/improvement_v13_20261016_01/index.html) · [历史完整展示](reproduction/progress_v11_20261015_01/demo/index.html) · [v12结果](reproduction/improvement_v12_20261015_01/index.html)。

前端是静态HTML/CSS/JavaScript，不需要npm或Node.js。必须在项目根目录启动HTTP服务；启动服务不会运行训练或机器人仿真。视频和曲线均来自保存实验。根路径只出现文件列表通常意味着入口文件缺失或启动了别的目录，请检查工作目录。

## 最新评估

本轮完整阶段共1976次评估执行，另保留中断批次的17个完成单任务与2个不完整任务。没有泛化训练或论文正文。正式v5冻结证据继续保留；v13与v6/v12的本批比较不能直接证明优于另批v5。

| 阶段 | 结果 | 证据边界 |
|---|---|---|
| 最终小测试 | v12 3/6、S 5/6、R 3/6、v13 6/6 | 已知诊断 |
| 四组消融 | v12 32/50、S 40/50、R 32/50、v13 41/50 | 50执行条件，复用部分起点 |
| 开发 | v6/v12/v13均236/240，无新增退步 | 30固定起点×8条件；没有提高成功率 |
| 独立确认 | v6 445/480、v12 437/480、v13 448/480 | 本轮冻结后60个新起点×8条件，按起点配对统计 |


[v13完整报告](reproduction/improvement_v13_20261016_01/REPORT.md)列出全部失败、统计区间、门槛及核验。v13新增侧倒箱沿/斜靠支撑资格检查，以及长等待后最多一次受检撤退重规划。S同时包含新支撑家族的路径入口；R单独没有提高已知成功数，不能夸大其独立效果。

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
| `reproduction/improvement_v13_20261016_01/` | 本轮控制器、源码快照、原始轨迹、统计、图表和前端 |
| `data/` | 数据、划分和来源校验 |
| `WORKSPACE/` | 分类导航，原始路径保留 |

[运行指南](PROGRAM_GUIDE.md) · [环境说明](ENVIRONMENT_GUIDE.md) · [结果](RESULTS.md) · [证据索引](EVIDENCE_INDEX.md) · [项目导航](PROJECT_NAVIGATION.md) · [演示讲解](DEMO_GUIDE.md) · [当前状态](STATUS.md)。

## 环境和完整性检查

PyCharm解释器使用`C:\Users\Livio\Desktop\robot_can\.venv\Scripts\python.exe`。已有环境可以继续使用；显式指定解释器不受终端`(base)`前缀影响。

```powershell
& '.\.venv\Scripts\python.exe' -c "import sys; print(sys.executable); print(sys.version)"
& '.\.venv\Scripts\python.exe' -m pip check
```

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v13_20261016_01/verify_integrity.py
```

只读检查本轮前10982个登记路径、9份活动文档的原样备份、当前交付清单及开发/确认冻结锁。不会训练或仿真。旧verify绑定当时根文档，可能因后续授权更新而提示差异；不要改旧manifest或删除结果绕过检查。


仿真重跑命令见[本轮README](reproduction/improvement_v13_20261016_01/README.md)，使用新的阶段目录，不能覆盖既有输出。重复旧起点只算复核，不是新的独立确认。

## 图表、迁移与项目边界

本轮5张图提供600dpi PNG、矢量PDF/SVG、CSV及源哈希，见[图表解释](reproduction/improvement_v13_20261016_01/FIGURE_GUIDE.md)。平台是等待，折点是原始控制/状态切换；曲线不平滑，成功后按真实终点结束。两段新视频为20fps逐步物理回放。此前36张论文图仍保留在[旧图表包](reproduction/paper_quality_20261015_01/FIGURE_CATALOG.md)。

换设备请使用同步后的完整Git项目。旧ZIP不含v12/v13，单独复制v13目录也缺少继承模块和权重。详见[跨设备说明](THESIS_HANDOFF_LATEST.md)。

项目具备本科毕设的工程与实验材料，仍有恢复失败、规划耗时峰值和有限泛化范围；不能宣称世界模型稳定优于强BC、任意物体泛化或真机安全。正式学校要求、论文正文和答辩仍需另行完成。本轮未写论文。

当前README更新于2026-10-16；修改前原样文件在`reproduction/improvement_v13_20261016_01/before/README.md`。所有旧算法、权重、结果及历史页面保留。
