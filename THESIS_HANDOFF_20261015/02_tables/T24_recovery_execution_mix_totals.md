# v5 dev_a 执行混合总表及净救回

v5 开发比较：30 个复用起点。表含 5 版本共 1,200 条已存在记录，其中 v2/v4 共 480 条为沿用；本阶段只新执行 T/S/v5 720 回合。不是 1,200 个独立样本。区间按起点重采样，3 个固定 Full 种子在起点内平均。

完整数值：`T24_recovery_execution_mix_totals.csv`。Markdown 仅显示约 6 位有效数字。

| version | successes | episodes | rescues_vs_v2 | regressions_vs_v2 | distinct_rescued_starts_vs_v2 | rescues_vs_v4 | regressions_vs_v4 | distinct_rescued_starts_vs_v4 | success_percent | distinct_rescued_N_vs_v2 | distinct_rescued_N_vs_v4 | condition | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2 | 229 | 240 | 0 | 0 | [] | 0 | 0 | [] | 95.4167 | 0 | 0 | see_row_or_catalog | 30 | 3 |
| v4 | 231 | 240 | 2 | 0 | ["demo_188"] | 0 | 0 | [] | 96.25 | 1 | 0 | see_row_or_catalog | 30 | 3 |
| timing_only | 234 | 240 | 5 | 0 | ["demo_124","demo_188","demo_73"] | 3 | 0 | ["demo_124","demo_73"] | 97.5 | 3 | 2 | see_row_or_catalog | 30 | 3 |
| side_only | 233 | 240 | 4 | 0 | ["demo_128","demo_188","demo_97"] | 2 | 0 | ["demo_128","demo_97"] | 97.0833 | 3 | 2 | see_row_or_catalog | 30 | 3 |
| v5 | 236 | 240 | 7 | 0 | ["demo_124","demo_128","demo_188","demo_73","demo_97"] | 5 | 0 | ["demo_124","demo_128","demo_73","demo_97"] | 98.3333 | 5 | 4 | see_row_or_catalog | 30 | 3 |
