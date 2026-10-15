# v5：时间预算与侧倒抓取间隙实验

本目录为独立实验版本。以 v4 AB 为基础，新增 T（恢复时机与剩余步数安排）、S（侧倒抓取间隙）及 TS（组合 v5）。固定 400 步、D=2 动作队列、最多两次恢复尝试；BC k=2 与 Full 共用相同恢复控制器。没有训练或替换任何模型权重，没有修改旧版入口，没有撰写论文。

先读 [整体评估](ASSESSMENT.md)。原始计划在 [study_plan.json](study_plan.json)，开发过程在 [DEVELOPMENT_NOTES.md](DEVELOPMENT_NOTES.md)。开发集选中 v5 后才冻结并生成独立起点；所有确认结果均报告，不能在确认集上重新选择或调整参数。

## 证据位置

| 内容 | 位置 |
|---|---|
| 两轮小测试与原始源码快照 | `pilot_a/`、`pilot_b/` |
| 小测试逐步核验 | `validation_pilot_a.json`、`pilot_acceptance.json` |
| 新模块关闭时复现 v4，几何边界检查 | `mechanism_tests_b.json` |
| T / S / TS 开发集，各 240 回合 | `dev_a/`、`analysis_dev_a/` |
| 开发门槛与冻结 | `promotion_dev_a.json`、`freeze_before_states.json` |
| 新起点、生成验证与输入锁 | `confirmation_starts.hdf5`、`geometry_starts.hdf5`、`confirmation_state_validation.json`、`confirmation_lock.json` |
| 60 个新原生起点，五版共 2400 回合 | `confirmation/`、`analysis_confirmation/` |
| 16 个新几何起点，五版共 80 回合 | `geometry_confirmation/`、`analysis_geometry_confirmation/` |
| 剩余失败、相对救回及退步 | `posthoc_failure_review.json`、`diagnosis_confirmation.json` |
| 机制触发与完整物理回放 | `mechanisms_confirmation.json`、`mechanism_physics.json`、`stress_failure_physics.json` |
| 旧文件保留与最终完整度 | `before_manifest.json`、`delivery_validation.json` |

各个 job 下有 `result.json` 与逐步 `trace.jsonl`。只有 `status: complete` 才是完整结果。图表同时输出 PNG（300 dpi）、SVG 和 PDF。原生实验与人工构造的几何压力测试分开统计；同一起点的多个训练种子和噪声条件不算额外独立起点。

## 在 PyCharm 终端重新核验

以下是 PowerShell 命令，使用项目已配置的虚拟环境，无需重新安装依赖。

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
$STAMP = Get-Date -Format 'yyyyMMdd_HHmmss'
.\.venv\Scripts\python.exe -X utf8 -B -u reproduction\recovery_v5_20261012_01\verify_stage.py --stage confirmation --receipt "validation_confirmation_recheck_$STAMP.json"
.\.venv\Scripts\python.exe -X utf8 -B -u reproduction\recovery_v5_20261012_01\verify_stage.py --stage geometry_confirmation --receipt "validation_geometry_recheck_$STAMP.json"
```

核验读取既有轨迹，逐步重算控制器、D2 队列与噪声，并抽样重新执行物理仿真。它不重新采样起点、不改变控制器、不覆盖原始结果。小测试第一轮必须用它自己的归档源码核验，不能用最终 v5 代码替代。

## 完整重跑冻结实验

确实需要重新执行时使用下列入口。它先核对冻结 SHA-256，在本目录自动创建带时间戳的全新子目录，运行后再核验，原结果保持不变。

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -u reproduction\recovery_v5_20261012_01\rerun_frozen.py --suite native --workers 6
.\.venv\Scripts\python.exe -X utf8 -B -u reproduction\recovery_v5_20261012_01\rerun_frozen.py --suite geometry --workers 2
```

这两条命令分别重跑 2400 / 80 回合，使用已经冻结的同一批起点；它们是重复运行核验，**不能称为另一批独立确认实验**。重跑封装脚本已做语法检查，未为验证封装再重复执行整批实验；底层 `run_stage.py` 和 `verify_stage.py` 已在本轮实际运行。结果若需继续改进，应另建目录、预登记、开发验收，再使用新的独立起点。

## 初始化修正记录

`prepare_confirmation.py` 的首次预检未通过：原生几何重新生成复用了从 XML 还原过的仿真模型；后续又发现 `env.step` 返回观测与保存状态的前向运动学刷新时点不同。冻结的原生成器与第一次修正脚本快照保留。

`complete_state_validation.py` 使用独立原生/序列化环境，并在比较观测前统一 `sim.forward` 和传感器刷新。没有修改 76 个已生成物理起点、种子、姿态、控制器或权重。修正记录在 [initialization_validation_amendment.json](initialization_validation_amendment.json)，登记时间早于新起点上的任何策略运行。实际评价始终使用同一个既有 `restore_demo`。后续复现直接读取冻结起点即可，不要在原目录重新执行生成器覆盖它们。

## 结论边界

T 包含启动时机、下降无进展中止和预算紧张时的有界移动安排，当前消融分离的是模块整体，未逐一分离内部阈值的作用。S 是固定场景下的夹爪几何候选筛选，不是整臂轨迹规划器，也不保证任意抓持稳定。仿真使用低维状态观测，未包含视觉估计误差或实机测试。共享恢复的收益不能解释为世界模型本身预测能力变强。
