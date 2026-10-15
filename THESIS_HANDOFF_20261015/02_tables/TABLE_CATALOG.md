# 论文数据表目录与使用口径

全部数值从已存在的 JSON/CSV 导出，原始小数保留在 UTF-8 BOM CSV 中，便于 Excel/Word/脚本读取。此次只计算计数、单位转换、已有指标首末差等描述性整理；没有训练、仿真、checkpoint 推理或新增 bootstrap。

## 使用次序

正文主要结果优先 T01/T02（WM 独立确认）和 T18/T20/T21（共享恢复独立确认）；T05/T06 用于消融，T12–T17 用于机制诊断；T26–T29 与 T30–T40 用于局限性或附录。不同 cohort 不可直接计算因果提升。

## 必须保留的限制

- 60 个起点在多个种子和两个噪声条件下重复使用，不能把 180/360/480 次执行写成独立样本数。
- WM 主确认的 Full 相对 BC 改善较小；Full 相对 Plain 的区间包含 0，排序模块的独立增益未得到清晰确认。
- v5 原生确认中，同样有恢复的 BC 成功率高于 Full；不能用恢复总收益证明世界模型优于全部强基线。
- v5 相对 v4 净救回只集中在少数起点；pointwise CI 不含多重比较校正、不能证明普适等效。
- 满成功、零不一致或固定种子可能导致 bootstrap 区间退化为零宽；不能声称不存在不确定性。
- 训练曲线复算显示 train/dev 差距，反复使用的 8 个分支开发父回合不足以证明广泛泛化。
- 并行执行时记录的 decision_ms 受机器/负载影响，保留供追溯，不能作为严格延迟性能基准。

本目录共 40 张数据表，引用 25 个源文件，自动检查 204 项。逐表 SHA 见 PROVENANCE.csv。

## T01_wm_confirmation_summary.csv — 世界模型独立确认主表

- 行数：9；cohort：`wm_confirmation_60_new_starts`；独立 N：60；种子数：row-specific。
- 证据性质：`independent_confirmation`。
- 用法与限制：独立确认：60 个全新起点，clean/noise 重用同一批起点；BC 固定权重，Full/Plain 各 3 个训练种子。联合结果等权平均两条件，仍只有 60 个独立起点。区间沿用原有配对交叉 bootstrap。
- 源文件：`reproduction/confirmation_20261012_01/analysis/summary.csv`。

## T02_wm_confirmation_paired.csv — 世界模型独立确认配对差值

- 行数：9；cohort：`wm_confirmation_60_new_starts`；独立 N：60；种子数：3。
- 证据性质：`independent_confirmation`。
- 用法与限制：独立确认：60 个全新起点，clean/noise 重用同一批起点；BC 固定权重，Full/Plain 各 3 个训练种子。联合结果等权平均两条件，仍只有 60 个独立起点。区间沿用原有配对交叉 bootstrap。
- 源文件：`reproduction/confirmation_20261012_01/analysis/paired_comparisons.csv`。

## T03_wm_confirmation_per_seed.csv — 世界模型独立确认逐种子结果与截断步数

- 行数：14；cohort：`wm_confirmation_60_new_starts`；独立 N：60；种子数：row-specific。
- 证据性质：`independent_confirmation`。
- 用法与限制：独立确认：60 个全新起点，clean/noise 重用同一批起点；BC 固定权重，Full/Plain 各 3 个训练种子。联合结果等权平均两条件，仍只有 60 个独立起点。区间沿用原有配对交叉 bootstrap。
- 源文件：`reproduction/confirmation_20261012_01/analysis/per_seed.csv`。

## T04_wm_confirmation_paired_per_seed.csv — 世界模型独立确认逐种子不一致起点

- 行数：18；cohort：`wm_confirmation_60_new_starts`；独立 N：60；种子数：1。
- 证据性质：`independent_confirmation`。
- 用法与限制：独立确认：60 个全新起点，clean/noise 重用同一批起点；BC 固定权重，Full/Plain 各 3 个训练种子。联合结果等权平均两条件，仍只有 60 个独立起点。区间沿用原有配对交叉 bootstrap。
- 源文件：`reproduction/confirmation_20261012_01/analysis/paired_per_seed.csv`。

## T05_development_all_ablation.csv — 全部开发集方法与公平消融

