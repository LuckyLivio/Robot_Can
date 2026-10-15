# 源码与模块

分类入口；原文件保留在既有路径，没有搬移、复制执行源码或改写历史结果。

- [观测、环境、动作块BC与状态恢复](../../common.py) — `common.py`
- [世界模型、候选评分、排序损失](../../world_model.py) — `world_model.py`
- [BC训练历史入口](../../train_policy.py) — `train_policy.py`
- [真实队列一致的分支采集](../../collect_rollout_branches.py) — `collect_rollout_branches.py`
- [三种子公平训练源码](../../reproduction/multiseed_20261012_01/train_suite.py) — `reproduction/multiseed_20261012_01/train_suite.py`
- [冻结世界模型确认的控制语义](../../reproduction/confirmation_20261012_01/evaluator_core.py) — `reproduction/confirmation_20261012_01/evaluator_core.py`
- [v5共享恢复状态机](../../reproduction/recovery_v5_20261012_01/recovery_controller.py) — `reproduction/recovery_v5_20261012_01/recovery_controller.py`
- [侧倒几何间隙判定](../../reproduction/recovery_v5_20261012_01/clearance.py) — `reproduction/recovery_v5_20261012_01/clearance.py`


当前版本补充：[全项目审查](../../reproduction/project_audit_20261015_01/REPORT.md) · [最新交接说明](../../THESIS_HANDOFF_LATEST.md) · [候选v11](../../reproduction/improvement_v11_20261015_01/REPORT.md)。旧迁移包为c8bbe86快照，不含后续候选。
