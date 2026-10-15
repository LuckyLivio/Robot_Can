# 分支训练开发数据与有效排序对

160/64 是候选分支组数，同一父回合可贡献多个相关组；独立父回合仅 train=20、dev=8。非平凡排序对按真值分差阈值筛选。

完整数值：`T09_branch_dataset_statistics.csv`。Markdown 仅显示约 6 位有效数字。

| split | groups | risk_positive_steps | branch_steps | nontrivial_rank_pairs | possible_rank_pairs | groups_with_score_spread_over_0025 | independent_N | condition | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | 160 | 287 | 5120 | 96 | 960 | 28 | 20 | see_row_or_catalog | 0 |
| dev | 64 | 130 | 2048 | 39 | 384 | 11 | 8 | see_row_or_catalog | 0 |
