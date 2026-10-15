# 数据字典与统计口径

本字典适用于 T01–T40，未重命名的字段沿用各来源分析文件。所有 CSV 使用 UTF-8 BOM；空值表示未计算/不适用，不等于 0。数组、字典字段在 CSV 中保存 JSON 字符串。

| 字段/字段族 | 单位与定义 | 使用限制 |
| --- | --- | --- |
| dataset / cohort | 固定数据批次或证据集合标识 | 同名批次可配对；不同批次不得相减写成效果 |
| independent_N / independent_initial_states / distinct_parents / parents | 独立起点或分支父回合数 | 分支父回合≠分支组数；重复条件/种子不扩大 N |
| seed_count / train_seeds / world_model_training_seeds | 世界模型训练种子数；固定 BC 写 0；逐种子行通常写 1 | 0 并非没有策略或没有重复执行 |
| seed / seed_order | 17、23、41 等已冻结训练随机种子 | 不含任意重训分布的完整不确定性 |
| condition / noise | clean=0；noise005=0.05；joint_equal_weight=两条件等权 | 两条件复用起点，非新增独立实验 |
| source_repo_path / source | 原项目相对路径，可在 ../04_snapshot 镜像找到 | PROVENANCE.csv 记录源 SHA-256 |
| evidence_scope | independent_confirmation / development_selection / diagnosis / stress / posthoc 等 | 不可把开发或事后分析描述为预注册独立确认 |
| successes / success / success_counts / success_s17... | 成功执行计数或逐回合布尔值 | 三种子总成功数的分母通常为 3N，独立 N 仍为 N |
| execution_count / episodes / episodes_per_seed | 已有执行记录条数 | 同一起点可能有多个高度相关执行 |
| mean_success_percent / success_percent / rate | 百分比；rate 原字段通常为 0–1 | 看列名区分百分比与比例 |
| seed_sd_pp / seed_sample_sd_pp | 三个种子成功率的样本标准差，百分点 | 成功数相同可为 0，并非总体不确定性为 0 |
| ...difference_pp / ...delta... / ...minus... | 同批配对成功率差，百分点；left−right | 跨 cohort descriptive_change_pp 仅描述分布变化 |
| ...ci...low/high... / ci95_pp | 沿用来源的 95% bootstrap 区间 | WM 表为 starts×seeds 交叉重采样；v5 为起点重采样、固定三种子均值；均为逐点区间 |
| overall_execution_mix | v5 每起点 8 执行的等权混合 | BC 2/8、Full 6/8；不是两种方法各 1/2 |
| joint_equal_weight | WM 主确认 clean/noise 条件等权平均 | 不等同 v5 execution mix |
| wins / losses / rescues / regressions | 配对不一致执行数 | 同一起点可贡献多个条件/种子，另看 distinct/rescued IDs |
| mean_steps_failures_capped_400 / mean_steps_capped | 所有起点平均步数，失败以 400 封顶 | 同时受成功率与效率影响 |
| paired_n / mean_difference / median_difference | 双方均成功子集的 N、Full步数−BC步数 | 负值表示 Full 更快，只对该条件子集有效 |
| override_fraction / fraction_override | 门控所选动作不同于回退 k=2 的决策比例 | 不是成功率，也不等于模型预测准确率 |
| parallel...decision_ms / mean_decision_ms... | 旧运行记录的平均毫秒 | 并行负载，不能当严格推理延迟基准 |
| groups / branch_steps / nontrivial_pairs | 候选分支组、分支时刻、真值分差>.025的候选对 | 同父回合相关；有效排序对远少于全部可能对 |
| normalized_state_mse / prediction_mse | 按既有训练标准化的状态均方误差 | 无量纲，不是米；低于持久性不等于控制收益必然提升 |
| eef_position_rmse_m / object_position_rmse_m | 末端/物体位置误差，米 | 与 object_error_mm 的指标定义不同 |
| object_error_mm | 全量 checkpoint 诊断中的平均物体欧氏位置误差，毫米 | 不要与 m 单位 RMSE 混用；须看原诊断脚本定义 |
| normalized_mse_per_horizon / horizon_step | 每预测步的标准化状态 MSE | x 轴是预测步数而非训练 step |
| step / base_selected_step / head_selected_step | 优化更新次数 | 不是 epoch；不同阶段 step 不应直接拼接 |
| progress_bce / risk_bce / ranking_loss / total_loss | 各训练目标损失；total 含既有权重 | 各损失尺度不同，不应靠形状判断所有模块共同改善 |
| raw_regret / mean_regret | 候选真实最好分数减模型选中候选的真实分数 | 对固定候选集成立；非全局任务 regret |
| gated_regret | 经过风险/优势门控及 k=2 回退后的候选 regret | 即使 oracle raw=0，门控后也可非零 |
| pair_accuracy_ties_half | 非平凡候选对排序准确率，预测并列计半对 | 必须一起报告有效对数与 pair_tie_rate |
| risk / grasp-loss | 已有训练标注定义的失抓风险目标 | 不等于所有碰撞/失败原因的概率 |
| effective_trainable_parameters_this_phase | 该训练阶段实际可更新的参数数 | 不等于模型总参数、也不能跨阶段简单加总 |
| worst_share_of_total_regret | 最大 regret 组占全部 regret 之和比例 | 单组主导提示指标脆弱性，不代表数据造假 |
| observation_based_category | 依据旧轨迹观测的事后失败分类 | 不作为物理碰撞真值或严格因果诊断 |

原始 CSV 一致性复核：VALIDATION_CHECKS.csv。源/产物 SHA：PROVENANCE.csv。可迁移机器目录：table_catalog.json。脚本只用 Python 标准库，`python 02_tables/build_tables.py` 可从包根目录运行；优先读取 04_snapshot，若缺失才读取原 checkout，缺失两处会明确报错。
