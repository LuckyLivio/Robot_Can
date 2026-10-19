# v19：过渡窗口、候选预算与终端收敛

**小测试门槛未通过；保留候选和负结果，未进入大规模消融、开发或独立确认。**

本目录保存独立的v19实现、固定协议、真实执行、核验与图表。父版本和历史权重/结果保留；本轮不训练、不写论文。

## 查看前端

在项目根目录的 PowerShell / PyCharm Terminal 执行：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1
```

保持该终端运行，浏览器打开完整页面地址：

[http://127.0.0.1:8766/reproduction/improvement_v19_20261019_01/index.html](http://127.0.0.1:8766/reproduction/improvement_v19_20261019_01/index.html)

如果8766已经由同一项目根目录提供服务，直接打开上述地址。当前根地址会跳转到v19页面；为避免打开旧入口，建议使用上述完整地址。

## 结果与证据

- 已完成评估：72次；采用状态：未采用。
- [完整报告](REPORT.md) / [机器可读汇总](SUMMARY.json) / [执行前协议](protocols/PLAN.md)。
- [图表目录及来源](figures/CATALOG.json)：600 dpi PNG、矢量PDF/SVG和原始绘图CSV。
- 每组9个小测试profile包括8个标准起点和1个复用6000005的配置；八组执行不能相加当作独立样本。
- A/B/C/AB/ABC全部继承完整v18。旧v15预算组保护不同，仅作成功数参考。

| 后续阶段 | 预定执行数 | 当前状态 |
|---|---:|---|
| 已知条件消融 | 752 | 未运行 |
| 开发对照 | 720 | 未运行 |
| 独立确认 | 1440 | 未运行 |

保存输入回放、物理回放和静态检查均不是新增统计样本。论文使用本目录数据时，应保留阶段、版本、分母和保护差异说明。

## 重新生成交付文件

仅在对应完整结果、动作/物理核验、五项有效预检以及人工核对的report_findings都已存在时运行：

```powershell
& '.\.venv\Scripts\python.exe' -B -X utf8 'reproduction/improvement_v19_20261019_01/build_delivery.py'
```

该命令只读取保存结果，不启动实验。已有图表会验证来源和输出哈希；若变化则拒绝覆盖。首次导出图表需要本机nature-figure的Python布局核验工具，可通过FIGURE_QA_SCRIPTS指定其scripts目录。

## 只读核验

最终交付封存后，从项目根目录执行；不会重跑实验：

```powershell
& '.\.venv\Scripts\python.exe' -B -X utf8 'reproduction/improvement_v19_20261019_01/verify_integrity.py'
```

检查旧文件保留、九份入口备份、当前交付文件及实验源码与结果哈希。
