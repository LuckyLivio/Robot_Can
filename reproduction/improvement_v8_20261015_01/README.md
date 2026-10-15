# v8 候选：实际几何与有界撤离重规划

**两轮五路消融完成，未达标，不替换主版本。** 两轮各 185 回合，共 370 回合；v6 31/37，v8 30/37。没有启动 240 回合开发集、泛化训练或论文写作。

- [报告与下一步](REPORT.md)
- [最终检查凭据](analysis/final_receipt.json)
- [预登记](protocols/study_plan.json) / [第二轮修订](protocols/revision_b.md)
- [配对结果 CSV](analysis/pilot_b_pairs.csv) / [原始运动指标](analysis/motion_metrics.csv)
- [关节限位诊断](analysis/alignment_diagnosis.json) / [计算耗时](analysis/decision_timing.json)
- [前端入口](../progress_20261015_01/demo/index.html)

`recovery/` 保存候选实现与静态几何，`pilot_a/`、`pilot_b/` 各保存当轮源代码、日志、原始轨迹及结果；`before/` 是本次授权修改的根 README 和页面入口的逐字节备份。旧权重、代码、实验结果和历史前端原位保留。

所有执行器仍为最多 400 步、20 Hz 仿真时钟、D=2。几何规划一次可能耗时约 1.7 秒，目前不代表实时控制能力。当前不应直接启动开发对照。