- 行数：24；cohort：`development_30_reused_starts`；独立 N：30；种子数：row-specific。
- 证据性质：`development_selection`。
- 用法与限制：反复查看的 30 个开发起点；用于模型/参数选择和消融，不能作为独立泛化确认。各方法的训练种子数见行字段；BC 的 0 表示固定策略且无世界模型训练种子。
- 源文件：`reproduction/multiseed_20261012_01/analysis/summary.csv`。

## T06_development_paired.csv — 开发集全部配对比较

- 行数：30；cohort：`development_30_reused_starts`；独立 N：30；种子数：3。
- 证据性质：`development_selection`。
- 用法与限制：反复查看的 30 个开发起点；用于模型/参数选择和消融，不能作为独立泛化确认。各方法的训练种子数见行字段；BC 的 0 表示固定策略且无世界模型训练种子。
- 源文件：`reproduction/multiseed_20261012_01/analysis/paired_comparisons.csv`。

## T07_development_per_seed.csv — 开发集逐种子结果与控制代价

- 行数：60；cohort：`development_30_reused_starts`；独立 N：30；种子数：row-specific。
- 证据性质：`development_selection`。
- 用法与限制：反复查看的 30 个开发起点；用于模型/参数选择和消融，不能作为独立泛化确认。各方法的训练种子数见行字段；BC 的 0 表示固定策略且无世界模型训练种子。
- 源文件：`reproduction/multiseed_20261012_01/analysis/per_seed.csv`。

## T08_training_budget_model_metadata.csv — 模型参数、训练预算和选择 checkpoint

- 行数：18；cohort：`branch_training_and_selection`；独立 N：train_parent20_dev_parent8；种子数：1。
- 证据性质：`training_metadata`。
- 用法与限制：参数/预算表不是策略成功率。base 与额外 head 阶段分别列出；有效可训练参数不一定等于总参数。Full/Plain/Direct/Prediction-only 及校准/控制臂请勿混称一个模型。
- 源文件：`reproduction/multiseed_20261012_01/analysis/model_metadata.csv`。

## T09_branch_dataset_statistics.csv — 分支训练开发数据与有效排序对

- 行数：2；cohort：`fixed_branch_dataset`；独立 N：row-specific；种子数：0。
- 证据性质：`dataset_description`。
- 用法与限制：160/64 是候选分支组数，同一父回合可贡献多个相关组；独立父回合仅 train=20、dev=8。非平凡排序对按真值分差阈值筛选。
- 源文件：`reproduction/multiseed_20261012_01/analysis/analysis.json`。

## T10_head_calibration_offline.csv — 评分头校准离线指标

- 行数：9；cohort：`branch_dev_8_parents_64_groups`；独立 N：8；种子数：1。
- 证据性质：`development_mechanism_diagnosis`。
- 用法与限制：评分头校准/继续训练控制臂在已用于选择的开发标签上评估，不构成新测试集效果。MAE/Brier/regret 的单位和输入对象不同。
- 源文件：`reproduction/multiseed_20261012_01/analysis/head_calibration_offline.csv`。

## T11_development_controller_usage.csv — 开发集候选覆盖与回退比例

- 行数：18；cohort：`development_30_reused_starts`；独立 N：30；种子数：row-specific。
- 证据性质：`development_selection`。
- 用法与限制：反复查看的 30 个开发起点；用于模型/参数选择和消融，不能作为独立泛化确认。各方法的训练种子数见行字段；BC 的 0 表示固定策略且无世界模型训练种子。
- 源文件：`reproduction/multiseed_20261012_01/analysis/controller_usage.csv`。

## T12_supplementary_H_K_persistence_oracle.csv — H、K、持续性和真值候选排序补充诊断

- 行数：22；cohort：`development_30_reused_starts`；独立 N：30；种子数：row-specific。
- 证据性质：`development_supplementary_diagnosis`。
- 用法与限制：补充开发诊断：复用 30 个已知起点。H/K 的结果依赖既有 D=2、门控和 k=2 回退；H=1、K=1、持续性基线始终回退。K=8 超出训练时 K=0..3 候选支持。oracle 只对既定候选用真值排序，不是全局最优控制器。
- 源文件：`reproduction/extensions_20261012_01/analysis/summary.json`。

## T13_supplementary_paired.csv — 补充诊断配对差值

