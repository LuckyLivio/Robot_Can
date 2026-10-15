> **v12更新（2026-10-15）**：v12已完成：开发236/240；全新60起点确认v12 465/480、v6 473/480；救回1、退步9。对照门槛未通过；配对区间没有高于零，不能宣称总体成功率提升。 [报告](reproduction/improvement_v12_20261015_01/REPORT.md) · [新前端](reproduction/improvement_v12_20261015_01/index.html)。旧v5冻结证据及全部旧资产保留。

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
- [本轮修改前10,270文件索引](reproduction/paper_quality_20261015_01/FILE_INVENTORY.csv)；[旧3,946文件快照分类](WORKSPACE/FILE_INDEX.csv)

建议收藏WORKSPACE及本轮目录`reproduction/paper_quality_20261015_01`。新图和当前提纲优先使用本轮版本；旧写作包用于既有40表与冻结资料，v6—v11另有增补。

演示服务仍从原项目根运行：

```powershell
& .\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1
```

打开 http://127.0.0.1:8766/ ，分类导航为 http://127.0.0.1:8766/WORKSPACE/index.html 。写论文看迁移包03_figures/index.html可直接离线打开。
