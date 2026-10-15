# 写作材料交接状态 · 当前入口

**v14 两轮小测试共64次；最终 v13 / T / C / v14 为6/8、6/8、5/8、6/8。门槛未通过，未采用；未运行大规模消融、240次开发或全新起点确认。**

[本轮检查报告](reproduction/improvement_v14_20261016_01/REPORT.md) · [v14前端](reproduction/improvement_v14_20261016_01/index.html) · [执行前协议](reproduction/improvement_v14_20261016_01/protocols/PLAN.md) · [v13原报告](reproduction/improvement_v13_20261016_01/REPORT.md)

既有跨设备写作包是历史封存材料，不包含本轮v14新增文件。当前不更新论文正文或把v14写成已确认优势；若之后写作，使用本轮报告准确说明门槛失败。

[本轮原始配对表](reproduction/improvement_v14_20261016_01/analysis/smoke_b_pairs.csv) · [本轮图表](reproduction/improvement_v14_20261016_01/figures/CATALOG.json) · [完整度检查脚本](reproduction/improvement_v14_20261016_01/verify_integrity.py)

## 历史内容（以下为此前文档，按原版本时间解释）

> **v13更新（2026-10-16）**：v13完成：开发236/240；全新60起点确认v6 445/480、v12 437/480、v13 448/480。未通过本轮对照采用门槛，保留为候选；主要配对区间未完全高于零，不能宣称总体成功率改善。 [报告](reproduction/improvement_v13_20261016_01/REPORT.md) · [前端](reproduction/improvement_v13_20261016_01/index.html)。旧代码、权重、结果保留。

# 跨设备资料交接（2026-10-16）

最新资料为[v13完整报告](reproduction/improvement_v13_20261016_01/REPORT.md)及其源数据、五张新图和两段视频。本轮没有论文正文，也没有改写旧论文提纲；后续写作需将本轮结论和负结果补入相应实验章节，不能沿用旧提纲中停在v11/v12的状态描述。

**旧ZIP不包含v12和v13。换设备请使用同步后的完整Git项目，或完整复制robot_can项目（虚拟环境需在新设备重新配置）。只复制v13目录无法运行继承的v5—v12模块，也缺少数据与冻结权重。** GitHub入口：https://github.com/LuckyLivio/Robot_can 。

| 内容 | 路径 |
|---|---|
| 本轮整体评估 | [reproduction/improvement_v13_20261016_01/REPORT.md](reproduction/improvement_v13_20261016_01/REPORT.md) |
| 最新实现与原始轨迹 | `reproduction/improvement_v13_20261016_01/recovery/`、各阶段`result.json`与`trace.jsonl` |
| 配对数据与统计 | `reproduction/improvement_v13_20261016_01/analysis/confirmation_pairs.csv`、`confirmation.json` |
| 新图、图注、CSV | [图表说明](reproduction/improvement_v13_20261016_01/FIGURE_GUIDE.md)、`reproduction/improvement_v13_20261016_01/figures/` |
| 视频与回放验证 | `reproduction/improvement_v13_20261016_01/demo/`、`analysis/demo_replay_*.json` |
| 旧详细提纲与36张图 | [提纲](reproduction/paper_quality_20261015_01/THESIS_OUTLINE_REVIEWED.md)、[图目录](reproduction/paper_quality_20261015_01/FIGURE_CATALOG.md) |
| 原始迁移包 | [说明](reproduction/portable_delivery_20261015_01/README.md) |

旧迁移包的本机移位、标准库环境和前端检查属于历史验收，不能声称新设备已经验证。新设备先按[环境指南](ENVIRONMENT_GUIDE.md)配置，再按[运行指南](PROGRAM_GUIDE.md)检查；使用`verify_integrity.py`做字节核验。当前完整成果以v13报告为准，旧包只作历史资料。

写作边界：60独立起点不等于480独立样本；共享恢复收益不归因于世界模型；真值状态不等于视觉感知；不同确认批次不直接拼接。旧v5冻结证据和所有失败结果保留。本科毕设工程材料已较完整，论文论证、学校格式和答辩准备尚需完成。