- 行数：22；cohort：`development_30_reused_starts`；独立 N：30；种子数：row-specific。
- 证据性质：`development_supplementary_diagnosis`。
- 用法与限制：补充开发诊断：复用 30 个已知起点。H/K 的结果依赖既有 D=2、门控和 k=2 回退；H=1、K=1、持续性基线始终回退。K=8 超出训练时 K=0..3 候选支持。oracle 只对既定候选用真值排序，不是全局最优控制器。
- 源文件：`reproduction/extensions_20261012_01/analysis/paired_comparisons.csv`。

## T14_offline_prediction_metrics.csv — 离线预测：Full、Plain 与持续性

- 行数：9；cohort：`branch_dev_8_parents_64_groups`；独立 N：8；种子数：1。
- 证据性质：`development_offline_diagnosis`。
- 用法与限制：现有分支开发集已用于 checkpoint 选择；64 个相关分支组来自 8 个父回合。归一化状态 MSE、位置 RMSE、评分 regret 分别反映不同性质；不可把它们混画成同单位损失。
- 源文件：`reproduction/extensions_20261012_01/offline_metrics.json`。

## T15_prediction_error_by_horizon.csv — 逐预测时域状态误差

- 行数：72；cohort：`branch_dev_8_parents_64_groups`；独立 N：8；种子数：1。
- 证据性质：`development_offline_diagnosis`。
- 用法与限制：现有分支开发集已用于 checkpoint 选择；64 个相关分支组来自 8 个父回合。归一化状态 MSE、位置 RMSE、评分 regret 分别反映不同性质；不可把它们混画成同单位损失。
- 源文件：`reproduction/extensions_20261012_01/offline_metrics.json`。

## T16_offline_scoring_and_ranking.csv — 预测状态评分与真值状态评分

- 行数：18；cohort：`branch_dev_8_parents_64_groups`；独立 N：8；种子数：1。
- 证据性质：`development_offline_diagnosis`。
- 用法与限制：现有分支开发集已用于 checkpoint 选择；64 个相关分支组来自 8 个父回合。归一化状态 MSE、位置 RMSE、评分 regret 分别反映不同性质；不可把它们混画成同单位损失。
- 源文件：`reproduction/extensions_20261012_01/offline_metrics.json`。

## T17_oracle_offline_reference.csv — 真值候选评分离线参考

- 行数：1；cohort：`branch_dev_8_parents_64_groups`；独立 N：8；种子数：0。
- 证据性质：`development_offline_diagnosis`。
- 用法与限制：现有分支开发集已用于 checkpoint 选择；64 个相关分支组来自 8 个父回合。归一化状态 MSE、位置 RMSE、评分 regret 分别反映不同性质；不可把它们混画成同单位损失。 oracle 的 raw regret 为候选内参考零；门控仍可能回退而带来非零 gated regret。
- 源文件：`reproduction/extensions_20261012_01/offline_metrics.json`。

## T18_recovery_main.csv — v5 confirmation 分条件主表

- 行数：20；cohort：`recovery_v5_confirmation_60_starts`；独立 N：60；种子数：row-specific。
- 证据性质：`independent_confirmation`。
- 用法与限制：v5 独立确认的 60 个新起点，与 WM 主确认的 60 个起点不是同一批。每版本 480 次执行是 BC 2 条件 + Full 3 种子×2条件；仍只有 60 个独立起点。overall_execution_mix 为预定 8 次执行等权（BC 占1/4、Full占3/4），不能解释成模型等权平均。
- 源文件：`reproduction/recovery_v5_20261012_01/analysis_confirmation/summary.json`。

## T20_recovery_execution_mix_totals.csv — v5 confirmation 执行混合总表及净救回

- 行数：5；cohort：`recovery_v5_confirmation_60_starts`；独立 N：60；种子数：3。
- 证据性质：`independent_confirmation`。
- 用法与限制：v5 独立确认的 60 个新起点，与 WM 主确认的 60 个起点不是同一批。每版本 480 次执行是 BC 2 条件 + Full 3 种子×2条件；仍只有 60 个独立起点。overall_execution_mix 为预定 8 次执行等权（BC 占1/4、Full占3/4），不能解释成模型等权平均。
- 源文件：`reproduction/recovery_v5_20261012_01/analysis_confirmation/summary.json`。

## T21_recovery_statistical_comparisons.csv — v5 confirmation 全部估计量及既有区间

