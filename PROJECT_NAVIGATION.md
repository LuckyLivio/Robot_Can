# 项目分类导航 · 当前入口

**v16已完成63次七组小测试：v14 / v15 / 预算候选 / IK修复 / 持物修复 / 箱沿修复 / 完整v16为6/9、4/9、7/9、2/9、4/9、2/9、2/9。门槛未通过，完整v16未采用。**

9个条件包含8个标准条件和1个复用6000005起点的预算配置profile，只有8个不同起点。标准条件下v16为2/8、v15为3/8、v14为6/8。三个修复单项分别加在完整v15之上；预算候选沿用原v15仅预算配置。

局部IK找到更多合法路径，部分持物转向达标，但没有提高整回合成功率。新的等待、规划与运输耗时导致预算不足，另有等价大角转向超时及观测失抓信号并触发恢复。预算模块继续保留为候选。既有正式成果不替换；658次扩展消融、三版各240次开发（共720次）和1440次全新起点确认均未运行。

[本轮完整报告](reproduction/improvement_v16_20261016_01/REPORT.md) · [v16前端](reproduction/improvement_v16_20261016_01/index.html) · [执行前协议](reproduction/improvement_v16_20261016_01/protocols/PLAN.md) · [v15原报告](reproduction/improvement_v15_20261016_01/REPORT.md)



[本轮逐条件配对表](reproduction/improvement_v16_20261016_01/analysis/smoke_a_pairs.csv) · [图表与来源](reproduction/improvement_v16_20261016_01/figures/CATALOG.json) · [完整度检查](reproduction/improvement_v16_20261016_01/verify_integrity.py)

## 历史内容（以下按各自版本和时间解释）

# 项目分类导航 · 当前入口

**v15已完成45次五组小测试：v14 / 仅搬运A / 仅分段B / 仅预算C / 完整v15为6/9、3/9、6/9、7/9、4/9。小测试未通过，v15未采用。**

9个条件包含8个标准条件和1个复用6000005起点的预算配置profile，不能当作9个独立起点。标准条件下完整v15为3/8、父v14为6/8；预算专用profile为v15成功、父版失败。

预算模块单独运行救回时间不足案例且未损失旧成功；搬运模块的局部IK误拒和转向耗时导致三个旧成功退步，两个主难例仍未完成。因此不替换既有正式成果，不进入470次消融、两版各240次开发或1440次全新起点确认。

[本轮完整报告](reproduction/improvement_v15_20261016_01/REPORT.md) · [v15前端](reproduction/improvement_v15_20261016_01/index.html) · [执行前协议](reproduction/improvement_v15_20261016_01/protocols/PLAN.md) · [v14原报告](reproduction/improvement_v14_20261016_01/REPORT.md)



[本轮逐条件配对表](reproduction/improvement_v15_20261016_01/analysis/smoke_a_pairs.csv) · [图表与来源](reproduction/improvement_v15_20261016_01/figures/CATALOG.json) · [完整度检查](reproduction/improvement_v15_20261016_01/verify_integrity.py)

## 历史内容（以下按各自版本和时间解释）

# 项目导航 · 当前入口

**v14 两轮小测试共64次；最终 v13 / T / C / v14 为6/8、6/8、5/8、6/8。门槛未通过，未采用；未运行大规模消融、240次开发或全新起点确认。**

[本轮检查报告](reproduction/improvement_v14_20261016_01/REPORT.md) · [v14前端](reproduction/improvement_v14_20261016_01/index.html) · [执行前协议](reproduction/improvement_v14_20261016_01/protocols/PLAN.md) · [v13原报告](reproduction/improvement_v13_20261016_01/REPORT.md)

[本轮原始配对表](reproduction/improvement_v14_20261016_01/analysis/smoke_b_pairs.csv) · [本轮图表](reproduction/improvement_v14_20261016_01/figures/CATALOG.json) · [完整度检查脚本](reproduction/improvement_v14_20261016_01/verify_integrity.py)

## 历史内容（以下为此前文档，按原版本时间解释）

> **v13更新（2026-10-16）**：v13完成：开发236/240；全新60起点确认v6 445/480、v12 437/480、v13 448/480。未通过本轮对照采用门槛，保留为候选；主要配对区间未完全高于零，不能宣称总体成功率改善。 [报告](reproduction/improvement_v13_20261016_01/REPORT.md) · [前端](reproduction/improvement_v13_20261016_01/index.html)。旧代码、权重、结果保留。

# 项目总导航

- 最新实现、结果和视频：[reproduction/improvement_v13_20261016_01/](reproduction/improvement_v13_20261016_01/README.md)。
- 直接查看：[v13前端](reproduction/improvement_v13_20261016_01/index.html)；总报告：[v13完整报告](reproduction/improvement_v13_20261016_01/REPORT.md)。
- 启动与复核：[README](README.md)、[PROGRAM_GUIDE](PROGRAM_GUIDE.md)、[DEMO_GUIDE](DEMO_GUIDE.md)。
- 全阶段证据：[EVIDENCE_INDEX](EVIDENCE_INDEX.md)、[RESULTS](RESULTS.md)。
- 跨设备：[THESIS_HANDOFF_LATEST](THESIS_HANDOFF_LATEST.md)。旧包不含v12/v13，使用完整同步项目。
- 旧路径未移动；分类入口仍在[WORKSPACE](WORKSPACE/index.html)。

## 历史记录（截至2026-10-15；按原批次解释）

> 历史阶段：2026-10-15论文图表复查：[新图与数据总览](reproduction/paper_quality_20261015_01/index.html) · [全项目报告](reproduction/paper_quality_20261015_01/REPORT.md) · [当前提纲与证据映射](reproduction/paper_quality_20261015_01/THESIS_OUTLINE_REVIEWED.md)。36张图重新生成；没有新增训练、仿真或论文正文。

> [全项目审查与清理/调整计划](reproduction/project_audit_20261015_01/REPORT.md) · [审查网页](reproduction/project_audit_20261015_01/index.html)

# 项目分类总导航

原路径保留；新增用途分组，不搬移冻结源码、权重、数据或历史结果。

- [打开分类导航](WORKSPACE/index.html)
- [源码与模块](WORKSPACE/01_code/README.md)
- [文档与规范](WORKSPACE/02_documents/README.md)
- [实验与证据](WORKSPACE/03_experiments/README.md)
- [数据与权重](WORKSPACE/04_data_weights/README.md)
- [前端与图表](WORKSPACE/05_visualization/README.md)
- [当前论文交接说明](THESIS_HANDOFF_LATEST.md)；[旧迁移包](THESIS_HANDOFF_20261015/00_READ_FIRST.md)
- [该历史阶段修改前10,270文件索引](reproduction/paper_quality_20261015_01/FILE_INVENTORY.csv)；[旧3,946文件快照分类](WORKSPACE/FILE_INDEX.csv)

建议收藏WORKSPACE及该历史阶段目录`reproduction/paper_quality_20261015_01`。新图和当前提纲优先使用该历史阶段版本；旧写作包用于既有40表与冻结资料，v6—v11另有增补。

演示服务仍从原项目根运行：

```powershell
& .\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1
```

打开 http://127.0.0.1:8766/ ，分类导航为 http://127.0.0.1:8766/WORKSPACE/index.html 。写论文看迁移包03_figures/index.html可直接离线打开。
