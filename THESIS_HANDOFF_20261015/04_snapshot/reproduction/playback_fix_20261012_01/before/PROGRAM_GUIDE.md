# 当前项目运行与模块指南

工作目录 `C:\Users\Livio\Desktop\robot_can`；PyCharm解释器沿用 `.venv\Scripts\python.exe`。环境版本与兼容说明见[ENVIRONMENT_GUIDE](ENVIRONMENT_GUIDE.md)。

## 先看成果

当前[展示页面](reproduction/consolidation_20261012_01/demo/index.html)包含原始视频、v5结果和日志轨迹。用PowerShell启动静态服务：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1
```

浏览器打开 `http://127.0.0.1:8766/reproduction/consolidation_20261012_01/demo/index.html`。这是文件服务，不训练或运行机器人。若端口已经由项目文件服务使用，复用该服务。

## 当前只读完整性复核

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction\consolidation_20261012_01\verify.py
```

该入口按本阶段清单验证：旧根文档对应归档副本、其他原文件保持原位，新文档/前端/分析哈希不变；不调用环境、模型、训练或物理回放。旧review/v5验收脚本绑定历史根文档，根文档已授权更新，直接调用可能提示根文档变动。旧验收记录保留，不修改其清单。

## 实验复核/重跑入口

当前查看成果不需要重新训练。v5逐步/物理核验与另开目录完整重跑命令见[v5 README](reproduction/recovery_v5_20261012_01/README.md)；它们会执行仿真，需主动选择。最新根文档已更新，如其旧全项目保护检查提示根文档变动，先用当前verify核对归档，不删除结果或改历史保护清单。

各实验原脚本仍在原目录，重跑应在新的副本/输出目录进行，并重新登记。prepare生成器、统计图脚本常为排他写入，不能删除旧产物强行运行。不得把已看过的起点重复运行称新的独立确认。

## 模块

| 模块 | 作用 |
|---|---|
| common.py | 环境/数据、23维观测、控制器/传感器恢复、BC加载 |
| train_policy.py / ChunkPolicy | 混合密度动作块BC；当前冻结权重沿用 |
| collect_rollout_branches.py | 完整历史回放、真实队列同状态分支采集 |
| world_model.py / train_world.py | GRU残差状态预测、进度/抓持丢失头、组内排序 |
| evaluate_delay.py | 原世界模型候选门限与延迟闭环 |
| extensions/evaluate.py | 持续性、短期oracle、H/K开发诊断 |
| recovery_v5/recovery_controller.py / clearance.py | 共享恢复状态机与固定夹爪几何筛选 |
| consolidation/build_evidence.py | 读取已有结果统计和轨迹；没有策略运行 |
| consolidation/demo | 静态前端，读取既有结果与视频 |

根目录33个原Python脚本未改动；旧探索资产见原[模块清单](reproduction/review_20261012_01/module_inventory.json)，不要逐个运行默认参数来代替当前复核。

版本：2026-10-12 成果整合版；旧根文档见 reproduction/consolidation_20261012_01/previous_documents/
