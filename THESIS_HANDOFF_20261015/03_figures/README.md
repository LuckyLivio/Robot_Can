# 论文图包

先打开 [index.html](index.html) 离线看图，再读 [FIGURE_CATALOG.md](FIGURE_CATALOG.md) 中的19组详细图注、实验批次、样本量、单位、可支持的结论和限制。

- 44个既有PNG/PDF/SVG文件，全部与源字节一致；主要采用第二轮深核查图，避免用10月9日旧图。
- [FIGURE_PROVENANCE.csv](FIGURE_PROVENANCE.csv)：逐文件原路径、现路径、SHA-256、格式与视觉检查。
- [FIGURE_GROUPS.json](FIGURE_GROUPS.json)：可供其他写作软件读取的详细图注。
- [source_material](source_material/)：49个与图有关的小型测量表、JSON、报告和代码来源。原脚本部分包含推理或仿真，请不要为写论文执行它们。
- [system_overview.mmd](system_overview.mmd)：包含共享规则恢复的系统总图Mermaid源码，仅为结构示意，不是新增实验测量。原世界模型方法草图另在F01。
- [verify_figures.py](verify_figures.py)：只用Python标准库校验本图包，既不推理也不运行仿真；不需要装PyTorch、MuJoCo。

在本目录终端可以执行：

```powershell
python -B verify_figures.py
```

F09与F19完全同源、表达不同，正文择一。图号按八章提纲给建议，排版后统一编号。这个图包保留负结果，不代表实验完美或论文已经通过审核。
