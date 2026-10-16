# v16：局部 IK、持物转向与箱沿稳位

本轮完成 **63 次七组闭环小测试，完整 v16 为 2/9，门槛未通过，未采用**。原 v14 / v15 / 预算候选 / IK 修复 / 持物修复 / 箱沿修复分别为 6/9、4/9、7/9、2/9、4/9、2/9。三个修复单项均加在完整 v15 上；预算候选仍是原 v15 的仅预算模块。

9 个条件包含 8 个标准条件和 1 个复用 6000005 起点的配置 profile，不能当成 9 个独立起点。标准条件 v16 为 2/8；所有正负结果均保留。658 次扩展消融、三版各 240 次开发（共 720 次）、1440 次独立确认均未运行，未生成新确认起点。没有泛化训练或论文正文。

[完整评估](REPORT.md) · [前端](index.html) · [执行前协议](protocols/PLAN.md) · [原始配对表](analysis/smoke_a_pairs.csv) · [图表目录](figures/CATALOG.json) · [父版本 v15](../improvement_v15_20261016_01/REPORT.md)

## 启动前端

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v16_20261016_01/index.html**。已有 8766 服务时直接打开，不重复启动。根地址也会跳转到本轮页面。

本轮页面展示数据、失败原因和新图，没有新增 v16 机器人视频。链接的 v14 演示属于历史记录。

运行仍依赖原项目中的 v5–v15 模块、数据集和冻结权重。换设备应使用完整 Git 项目并重新配置环境，不能只复制本目录。

## 文件导航

| 位置 | 内容 |
|---|---|
| `recovery/recovery_controller.py` | 独立 v16 监督器；全部新开关关闭时精确复现 v15 |
| `recovery/carry_search.py` | 有界连续 IK、原接受区域内部的目标、完整分段路径证书 |
| `recovery/pose_servo.py` | 观测运动制动、混合平移与转向的名义几何包络检查 |
| `smoke_a/` | 63 次原始结果、逐步轨迹、日志和实际运行源码快照 |
| `analysis/` | 七组配对统计、机制检查、动作审计、物理回放及失败诊断 |
| `protocols/` | 执行前方案、63/658 次固定条件、前置保护记录 |
| `figures/` | 600 dpi PNG、矢量 PDF/SVG、CSV、来源哈希和布局检查 |
| `before/`、`before_manifest.json` | 九个入口文档原样备份与 12,535 条既有路径保护 |
| `validation/` | 文档、图表、前端、阶段门槛及历史诊断说明 |

保留 400 步、20 Hz、D2 FIFO、最多两次抓取、100 项继承参数。局部路径使用 0.04 rad 关节余量与原几何阈值。几何检查是当前观测下的名义手/物体路径证书，不代表完整机械臂、未来延迟执行或抓持稳定性的保证。

## 核验

交付封存后，可重复执行以下只读核验，不会重跑物理实验：

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B 'reproduction\improvement_v16_20261016_01\verify_integrity.py'
```

`verify_mechanisms.py`、`verify_components.py`、`verify_run.py` 和 `verify_physics.py` 的现有回执位于 `analysis/`；物理回放重复已有轨迹，不增加统计样本。原脚本使用独占文件创建，不能覆盖已有回执或实验目录。

`protocols/pilot_jobs.json` 只是预登记的 658 次作业。`freeze_development.py` 在本轮小测试结果门槛处拒绝继续，见 [门槛核验](validation/development_gate.json)。不要把已准备的脚本和作业写成已完成实验。

## 当前判断

局部 IK 和部分持物转向有机制层面的进展，但整体成功率下降。本轮不能替换既有正式成果，也不能作为泛化改善证据。下一步应优先去重公共路径求解、减少不必要干预、按实际执行耗时安排可完成路径，并单独处理持物打滑；保护阈值和 400 步预算继续保持。
