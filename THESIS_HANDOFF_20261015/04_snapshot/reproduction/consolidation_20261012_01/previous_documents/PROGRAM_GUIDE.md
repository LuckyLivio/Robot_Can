# 项目运行与模块指南

版本：2026-10-12 冻结确认后的文档整理版。历史文档完整保存在 [previous_documents](reproduction/release_20261012_01/previous_documents/)。

项目路径：`C:\Users\Livio\Desktop\robot_can`。PyCharm解释器使用已有`.venv\Scripts\python.exe`，工作目录设为项目根目录；不重建或替换环境。

## 1. 当前环境

Python 3.10.9；PyTorch 2.14.1+cu130；NumPy 1.26.4；robosuite 1.5.1；MuJoCo 3.3.0。训练使用既有GPU；确认评估使用CPU，每进程2个torch线程。完整配置见[environment.json](reproduction/confirmation_20261012_01/environment.json)。视频使用当前机器已有FFmpeg和Pillow/OpenCV，不改变训练依赖。

本次实测[pip/CUDA/版本](reproduction/review_20261012_01/environment.json)通过，另存[完整安装版本快照](reproduction/review_20261012_01/environment-freeze.txt)。根目录`requirements-repro.txt`是旧安装建议，其torch 2.9.1注释不代表冻结实验实际版本；当前实际为2.14.1+cu130。不要为了对齐旧注释降级现有环境。版本快照不是跨机器离线安装包，Windows DLL/WGL兼容配置见历史`data/windows_compatibility.json`和`setup_windows.py`；现环境已配置，本轮未执行安装或补丁。

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
$PY = '.\.venv\Scripts\python.exe'
& $PY -X utf8 -B -u '.\reproduction\review_20261012_01\verify_project.py'
```

该命令核对当前文档/前端与全部原有非根文档文件，不重新训练。上一版release验收脚本绑定上一版根文档，保留为历史入口；当前文档已获准修订，使用这里的新命令。

## 2. 模块职责

| 模块 | 作用 |
| --- | --- |
| common.py | 数据/环境构造、23维状态打包、恢复仿真和控制器缓存、BC加载 |
| train_policy.py | 示范学习动作块BC；本轮沿用冻结policy_15000.pt |
| collect_rollout_branches.py | 回放完整动作历史，同状态/真实FIFO下采集候选分支与标签 |
| world_model.py | GRU残差动力学、未来状态评分头、组内排序损失、Direct对照 |
| train_world.py / multiseed目录train_suite.py | 基础训练入口 / 已验证的配对种子训练编排 |
| evaluate_delay.py | 延迟队列与候选门限闭环；原始核心保留 |
| diagnose_candidate_truth.py / calibrate_score_head.py | 真实后果诊断 / 评分头校准探索 |
| confirmation目录prepare_states.py、evaluate_confirmation.py | 锁定新起点 / 调用不变的评估核心 |
| confirmation目录analyze_confirmation.py | 从原始JSON生成配对统计和PNG/PDF |
| release目录make_demo.py | 重复运行核对、精确动作回放、并排视频及本地展示页 |

根目录共有33份Python脚本。上表是当前主线，完整逐项用途、历史运行证据和未完成范围见[全项目复核](PROJECT_AUDIT.md)及[模块清单](reproduction/review_20261012_01/module_inventory.json)。旧探索脚本的默认参数不是本轮锁定配置，部分旧脚本会写回固定路径，不要用“全部逐个执行”代替当前复核。

## 3. 直接看当前成果

先读[结果](RESULTS.md)，再打开[新版演示页面](reproduction/review_20261012_01/demo/index.html)。使用本地服务的方法和逐段讲解见[DEMO_GUIDE](DEMO_GUIDE.md)。主图为[确认成功率](reproduction/confirmation_20261012_01/analysis/confirmation_success.png)与[配对差异](reproduction/confirmation_20261012_01/analysis/paired_effects.png)，无需重新计算。

## 4. 核对已完成确认任务

```powershell
& $PY -X utf8 -B -u '.\reproduction\confirmation_20261012_01\run_confirmation.py'
```

完整任务会核对输入及输出哈希后跳过，不覆盖结果；发现中断日志会停止要求检查。确认数据、全部7个权重及控制参数见[design.json](reproduction/confirmation_20261012_01/design.json)与[lock.json](reproduction/confirmation_20261012_01/lock.json)。不能为了重跑而删除原输出或改锁定清单。

## 5. 另开目录重跑开发训练（可选，不是看演示的前置步骤）

```powershell
& '.\reproduction\multiseed_20261012_01\rerun.ps1' -Tag ('multiseed_repeat_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
```

该命令训练并评估整套开发消融，耗时明显较长；自动新建目录，不替换当前权重。后续若改算法，需要另立预登记确认实验，不能把目前60个起点再次当未见数据。

## 6. 权重与旧文件

BC：`policy/bc_chunk_dev_v4/policy_15000.pt`。Full/Plain：`models/multiseed_20261012_01_{full,plain}_s{17,23,41}/model.pt`。不将某个确认表现最好种子提升为全局默认。

用户最初提供的`model.pt`仍保留为旧版本权重；其用途和当时哈希见[首次检查归档](reproduction/release_20261012_01/previous_documents/REPRODUCTION_PLAN.md)。旧`make_figures.py`包含历史固定数组，旧`RESULTS_TABLE.csv`和`figures/`不作当前图表入口。所有既有文件保留，历史试验与当前主表分开。
