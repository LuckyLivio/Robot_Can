# 预测状态评分与真值状态评分

现有分支开发集已用于 checkpoint 选择；64 个相关分支组来自 8 个父回合。归一化状态 MSE、位置 RMSE、评分 regret 分别反映不同性质；不可把它们混画成同单位损失。

完整数值：`T16_offline_scoring_and_ranking.csv`。Markdown 仅显示约 6 位有效数字。

| method | seed | scorer_input | raw_regret | gated_regret | gated_optimal_within_025 | nontrivial_pairs | pair_tie_rate | pair_accuracy_ties_half | override_fraction | oracle_gate_agreement | condition | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 17 | forecast_score | 0.00531631 | 0.00640218 | 0.984375 | 39 | 0 | 0.974359 | 0.234375 | 0.875 | see_row_or_catalog | 8 | 1 |
| full | 17 | same_head_on_true_states | 0.00306914 | 0.00955585 | 0.921875 | 39 | 0 | 0.717949 | 0.09375 | 0.859375 | see_row_or_catalog | 8 | 1 |
| persistence | 17 | forecast_score | 0.0165166 | 0.0174042 | 0.90625 | 39 | 1 | 0.5 | 0 | 0.890625 | see_row_or_catalog | 8 | 1 |
| persistence | 17 | same_head_on_true_states | 0.00306914 | 0.00955585 | 0.921875 | 39 | 0 | 0.717949 | 0.09375 | 0.859375 | see_row_or_catalog | 8 | 1 |
| full | 23 | forecast_score | 0.000503238 | 0.00156687 | 1 | 39 | 0 | 1 | 0.25 | 0.859375 | see_row_or_catalog | 8 | 1 |
| full | 23 | same_head_on_true_states | 0.017766 | 0.0175731 | 0.90625 | 39 | 0 | 0.512821 | 0.078125 | 0.84375 | see_row_or_catalog | 8 | 1 |
| persistence | 23 | forecast_score | 0.016366 | 0.0174042 | 0.90625 | 39 | 1 | 0.5 | 0 | 0.890625 | see_row_or_catalog | 8 | 1 |
| persistence | 23 | same_head_on_true_states | 0.017766 | 0.0175731 | 0.90625 | 39 | 0 | 0.512821 | 0.078125 | 0.84375 | see_row_or_catalog | 8 | 1 |
| full | 41 | forecast_score | 0.000166333 | 0.00130225 | 1 | 39 | 0 | 1 | 0.203125 | 0.90625 | see_row_or_catalog | 8 | 1 |
| full | 41 | same_head_on_true_states | 0.0106469 | 0.0116025 | 0.921875 | 39 | 0 | 0.589744 | 0.046875 | 0.875 | see_row_or_catalog | 8 | 1 |
| persistence | 41 | forecast_score | 0.016366 | 0.0174042 | 0.90625 | 39 | 1 | 0.5 | 0 | 0.890625 | see_row_or_catalog | 8 | 1 |
| persistence | 41 | same_head_on_true_states | 0.0106469 | 0.0116025 | 0.921875 | 39 | 0 | 0.589744 | 0.046875 | 0.875 | see_row_or_catalog | 8 | 1 |
| plain | 17 | forecast_score | 0.00122425 | 0.00180891 | 0.984375 | 39 | 0 | 1 | 0.125 | 0.953125 | see_row_or_catalog | 8 | 1 |
| plain | 17 | same_head_on_true_states | 0.00284557 | 0.0094827 | 0.9375 | 39 | 0 | 0.846154 | 0.0625 | 0.890625 | see_row_or_catalog | 8 | 1 |
| plain | 23 | forecast_score | 0.000637892 | 0.0163101 | 0.921875 | 39 | 0 | 1 | 0.09375 | 0.859375 | see_row_or_catalog | 8 | 1 |
| plain | 23 | same_head_on_true_states | 0.00373041 | 0.00990266 | 0.921875 | 39 | 0 | 0.74359 | 0.046875 | 0.875 | see_row_or_catalog | 8 | 1 |
| plain | 41 | forecast_score | 0.00103689 | 0.00833968 | 0.953125 | 39 | 0 | 1 | 0.109375 | 0.90625 | see_row_or_catalog | 8 | 1 |
| plain | 41 | same_head_on_true_states | 0.0027242 | 0.0115844 | 0.921875 | 39 | 0 | 0.666667 | 0.03125 | 0.890625 | see_row_or_catalog | 8 | 1 |