- 行数：84；cohort：`recovery_v5_confirmation_60_starts`；独立 N：60；种子数：row-specific。
- 证据性质：`independent_confirmation`。
- 用法与限制：v5 独立确认的 60 个新起点，与 WM 主确认的 60 个起点不是同一批。每版本 480 次执行是 BC 2 条件 + Full 3 种子×2条件；仍只有 60 个独立起点。overall_execution_mix 为预定 8 次执行等权（BC 占1/4、Full占3/4），不能解释成模型等权平均。
- 源文件：`reproduction/recovery_v5_20261012_01/analysis_confirmation/summary.json`。

## T19_recovery_confirmation_jobs.csv — v5 确认逐种子、条件与介入情况

- 行数：40；cohort：`recovery_v5_confirmation_60_starts`；独立 N：60；种子数：row-specific。
- 证据性质：`independent_confirmation`。
- 用法与限制：v5 独立确认的 60 个新起点，与 WM 主确认的 60 个起点不是同一批。每版本 480 次执行是 BC 2 条件 + Full 3 种子×2条件；仍只有 60 个独立起点。overall_execution_mix 为预定 8 次执行等权（BC 占1/4、Full占3/4），不能解释成模型等权平均。
- 源文件：`reproduction/recovery_v5_20261012_01/analysis_confirmation/summary.json`。

## T22_recovery_confirmation_paired.csv — v5 确认逐种子配对救回与退步

- 行数：72；cohort：`recovery_v5_confirmation_60_starts`；独立 N：60；种子数：row-specific。
- 证据性质：`independent_confirmation`。
- 用法与限制：v5 独立确认的 60 个新起点，与 WM 主确认的 60 个起点不是同一批。每版本 480 次执行是 BC 2 条件 + Full 3 种子×2条件；仍只有 60 个独立起点。overall_execution_mix 为预定 8 次执行等权（BC 占1/4、Full占3/4），不能解释成模型等权平均。
- 源文件：`reproduction/recovery_v5_20261012_01/analysis_confirmation/comparisons.csv`。

## T23_recovery_main.csv — v5 dev_a 分条件主表

- 行数：20；cohort：`recovery_v5_dev_a_30_starts`；独立 N：30；种子数：row-specific。
- 证据性质：`development_selection`。
- 用法与限制：v5 开发比较：30 个复用起点。表含 5 版本共 1,200 条已存在记录，其中 v2/v4 共 480 条为沿用；本阶段只新执行 T/S/v5 720 回合。不是 1,200 个独立样本。区间按起点重采样，3 个固定 Full 种子在起点内平均。
- 源文件：`reproduction/recovery_v5_20261012_01/analysis_dev_a/summary.json`。

## T24_recovery_execution_mix_totals.csv — v5 dev_a 执行混合总表及净救回

- 行数：5；cohort：`recovery_v5_dev_a_30_starts`；独立 N：30；种子数：3。
- 证据性质：`development_selection`。
- 用法与限制：v5 开发比较：30 个复用起点。表含 5 版本共 1,200 条已存在记录，其中 v2/v4 共 480 条为沿用；本阶段只新执行 T/S/v5 720 回合。不是 1,200 个独立样本。区间按起点重采样，3 个固定 Full 种子在起点内平均。
- 源文件：`reproduction/recovery_v5_20261012_01/analysis_dev_a/summary.json`。

## T25_recovery_statistical_comparisons.csv — v5 dev_a 全部估计量及既有区间

- 行数：84；cohort：`recovery_v5_dev_a_30_starts`；独立 N：30；种子数：row-specific。
- 证据性质：`development_selection`。
- 用法与限制：v5 开发比较：30 个复用起点。表含 5 版本共 1,200 条已存在记录，其中 v2/v4 共 480 条为沿用；本阶段只新执行 T/S/v5 720 回合。不是 1,200 个独立样本。区间按起点重采样，3 个固定 Full 种子在起点内平均。
- 源文件：`reproduction/recovery_v5_20261012_01/analysis_dev_a/summary.json`。

## T26_geometry_stress_strata.csv — 几何压力分层与总表

- 行数：25；cohort：`geometry_stress_16_manual_starts`；独立 N：row-specific；种子数：0。
- 证据性质：`descriptive_geometry_stress`。
- 用法与限制：手工指定几何压力测试：16 个起点，4 类各 4 个，5 版本共 80 次执行；第 80 步强制恢复，stationary-open 提案。分层描述性数据，无独立泛化显著性结论，不能并入自然策略确认集。
- 源文件：`reproduction/recovery_v5_20261012_01/analysis_geometry_confirmation/summary.json`。

