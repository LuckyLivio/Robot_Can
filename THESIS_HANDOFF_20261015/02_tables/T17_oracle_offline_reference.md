# 真值候选评分离线参考

现有分支开发集已用于 checkpoint 选择；64 个相关分支组来自 8 个父回合。归一化状态 MSE、位置 RMSE、评分 regret 分别反映不同性质；不可把它们混画成同单位损失。 oracle 的 raw regret 为候选内参考零；门控仍可能回退而带来非零 gated regret。

完整数值：`T17_oracle_offline_reference.csv`。Markdown 仅显示约 6 位有效数字。

| raw_regret | gated_regret | gated_optimal_within_025 | nontrivial_pairs | pair_tie_rate | pair_accuracy_ties_half | override_fraction | oracle_gate_agreement | condition | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.00128913 | 1 | 39 | 0 | 1 | 0.109375 | 1 | see_row_or_catalog | 8 | 0 |
