# v18：下降控制衔接与受保护的短路线

本轮是新目录中的候选改进，没有替换 v17、预算候选、既有代码、训练权重或实验结果。保持 400 步、D2 FIFO、20 Hz、原保护阈值和成功定义。未做泛化训练，未写论文。

## 结果与范围

已完成六组共 54 回合小测试及消融，每组 9 个条件、共用 8 个不同起点：实际 v16 为 2/9，实际 v17 为 3/9，原预算 C 为 7/9，衔接单项、短路线单项、完整 v18 均为 2/9。预算组的持物保护与当前版本不同，不能整体采用。

**完整 v18 未通过门槛，未采用。** 三个预登记目标未完成，12000036 从 v17 成功变为失败。564 次扩展诊断、v16/v17/v18 各 240 次开发（共 720 次）、1440 次全新起点独立确认均未运行；未生成新确认起点。本组是已知困难案例，2/9 不能解释为整个项目的总体成功率。

- [完整报告](REPORT.md) · [机器可读汇总](SUMMARY.json)
- [执行前正式协议](protocols/PLAN.md) · [源码与输入锁](protocols/protocol_lock.json)
- [小测试统计](analysis/smoke_a.json) · [逐条件 CSV](analysis/smoke_a_pairs.csv)
- [真实下降衔接诊断](analysis/smoke_a_handoff_diagnosis.json)
- [真实路线诊断](analysis/smoke_a_route_diagnosis.json) · [关键案例逐帧分析](analysis/smoke_a_route_findings.json)
- [图表与来源](figures/CATALOG.json) · [旧版本报告](../improvement_v17_20261019_01/REPORT.md)

## 前端启动

在 PyCharm PowerShell 终端执行：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：

**http://127.0.0.1:8766/reproduction/improvement_v18_20261019_01/index.html**

若 8766 已有本项目服务，直接打开地址即可；不用重复启动。服务终端保持运行，用 Ctrl+C 停止。页面展示本轮实际数据与图表，不会启动实验。历史 v14 视频明确标注版本，本轮没有新拍的 v18 机器人视频。

## 文件用途

| 路径 | 内容 |
|---|---|
| `recovery/` | 新控制器、无状态衔接 helper、四候选短路线搜索 |
| `protocols/` | 执行前协议、54/564 登记作业、输入与源码锁 |
| `smoke_a/` | 54 个真实回合、原始观察/动作/FIFO、日志、运行源码快照 |
| `analysis/` | 独立静态检查、组件、全关等价、逐步核验、物理回放及诊断 |
| `figures/` | 600 dpi PNG、矢量 PDF/SVG、CSV 及来源哈希 |
| `validation/` | 文档、浏览器、图表与阶段门槛核验 |
| `before/` | 本轮修改前九份入口文档的原样备份 |
| `before_manifest.json` | 本轮开始前 13,123 个已跟踪路径的哈希 |
| `delivery_manifest.json` | 本轮最终交付文件及更新入口的哈希 |

## 核验与复现

从项目根目录执行以下命令可检查最终文件、旧文件保留及已执行阶段；**不会重新运行物理实验**：

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B 'reproduction\improvement_v18_20261019_01\verify_integrity.py'
```

结果统计也可以只读重算，不传 `--save` 不覆盖已有结果：

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B 'reproduction\improvement_v18_20261019_01\analyze.py' --stage smoke_a
```

原始运行命令如下，仅记录本次如何执行；`smoke_a` 已存在，运行器会拒绝覆盖：

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B -u 'reproduction\improvement_v18_20261019_01\run_batch.py' --stage smoke_a --jobs protocols/smoke_jobs.json --workers 4
```

执行前需四份源码绑定回执和协议锁全部匹配。保存输入重放与物理回放是已有轨迹核验，不是新增成功率样本。不要修改已锁定文件来绕过后续阶段门槛；下一候选应另建目录、重新登记并保留本轮负结果。

## 下一步候选方向

1. 将衔接修复限制在短过渡段，验证能否避免整个下降阶段多耗时间。
2. 给新增路线单独分配验证预算，避免挤占既有候选和放置、释放所需时间。
3. 单独检查 D2 下持物末端的连续到位，保持 9 mm / 0.08 rad 和原五帧条件。

这些是待验证方案，未在本轮继续实现或作为已改善结果。
