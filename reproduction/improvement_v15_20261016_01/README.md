# v15 · 持物搬运与箱沿分段路径

本目录保存 v15 新控制器、执行前协议、全部小测试正负结果、源快照及核验。历史 v14 及以前代码、权重和实验保持原样。最新结论以 [检查报告](REPORT.md) 与 [机器可读汇总](SUMMARY.json) 为准。

## 打开前端

在项目根目录的 PyCharm PowerShell 终端运行；已有 8766 服务时直接打开下面的完整地址。

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

http://127.0.0.1:8766/reproduction/improvement_v15_20261016_01/index.html

终端保留运行；按 Ctrl+C 停止服务。网页只展示封存成果，不启动训练或控制实验。

## 文件与证据

- [执行前协议](protocols/PLAN.md)：400步、原保护阈值、信息边界与各阶段门槛。
- `recovery/recovery_controller.py`：三个独立开关和与 v14 的兼容入口。
- `recovery/carry_path.py`：真实观测持物包络、搬运与放置IK、分段路径检查。
- `recovery/edge_path.py`：先平移、后转向、再接近和下降的箱沿路径。
- `protocols/smoke_jobs.json`：9个条件profile×5组；同一起点不同profile不当作独立样本。
- `protocols/pilot_jobs.json`：预先准备的470次已知条件消融；文件存在不代表已执行。
- `smoke_*/`：每次修订独立目录，包含作业、源快照、日志、逐步观测/动作和结果。
- `analysis/`：逐条件比较、门槛、保存输入回放、物理回放和静态诊断。
- [图表目录](figures/CATALOG.json)：原始CSV、600dpi PNG、矢量PDF/SVG及来源哈希。
- `before/` 与 `before_manifest.json`：原入口文档备份及全部旧跟踪文件哈希。
- `delivery_manifest.json` 与 `integrity_receipt.json`：交付封存与完整性回执。

## 只读检查

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -X utf8 -B 'reproduction/improvement_v15_20261016_01/verify_integrity.py'
& '.\.venv\Scripts\python.exe' -X utf8 -B 'reproduction/improvement_v15_20261016_01/analyze.py' --stage smoke_a
```

`analyze.py` 不加 `--save` 时只复算并显示。原始实验、核验回执与图表均禁止覆盖。若报告列出后续修订，使用相应stage。新实验必须使用新目录，并按门槛推进；未过小测试不能直接运行470次消融、两版各240次开发或全新起点确认。

持物包络是观测刚体相对位姿代理；局部IK不是实际OSC跟踪或完整机械臂碰撞证明。当前结果属于特权状态仿真，不能解释为视觉闭环、实机或普遍泛化验证。本轮不做泛化训练，也不写论文。
