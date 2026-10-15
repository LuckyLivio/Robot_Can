# 离线预测：Full、Plain 与持续性

现有分支开发集已用于 checkpoint 选择；64 个相关分支组来自 8 个父回合。归一化状态 MSE、位置 RMSE、评分 regret 分别反映不同性质；不可把它们混画成同单位损失。

完整数值：`T14_offline_prediction_metrics.csv`。Markdown 仅显示约 6 位有效数字。

| method | seed | groups | parents | normalized_state_mse | eef_position_rmse_m | object_position_rmse_m | condition | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 17 | 64 | 8 | 0.122857 | 0.0287064 | 0.0286843 | see_row_or_catalog | 8 | 1 |
| persistence | 17 | 64 | 8 | 0.130317 | 0.0591708 | 0.0520276 | see_row_or_catalog | 8 | 1 |
| full | 23 | 64 | 8 | 0.12201 | 0.0320624 | 0.049251 | see_row_or_catalog | 8 | 1 |
| persistence | 23 | 64 | 8 | 0.130317 | 0.0591708 | 0.0520276 | see_row_or_catalog | 8 | 1 |
| full | 41 | 64 | 8 | 0.126612 | 0.0323593 | 0.0269141 | see_row_or_catalog | 8 | 1 |
| persistence | 41 | 64 | 8 | 0.130317 | 0.0591708 | 0.0520276 | see_row_or_catalog | 8 | 1 |
| plain | 17 | 64 | 8 | 0.126698 | 0.0280936 | 0.0280468 | see_row_or_catalog | 8 | 1 |
| plain | 23 | 64 | 8 | 0.151522 | 0.0343885 | 0.0280776 | see_row_or_catalog | 8 | 1 |
| plain | 41 | 64 | 8 | 0.131985 | 0.0273905 | 0.0247957 | see_row_or_catalog | 8 | 1 |
