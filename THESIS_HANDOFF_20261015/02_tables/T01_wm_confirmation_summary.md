# 世界模型独立确认主表

独立确认：60 个全新起点，clean/noise 重用同一批起点；BC 固定权重，Full/Plain 各 3 个训练种子。联合结果等权平均两条件，仍只有 60 个独立起点。区间沿用原有配对交叉 bootstrap。

完整数值：`T01_wm_confirmation_summary.csv`。Markdown 仅显示约 6 位有效数字。

| method | condition | independent_initial_states | world_model_training_seeds | success_s17_or_fixed_bc | success_s23 | success_s41 | mean_success_percent | seed_sd_pp | paired_crossed_bootstrap_low_percent | paired_crossed_bootstrap_high_percent | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bc_k2 | clean | 60 | 0 | 51 |  |  | 85.0 |  | 75.0 | 93.33333333333333 | 60 | 0 |
| full | clean | 60 | 3 | 54 | 54 | 54 | 90.0 | 0.0 | 81.66666666666667 | 96.66666666666667 | 60 | 3 |
| plain | clean | 60 | 3 | 53 | 53 | 53 | 88.33333333333333 | 0.0 | 80.0 | 95.0 | 60 | 3 |
| bc_k2 | noise005 | 60 | 0 | 49 |  |  | 81.66666666666667 |  | 71.66666666666667 | 91.66666666666666 | 60 | 0 |
| full | noise005 | 60 | 3 | 52 | 52 | 51 | 86.11111111111111 | 0.9622504486493794 | 77.22222222222223 | 94.44444444444444 | 60 | 3 |
| plain | noise005 | 60 | 3 | 50 | 51 | 50 | 83.88888888888889 | 0.9622504486493729 | 74.44444444444444 | 92.77777777777779 | 60 | 3 |
| bc_k2 | joint_equal_weight | 60 | 0 |  |  |  | 83.33333333333334 |  | 74.16666666666667 | 91.66666666666666 | 60 | 0 |
| full | joint_equal_weight | 60 | 3 |  |  |  | 88.05555555555556 | 0.48112522432468646 | 80.0 | 95.0 | 60 | 3 |
| plain | joint_equal_weight | 60 | 3 |  |  |  | 86.11111111111111 | 0.4811252243246928 | 77.5 | 93.88888888888889 | 60 | 3 |