## T27_geometry_stress_paired.csv — 几何压力配对变化

- 行数：7；cohort：`geometry_stress_16_manual_starts`；独立 N：16；种子数：0。
- 证据性质：`descriptive_geometry_stress`。
- 用法与限制：手工指定几何压力测试：16 个起点，4 类各 4 个，5 版本共 80 次执行；第 80 步强制恢复，stationary-open 提案。分层描述性数据，无独立泛化显著性结论，不能并入自然策略确认集。
- 源文件：`reproduction/recovery_v5_20261012_01/analysis_geometry_confirmation/summary.json`。

## T28_recovery_WM_factorial_cells.csv — 世界模型×共享恢复的既有同批 2×2 单元

- 行数：24；cohort：`separate_historical_factorial_cohorts`；独立 N：row-specific；种子数：row-specific。
- 证据性质：`posthoc_existing_results`。
- 用法与限制：对以前已观察的 v2/v3 确认结果进行事后 2×2 整理：相同起点内比较 WM 开关与恢复开关。三个小表中两个共享 v3 的同一批起点；不能相加当作 180 个独立起点，也不能与最新 v5 批次直接相减。既有 20,000 次配对起点 bootstrap，固定三种子平均、逐点区间。
- 源文件：`reproduction/consolidation_20261012_01/factorial_analysis.json`。

## T29_recovery_WM_factorial_effects.csv — 世界模型×恢复的主效应与交互

- 行数：30；cohort：`separate_historical_factorial_cohorts`；独立 N：row-specific；种子数：3。
- 证据性质：`posthoc_existing_results`。
- 用法与限制：对以前已观察的 v2/v3 确认结果进行事后 2×2 整理：相同起点内比较 WM 开关与恢复开关。三个小表中两个共享 v3 的同一批起点；不能相加当作 180 个独立起点，也不能与最新 v5 批次直接相减。既有 20,000 次配对起点 bootstrap，固定三种子平均、逐点区间。
- 源文件：`reproduction/consolidation_20261012_01/factorial_analysis.json`。

## T30_training_full_checkpoint_metrics.csv — 全量训练开发 checkpoint 曲线数据

- 行数：72；cohort：`fixed_branch_train_dev_checkpoint_diagnostic`；独立 N：row-specific；种子数：1。
- 证据性质：`existing_checkpoint_offline_diagnosis`。
- 用法与限制：现有 36 个 checkpoint 的离线全量复算：3 种子×12 保存 step×train/dev=72 行；原深核查在 10 月14日已完成，此次只整理其 CSV/JSON，没有重新推理。横轴是 optimizer update step，非 epoch。train=160组/20父回合，dev=64组/8父回合；同一父回合、相邻 checkpoint 高度相关。
- 源文件：`reproduction/figures_deepcheck_20261014_01/checkpoint_metrics.csv`。

## T31_training_generalization_gap.csv — 逐种子逐 step 泛化差距

- 行数：36；cohort：`fixed_branch_train_dev_checkpoint_diagnostic`；独立 N：8；种子数：1。
- 证据性质：`existing_checkpoint_offline_diagnosis`。
- 用法与限制：现有 36 个 checkpoint 的离线全量复算：3 种子×12 保存 step×train/dev=72 行；原深核查在 10 月14日已完成，此次只整理其 CSV/JSON，没有重新推理。横轴是 optimizer update step，非 epoch。train=160组/20父回合，dev=64组/8父回合；同一父回合、相邻 checkpoint 高度相关。
- 源文件：`reproduction/figures_deepcheck_20261014_01/checkpoint_metrics.csv`。

## T32_training_endpoints.csv — 训练曲线首末保存点摘要

- 行数：6；cohort：`fixed_branch_train_dev_checkpoint_diagnostic`；独立 N：row-specific；种子数：1。
- 证据性质：`existing_checkpoint_offline_diagnosis`。
- 用法与限制：现有 36 个 checkpoint 的离线全量复算：3 种子×12 保存 step×train/dev=72 行；原深核查在 10 月14日已完成，此次只整理其 CSV/JSON，没有重新推理。横轴是 optimizer update step，非 epoch。train=160组/20父回合，dev=64组/8父回合；同一父回合、相邻 checkpoint 高度相关。
- 源文件：`reproduction/figures_deepcheck_20261014_01/checkpoint_metrics.csv`。

## T33_common_success_paired_steps.csv — 共同成功起点的步数差

