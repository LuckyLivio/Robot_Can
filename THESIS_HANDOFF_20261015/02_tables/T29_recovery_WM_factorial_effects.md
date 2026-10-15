# 世界模型×恢复的主效应与交互

对以前已观察的 v2/v3 确认结果进行事后 2×2 整理：相同起点内比较 WM 开关与恢复开关。三个小表中两个共享 v3 的同一批起点；不能相加当作 180 个独立起点，也不能与最新 v5 批次直接相减。既有 20,000 次配对起点 bootstrap，固定三种子平均、逐点区间。

完整数值：`T29_recovery_WM_factorial_effects.csv`。Markdown 仅显示约 6 位有效数字。

| factorial_cohort | enabled_version | condition | estimand | difference_pp | ci95_low_pp | ci95_high_pp | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | clean | world_model_without_recovery | -1.11111 | -6.11111 | 2.77778 | 60 | 3 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | clean | world_model_with_recovery | 3.33333 | -1.11111 | 8.33333 | 60 | 3 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | clean | recovery_for_bc | 13.3333 | 5 | 23.3333 | 60 | 3 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | clean | recovery_for_full | 17.7778 | 9.44444 | 27.2222 | 60 | 3 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | clean | interaction | 4.44444 | -7.40149e-16 | 10 | 60 | 3 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | noise005 | world_model_without_recovery | -1.66667 | -6.66667 | 1.66667 | 60 | 3 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | noise005 | world_model_with_recovery | -1.66667 | -3.90278 | 0.555556 | 60 | 3 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | noise005 | recovery_for_bc | 16.6667 | 8.33333 | 26.6667 | 60 | 3 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | noise005 | recovery_for_full | 16.6667 | 8.33333 | 25.5556 | 60 | 3 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | noise005 | interaction | -9.25186e-17 | -3.88889 | 5 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | clean | world_model_without_recovery | -3.33333 | -9.44444 | 1.66667 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | clean | world_model_with_recovery | -3.70074e-16 | -5.55556 | 5.55556 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | clean | recovery_for_bc | 10 | 3.33333 | 18.3333 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | clean | recovery_for_full | 13.3333 | 6.11111 | 21.6667 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | clean | interaction | 3.33333 | -2.22222 | 8.88889 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | noise005 | world_model_without_recovery | -0.555556 | -6.11111 | 4.44444 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | noise005 | world_model_with_recovery | -1.85037e-16 | -5.55556 | 5.55556 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | noise005 | recovery_for_bc | 13.3333 | 5 | 23.3333 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | noise005 | recovery_for_full | 13.8889 | 6.11111 | 22.7778 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | noise005 | interaction | 0.555556 | -4.44444 | 6.11111 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | clean | world_model_without_recovery | -3.33333 | -9.44444 | 1.66667 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | clean | world_model_with_recovery | -1.11111 | -6.11111 | 3.33333 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | clean | recovery_for_bc | 10 | 3.33333 | 18.3333 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | clean | recovery_for_full | 12.2222 | 5.55556 | 20 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | clean | interaction | 2.22222 | -2.77778 | 6.66667 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | noise005 | world_model_without_recovery | -0.555556 | -6.11111 | 4.44444 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | noise005 | world_model_with_recovery | 2.22222 | -2.22222 | 7.22222 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | noise005 | recovery_for_bc | 11.6667 | 5 | 20 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | noise005 | recovery_for_full | 14.4444 | 6.66667 | 23.8889 | 60 | 3 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | noise005 | interaction | 2.77778 | 0 | 7.22222 | 60 | 3 |
