# 统一成果与版本索引

## 当前入口

[展示](reproduction/consolidation_20261012_01/demo/index.html) · [结果](RESULTS.md) · [贡献](CONTRIBUTIONS.md) · [统计](STATISTICS.md) · [相关工作](RELATED_WORK.md) · [交付清单](DELIVERY_CHECKLIST.md)

最新只读验收：[figures_audit/verify.py](reproduction/figures_audit_20261014_01/verify.py)；本次全项目复查和侧倒/失抓播放修复见[报告](reproduction/playback_fix_20261012_01/REPORT.md)。旧验证清单保留，授权修改的页面和指南映射到补丁前归档。

## 研究过程

| 目录/版本 | 作用 | 当前使用方式 |
|---|---|---|
| queuepair / candidate_truth / headcal / tailprobe | 一致性、同状态真值、评分校准与续接探索 | 开发诊断，不作新独立确认 |
| multiseed_20261012_01 | 15训练任务、18权重、60开发评估 | 三种子公平消融，全部种子保留 |
| confirmation_20261012_01 | 原世界模型14任务840回合 | 无共享恢复的原确认；60起点 |
| extensions_20261012_01 | 88任务900回合 | 持续性、短期oracle、H/K已完成 |
| recovery_20261012_01（v1） | 抓持/失抓、持物停滞 | 原240回合开发改善，仍有失败 |
| recovery_v2_20261012_01 | 长期无进展、侧倒与几何恢复 | 开发和独立确认，含关闭恢复对照 |
| recovery_v3_20261012_01 | 对齐/角落探索 | 确认未整体超过v2，负结果保留 |
| recovery_v4_20261012_01 | 等价方向切换、区域约束 | 自身开发推进门槛未通过；作为v5冻结参考后来被评价 |
| recovery_v5_20261012_01 | T时间、S侧倒间隙及组合 | 最新完成开发/冻结/新确认，局部改善不代表全面恢复 |
| release / review | 原视频、旧文档与Apple页面 | 历史展示保持原样 |
| consolidation_20261012_01 | 本次成果与文献整合、旧四组统计、新前端 | 不新增策略/训练回合 |

每个实验目录内的protocol/design/study_plan/lock、result/trace与validation为原始证据，目录中的旧评估按当时进度解释。不能因当前结果更新而改写过去门槛或负结果。

## 新增分析与可查资产

[已有四组对照](reproduction/consolidation_20261012_01/FACTORIAL_REVIEW.md)、[整合数据](reproduction/consolidation_20261012_01/evidence.json)、[文献元数据](reproduction/consolidation_20261012_01/references_metadata.json)、[BibTeX](reproduction/consolidation_20261012_01/references_verified.bib)、[未来草案](reproduction/consolidation_20261012_01/FOLLOWUP_PLAN.md)。

13份本次修改前根文档位于[previous_documents](reproduction/consolidation_20261012_01/previous_documents/)。旧 make_figures.py 与旧图已归档于 reproduction/figures_audit_20261014_01/before/；当前 make_figures.py 读取真实回合与训练记录重绘，见 [图表说明](figures/README.md)。RESULTS_TABLE.csv 等历史表不作当前主表。原ADAPTIVE_PROTOCOL是另一条探索线，不能混入本轮确认。

版本：2026-10-12 成果整合版；旧根文档见 reproduction/consolidation_20261012_01/previous_documents/
