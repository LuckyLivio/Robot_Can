# v20：方向衔接与延迟制动

**小测试门槛未通过；保留候选和负结果，未进入大规模消融、开发或独立确认。**

本目录保存独立的v20实现、固定协议、真实执行、核验与图表。父版本和历史权重/结果保留；本轮不训练、不写论文。

## 查看前端

在项目根目录的 PowerShell / PyCharm Terminal 执行：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

保持该终端运行，浏览器打开完整页面地址：

[http://127.0.0.1:8766/reproduction/improvement_v20_20261019_01/index.html](http://127.0.0.1:8766/reproduction/improvement_v20_20261019_01/index.html)

如果8766已经由同一项目根目录提供服务，直接打开上述地址。根入口会跳转当前v20报告；建议使用完整版本地址以明确查看的版本。

## 结果与证据

- 已完成评估：54次；采用状态：未采用。
- [完整报告](REPORT.md) / [机器可读汇总](SUMMARY.json) / [执行前协议](protocols/PLAN.md)。
- [图表目录及来源](figures/CATALOG.json)：600 dpi PNG、矢量PDF/SVG和原始绘图CSV。
- 每组9个小测试profile包括8个标准起点和1个复用6000005的配置；六组执行不能相加当作独立样本。
- v19/A/B/A+B是两因素2×2配对诊断；A/B/A+B全部继承完整v19。旧预算组本轮实际重跑，但保护不同，仅作成功数参考。

| 后续阶段 | 预定执行数 | 当前状态 |
|---|---:|---|
| 已知条件消融 | 564 | 未运行 |
| 开发对照 | 720 | 未运行 |
| 独立确认 | 1440 | 未运行 |

保存输入回放、物理回放和静态检查均不是新增统计样本。论文使用本目录数据时，应保留阶段、版本、分母和保护差异说明。

## 文件导航

- `recovery/`：本轮独立控制器与两个helper；旧代码、权重和结果保持原路径。
- `protocols/`：正式协议、六组作业登记与执行前源码锁；登记不等于运行。
- `smoke_*` 等阶段目录：原始结果、逐步轨迹与冻结源码快照。
- `analysis/`：结果汇总、消融配对、静态检查、两类回放及观察诊断。
- `figures/`：600 dpi PNG、矢量PDF/SVG、CSV、来源哈希和布局回执。
- `validation/`：文件、图表、页面与文档的交付核验，范围以回执为准。

## 只读完整性核验

交付封存后，在项目根目录执行；该命令检查哈希和已有回执，不运行实验：

```powershell
& '.\.venv\Scripts\python.exe' -B -X utf8 'reproduction/improvement_v20_20261019_01/verify_integrity.py'
```

## 重新生成交付文件

仅在对应完整结果、动作/物理核验、四项有效预检以及人工核对的report_findings都已存在时运行：

```powershell
& '.\.venv\Scripts\python.exe' -B -X utf8 'reproduction/improvement_v20_20261019_01/build_report.py'
```

该命令只读取保存结果，不启动实验。已有图表会验证来源和输出哈希；若变化则拒绝覆盖。布局和字号检查使用项目内代码，不依赖另一台设备的个人技能路径。PDF渲染和实际视觉复查须另行执行并保留回执。
