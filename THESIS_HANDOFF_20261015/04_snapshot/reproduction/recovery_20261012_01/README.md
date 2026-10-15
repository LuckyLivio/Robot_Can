# 隔离恢复控制实验

已完成240回合开发集实验。先读本目录的 `REPORT.md`；此目录为新增工程实验，没有替换原项目。

执行链路：原BC/Full决策 → 观测式抓持/停滞/失抓检测 → 必要时共享恢复控制 → 原D=2动作队列 → 原动作噪声 → MuJoCo。原有模型文件不变，没有新增训练。

入口与用途：

| 文件 | 用途 |
|---|---|
| recovery_controller.py | 独立状态机与观测式抓持确认 |
| evaluate_recovery.py | 原决策与恢复层的运行适配、逐步记录 |
| run_pilot.py | 训练起点小测试，按新revision保存源码快照 |
| validate_small.py | 夹爪、坐标、原评测程序逐步等价性 |
| validate_held_stall.py | 物理持物停滞故障测试与Full小测试 |
| freeze_study.py | 小测试验收、冻结参数、登记正式作业 |
| run_formal.py | 执行冻结的240回合；拒绝覆盖已有formal目录 |
| analyze_results.py | 从全部正式原始结果生成汇总与图表 |
| verify_results.py | 旧文件保护、输入哈希、逐步重放及四条MuJoCo轨迹抽查 |

所有控制器动作使用当前状态和固定几何；不读接触真值、阶段奖励或未来分支。`ever_grasped`保留旧评测的双指接触含义；`stable_hold_observed`是观测规则，`verified_regrasps`是抬升跟随确认次数；只有`success`代表任务最终成功。

现有结果已经完成，无需重新运行。以下命令可在PyCharm的PowerShell终端重新核验，生成新的核验回执，不覆盖旧结果：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
$RECOVERY_CHECK = 'verification_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '.json'
& '.\.venv\Scripts\python.exe' -X utf8 -B -u '.\reproduction\recovery_20261012_01\verify_results.py' --receipt $RECOVERY_CHECK
```

`run_formal.py`在已有目录上拒绝再次运行是保存机制，不是环境错误。新实验应使用新的隔离目录和协议，不要删除当前formal目录来强行重跑。当前冻结协议中的输入哈希仍引用原工作区文件，不能直接通过移动文件后忽略校验来复现。

主要结果：BC从25/30、24/30提升至28/30、27/30；Full三个种子合计从71/90、74/90提升至79/90、86/90。以上依次为干净和含噪声条件。共享恢复层带来收益，但两类方法跨条件成功率均为91.7%，且存在20次失败；完整边界见报告。
