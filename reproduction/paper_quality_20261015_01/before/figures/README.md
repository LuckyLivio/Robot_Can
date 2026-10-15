# 当前图表的实验口径

更新：2026-10-14。7 组 PNG（300 dpi）与矢量 PDF 从原始回合 / 训练日志生成；没有新增训练或策略回合。绘图入口为根目录 `make_figures.py`。

| 文件前缀 | 数据与含义 |
|---|---|
| figure_success_rate | confirmation_20261012_01：每条件 60 个共同起点；BC k=2 固定权重，Full / Plain 各 3 个训练种子；不含共享恢复 |
| figure_paired_clean | 同一独立确认的无噪声逐起点配对；按三个 Full 种子分别展示 |
| figure_paired_noise005 | 同上，动作噪声标准差 0.05 |
| figure_success_steps | 同一起点双方都成功的 Full−BC 步数差；各种子分别作图；不代表全体回合效率 |
| figure_ablation | multiseed_20261012_01 开发集；每条件 30 个已查看起点；Full、Plain、Direct、仅预测、无风险评分、无门控；不能当独立确认 |
| figure_training_curves | multiseed Full 三种子训练日志；横轴为真实 step，每 250 次更新记录一次；原始批次损失与开发集 regret 分面展示 |
| figure_method_diagram | 世界模型确认配置的选择流程；D=2、H=8、k=0..3、k=2 回退；不含 v1–v5 恢复 |

训练曲线连接的是真实采样点，未平滑，没有补造缺失的逐 step 或 epoch 数据。总损失包含预测、进展、风险和排序项，不能从单条预测损失推断总损失必须单调下降。开发集 regret 是离散候选选择的评价，不是闭环成功率。

成功率柱为均值，蓝 / 绿 / 橙点对应种子 17 / 23 / 41（BC 只有固定权重）。种子点的分散不是起点抽样置信区间；三个模型共享同批起点，不能把 60 个起点算成 180 个独立起点。配对置信区间见原 [确认分析](../reproduction/confirmation_20261012_01/analysis/paired_comparisons.csv)。Full 相对 Plain 的联合区间跨零，不能声称排序损失已被证明有效。

`figure_data.json` 保存全部绘图数值、配对步数及源文件 SHA-256。脚本在绘图前检查重复/缺失起点、原始 JSON 与索引逐行一致、各组起点一致以及成功率与原分析表一致。它核对 840 条确认记录与 1,800 条开发记录，不代表新增独立样本。

原图和原脚本见 [before](../reproduction/figures_audit_20261014_01/before/)，具体问题见 [核对报告](../reproduction/figures_audit_20261014_01/REPORT.md)。后续恢复实验仍使用其原目录内图表与独立起点；本轮未改前端或历史页面里的图。

在项目根目录 PowerShell 重新绘制到新目录：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -B .\make_figures.py --output-dir .\reproduction\figures_preview
```

只读完整性核验：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -B .\reproduction\figures_audit_20261014_01\verify.py
```
