# 世界模型独立确认逐种子不一致起点

独立确认：60 个全新起点，clean/noise 重用同一批起点；BC 固定权重，Full/Plain 各 3 个训练种子。联合结果等权平均两条件，仍只有 60 个独立起点。区间沿用原有配对交叉 bootstrap。

完整数值：`T04_wm_confirmation_paired_per_seed.csv`。Markdown 仅显示约 6 位有效数字。

| left | right | condition | seed | left_only_success | right_only_success | difference_pp | left_only_ids | right_only_ids | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | bc_k2 | clean | 17 | 3 | 0 | 5.0 | demo_1000026;demo_1000028;demo_1000045 |  | 60 | 1 |
| full | bc_k2 | clean | 23 | 3 | 0 | 5.0 | demo_1000026;demo_1000028;demo_1000045 |  | 60 | 1 |
| full | bc_k2 | clean | 41 | 3 | 0 | 5.0 | demo_1000026;demo_1000028;demo_1000045 |  | 60 | 1 |
| plain | bc_k2 | clean | 17 | 2 | 0 | 3.3333333333333335 | demo_1000028;demo_1000045 |  | 60 | 1 |
| plain | bc_k2 | clean | 23 | 2 | 0 | 3.3333333333333335 | demo_1000028;demo_1000045 |  | 60 | 1 |
| plain | bc_k2 | clean | 41 | 2 | 0 | 3.3333333333333335 | demo_1000028;demo_1000045 |  | 60 | 1 |
| full | plain | clean | 17 | 1 | 0 | 1.6666666666666667 | demo_1000026 |  | 60 | 1 |
| full | plain | clean | 23 | 1 | 0 | 1.6666666666666667 | demo_1000026 |  | 60 | 1 |
| full | plain | clean | 41 | 1 | 0 | 1.6666666666666667 | demo_1000026 |  | 60 | 1 |
| full | bc_k2 | noise005 | 17 | 3 | 0 | 5.0 | demo_1000011;demo_1000026;demo_1000045 |  | 60 | 1 |
| full | bc_k2 | noise005 | 23 | 3 | 0 | 5.0 | demo_1000026;demo_1000045;demo_1000054 |  | 60 | 1 |
| full | bc_k2 | noise005 | 41 | 2 | 0 | 3.3333333333333335 | demo_1000026;demo_1000045 |  | 60 | 1 |
| plain | bc_k2 | noise005 | 17 | 1 | 0 | 1.6666666666666667 | demo_1000045 |  | 60 | 1 |
| plain | bc_k2 | noise005 | 23 | 2 | 0 | 3.3333333333333335 | demo_1000041;demo_1000045 |  | 60 | 1 |
| plain | bc_k2 | noise005 | 41 | 1 | 0 | 1.6666666666666667 | demo_1000045 |  | 60 | 1 |
| full | plain | noise005 | 17 | 2 | 0 | 3.3333333333333335 | demo_1000011;demo_1000026 |  | 60 | 1 |
| full | plain | noise005 | 23 | 2 | 1 | 1.6666666666666667 | demo_1000026;demo_1000054 | demo_1000041 | 60 | 1 |
| full | plain | noise005 | 41 | 1 | 0 | 1.6666666666666667 | demo_1000026 |  | 60 | 1 |
