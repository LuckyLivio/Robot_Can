# 程序说明与复现实验指南

工作目录：`C:\Users\Livio\Desktop\robot_can`。以下命令默认在该目录、PowerShell 中执行。当前 PyCharm 项目解释器是 `.\.venv\Scripts\python.exe`（Python 3.10.9）。新机器的环境配置、检查发现和分阶段复现步骤见 `REPRODUCTION_PLAN.md`；本指南其余实验内容保留原样。

## 1. 代码结构

- `common.py`：robosuite 环境、观测打包、示范恢复、BC 策略加载。
- `collect_delay_branches.py`：在 FIFO 延迟下从同一示范状态采集多个动作候选的真实未来状态和进度/风险标签。
- `world_model.py`：action-conditioned GRU 世界模型、DirectScore 消融和评分函数。
- `train_world.py`：状态预测、进度/风险监督、组内候选排序损失的训练入口。
- `evaluate_delay.py`：延迟闭环仿真；支持 BC、固定偏移、WM 门控、噪声和封存测试。
- `make_figures.py`：读取结果 JSON，生成论文 PNG/PDF 图。
- `queue_v2.py`：早期队列覆盖探索，保留用于审计，不属于主线。

模型、数据和运行结果分别放在 `models/`、`data/` 和 `figures/`。每个评估 JSON 都保存参数、每个起点的成功与步数以及总成功率，因此表格不依赖终端日志。

## 2. 环境检查

```powershell
$PY = ".\.venv\Scripts\python.exe"
# 首次安装依赖后，先执行 Windows 兼容准备，再导入 robosuite。
& $PY setup_windows.py
& $PY -c "import torch,robosuite,h5py; print(torch.__version__, torch.cuda.is_available(), robosuite.__version__)"
& $PY smoke_env.py
```

官方数据文件应为 `data/can_ph_lowdim_v15.hdf5`，并由 `data/splits.json` 给出完整轨迹划分。训练、开发、封存测试按父轨迹切分，不能按帧随机切分。

## 3. 重新采集延迟分支

主线使用固定偏移候选、延迟 2、每条轨迹 8 个状态点、4 个候选：

```powershell
& $PY collect_delay_branches.py --split train --demos 20 --points 8 --horizon 8 --candidates 4 --delay 2 --seed 2718 --name delay2_shift_v0 --policy bc_chunk_dev_v4 --policy-checkpoint policy_15000.pt --candidate-mode shift
& $PY collect_delay_branches.py --split dev --demos 30 --points 8 --horizon 8 --candidates 4 --delay 2 --seed 2718 --name delay2_shift_v0 --policy bc_chunk_dev_v4 --policy-checkpoint policy_15000.pt --candidate-mode shift
```

扩大训练量的补充版本把 `--demos 100 --name delay2_shift_big100`，但它只能作为敏感性实验，不能替换已冻结的主表配置。

## 4. 训练三个结构版本

```powershell
& $PY train_world.py --method full --dataset delay2_shift_v0 --run full_future_delay2_shift_v0 --seed 17 --updates 3000 --batch 16 --future-only --rank-weight .2
& $PY train_world.py --method plain --dataset delay2_shift_v0 --run plain_future_delay2_shift_v0 --seed 17 --updates 3000 --batch 16 --future-only --rank-weight .2
& $PY train_world.py --method direct --dataset delay2_shift_v0 --run direct_delay2_shift_v0 --seed 17 --updates 3000 --batch 16 --rank-weight .2
```

`full` 是完整方法；`plain` 将排序损失权重置为 0；`direct` 不生成未来状态，只学习直接评分。`model.pt` 会保存开发集最优检查点，`log.json` 保存训练日志。

## 5. 复现主线评估

先在开发集选择固定偏移：

```powershell
foreach ($k in 0,1,2,3) {
  & $PY evaluate_delay.py --method bc_shift --model full_future_delay2_shift_v0 --split dev --delay 2 --episodes 30 --shift-index $k
}
```

然后冻结 `k=1`、门控阈值 `0.02`，运行封存测试。封存结果只用于报告，不再调参：

```powershell
& $PY evaluate_delay.py --method bc --model full_future_delay2_shift_v0 --split sealed_test --delay 2 --episodes 30
& $PY evaluate_delay.py --method bc_shift --model full_future_delay2_shift_v0 --split sealed_test --delay 2 --episodes 30 --shift-index 1
& $PY evaluate_delay.py --method bc_shift --model full_future_delay2_shift_v0 --split sealed_test --delay 2 --episodes 30 --shift-index 1 --noise .05
& $PY evaluate_delay.py --method wm --model full_future_delay2_shift_v0 --split sealed_test --delay 2 --episodes 30 --candidate-mode shift --candidates 4 --score-only --fallback shift --fallback-index 1 --gate-margin .02
& $PY evaluate_delay.py --method wm --model full_future_delay2_shift_v0 --split sealed_test --delay 2 --episodes 30 --candidate-mode shift --candidates 4 --score-only --fallback shift --fallback-index 1 --gate-margin .02 --noise .05
```

`--score-only` 表示控制器按学习到的未来进度/风险评分选候选；完整模型内部仍然递归预测状态。部署过程不读取仿真器的真值目标或未来奖励，真值只在分支采集阶段作为训练标签。

## 6. 生成图和核对结果

```powershell
& $PY make_figures.py
Get-Content RESULTS_TABLE.csv
```

生成的论文图包括：成功率与固定偏移扫描、结构消融、成对胜负、成功回合步数箱线图、训练曲线；每张图同时保存为 `figures/*.png` 和 `figures/*.pdf`。

## 7. 结果解释规则

主比较是“开发集选出的最强固定偏移 `k=1`”对“同一策略、同一延迟、同一起点上的 WM 门控”。不要把旧的 `k=2` 运行和新 `k=1` 运行放在同一主表中。报告成功率、成对胜负和噪声条件；开发集负责选模型/阈值，sealed_test 只负责最终检验。

当前低维状态结果说明世界模型在动作噪声下能够依据预测风险选择候选动作，不能直接写成真实机器人或完整视觉系统已经验证。若论文题目包含“视觉”，后续应加图像编码器和一组小规模视觉复核，或把题目明确写成“视觉世界模型的低维状态控制诊断”。
