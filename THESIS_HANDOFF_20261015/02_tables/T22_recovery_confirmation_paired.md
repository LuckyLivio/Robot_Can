# v5 确认逐种子配对救回与退步

v5 独立确认的 60 个新起点，与 WM 主确认的 60 个起点不是同一批。每版本 480 次执行是 BC 2 条件 + Full 3 种子×2条件；仍只有 60 个独立起点。overall_execution_mix 为预定 8 次执行等权（BC 占1/4、Full占3/4），不能解释成模型等权平均。

完整数值：`T22_recovery_confirmation_paired.csv`。Markdown 仅显示约 6 位有效数字。

| version | reference | method | seed | noise | successes | baseline_successes | episodes | rescues | regressions | rescued_demos | regressed_demos | condition | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v4 | v2 | bc_k2 |  | 0.0 | 59 | 59 | 60 | 0 | 0 | [] | [] | clean | 60 | 0 |
| v4 | v2 | full | 17 | 0.0 | 58 | 58 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| v4 | v2 | full | 23 | 0.0 | 58 | 58 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| v4 | v2 | full | 41 | 0.0 | 57 | 57 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| v4 | v2 | bc_k2 |  | 0.05 | 57 | 57 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 0 |
| v4 | v2 | full | 17 | 0.05 | 56 | 57 | 60 | 0 | 1 | [] | ['demo_10000034'] | noise005 | 60 | 1 |
| v4 | v2 | full | 23 | 0.05 | 57 | 56 | 60 | 1 | 0 | ['demo_10000034'] | [] | noise005 | 60 | 1 |
| v4 | v2 | full | 41 | 0.05 | 55 | 55 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| timing_only | v2 | bc_k2 |  | 0.0 | 60 | 59 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 0 |
| timing_only | v2 | full | 17 | 0.0 | 59 | 58 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 1 |
| timing_only | v2 | full | 23 | 0.0 | 59 | 58 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 1 |
| timing_only | v2 | full | 41 | 0.0 | 57 | 57 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| timing_only | v2 | bc_k2 |  | 0.05 | 58 | 57 | 60 | 1 | 0 | ['demo_10000029'] | [] | noise005 | 60 | 0 |
| timing_only | v2 | full | 17 | 0.05 | 57 | 57 | 60 | 1 | 1 | ['demo_10000029'] | ['demo_10000034'] | noise005 | 60 | 1 |
| timing_only | v2 | full | 23 | 0.05 | 58 | 56 | 60 | 2 | 0 | ['demo_10000029', 'demo_10000034'] | [] | noise005 | 60 | 1 |
| timing_only | v2 | full | 41 | 0.05 | 55 | 55 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| timing_only | v4 | bc_k2 |  | 0.0 | 60 | 59 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 0 |
| timing_only | v4 | full | 17 | 0.0 | 59 | 58 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 1 |
| timing_only | v4 | full | 23 | 0.0 | 59 | 58 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 1 |
| timing_only | v4 | full | 41 | 0.0 | 57 | 57 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| timing_only | v4 | bc_k2 |  | 0.05 | 58 | 57 | 60 | 1 | 0 | ['demo_10000029'] | [] | noise005 | 60 | 0 |
| timing_only | v4 | full | 17 | 0.05 | 57 | 56 | 60 | 1 | 0 | ['demo_10000029'] | [] | noise005 | 60 | 1 |
| timing_only | v4 | full | 23 | 0.05 | 58 | 57 | 60 | 1 | 0 | ['demo_10000029'] | [] | noise005 | 60 | 1 |
| timing_only | v4 | full | 41 | 0.05 | 55 | 55 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| side_only | v2 | bc_k2 |  | 0.0 | 59 | 59 | 60 | 0 | 0 | [] | [] | clean | 60 | 0 |
| side_only | v2 | full | 17 | 0.0 | 58 | 58 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| side_only | v2 | full | 23 | 0.0 | 58 | 58 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| side_only | v2 | full | 41 | 0.0 | 58 | 57 | 60 | 1 | 0 | ['demo_10000012'] | [] | clean | 60 | 1 |
| side_only | v2 | bc_k2 |  | 0.05 | 57 | 57 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 0 |
| side_only | v2 | full | 17 | 0.05 | 56 | 57 | 60 | 0 | 1 | [] | ['demo_10000034'] | noise005 | 60 | 1 |
| side_only | v2 | full | 23 | 0.05 | 57 | 56 | 60 | 1 | 0 | ['demo_10000034'] | [] | noise005 | 60 | 1 |
| side_only | v2 | full | 41 | 0.05 | 55 | 55 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| side_only | v4 | bc_k2 |  | 0.0 | 59 | 59 | 60 | 0 | 0 | [] | [] | clean | 60 | 0 |
| side_only | v4 | full | 17 | 0.0 | 58 | 58 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| side_only | v4 | full | 23 | 0.0 | 58 | 58 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| side_only | v4 | full | 41 | 0.0 | 58 | 57 | 60 | 1 | 0 | ['demo_10000012'] | [] | clean | 60 | 1 |
| side_only | v4 | bc_k2 |  | 0.05 | 57 | 57 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 0 |
| side_only | v4 | full | 17 | 0.05 | 56 | 56 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| side_only | v4 | full | 23 | 0.05 | 57 | 57 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| side_only | v4 | full | 41 | 0.05 | 55 | 55 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| v5 | v2 | bc_k2 |  | 0.0 | 60 | 59 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 0 |
| v5 | v2 | full | 17 | 0.0 | 59 | 58 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 1 |
| v5 | v2 | full | 23 | 0.0 | 59 | 58 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 1 |
| v5 | v2 | full | 41 | 0.0 | 58 | 57 | 60 | 1 | 0 | ['demo_10000012'] | [] | clean | 60 | 1 |
| v5 | v2 | bc_k2 |  | 0.05 | 58 | 57 | 60 | 1 | 0 | ['demo_10000029'] | [] | noise005 | 60 | 0 |
| v5 | v2 | full | 17 | 0.05 | 57 | 57 | 60 | 1 | 1 | ['demo_10000029'] | ['demo_10000034'] | noise005 | 60 | 1 |
| v5 | v2 | full | 23 | 0.05 | 58 | 56 | 60 | 2 | 0 | ['demo_10000029', 'demo_10000034'] | [] | noise005 | 60 | 1 |
| v5 | v2 | full | 41 | 0.05 | 55 | 55 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| v5 | v4 | bc_k2 |  | 0.0 | 60 | 59 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 0 |
| v5 | v4 | full | 17 | 0.0 | 59 | 58 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 1 |
| v5 | v4 | full | 23 | 0.0 | 59 | 58 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 1 |
| v5 | v4 | full | 41 | 0.0 | 58 | 57 | 60 | 1 | 0 | ['demo_10000012'] | [] | clean | 60 | 1 |
| v5 | v4 | bc_k2 |  | 0.05 | 58 | 57 | 60 | 1 | 0 | ['demo_10000029'] | [] | noise005 | 60 | 0 |
| v5 | v4 | full | 17 | 0.05 | 57 | 56 | 60 | 1 | 0 | ['demo_10000029'] | [] | noise005 | 60 | 1 |
| v5 | v4 | full | 23 | 0.05 | 58 | 57 | 60 | 1 | 0 | ['demo_10000029'] | [] | noise005 | 60 | 1 |
| v5 | v4 | full | 41 | 0.05 | 55 | 55 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| v5 | timing_only | bc_k2 |  | 0.0 | 60 | 60 | 60 | 0 | 0 | [] | [] | clean | 60 | 0 |
| v5 | timing_only | full | 17 | 0.0 | 59 | 59 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| v5 | timing_only | full | 23 | 0.0 | 59 | 59 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| v5 | timing_only | full | 41 | 0.0 | 58 | 57 | 60 | 1 | 0 | ['demo_10000012'] | [] | clean | 60 | 1 |
| v5 | timing_only | bc_k2 |  | 0.05 | 58 | 58 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 0 |
| v5 | timing_only | full | 17 | 0.05 | 57 | 57 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| v5 | timing_only | full | 23 | 0.05 | 58 | 58 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| v5 | timing_only | full | 41 | 0.05 | 55 | 55 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
| v5 | side_only | bc_k2 |  | 0.0 | 60 | 59 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 0 |
| v5 | side_only | full | 17 | 0.0 | 59 | 58 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 1 |
| v5 | side_only | full | 23 | 0.0 | 59 | 58 | 60 | 1 | 0 | ['demo_10000029'] | [] | clean | 60 | 1 |
| v5 | side_only | full | 41 | 0.0 | 58 | 58 | 60 | 0 | 0 | [] | [] | clean | 60 | 1 |
| v5 | side_only | bc_k2 |  | 0.05 | 58 | 57 | 60 | 1 | 0 | ['demo_10000029'] | [] | noise005 | 60 | 0 |
| v5 | side_only | full | 17 | 0.05 | 57 | 56 | 60 | 1 | 0 | ['demo_10000029'] | [] | noise005 | 60 | 1 |
| v5 | side_only | full | 23 | 0.05 | 58 | 57 | 60 | 1 | 0 | ['demo_10000029'] | [] | noise005 | 60 | 1 |
| v5 | side_only | full | 41 | 0.05 | 55 | 55 | 60 | 0 | 0 | [] | [] | noise005 | 60 | 1 |
