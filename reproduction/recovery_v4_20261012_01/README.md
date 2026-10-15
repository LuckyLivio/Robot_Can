# v4 隔离开发实验

**状态：实现及开发实验完成，未达到独立确认推进门槛，保留 v2 为参考版本。**

先阅读 [最终评估](ASSESSMENT.md)。本目录不替换任何旧入口、权重、控制器或结果；没有论文文件。开发集 v2 为 229/240，仅方向切换 229/240，仅区域约束 231/240，组合 231/240。新增两次成功均来自已知 demo_188；无新增失败。

## 文件入口

| 文件 | 用途 |
|---|---|
| recovery_controller.py | v2 基础上的观察量控制器，A/B 两项独立开关 |
| study_plan.json | 运行前登记设计、通过门槛和预定新种子 |
| DEVELOPMENT_NOTES.md | 两轮小测试及实现调整记录 |
| pilot_a、pilot_b | 各 100 回合，原始状态/动作、结果、日志、源码快照 |
| dev_a | 三个候选共 720 新回合；v2 使用保护的历史同协议对照 |
| analysis_dev_a | 成功率、配对差值、逐例 CSV、PNG/SVG 图表 |
| promotion_dev_a.json | 未通过推进门槛的判定，未选中确认候选 |
| mechanism_physics.json | 已知对齐/角落案例的事后物理诊断 |
| diagnosis_dev_a.json | 剩余失败逐例记录 |
| delivery_validation.json | 本轮验证汇总及旧文件保护检查 |

控制器的 `Config(alignment_switch=True, region_guard=False)` 为 A，`Config(alignment_switch=False, region_guard=True)` 为 B，两项都开启为 AB；两项关闭经 4959 步动作/事件复算与 v2 完全一致。B 包含区域与几何约束下的角落处理，不只是一个无行为影响的布尔检查。A 包含无进展检测、有限等待、安全退回及等价方向重试；本轮是两个模块级消融，没有声称拆分了模块内部每个阈值的独立贡献。

## 在 PyCharm PowerShell 终端复跑

以下明确指定已有虚拟环境，不要求修改全局 Python。运行目录为 `C:\Users\Livio\Desktop\robot_can`。每次必须使用尚不存在的输出目录名，工具会拒绝覆盖旧结果。

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
.\.venv\Scripts\python.exe -X utf8 -B -u reproduction/recovery_v4_20261012_01/run_pilot.py --revision pilot_user_01 --jobs pilot_jobs_b.json --workers 4
```

开发集复跑（720 回合，沿用原开发起点，不是独立确认）：

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -u reproduction/recovery_v4_20261012_01/run_stage.py --stage dev_user_01 --jobs dev_jobs.json --workers 6
.\.venv\Scripts\python.exe -X utf8 -B -u reproduction/recovery_v4_20261012_01/analyze_stage.py --stage dev_user_01
.\.venv\Scripts\python.exe -X utf8 -B -u reproduction/recovery_v4_20261012_01/verify_stage.py --stage dev_user_01
```

仅重做行为边界检查并保存新收据：

```powershell
.\.venv\Scripts\python.exe -X utf8 -B reproduction/recovery_v4_20261012_01/test_mechanisms.py mechanism_tests_user_01.json
```

不要重新运行 `bootstrap.py` 或 `prepare_pilot.py`，它们是本次首次建档工具，会拒绝覆盖已有文件。`prepare_confirmation.py` 是条件流程的预备程序，本轮未执行；它要求开发通过收据和冻结文件，当前故意不具备这些条件。若未来修改控制器，应另建目录、登记新设计并重新做小测试，不在本目录覆盖已经评估的源码或结果。

## 适用范围

PickPlaceCan / Panda，23 维特权低维观测、固定箱体几何，20 Hz，真实 D=2 动作队列，最多 400 步、两次恢复尝试。BC 与 Full 使用同一恢复实现。Full 的三个固定训练种子在统计时按起点内求均值；不把重复执行当成更多独立起点。

区域规则仅覆盖合法直立角落，侧倒近墙抓取仍是明确缺口。程序或轨迹核验通过不等于控制器具备任意姿态成功保证，也不等于真实机器人硬件验证。
