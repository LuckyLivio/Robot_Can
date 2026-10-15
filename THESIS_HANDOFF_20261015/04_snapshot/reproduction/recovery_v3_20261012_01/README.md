# Recovery v3：独立实验目录

请先读 [最终评估](ASSESSMENT.md)：独立确认 v3 为 434/480，v2 为 436/480，本轮不建议用 v3 替代 v2。完整数据见 [REPORT.md](REPORT.md)，开发过程见 [DEVELOPMENT_NOTES.md](DEVELOPMENT_NOTES.md)。这些是工程与实验记录，未撰写论文。

环境仍使用项目根目录的 `.venv`；本目录没有替换旧代码或权重。PyCharm 工作目录设为 `C:\Users\Livio\Desktop\robot_can`，解释器选择其中的 `.venv\Scripts\python.exe`。

## 查看结果

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
$R = 'reproduction\recovery_v3_20261012_01'
Get-Content "$R\delivery_validation.json" -Raw
Get-Content "$R\analysis_confirmation\summary.json" -Raw
```

主要文件：`REPORT.md`、`analysis_confirmation/success_comparison.png`、`analysis_confirmation/episodes.csv`、`geometry_comparison.json`。失败原因、救回与退步清单在 `diagnosis_confirmation.json`。

## 重新核查冻结后的结果

以下只复核日志、输入哈希、D=2 队列和抽样物理轨迹，不重新训练。`--receipt` 必须用未存在的新文件名，以保留原验证记录。

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B -u "$R\verify_stage.py" --stage confirmation --receipt validation_confirmation_manual_01.json
& '.\.venv\Scripts\python.exe' -X utf8 -B -u "$R\verify_stage.py" --stage geometry_confirmation --receipt validation_geometry_manual_01.json
```

## 在额外目录复跑某个固定任务

例如复跑 v3 + BC、无噪声、同一批 60 个确认起点。输出目录必须未包含 `result.json` 或 `trace.jsonl`。这是复核既有测试，不是新的独立确认。

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B -u "$R\evaluate_recovery.py" --job-file "$R\confirmation_jobs.json" --job-id v3_bc_k2_clean --output-dir "$R\manual_check_01\v3_bc_k2_clean"
```

Full 三个任务使用 `v3_full_s17_clean`、`v3_full_s23_clean`、`v3_full_s41_clean`。加噪声任务把 `_clean` 换成 `_noise005`。

## 版本与实验口径

- `recovery_controller.py` 为本轮最终控制器；BC 与 Full 共享。网络权重、候选评分、D=2、400 步和两次恢复限制不变。
- `pilot_a` 至 `pilot_e` 保留每次原型的控制器/评估器源码快照；`dev_a`、`dev_b`、`dev_c` 为同一开发集的三次不同实现，不能合并成更多独立样本。
- `dev_a`、`dev_b` 的验证收据记录的是对应代码版本当时的通过状态；当前控制器属于最终版本，不能直接用它重新解释旧版本动作日志。旧源码保存在各自 `source/` 中。
- `confirmation` 是冻结后的四版本公平对照，60 个唯一原生起点 × 两种噪声 ×（BC 一组 + Full 三训练种子）× 四版本，共 1920 回合。
- `geometry_confirmation` 另有 16 个新几何起点 × v2/v3，共 32 回合。使用固定静止张爪提议、相同第 80 步恢复触发，属于机制压力测试，单独统计。
- 不要重复运行 `bootstrap.py`、`adapt_tools.py` 或 `adapt_confirmation.py`；它们记录首次建档过程。实验脚本用独占创建保护原结果。新方法开发应另建目录，不能在本目录冻结后继续调整并沿用独立测试结论。

本目录不改变既有前端演示；本次工作范围是控制改进、实验和评估。
