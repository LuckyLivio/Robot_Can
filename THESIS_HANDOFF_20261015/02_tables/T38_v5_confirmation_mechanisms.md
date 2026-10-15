# v5 确认恢复机制事件覆盖

事件覆盖数按执行回合计，不是独立起点数。侧倒可行方案自然触发很稀少；不能把压力测试改善直接解释成自然分布上稳定的侧倒收益。

完整数值：`T38_v5_confirmation_mechanisms.csv`。Markdown 仅显示约 6 位有效数字。

| version | episodes | with_feasible_side_plan | with_infeasible_side_plan | with_budget_pressure | with_early_stall | with_early_descent_abort | failure_final_modes | condition | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2 | 480 | 0 | 0 | 0 | 0 | 0 | {"EXHAUSTED":19,"NORMAL":4} | see_row_or_catalog | 60 | 3 |
| v4 | 480 | 0 | 0 | 0 | 0 | 0 | {"RELEASE":3,"NORMAL":4,"EXHAUSTED":13,"RETREAT":3} | see_row_or_catalog | 60 | 3 |
| timing_only | 480 | 0 | 0 | 95 | 0 | 1 | {"NORMAL":4,"EXHAUSTED":13} | see_row_or_catalog | 60 | 3 |
| side_only | 480 | 1 | 0 | 0 | 0 | 0 | {"RELEASE":3,"NORMAL":4,"EXHAUSTED":12,"RETREAT":3} | see_row_or_catalog | 60 | 3 |
| v5 | 480 | 1 | 0 | 94 | 0 | 0 | {"NORMAL":4,"EXHAUSTED":12} | see_row_or_catalog | 60 | 3 |
