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
- [当前审查前10,146文件索引](reproduction/project_audit_20261015_01/FILE_INVENTORY.csv)；[旧3,946文件快照分类](WORKSPACE/FILE_INDEX.csv)

建议在PyCharm中收藏WORKSPACE和THESIS_HANDOFF_20261015。图表可参考旧迁移包的详细图注，但它不含v6—v11；当前根THESIS_OUTLINE与最新交接说明补充候选版本边界。

演示服务仍从原项目根运行：

```powershell
& .\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1
```

打开 http://127.0.0.1:8766/ ，分类导航为 http://127.0.0.1:8766/WORKSPACE/index.html 。写论文看迁移包03_figures/index.html可直接离线打开。
