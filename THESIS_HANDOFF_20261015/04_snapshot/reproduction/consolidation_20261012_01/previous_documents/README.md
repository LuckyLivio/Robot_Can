# 动作延迟下的机器人世界模型控制

版本：2026-10-12 冻结确认后的文档整理版。历史文档完整保存在 [previous_documents](reproduction/release_20261012_01/previous_documents/)。

Panda 机械臂在 PickPlaceCan 仿真中抓取罐子并放入目标箱。固定 BC 动作块策略提供候选；世界模型预测候选后果并用进度/抓持丢失评分选择动作，通过 FIFO 执行队列模拟 2 步延迟。

**当前范围是包含物体真值的23维低维状态控制，未实现纯视觉或真机验证。** 已完成三种子公平消融及冻结后的60个新起点确认。本仓库是实现、复现与实验分析项目，未证明各条件均显著领先或排序模块具有稳定独立增益。

## 当前入口

- [PROJECT_AUDIT](PROJECT_AUDIT.md)：2026-10-12全项目复核、未完成项及本科毕业设计适用性。
- [新版机器人演示](reproduction/review_20261012_01/demo/index.html)：Apple风格改版，沿用冻结视频与结果。

- [PROGRAM_GUIDE](PROGRAM_GUIDE.md)：环境、模块和可复制命令。
- [RESULTS](RESULTS.md)：当前结果，开发与确认分表。
- [STATISTICS](STATISTICS.md)：统计单位、区间和解释边界。
- [THESIS_OUTLINE](THESIS_OUTLINE.md)：更新后的论文提纲与证据映射。
- [DEMO_GUIDE](DEMO_GUIDE.md)：相同起点机器人对比演示及讲解顺序。
- [STATUS](STATUS.md)：已完成、未完成及交付边界。

## 冻结确认摘要

每个控制器/条件60回合；Full、Plain按训练种子17、23、41列出成功数。BC为一个固定权重。

| 方法 | 干净：成功数；平均成功率 | 噪声0.05：成功数；平均成功率 |
| --- | --- | --- |
| BC k=2 | 51；85.00% | 49；81.67% |
| Full | 54、54、54；90.00% | 52、52、51；86.11% |
| Plain（去排序） | 53、53、53；88.33% | 50、51、50；83.89% |

Full相对BC在干净、加噪条件的平均提升分别为5.00、4.44个百分点；分条件95%配对区间均接触零。预登记两条件等权综合提升4.72个百分点，描述性区间[0.56,10.28]；仍应结合小样本和Full−Plain结果解释。[三种子开发消融](reproduction/multiseed_20261012_01/analysis/report.txt) · [独立确认报告](reproduction/confirmation_20261012_01/analysis/report.txt) · [冻结哈希清单](reproduction/release_20261012_01/frozen_results.json)

## 保存约定

不覆盖 models、policy、data、既有reproduction和figures中的原始文件。原视频和上一版页面位于 `reproduction/release_20261012_01/demo/`；当前前端位于 `reproduction/review_20261012_01/demo/`，引用同一批视频。冻结表示哈希锁定与防覆盖流程，并非修改文件系统只读属性。

根目录 `make_figures.py`、`RESULTS_TABLE.csv` 及旧 `figures/` 是历史产物，不用于当前主结论；本轮图表在 [确认图目录](reproduction/confirmation_20261012_01/analysis/) 和 [三种子图目录](reproduction/multiseed_20261012_01/analysis/)。

2026-10-12本次复核保存了修改前的11份根文档，见[本轮文档归档](reproduction/review_20261012_01/previous_documents/)。本轮不写论文正文，当前保护与验收入口见[运行指南](PROGRAM_GUIDE.md)。
