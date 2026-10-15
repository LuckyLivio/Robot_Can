# v5 confirmation 分条件主表

v5 独立确认的 60 个新起点，与 WM 主确认的 60 个起点不是同一批。每版本 480 次执行是 BC 2 条件 + Full 3 种子×2条件；仍只有 60 个独立起点。overall_execution_mix 为预定 8 次执行等权（BC 占1/4、Full占3/4），不能解释成模型等权平均。

完整数值：`T18_recovery_main.csv`。Markdown 仅显示约 6 位有效数字。

| version | method | noise | successes | execution_count | success_percent | ci95_low_percent | ci95_high_percent | seed_count | ci_method | condition | independent_N |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2 | bc_k2 | 0 | 59 | 60 | 98.3333 | 95 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 60 |
| v2 | bc_k2 | 0.05 | 57 | 60 | 95 | 88.3333 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 60 |
| v2 | full | 0 | 173 | 180 | 96.1111 | 91.1111 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 60 |
| v2 | full | 0.05 | 168 | 180 | 93.3333 | 87.2222 | 98.3333 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 60 |
| v4 | bc_k2 | 0 | 59 | 60 | 98.3333 | 95 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 60 |
| v4 | bc_k2 | 0.05 | 57 | 60 | 95 | 88.3333 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 60 |
| v4 | full | 0 | 173 | 180 | 96.1111 | 91.1111 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 60 |
| v4 | full | 0.05 | 168 | 180 | 93.3333 | 87.2222 | 98.3333 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 60 |
| timing_only | bc_k2 | 0 | 60 | 60 | 100 | 100 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 60 |
| timing_only | bc_k2 | 0.05 | 58 | 60 | 96.6667 | 91.6667 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 60 |
| timing_only | full | 0 | 175 | 180 | 97.2222 | 93.3333 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 60 |
| timing_only | full | 0.05 | 170 | 180 | 94.4444 | 89.4444 | 98.3333 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 60 |
| side_only | bc_k2 | 0 | 59 | 60 | 98.3333 | 95 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 60 |
| side_only | bc_k2 | 0.05 | 57 | 60 | 95 | 88.3333 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 60 |
| side_only | full | 0 | 174 | 180 | 96.6667 | 91.6667 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 60 |
| side_only | full | 0.05 | 168 | 180 | 93.3333 | 87.2222 | 98.3333 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 60 |
| v5 | bc_k2 | 0 | 60 | 60 | 100 | 100 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 60 |
| v5 | bc_k2 | 0.05 | 58 | 60 | 96.6667 | 91.6667 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 60 |
| v5 | full | 0 | 176 | 180 | 97.7778 | 93.8889 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 60 |
| v5 | full | 0.05 | 170 | 180 | 94.4444 | 89.4444 | 98.3333 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 60 |
