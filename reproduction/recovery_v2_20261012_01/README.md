# 恢复控制v2：隔离实现与前瞻确认

本目录独立保存新版代码、所有小测试、开发集、冻结协议、新起点和确认结果。原项目和上一版恢复目录均不修改；旧文件清单见 `before_manifest.json`。没有训练或替换权重，没有撰写论文。

当前控制链路：原BC k=2或Full候选评分 → 当前状态历史上的恢复判断 → 必要时规则控制 → 原D=2 FIFO → 原动作噪声 → MuJoCo。总预算仍为400步。固定任务目标、箱体几何和当前23维状态属于显式特权输入；控制器不读取接触真值、奖励或未来分支。

相对v1的改动：

- 在近距离短期停滞之外，累计“最佳接近距离没有实质改善”的时间。最低80步后才启用未抓持干预；65步无新的接近进展可接管；到第160步尚未抓持且未到目标区域时，为恢复保留预算。已经确认抓持的状态仍使用持物进展判断。
- 从物体四元数估计圆柱轴方向。侧倒时让夹爪闭合方向垂直于物体轴，并调整网格原点至抓取位置的偏移及高度。
- 直立物体按当前源料箱或目标箱的边壁、隔板选择抓取方向。先保持原朝向回撤，再在上方旋转对齐，避免边回撤边大幅转动。
- 其余执行约束、重试上限、正常策略、权重、评分与成功判据保持原设定。规则不能覆盖任意障碍、地面拾取或所有罐体姿态。

| 文件或目录 | 用途 |
|---|---|
| recovery_controller.py | 新版观测式抓持、长期停滞和抓取几何逻辑 |
| evaluate_recovery.py | 同一执行循环支持disabled、v1、v2；记录全部控制步 |
| study_plan.json | 在实验前登记开发集门槛和主确认设计 |
| pilot_a、pilot_b | 全部工程试运行与源码快照，失败版本也保留 |
| pilot_acceptance.json、interface_qa | 小测试验收、旧接口逐步等价对照 |
| dev_a、analysis_dev_a | 240回合开发集及完整配对分析 |
| promotion.json | 自动检查预先登记的晋级条件 |
| freeze_before_states.json | 开发集通过后、生成新起点之前冻结版本 |
| confirmation_state_validation.json | 60个新原生重置起点的独立生成、重复生成和旧起点排重 |
| confirmation_lock.json | 主确认及独立几何测试的输入哈希和环境版本 |
| confirmation、analysis_confirmation | 三个版本共1440回合主确认与统计 |
| geometry_confirmation、geometry_comparison.json | 独立12起点、两版共24回合的机制验证 |
| validation_*.json | 旧文件保护、逐控制步校验及抽样物理重放 |

主确认的60个起点按预先指定的种子426101201至426101260生成，全部保留，不根据策略结果筛选。三个版本共享相同初态、模型和动作噪声。Full使用17/23/41三个固定训练种子，BC只有一个固定策略，不重复计算为三个训练种子。主确认不注入故障，也不强制接管。

几何确认使用另外12个初始化种子，预先设置侧倒或贴近箱壁的初始姿态并完成物理稳定。两版均在第80步开始恢复，基础动作固定为静止张爪，用于隔离抓取机制；这些结果不混入主任务成功率。只有初始化设置了物体姿态，恢复运行中不重置或传送物体。

最初的 `pilot_starts.hdf5`、`pilot_jobs.json`、`pilot_state_description.json` 保存了未投入测试的初始化草案。预运行发现第二个侧倒方向的旋转组合顺序不符合设计，随后新建了带 `_fixed` 后缀的初态文件；所有实际小测试都使用修正后的初始化。该修正发生在策略测试之前，没有按结果筛选起点。

数据含义：`success`是最终任务成功；`ever_grasped`保留旧版双指接触标签的含义；`stable_hold_observed`和`verified_regrasps`是观测式确认，不能与真值抓持或最终成功混为一谈。故障测试或几何确认中的固定动作由作业参数明确标记。

在PyCharm的PowerShell终端重新核验已有主确认结果，可生成新的回执而不覆盖旧文件：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
$RECOVERY_AUDIT = 'recheck_confirmation_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '.json'
& '.\.venv\Scripts\python.exe' -X utf8 -B -u '.\reproduction\recovery_v2_20261012_01\verify_stage.py' --stage confirmation --receipt $RECOVERY_AUDIT
```

执行脚本默认拒绝覆盖已有阶段目录、结果和分析文件。不要删除已完成结果来重跑；后续改进应另建目录、重新登记协议，不能把这里已经看过结果的确认起点再次称为未见测试集。
