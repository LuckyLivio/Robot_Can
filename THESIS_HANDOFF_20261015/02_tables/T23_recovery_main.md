# v5 dev_a 分条件主表

v5 开发比较：30 个复用起点。表含 5 版本共 1,200 条已存在记录，其中 v2/v4 共 480 条为沿用；本阶段只新执行 T/S/v5 720 回合。不是 1,200 个独立样本。区间按起点重采样，3 个固定 Full 种子在起点内平均。

完整数值：`T23_recovery_main.csv`。Markdown 仅显示约 6 位有效数字。

| version | method | noise | successes | execution_count | success_percent | ci95_low_percent | ci95_high_percent | seed_count | ci_method | condition | independent_N |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2 | bc_k2 | 0 | 28 | 30 | 93.3333 | 83.3333 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 30 |
| v2 | bc_k2 | 0.05 | 28 | 30 | 93.3333 | 83.3333 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 30 |
| v2 | full | 0 | 84 | 90 | 93.3333 | 84.4444 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 30 |
| v2 | full | 0.05 | 89 | 90 | 98.8889 | 96.6667 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 30 |
| v4 | bc_k2 | 0 | 29 | 30 | 96.6667 | 90 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 30 |
| v4 | bc_k2 | 0.05 | 28 | 30 | 93.3333 | 83.3333 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 30 |
| v4 | full | 0 | 85 | 90 | 94.4444 | 86.6667 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 30 |
| v4 | full | 0.05 | 89 | 90 | 98.8889 | 96.6667 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 30 |
| timing_only | bc_k2 | 0 | 29 | 30 | 96.6667 | 90 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 30 |
| timing_only | bc_k2 | 0.05 | 30 | 30 | 100 | 100 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 30 |
| timing_only | full | 0 | 85 | 90 | 94.4444 | 86.6667 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 30 |
| timing_only | full | 0.05 | 90 | 90 | 100 | 100 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 30 |
| side_only | bc_k2 | 0 | 29 | 30 | 96.6667 | 90 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 30 |
| side_only | bc_k2 | 0.05 | 28 | 30 | 93.3333 | 83.3333 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 30 |
| side_only | full | 0 | 87 | 90 | 96.6667 | 91.1111 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 30 |
| side_only | full | 0.05 | 89 | 90 | 98.8889 | 96.6667 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 30 |
| v5 | bc_k2 | 0 | 29 | 30 | 96.6667 | 90 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 30 |
| v5 | bc_k2 | 0.05 | 30 | 30 | 100 | 100 | 100 | 0 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 30 |
| v5 | full | 0 | 87 | 90 | 96.6667 | 91.1111 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | clean | 30 |
| v5 | full | 0.05 | 90 | 90 | 100 | 100 | 100 | 3 | existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty | noise005 | 30 |
