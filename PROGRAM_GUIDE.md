> **v13更新（2026-10-16）**：v13完成：开发236/240；全新60起点确认v6 445/480、v12 437/480、v13 448/480。未通过本轮对照采用门槛，保留为候选；主要配对区间未完全高于零，不能宣称总体成功率改善。 [报告](reproduction/improvement_v13_20261016_01/REPORT.md) · [前端](reproduction/improvement_v13_20261016_01/index.html)。旧代码、权重、结果保留。

# 项目运行与模块指南

更新：2026-10-16。项目根`C:\Users\Livio\Desktop\robot_can`，解释器`.venv\Scripts\python.exe`。

## 1. 展示已有成果

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1
```

保持终端运行，打开 **http://127.0.0.1:8766/** 。根入口自动跳到v13。已有该端口服务时直接打开，不必重复启动。关闭服务按`Ctrl+C`；另用端口时命令和网址一起修改。


最新页面：[v13](reproduction/improvement_v13_20261016_01/index.html)。展示包含最终小测试、四组消融、240开发、1440配对确认、两段同起点视频和五张新图。历史v12及完整世界模型/v5展示从页面导航进入。

## 2. 不运行实验的完整性核验

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v13_20261016_01/verify_integrity.py
```

只读检查本轮前10982个登记路径、9份活动文档的原样备份、当前交付清单及开发/确认冻结锁。不会训练或仿真。旧verify绑定当时根文档，可能因后续授权更新而提示差异；不要改旧manifest或删除结果绕过检查。


## 3. 本轮实验复核入口

冻结代码在`reproduction/improvement_v13_20261016_01/recovery/`，各阶段同时保存source快照。原始结果和trace位于smoke_a/c/d/e、pilot_a、dev_a、confirmation；smoke_b为保留的中断记录。

新的重复执行目录示例：

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v13_20261016_01/run_batch.py --stage smoke_repeat_01 --jobs protocols/smoke_jobs.json --workers 4
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v13_20261016_01/verify_run.py --stage smoke_repeat_01
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v13_20261016_01/verify_physics.py --stage smoke_repeat_01
```

完整开发/确认重复可分别使用`protocols/dev_jobs.json`、`protocols/confirmation_jobs.json`，阶段名必须未存在。重复执行改变本轮交付目录后，交付清单不会自动覆盖新增文件；原封存资料继续有效，新增复核应单独登记。不要再次运行原确认生成器或覆盖原analysis。重复旧起点不是新的独立确认。

## 4. 算法和数据流

`common.py`创建仿真并读取23维真值状态 → 冻结BC输出动作块 → BC k=2固定选第三项或Full对四个候选评分 → 共享恢复监督器按可行性/抓持证据选择动作 → D2 FIFO出队并施加动作噪声 → 仿真一步并记录。成功标签只用于评估终止，不参与控制选择。

恢复器额外使用当前7关节角和已知几何。S为支撑识别加新候选路径；R为长等待有界撤退/重规划。控制器不因未知可行性默认下降。400步包括规划等待和恢复，时钟不会重置。

## 5. 环境、历史与迁移

[环境指南](ENVIRONMENT_GUIDE.md)保留实际版本和兼容说明。`requirements-repro.txt`是旧建议，不是当前完整可移植锁文件。看视频无需重装仿真环境。

[完整结果](RESULTS.md) · [证据索引](EVIDENCE_INDEX.md) · [v13完整报告](reproduction/improvement_v13_20261016_01/REPORT.md) · [旧v5README](reproduction/recovery_v5_20261012_01/README.md)。旧代码依赖和历史结果不得删掉。本轮没有训练或论文；换设备使用完整仓库，详见[交接说明](THESIS_HANDOFF_LATEST.md)。
