# 开发集候选覆盖与回退比例

反复查看的 30 个开发起点；用于模型/参数选择和消融，不能作为独立泛化确认。各方法的训练种子数见行字段；BC 的 0 表示固定策略且无世界模型训练种子。

完整数值：`T11_development_controller_usage.csv`。Markdown 仅显示约 6 位有效数字。

| method | noise | mean_per_seed_override_fraction | all_three_seeds_selected_k2_at_every_step | condition | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- |
| full | 0.0 | 0.24899646000567743 | False | clean | 30 | 3 |
| plain | 0.0 | 0.12061096624131902 | False | clean | 30 | 3 |
| direct | 0.0 | 0.2950233205916856 | False | clean | 30 | 3 |
| prediction_only | 0.0 | 0.0 | True | clean | 30 | 3 |
| head_control | 0.0 | 0.26337137993220433 | False | clean | 30 | 3 |
| calibrated | 0.0 | 0.24634714890891188 | False | clean | 30 | 3 |
| no_risk_score | 0.0 | 0.2505867441959166 | False | clean | 30 | 3 |
| no_gate | 0.0 | 0.8984178591529336 | False | clean | 30 | 3 |
| horizon4 | 0.0 | 0.052360456434772475 | False | clean | 30 | 3 |
| full | 0.05 | 0.24391590097895458 | False | noise005 | 30 | 3 |
| plain | 0.05 | 0.10192400095414478 | False | noise005 | 30 | 3 |
| direct | 0.05 | 0.3037711607382828 | False | noise005 | 30 | 3 |
| prediction_only | 0.05 | 0.0 | True | noise005 | 30 | 3 |
| head_control | 0.05 | 0.2539107293023579 | False | noise005 | 30 | 3 |
| calibrated | 0.05 | 0.2542317685994262 | False | noise005 | 30 | 3 |
| no_risk_score | 0.05 | 0.23995836390316397 | False | noise005 | 30 | 3 |
| no_gate | 0.05 | 0.9171750343991366 | False | noise005 | 30 | 3 |
| horizon4 | 0.05 | 0.049595150748553064 | False | noise005 | 30 | 3 |
