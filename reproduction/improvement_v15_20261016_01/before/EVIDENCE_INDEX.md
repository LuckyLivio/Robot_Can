# 证据索引 · 当前入口

**v14 两轮小测试共64次；最终 v13 / T / C / v14 为6/8、6/8、5/8、6/8。门槛未通过，未采用；未运行大规模消融、240次开发或全新起点确认。**

[本轮检查报告](reproduction/improvement_v14_20261016_01/REPORT.md) · [v14前端](reproduction/improvement_v14_20261016_01/index.html) · [执行前协议](reproduction/improvement_v14_20261016_01/protocols/PLAN.md) · [v13原报告](reproduction/improvement_v13_20261016_01/REPORT.md)

[本轮原始配对表](reproduction/improvement_v14_20261016_01/analysis/smoke_b_pairs.csv) · [本轮图表](reproduction/improvement_v14_20261016_01/figures/CATALOG.json) · [完整度检查脚本](reproduction/improvement_v14_20261016_01/verify_integrity.py)

## 历史内容（以下为此前文档，按原版本时间解释）

> **v13更新（2026-10-16）**：v13完成：开发236/240；全新60起点确认v6 445/480、v12 437/480、v13 448/480。未通过本轮对照采用门槛，保留为候选；主要配对区间未完全高于零，不能宣称总体成功率改善。 [报告](reproduction/improvement_v13_20261016_01/REPORT.md) · [前端](reproduction/improvement_v13_20261016_01/index.html)。旧代码、权重、结果保留。

# 当前证据索引

[v13前端](reproduction/improvement_v13_20261016_01/index.html) · [v13完整报告](reproduction/improvement_v13_20261016_01/REPORT.md) · [当前校验](reproduction/improvement_v13_20261016_01/verify_integrity.py) · [图表目录](reproduction/improvement_v13_20261016_01/figures/CATALOG.json)。

| 本轮内容 | 权威记录 |
|---|---|
| 执行前门槛 | [PLAN](reproduction/improvement_v13_20261016_01/protocols/PLAN.md) |
| 完整与中断执行台账 | [inventory](reproduction/improvement_v13_20261016_01/analysis/execution_inventory.json) |
| 小测试及四组消融 | [smoke_e](reproduction/improvement_v13_20261016_01/analysis/smoke_e.json)、[pilot_a](reproduction/improvement_v13_20261016_01/analysis/pilot_a.json) |
| 240开发 | [dev_a](reproduction/improvement_v13_20261016_01/analysis/dev_a.json) |
| 60新起点、1440配对执行 | [统计](reproduction/improvement_v13_20261016_01/analysis/confirmation.json)、[配对CSV](reproduction/improvement_v13_20261016_01/analysis/confirmation_pairs.csv) |
| 冻结与初态复核 | [锁](reproduction/improvement_v13_20261016_01/protocols/confirmation_lock.json)、[初态](reproduction/improvement_v13_20261016_01/analysis/confirmation_state_validation.json) |
| 剩余失败与耗时 | [diagnosis](reproduction/improvement_v13_20261016_01/analysis/confirmation_diagnosis.json) |
| 历史v12 | [报告](reproduction/improvement_v12_20261015_01/REPORT.md) |

## 历史记录（截至2026-10-15；按原批次解释）

> 历史阶段：2026-10-15论文图表复查：[新图与数据总览](reproduction/paper_quality_20261015_01/index.html) · [全项目报告](reproduction/paper_quality_20261015_01/REPORT.md) · [当前提纲与证据映射](reproduction/paper_quality_20261015_01/THESIS_OUTLINE_REVIEWED.md)。36张图重新生成；没有新增训练、仿真或论文正文。

# 当前成果与版本索引（2026-10-15）

[历史展示](reproduction/improvement_v12_20261015_01/index.html) · [历史校验](reproduction/improvement_v12_20261015_01/verify_integrity.py) · [全仓审查](reproduction/project_audit_20261015_01/REPORT.md) · [结果](RESULTS.md) · [贡献](CONTRIBUTIONS.md) · [统计](STATISTICS.md)

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
