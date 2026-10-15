# 同成功数、同起点和不同步数检查

成功数相同并不证明输出复制；identical_success_sets 指二值成功起点集合相同，identical_step_vectors 是全步数向量是否相同。噪声下成功集合可不同。

完整数值：`T34_seed_duplicate_success_diagnostic.csv`。Markdown 仅显示约 6 位有效数字。

| method | condition | identical_success_sets | identical_step_vectors | success_counts | independent_N | seed_count |
| --- | --- | --- | --- | --- | --- | --- |
| full | clean | True | False | [54,54,54] | 60 | 3 |
| plain | clean | True | False | [53,53,53] | 60 | 3 |
| full | noise005 | False | False | [52,52,51] | 60 | 3 |
| plain | noise005 | False | False | [50,51,50] | 60 | 3 |
