# v5 confirmation 执行混合总表及净救回

v5 独立确认的 60 个新起点，与 WM 主确认的 60 个起点不是同一批。每版本 480 次执行是 BC 2 条件 + Full 3 种子×2条件；仍只有 60 个独立起点。overall_execution_mix 为预定 8 次执行等权（BC 占1/4、Full占3/4），不能解释成模型等权平均。

完整数值：`T20_recovery_execution_mix_totals.csv`。Markdown 仅显示约 6 位有效数字。

| version | successes | episodes | rescues_vs_v2 | regressions_vs_v2 | distinct_rescued_starts_vs_v2 | rescues_vs_v4 | regressions_vs_v4 | distinct_rescued_starts_vs_v4 | success_percent | distinct_rescued_N_vs_v2 | distinct_rescued_N_vs_v4 | condition | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2 | 457 | 480 | 0 | 0 | [] | 0 | 0 | [] | 95.2083 | 0 | 0 | see_row_or_catalog | 60 | 3 |
| v4 | 457 | 480 | 1 | 1 | ["demo_10000034"] | 0 | 0 | [] | 95.2083 | 1 | 0 | see_row_or_catalog | 60 | 3 |
| timing_only | 463 | 480 | 7 | 1 | ["demo_10000029","demo_10000034"] | 6 | 0 | ["demo_10000029"] | 96.4583 | 2 | 1 | see_row_or_catalog | 60 | 3 |
| side_only | 458 | 480 | 2 | 1 | ["demo_10000012","demo_10000034"] | 1 | 0 | ["demo_10000012"] | 95.4167 | 2 | 1 | see_row_or_catalog | 60 | 3 |
| v5 | 464 | 480 | 8 | 1 | ["demo_10000012","demo_10000029","demo_10000034"] | 7 | 0 | ["demo_10000012","demo_10000029"] | 96.6667 | 3 | 2 | see_row_or_catalog | 60 | 3 |
