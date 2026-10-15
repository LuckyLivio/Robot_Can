> 2026-10-15论文图表复查：[新图与数据总览](reproduction/paper_quality_20261015_01/index.html) · [全项目报告](reproduction/paper_quality_20261015_01/REPORT.md) · [当前提纲与证据映射](reproduction/paper_quality_20261015_01/THESIS_OUTLINE_REVIEWED.md)。36张图重新生成；没有新增训练、仿真或论文正文。

# 当前成果与版本索引（2026-10-15）

[当前展示](reproduction/progress_v11_20261015_01/demo/index.html) · [当前校验](reproduction/paper_quality_20261015_01/verify.py) · [全仓审查](reproduction/project_audit_20261015_01/REPORT.md) · [结果](RESULTS.md) · [贡献](CONTRIBUTIONS.md) · [统计](STATISTICS.md)

| 阶段 | 完成情况与使用边界 | 权威入口 |
|---|---|---|
| 数据/队列/真值/评分诊断 | 开发与机制定位，非独立确认 | [队列](reproduction/queuepair_20261012_01/)、[真值](reproduction/candidate_truth_20261012_01/)、[校准](reproduction/headcal_20261012_01/) |
| 三种子公平消融 | 60组1800开发回合 | [报告](reproduction/multiseed_20261012_01/analysis/report.txt) |
| 原世界模型确认 | 840回合、60起点，无共享恢复 | [报告](reproduction/confirmation_20261012_01/analysis/report.txt) |
| 补充实验 | 持续性/oracle/H/K，900回合，已经完成 | [报告](reproduction/extensions_20261012_01/REPORT.md) |
| v1—v4 | 恢复探索、已有四组对照及负结果 | [四组汇总](reproduction/consolidation_20261012_01/FACTORIAL_REVIEW.md) |
| v5主线 | 开发236/240，确认464/480，压力12/16 | [评估](reproduction/recovery_v5_20261012_01/ASSESSMENT.md) |
| v6候选 | 开度/重复下降，开发236/240，未采用 | [报告](reproduction/improvement_v6_20261015_01/REPORT.md) |
| v7候选 | 最终30/37；pilot_a中断，pilot_b完整 | [报告](reproduction/improvement_v7_20261015_01/REPORT.md) |
| v8候选 | 两轮五路消融均未通过门槛 | [报告](reproduction/improvement_v8_20261015_01/REPORT.md) |
| v9候选 | 关节姿态与耗时；坐标系修订有记录 | [报告](reproduction/improvement_v9_20261015_01/REPORT.md) |
| v10候选 | 箱沿高度/路径，最终30/37 | [报告](reproduction/improvement_v10_20261015_01/REPORT.md) |
| v11候选 | 31/37；开发235/240；箱沿救回，整体未采用 | [报告](reproduction/improvement_v11_20261015_01/REPORT.md) |
| 图表深查 | 固定集泛化、评分敏感性与原始图替代表达 | [报告](reproduction/figures_deepcheck_20261014_01/REPORT.md) |
| 写作迁移 | c8bbe86旧主线 + fad3100候选增补 + 新图表提纲包 | [当前交接说明](THESIS_HANDOFF_LATEST.md) |

所有实验目录的protocol/design/study_plan/lock保留执行前字节；负结果及未启动阶段不删除。历史报告按当时范围阅读，不拿旧“尚未完成”覆盖后来的记录。RESULTS_TABLE.csv是早期历史表，当前结果以本索引链接的配对记录为准。ADAPTIVE_PROTOCOL是另一条历史探索线。

全文件和逐结果台账：[FILE_INVENTORY](reproduction/paper_quality_20261015_01/FILE_INVENTORY.csv)、[RESULT_LEDGER](reproduction/paper_quality_20261015_01/RESULT_LEDGER.csv)。
