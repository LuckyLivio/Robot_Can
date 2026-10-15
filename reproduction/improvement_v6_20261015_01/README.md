# 恢复控制 v6 实验目录

**先看 [REPORT.md](REPORT.md)。** 本轮已完成，结论为：小测试 29/37 → 31/37，240 回合开发对照仍为 236/240，无新增失败。开发提升门槛未通过，当前不替换旧版本、不启动泛化训练。本目录没有论文正文。

## 文件导航

| 路径 | 用途 |
|---|---|
| `recovery/recovery_controller.py` | 开度确认、等待、无可行候选退回/保持 |
| `recovery/clearance_guard.py` | 候选检查和两类几何模型 |
| `evaluate_recovery.py` / `variants.py` | 统一冻结策略评估与消融开关 |
| `protocols/` | 初始门槛、失败修订说明、作业清单和开发前冻结清单 |
| `pilot_a/` | 第一轮失败修订；保留其源代码、全部结果和轨迹 |
| `pilot_b/` | 通过的小测试与四组消融；148 回合 |
| `dev_a/` | 冻结新版本的开发结果；240 回合 |
| `analysis/` | 成功数、逐回合 CSV、失败审计和验证回执 |
| `figures/` | 3 张图的 PNG/PDF 和对应曲线数据 |
| `before_manifest.json` | 7,464 个旧文件的 SHA-256 保护清单 |

原 v1–v5、旧权重、旧结果与旧路径未修改。当前新代码通过导入 v5 复用控制逻辑，因此单独搬走本目录不足以运行；请保留完整项目及原数据/权重。

## 查看结果

直接打开 `REPORT.md`、`analysis/dev_pairs.csv` 和 `figures/` 即可，不需要重新跑实验。

## 如需自己重新执行

以下命令必须在项目根目录执行。输出使用新目录名，保护已经完成的本轮结果。

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
$RUN = 'reproduction\improvement_v6_20261015_01'
$STAGE = 'pilot_rerun_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
& '.\.venv\Scripts\python.exe' -X utf8 -B "$RUN\run_batch.py" --stage $STAGE --jobs protocols/pilot_jobs_a.json --workers 4
& '.\.venv\Scripts\python.exe' -X utf8 -B "$RUN\verify_run.py" --stage $STAGE --protected
& '.\.venv\Scripts\python.exe' -X utf8 -B "$RUN\verify_physics.py" --stage $STAGE
```

该命令使用当前冻结修订版和相同 37 条件，对四组各跑一遍，共 148 回合。`pilot_jobs_a.json` 是两轮共用的诊断清单；实际控制器版本由每轮保存的 `source/` 和 SHA-256 区分。

重跑冻结新版本的 240 回合开发对照：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
$RUN = 'reproduction\improvement_v6_20261015_01'
$STAGE = 'dev_rerun_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
& '.\.venv\Scripts\python.exe' -X utf8 -B "$RUN\run_batch.py" --stage $STAGE --jobs protocols/dev_jobs.json --workers 4
& '.\.venv\Scripts\python.exe' -X utf8 -B "$RUN\verify_run.py" --stage $STAGE --protected
& '.\.venv\Scripts\python.exe' -X utf8 -B "$RUN\verify_physics.py" --stage $STAGE
```

不要再次运行 `prepare_pilot.py` / `prepare_dev.py` 来覆盖登记信息。已保存的分析和制图程序使用排他创建文件：输出存在时会停止，避免静默覆盖证据。重跑不产生新的独立确认结论；它只是对同一已知起点的复现。