- 行数：6；cohort：`wm_confirmation_60_new_starts_common_success_subset`；独立 N：row-specific；种子数：1。
- 证据性质：`conditional_paired_efficiency`。
- 用法与限制：仅纳入 BC 与对应 Full 种子都成功的起点。差值为 Full步骤−BC步骤：负数更快、正数更慢。每种子/条件实际配对 N 见 paired_n；这是条件效率，不能取代全体成功率或失败按400封顶的平均步数。
- 源文件：`reproduction/figures_deepcheck_20261014_01/diagnostics.json`。

## T34_seed_duplicate_success_diagnostic.csv — 同成功数、同起点和不同步数检查

- 行数：4；cohort：`wm_confirmation_60_new_starts`；独立 N：60；种子数：3。
- 证据性质：`result_integrity_diagnosis`。
- 用法与限制：成功数相同并不证明输出复制；identical_success_sets 指二值成功起点集合相同，identical_step_vectors 是全步数向量是否相同。噪声下成功集合可不同。
- 源文件：`reproduction/figures_deepcheck_20261014_01/diagnostics.json`。

## T35_wm_confirmation_episode_records.csv — WM 独立确认全部逐回合记录

- 行数：840；cohort：`wm_confirmation_60_new_starts`；独立 N：60；种子数：row-specific。
- 证据性质：`independent_confirmation`。
- 用法与限制：独立确认：60 个全新起点，clean/noise 重用同一批起点；BC 固定权重，Full/Plain 各 3 个训练种子。联合结果等权平均两条件，仍只有 60 个独立起点。区间沿用原有配对交叉 bootstrap。
- 源文件：`reproduction/confirmation_20261012_01/analysis/episodes.csv`。

## T36_v5_failure_categories.csv — v5 剩余失败类别

- 行数：3；cohort：`recovery_v5_confirmation_failed_subset`；独立 N：7；种子数：3。
- 证据性质：`posthoc_observation_based_failure_review`。
- 用法与限制：现有观测日志的事后失败分类，不是碰撞因果或物理真值标签。v5 尚有失败执行和共同失败起点；不能写成恢复问题完全解决。
- 源文件：`reproduction/recovery_v5_20261012_01/posthoc_failure_review.json`。

## T37_v5_failed_executions.csv — v5 剩余失败逐回合索引

- 行数：16；cohort：`recovery_v5_confirmation_failed_subset`；独立 N：7；种子数：row-specific。
- 证据性质：`posthoc_observation_based_failure_review`。
- 用法与限制：现有观测日志的事后失败分类，不是碰撞因果或物理真值标签。v5 尚有失败执行和共同失败起点；不能写成恢复问题完全解决。
- 源文件：`reproduction/recovery_v5_20261012_01/posthoc_failure_review.json`。

## T38_v5_confirmation_mechanisms.csv — v5 确认恢复机制事件覆盖

- 行数：5；cohort：`recovery_v5_confirmation_60_starts`；独立 N：60；种子数：3。
- 证据性质：`posthoc_event_coverage`。
- 用法与限制：事件覆盖数按执行回合计，不是独立起点数。侧倒可行方案自然触发很稀少；不能把压力测试改善直接解释成自然分布上稳定的侧倒收益。
- 源文件：`reproduction/recovery_v5_20261012_01/mechanisms_confirmation.json`。

## T39_development_vs_confirmation_descriptive.csv — 开发与独立确认的描述性分布变化

- 行数：6；cohort：`two_distinct_cohorts_not_paired`；独立 N：dev30;confirmation60；种子数：row-specific。
- 证据性质：`descriptive_cross_cohort_only`。
- 用法与限制：原表 descriptive_change_pp 是不同起点分布间的描述性差值，不是同批配对提升，也不是训练改进效果。论文中应分别列开发结果和确认结果。
- 源文件：`reproduction/confirmation_20261012_01/analysis/dev_vs_confirmation.csv`。

## T40_development_regret_concentration.csv — 开发 regret 跳变集中度

- 行数：36；cohort：`branch_dev_8_parents_64_groups`；独立 N：8；种子数：1。
- 证据性质：`posthoc_curve_diagnosis`。
- 用法与限制：每 step 在 64 组中找 regret 最大组，给出其对总 regret 的占比。组索引是该诊断中的零基数组位置，不是新回合；多个相关组会使评分均值不稳定。
- 源文件：`reproduction/figures_deepcheck_20261014_01/diagnostics.json`。

