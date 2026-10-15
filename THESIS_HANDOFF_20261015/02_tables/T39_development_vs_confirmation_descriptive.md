# 开发与独立确认的描述性分布变化

原表 descriptive_change_pp 是不同起点分布间的描述性差值，不是同批配对提升，也不是训练改进效果。论文中应分别列开发结果和确认结果。

完整数值：`T39_development_vs_confirmation_descriptive.csv`。Markdown 仅显示约 6 位有效数字。

| method | condition | dev_initial_states | dev_success_percent | confirmation_initial_states | confirmation_success_percent | descriptive_change_pp | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bc_k2 | clean | 30 | 83.33333333333334 | 60 | 85.0 | 1.6666666666666572 | dev30;confirmation60 | 0 |
| full | clean | 30 | 78.88888888888889 | 60 | 90.0 | 11.111111111111114 | dev30;confirmation60 | 3 |
| plain | clean | 30 | 80.00000000000001 | 60 | 88.33333333333333 | 8.333333333333314 | dev30;confirmation60 | 3 |
| bc_k2 | noise005 | 30 | 80.00000000000001 | 60 | 81.66666666666667 | 1.6666666666666572 | dev30;confirmation60 | 0 |
| full | noise005 | 30 | 82.22222222222223 | 60 | 86.11111111111111 | 3.8888888888888857 | dev30;confirmation60 | 3 |
| plain | noise005 | 30 | 84.44444444444446 | 60 | 83.88888888888889 | -0.5555555555555713 | dev30;confirmation60 | 3 |
