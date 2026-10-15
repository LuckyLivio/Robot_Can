# 训练曲线首末保存点摘要

现有 36 个 checkpoint 的离线全量复算：3 种子×12 保存 step×train/dev=72 行；原深核查在 10 月14日已完成，此次只整理其 CSV/JSON，没有重新推理。横轴是 optimizer update step，非 epoch。train=160组/20父回合，dev=64组/8父回合；同一父回合、相邻 checkpoint 高度相关。

完整数值：`T32_training_endpoints.csv`。Markdown 仅显示约 6 位有效数字。

| seed | split | first_saved_step | last_saved_step | parents | first_prediction_mse | last_prediction_mse | first_object_error_mm | last_object_error_mm | first_mean_regret | last_mean_regret | condition | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 17 | dev | 250 | 3000 | 8 | 0.125643 | 0.125136 | 47.69 | 16.6228 | 0.00648725 | 0.00531744 | see_row_or_catalog | 8 | 1 |
| 17 | train | 250 | 3000 | 20 | 0.0740244 | 0.0185815 | 41.4296 | 10.4483 | 0.00273006 | 0.000449748 | see_row_or_catalog | 20 | 1 |
| 23 | dev | 250 | 3000 | 8 | 0.121504 | 0.131394 | 43.9445 | 20.8159 | 0.00722151 | 0.00578632 | see_row_or_catalog | 8 | 1 |
| 23 | train | 250 | 3000 | 20 | 0.0748469 | 0.0184014 | 41.516 | 11.7853 | 0.00268996 | 0.000428876 | see_row_or_catalog | 20 | 1 |
| 41 | dev | 250 | 3000 | 8 | 0.125811 | 0.12711 | 44.1514 | 16.7025 | 0.00649712 | 0.000193804 | see_row_or_catalog | 8 | 1 |
| 41 | train | 250 | 3000 | 20 | 0.0715473 | 0.0185692 | 37.694 | 10.7216 | 0.00248284 | 0.000587542 | see_row_or_catalog | 20 | 1 |
