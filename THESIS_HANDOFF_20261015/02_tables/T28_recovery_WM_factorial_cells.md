# 世界模型×共享恢复的既有同批 2×2 单元

对以前已观察的 v2/v3 确认结果进行事后 2×2 整理：相同起点内比较 WM 开关与恢复开关。三个小表中两个共享 v3 的同一批起点；不能相加当作 180 个独立起点，也不能与最新 v5 批次直接相减。既有 20,000 次配对起点 bootstrap，固定三种子平均、逐点区间。

完整数值：`T28_recovery_WM_factorial_cells.csv`。Markdown 仅显示约 6 位有效数字。

| factorial_cohort | enabled_version | recovery | method | noise | successes | executions | rate | starts | independent_N | seed_count | success_percent | condition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | disabled | BC k=2 | 0 | 47 | 60 | 0.783333 | 60 | 60 | 0 | 78.3333 | clean |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | disabled | Full (three-seed mean) | 0 | 139 | 180 | 0.772222 | 60 | 60 | 3 | 77.2222 | clean |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | v2 | BC k=2 | 0 | 55 | 60 | 0.916667 | 60 | 60 | 0 | 91.6667 | clean |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | v2 | Full (three-seed mean) | 0 | 171 | 180 | 0.95 | 60 | 60 | 3 | 95 | clean |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | disabled | BC k=2 | 0.05 | 48 | 60 | 0.8 | 60 | 60 | 0 | 80 | noise005 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | disabled | Full (three-seed mean) | 0.05 | 141 | 180 | 0.783333 | 60 | 60 | 3 | 78.3333 | noise005 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | v2 | BC k=2 | 0.05 | 58 | 60 | 0.966667 | 60 | 60 | 0 | 96.6667 | noise005 |
| reproduction/recovery_v2_20261012_01/confirmation:enabled=v2 | v2 | v2 | Full (three-seed mean) | 0.05 | 171 | 180 | 0.95 | 60 | 60 | 3 | 95 | noise005 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | disabled | BC k=2 | 0 | 48 | 60 | 0.8 | 60 | 60 | 0 | 80 | clean |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | disabled | Full (three-seed mean) | 0 | 138 | 180 | 0.766667 | 60 | 60 | 3 | 76.6667 | clean |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | v2 | BC k=2 | 0 | 54 | 60 | 0.9 | 60 | 60 | 0 | 90 | clean |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | v2 | Full (three-seed mean) | 0 | 162 | 180 | 0.9 | 60 | 60 | 3 | 90 | clean |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | disabled | BC k=2 | 0.05 | 47 | 60 | 0.783333 | 60 | 60 | 0 | 78.3333 | noise005 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | disabled | Full (three-seed mean) | 0.05 | 140 | 180 | 0.777778 | 60 | 60 | 3 | 77.7778 | noise005 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | v2 | BC k=2 | 0.05 | 55 | 60 | 0.916667 | 60 | 60 | 0 | 91.6667 | noise005 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v2 | v2 | v2 | Full (three-seed mean) | 0.05 | 165 | 180 | 0.916667 | 60 | 60 | 3 | 91.6667 | noise005 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | disabled | BC k=2 | 0 | 48 | 60 | 0.8 | 60 | 60 | 0 | 80 | clean |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | disabled | Full (three-seed mean) | 0 | 138 | 180 | 0.766667 | 60 | 60 | 3 | 76.6667 | clean |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | v3 | BC k=2 | 0 | 54 | 60 | 0.9 | 60 | 60 | 0 | 90 | clean |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | v3 | Full (three-seed mean) | 0 | 160 | 180 | 0.888889 | 60 | 60 | 3 | 88.8889 | clean |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | disabled | BC k=2 | 0.05 | 47 | 60 | 0.783333 | 60 | 60 | 0 | 78.3333 | noise005 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | disabled | Full (three-seed mean) | 0.05 | 140 | 180 | 0.777778 | 60 | 60 | 3 | 77.7778 | noise005 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | v3 | BC k=2 | 0.05 | 54 | 60 | 0.9 | 60 | 60 | 0 | 90 | noise005 |
| reproduction/recovery_v3_20261012_01/confirmation:enabled=v3 | v3 | v3 | Full (three-seed mean) | 0.05 | 166 | 180 | 0.922222 | 60 | 60 | 3 | 92.2222 | noise005 |
