> **v12更新（2026-10-15）**：v12已完成：开发236/240；全新60起点确认v12 465/480、v6 473/480；救回1、退步9。对照门槛未通过；配对区间没有高于零，不能宣称总体成功率提升。 [报告](reproduction/improvement_v12_20261015_01/REPORT.md) · [新前端](reproduction/improvement_v12_20261015_01/index.html)。旧v5冻结证据及全部旧资产保留。

> 历史阶段：2026-10-15论文图表复查：[新图与数据总览](reproduction/paper_quality_20261015_01/index.html) · [全项目报告](reproduction/paper_quality_20261015_01/REPORT.md) · [当前提纲与证据映射](reproduction/paper_quality_20261015_01/THESIS_OUTLINE_REVIEWED.md)。36张图重新生成；没有新增训练、仿真或论文正文。

# 当前项目运行与模块指南

更新：2026-10-15。项目根为 `C:\Users\Livio\Desktop\robot_can`，PyCharm解释器为 `.venv\Scripts\python.exe`。

## 先看成果

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1
```

保持终端运行，打开 **http://127.0.0.1:8766/** 。根入口自动跳到[v12当前展示](reproduction/improvement_v12_20261015_01/index.html)。若端口已有本项目服务，直接使用。前端是静态文件服务，不会运行机器人或训练。

此前全项目[审查页面](reproduction/project_audit_20261015_01/index.html)与[分类导航](WORKSPACE/index.html)另行提供。v12局部修复通过开发，但独立确认未过采用门槛；正式冻结主成果仍为v5，历史完整展示可从当前前端进入。

## 只读完整性检查

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction\improvement_v12_20261015_01\verify_integrity.py
```

验证本轮v12修改前10,594个登记文件：授权改动的9份活动文档按before原样备份核对，其他文件在原位置核对；另验当前交付清单及开发、确认冻结锁。不训练、不创建环境、不物理回放。历史verify绑定当时根文档，可能因后续授权文档更新失败；不要改旧manifest或删除结果绕过检查。

## 环境与模型

```powershell
& '.\.venv\Scripts\python.exe' -m pip check
```

当前版本、CUDA和主权重前向已核对，见[环境指南](ENVIRONMENT_GUIDE.md)。`requirements-repro.txt`是旧建议，不是当前可移植锁文件。看已有视频无需重装仿真环境。

## 模块与入口选择

| 模块 | 用途 |
|---|---|
| common.py | 数据/23维观测、BC加载、控制器和传感器状态恢复 |
| collect_rollout_branches.py | 同历史/同FIFO候选采集 |
| world_model.py / train_world.py | 残差动力学、进展/失抓头、排序；根训练入口为历史入口 |
| reproduction/multiseed_20261012_01/train_suite.py | 匹配三种子与公平训练 |
| reproduction/confirmation_20261012_01/ | 冻结世界模型确认协议与结果 |
| reproduction/recovery_v5_20261012_01/ | 当前冻结恢复主线与精确状态重跑包装 |
| reproduction/improvement_v6_… 至 v12_… | 分离候选与负结果，不能自动视为已采用 |
| reproduction/improvement_v12_20261015_01/ | 当前展示、等待抓持修复、消融、开发及新起点独立确认 |
| reproduction/progress_v11_20261015_01/demo/ | 历史完整展示、世界模型及v5—v11视频 |

33个根Python入口包含旧探索路线。不要逐个按默认参数运行来“验收整个项目”：例如evaluate_delay默认候选数、门限与冻结主协议不同。旧任务JSON含本机命令路径，迁移时需新包装器处理，保留旧协议。

完整v5重跑命令在[v5 README](reproduction/recovery_v5_20261012_01/README.md)。这些命令会仿真且拒绝覆盖；只读审查不执行它们。重跑必须新输出目录，已看过的起点重复执行不称独立确认。新机器方案见[调整计划](reproduction/project_audit_20261015_01/IMPROVEMENT_PLAN.md)。

## 换设备或只展示

[便携交付说明](reproduction/portable_delivery_20261015_01/README.md)提供展示包、v6—v11写作增补和三个ZIP的集中迁移目录。解压展示包后，在CAN_LAB_DEMO目录执行 `python -B portable.py serve --port 8767 --open`，首页为 http://127.0.0.1:8767/ 。无需安装仿真依赖。

新重跑包装入口在 `reproduction/portable_delivery_20261015_01/launcher.py`：无参数只显示帮助，rerun默认只列计划，必须显式实验名、新output及--execute才会仿真；源代码/权重/数据先做589项哈希核验。历史jobs保留原样。第二台电脑按[清单](reproduction/portable_delivery_20261015_01/TARGET_DEVICE_CHECKLIST.md)逐项验收。
