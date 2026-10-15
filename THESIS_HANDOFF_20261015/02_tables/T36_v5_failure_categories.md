# v5 剩余失败类别

现有观测日志的事后失败分类，不是碰撞因果或物理真值标签。v5 尚有失败执行和共同失败起点；不能写成恢复问题完全解决。

完整数值：`T36_v5_failure_categories.csv`。Markdown 仅显示约 6 位有效数字。

| failure_category | failure_execution_count | total_failure_executions | total_failure_distinct_starts | failure_start_ids | condition | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| object_below_recovery_floor | 6 | 16 | 7 | ["demo_10000001","demo_10000007","demo_10000018","demo_10000021","demo_10000029","demo_10000034","demo_10000037"] | see_row_or_catalog | 7 | 3 |
| attempts_exhausted_after_observed_loss | 4 | 16 | 7 | ["demo_10000001","demo_10000007","demo_10000018","demo_10000021","demo_10000029","demo_10000034","demo_10000037"] | see_row_or_catalog | 7 | 3 |
| attempts_exhausted_before_completion | 6 | 16 | 7 | ["demo_10000001","demo_10000007","demo_10000018","demo_10000021","demo_10000029","demo_10000034","demo_10000037"] | see_row_or_catalog | 7 | 3 |
