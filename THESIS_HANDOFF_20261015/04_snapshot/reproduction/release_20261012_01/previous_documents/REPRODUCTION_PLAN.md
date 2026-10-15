# Robot Can 项目检查与 PyCharm 复现计划

检查日期：2026 年 10 月 11 日。项目目录：`C:\Users\Livio\Desktop\robot_can`。

本项目已有原始示范数据、固定划分、分支数据、模型权重及逐回合结果，可以先用现有权重复跑历史实验。重新采集和训练前，需要处理动作序列含义不一致及分支恢复异常。两种复现目标分开验收：跑出历史结果不能自动证明数据采集与算法解释正确。

你已在 PyCharm 创建 `.venv`，实际解释器为 `C:\Users\Livio\Desktop\robot_can\.venv\Scripts\python.exe`，Python 3.10.9；检查时该环境尚未安装项目依赖。依赖由你手动安装。此次仅修改原指南的环境路径和 `setup_windows.py` 的环境校验，算法、数据、权重与历史结果未改动。

## 一 项目和两个文件的检查结论

任务是 robosuite `PickPlaceCan`：Panda 机械臂抓取易拉罐并放入料箱。输入为 23 维低维观测，其中包含物体真实状态；输出为 7 维动作。BC 策略产生长度为 8 的动作块，世界模型对 4 个时间偏移候选评分，控制频率 20 Hz，FIFO 延迟 2 个控制周期，即名义 100 ms。

| 外部文件 | 已核实的项目内对应文件 | 内容 |
|---|---|---|
| `C:\Users\Livio\Desktop\model.pt` | `models/full_future_delay2_shift_v0/model.pt` | 完整 GRU 世界模型，宽度 128，87,321 参数，训练预算 3,000 步，实际保存开发集最优的第 1,000 步 |
| `C:\Users\Livio\Desktop\policy_15000.pt` | `policy/bc_chunk_dev_v4/policy_15000.pt` | MLP 混合密度 BC 策略，宽度 512、5 个混合分量，第 15,000 步检查点 |

两对文件的 SHA256 分别完全一致，因此无需再次复制，也不要用开发集 NLL 最优的 `policy.pt` 替换冻结的 `policy_15000.pt`。

```text
model.pt
339b9f3e4b4efd3504f6dd945fe4a3a1357cea9691369d850c7b0f85bd05f46d

policy_15000.pt
ef375a81d5c2a5dce26662c68c2965e1954c736cd824e40085a084073777af14

data/can_ph_lowdim_v15.hdf5
3f2eb92e0a5025d0095e866ac16cc8092d6a762abe27dec90dbaff9027282962
```

已完成的检查：

- 25 个根目录 Python 文件通过语法解析。
- 使用 `torch.load(..., weights_only=True)` 成功读取两个权重，并成功进行 CPU 前向计算：策略输出 `[1,8,7]`，世界模型状态输出 `[1,8,23]`，进度与风险输出 `[1,8,2]`，均无非有限数值。该检查使用机器已有的另一 Python 环境，不代表新 `.venv` 已可运行。
- HDF5 有 200 条轨迹、23,207 个转移，文件大小 46,889,752 字节，哈希与原 manifest 一致。
- `splits.json` 的 140 train / 30 dev / 30 sealed_test 互不重复，并完整覆盖数据。BC 训练窗口数为 15,373。
- 主线分支训练集为 20 条父轨迹、160 组；开发分支为 8 条父轨迹、64 组。父轨迹均属于相应划分。每组 4 候选、8 步预测。
- 10 份主线和消融历史结果的成功率与逐回合记录一致，每份包含 30 个不同的封存起点。
- 当前 GPU 是 RTX 5080 Laptop，16 GB 显存。已有基础 Python 中的 PyTorch 2.9.1+cu130 通过一次 CUDA 矩阵乘法检查。

本轮没有在新 `.venv` 中安装依赖、运行物理仿真或训练。完整机器可读证据见 `reproduction/inspection_20261011.json`。

## 二 PyCharm 环境配置

在 PyCharm 的 Python Interpreter 设置中选择现有 `.venv\Scripts\python.exe`，不需要重建环境。所有 Run Configuration 的工作目录设置为项目根目录。解释器选择方式可参照 [JetBrains 官方说明](https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html)。

建议的安装组合如下。物理仿真版本保持历史配置；PyTorch 改用当前 GPU 已验证可以计算的版本。原记录使用 PyTorch 2.5.1+cu124 和 RTX 4060，不能直接把该 GPU 环境当成当前机器的配置。[PyTorch 官方安装表](https://pytorch.org/get-started/previous-versions/)提供 2.9.1 的 CUDA 13.0 Windows 安装源。

| 组件 | 本次建议 | 说明 |
|---|---|---|
| Python | 已创建的 3.10.9 | 历史记录为 3.10.20；记录补丁版本差异 |
| PyTorch | 2.9.1，cu130 | 当前机器已有环境通过基本 GPU 运算；新环境仍需验证 |
| robosuite | 1.5.1 | 与数据环境版本一致 |
| MuJoCo | 3.3.0 | 保持历史物理引擎版本 |
| NumPy | 1.26.4 | 与历史数据检查记录一致 |
| h5py | 3.11.0 | 本轮成功读取数据的版本；原记录为 3.16.0 |
| Matplotlib | 3.9.4 | 固定旧绘图接口；新结果仍需修正汇总来源 |

其他依赖见 `requirements-repro.txt`。这是建议的安装规格，尚未在新环境完成安装验证，不能称为原实验的完整依赖锁文件。安装通过后另存 `pip freeze`，包括 robosuite 自动安装的传递依赖。当前主线无需安装 robomimic 训练框架、torchvision、torchaudio 或独立 CUDA Toolkit。

在 PyCharm Terminal 的 PowerShell 中按顺序执行。后续代码块沿用此处的 `$PY` 和工作目录：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
$PY = '.\.venv\Scripts\python.exe'
& $PY -c "import sys; print(sys.executable); print(sys.version)"
& $PY -m pip install --upgrade pip
& $PY -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cu130
& $PY -m pip install -r requirements-repro.txt
& $PY -m pip check
```

每条命令成功后再执行下一条。若 `pip check` 报冲突，先处理并记录冲突，不要直接升级 MuJoCo 或 robosuite 来跳过问题。

Windows 下 robosuite 1.5.1 会从其 `utils` 目录加载 `mujoco.dll`，并可能由渲染宏强制选择 EGL，见 [该版本官方源代码](https://github.com/ARISE-Initiative/robosuite/blob/v1.5.1/robosuite/utils/binding_utils.py)。项目已有兼容脚本会复制 DLL 并关闭该宏；本次已将它的环境校验更新为当前项目 `.venv`。

先保存历史环境检查文件，再运行兼容准备：

```powershell
$audit = 'reproduction\local_environment_20261011'
if (Test-Path -LiteralPath $audit) { throw '该记录目录已存在，请使用新的日期或编号。' }
New-Item -ItemType Directory -Path $audit | Out-Null
Copy-Item -LiteralPath 'data\windows_compatibility.json','data\environment_smoke.json' -Destination $audit
& $PY setup_windows.py
& $PY -c "import torch,numpy,h5py,robosuite,mujoco; print(torch.__version__,numpy.__version__,h5py.__version__,robosuite.__version__,mujoco.__version__); print('CUDA',torch.cuda.is_available()); a=torch.randn(64,64,device='cuda'); print(torch.cuda.get_device_name(0),bool(torch.isfinite(a@a).all()))"
& $PY -m pip freeze | Set-Content -Encoding utf8 "$audit\requirements-lock.txt"
& $PY smoke_env.py
Copy-Item -LiteralPath 'data\windows_compatibility.json' -Destination "$audit\windows_compatibility_current.json"
Copy-Item -LiteralPath 'data\environment_smoke.json' -Destination "$audit\environment_smoke_current.json"
```

验收：解释器路径正确；依赖检查无冲突；CUDA 运算成功；两个 demo 的初始观测误差不超过 `1e-3`，重复分支误差不超过 `1e-4`。同时人工查看 40 步回放误差，历史约为 `9e-4`；原脚本对此项没有强制阈值，明显变大时需检查版本和恢复流程。

`smoke_env.py` 只检查两个特定起点的恢复，不能替代第五节的分支一致性验证。首次运行可能有 Numba 编译等待。主线使用无窗口仿真，终端有结果而不弹出机械臂窗口属于正常行为。

## 三 用现有权重复跑历史结果

先完成此路线。它回答的是当前机器能否执行已保存的策略和控制器。

### 1 创建独立评估输出目录

评估器直接向 `models/<model>` 写结果，文件名不包含所有参数，也不会拒绝覆盖已有结果。因此使用新目录，只复制权重，保留历史 JSON。

```powershell
$copies = @{
    'repro_20261011_smoke'  = 'full_future_delay2_shift_v0'
    'repro_20261011_full'   = 'full_future_delay2_shift_v0'
    'repro_20261011_plain'  = 'plain_future_delay2_shift_v0'
    'repro_20261011_direct' = 'direct_delay2_shift_v0'
}
foreach ($name in $copies.Keys) {
    if (Test-Path -LiteralPath "models\$name") { throw "输出目录已存在：$name" }
}
foreach ($name in $copies.Keys) {
    New-Item -ItemType Directory -Path "models\$name" | Out-Null
    Copy-Item -LiteralPath "models\$($copies[$name])\model.pt" -Destination "models\$name\model.pt"
}
```

`evaluate_delay.py` 在 BC 模式也会加载世界模型文件，因此基线同样需要有效的 `--model` 目录。

### 2 两回合开发集运行检查

```powershell
& $PY evaluate_delay.py --method wm --model repro_20261011_smoke --policy bc_chunk_dev_v4 --policy-checkpoint policy_15000.pt --split dev --episodes 2 --steps 400 --delay 2 --horizon 8 --candidate-mode shift --candidates 4 --score-only --fallback shift --fallback-index 1 --gate-margin .02
```

验收：生成包含 2 条完整记录的 JSON，每条具有 demo、成功标志和步数。该步骤只确认运行链路；两回合成功率不能用于效果判断。

若用 PyCharm 的 Run 按钮：Script path 选择 `evaluate_delay.py`；Parameters 填上面命令中从 `--method` 开始的部分；Interpreter 选择 `.venv`；Working directory 设为项目根目录。不要将 `$PY` 或 `&` 放入 Parameters。

### 3 开发集固定偏移扫描

```powershell
foreach ($k in 0,1,2,3) {
    & $PY evaluate_delay.py --method bc_shift --model repro_20261011_full --split dev --episodes 30 --steps 400 --delay 2 --shift-index $k
    if ($LASTEXITCODE -ne 0) { throw "开发集 k=$k 运行失败。" }
}
& $PY evaluate_delay.py --method wm --model repro_20261011_full --split dev --episodes 30 --steps 400 --delay 2 --horizon 8 --candidate-mode shift --candidates 4 --score-only --fallback shift --fallback-index 1 --gate-margin .02
```

历史对照：固定偏移 `k=0/1/2/3` 分别为 `15/24/23/21` 次成功，WM 为 `25/30`。复跑时沿用历史冻结的 `k=1` 和门控阈值 `0.02`。如果新环境偏移扫描结果不同，记录差异，不根据已公开的封存结果重新选参数。

### 4 主表和结构消融

```powershell
foreach ($noise in 0,.05) {
    & $PY evaluate_delay.py --method bc --model repro_20261011_full --split sealed_test --episodes 30 --steps 400 --delay 2 --noise $noise
    if ($LASTEXITCODE -ne 0) { throw 'BC 评估失败。' }
    & $PY evaluate_delay.py --method bc_shift --model repro_20261011_full --split sealed_test --episodes 30 --steps 400 --delay 2 --shift-index 1 --noise $noise
    if ($LASTEXITCODE -ne 0) { throw '固定偏移评估失败。' }
    & $PY evaluate_delay.py --method wm --model repro_20261011_full --split sealed_test --episodes 30 --steps 400 --delay 2 --horizon 8 --candidate-mode shift --candidates 4 --score-only --fallback shift --fallback-index 1 --gate-margin .02 --noise $noise
    if ($LASTEXITCODE -ne 0) { throw 'WM 评估失败。' }
}
foreach ($model in 'repro_20261011_plain','repro_20261011_direct') {
    & $PY evaluate_delay.py --method wm --model $model --split sealed_test --episodes 30 --steps 400 --delay 2 --horizon 8 --candidate-mode shift --candidates 4 --score-only --fallback shift --fallback-index 1 --gate-margin .02 --noise .05
    if ($LASTEXITCODE -ne 0) { throw "消融评估失败：$model" }
}
foreach ($noise in 0,.05) {
    & $PY evaluate_delay.py --method bc_shift --model repro_20261011_full --split sealed_test --episodes 30 --steps 400 --delay 2 --shift-index 2 --noise $noise
    if ($LASTEXITCODE -ne 0) { throw 'k=2 补充评估失败。' }
}
```

| 方法 | 干净条件历史成功数 | 位置动作噪声 0.05 历史成功数 |
|---|---:|---:|
| 普通 BC | 17/30 | 19/30 |
| 固定偏移 k=1 | 21/30 | 19/30 |
| 完整 WM，回退 k=1 | 23/30 | 23/30 |
| 去排序的 Plain future | 本表不要求 | 23/30 |
| Direct scorer | 本表不要求 | 22/30 |
| 固定偏移 k=2，补充诊断 | 22/30 | 24/30 |

噪声加在实际执行动作的前三个归一化位置控制分量上，不能把 `0.05` 直接写成 5 cm 的物理位移。

验收需要逐 demo 对齐成功标志、步数和运行参数，同时确认每份结果是 30 条、无重复且起点集合一致。先要求成功数和逐回合行为可解释；Python、PyTorch 及硬件发生变化，不能预先保证逐位一致。偏差时依次核对仿真版本、数据与权重哈希、`--score-only`、回退索引、噪声、400 步预算和恢复流程。不要为了得到历史数字而调整算法。

### 5 汇总与图表

原 `make_figures.py` 的第一张成功率图和消融图使用写死的数组；其余部分仍指向历史目录。它也没有重新生成 `RESULTS_TABLE.csv`。直接运行只会重画历史材料，不能验收新结果。

新实验汇总阶段应单独增加读取新目录 JSON 的汇总入口：按 demo 对齐，计算成功数、比例、配对结果、Wilson 区间与 McNemar 精确检验，再导出新 CSV 和图。训练曲线横轴应使用日志中的 `step`，原脚本的 1 至 12 个日志点被标为 epoch，含义不准确。这些修改不在本次仅迁移环境的范围内。

本轮根据原始记录重新计算：WM 对 k=1 的配对结果按“两者成功、WM 独胜、基线独胜、两者失败”依次为干净 `[20,3,1,6]`、噪声 `[19,4,0,7]`；双侧 McNemar 精确 p 值分别为 `0.625` 和 `0.125`。现有样本不支持常用 0.05 阈值下的显著优越结论。Plain 与 Full 同为 23/30，也不足以单凭成功率证明排序损失贡献。

## 四 按原实现从头训练的路线

这一路线用于核对原训练流水线，应与第五节的修正实验分开存放。已有 NPZ 可直接用于训练，不必首先重新采集。原 `PROGRAM_GUIDE.md` 开发分支采集命令写了 30 条，但实际主线训练使用的是 **8 条开发父轨迹**；30 是闭环开发评估回合数。

### 1 重新训练 BC

```powershell
& $PY train_policy.py --name repro_20261011_bc --architecture mlp --seed 17 --horizon 8 --width 512 --updates 15000 --batch 256 --lr .0003
```

输出为 `policy/repro_20261011_bc/`。使用 `policy_15000.pt`，不要误用 `policy.pt`。网络归一化只使用训练轨迹。新版本 PyTorch 训练不保证与旧权重完全相同；在新 BC 上生成的分支必须作为新的数据版本保存。

### 2 优先使用原分支数据训练三个模型

```powershell
& $PY train_world.py --method full --dataset delay2_shift_v0 --run repro_20261011_train_full --seed 17 --width 128 --updates 3000 --batch 16 --lr .0003 --future-only --rank-weight .2 --risk-weight .5
& $PY train_world.py --method plain --dataset delay2_shift_v0 --run repro_20261011_train_plain --seed 17 --width 128 --updates 3000 --batch 16 --lr .0003 --future-only --rank-weight .2 --risk-weight .5
& $PY train_world.py --method direct --dataset delay2_shift_v0 --run repro_20261011_train_direct --seed 17 --width 128 --updates 3000 --batch 16 --lr .0003 --rank-weight .2 --risk-weight .5
```

每条命令成功后再运行下一条。Plain 在代码内将排序权重置零；它仍有进度与风险监督。Direct 保留监督和排序损失，但不生成未来状态。世界模型按开发集 `mean_regret` 选择检查点，所以最终 `model.pt` 可能早于第 3,000 步。不要拿最后一条训练日志当作保存权重的指标。

然后使用第三节评估参数，将 `--model` 改成对应的训练输出目录。此步骤若仍用原分支数据，评估必须继续使用原 `bc_chunk_dev_v4/policy_15000.pt`，因为分支由它产生；不要不加说明地换成刚重训的 BC。

### 3 如需重跑原分支采集

以下命令复现原采集配置，本身不会解决第五节的问题。建议先用 `--demos 1 --points 2`、另取名称进行诊断，再执行正式采集。

```powershell
& $PY collect_delay_branches.py --split train --demos 20 --points 8 --horizon 8 --candidates 4 --delay 2 --seed 2718 --name repro_20261011_original --policy bc_chunk_dev_v4 --policy-checkpoint policy_15000.pt --candidate-mode shift
& $PY collect_delay_branches.py --split dev --demos 8 --points 8 --horizon 8 --candidates 4 --delay 2 --seed 2718 --name repro_20261011_original --policy bc_chunk_dev_v4 --policy-checkpoint policy_15000.pt --candidate-mode shift
```

应得到训练 `x=[160,23]`、`a=[160,4,8,7]`、`y=[160,4,8,23]`、`labels=[160,4,8,2]`；开发组数 64，其他维度相同。检查 parent 属于相应划分，并保存数据哈希。随后训练命令将 `--dataset` 改为 `repro_20261011_original`。

如需完整重训 BC 后再采集，两个采集命令都将 `--policy` 改为 `repro_20261011_bc`，另取数据名；后续训练和评估也必须使用这一组匹配的数据、模型和 BC。单独记录这条流水线与冻结权重复跑的差异。

## 五 重新采集训练前需要验证的问题

### 1 世界模型动作接口不一致

`collect_delay_branches.py` 第 23 至 28 行使用 FIFO 执行动作并记录状态，但保存到 NPZ 的 `a` 是入队前的候选命令。`train_world.py` 直接把该 `a` 送入模型。因此历史模型的训练目标已经包含采集阶段的延迟。

`evaluate_delay.py` 第 61 至 67 行则先拼接真实 FIFO 队列，再把序列送入同一模型。训练和评估对于动作输入的含义不同：前者是待提交命令，后者意图表示实际将执行的动作。这个接口不一致由静态代码即可确认；不能在未做对照仿真前声称它一定等效于某个固定的额外延迟。

建议新版本将世界模型输入统一为“每一步真正执行的动作”。采集时同时保存 submitted、executed、初始队列和结果状态；训练读取 executed；评估只拼接一次已知队列和候选后续命令。也可以设计显式接收队列的命令模型，但必须重新定义、训练和验证其接口，不能只在评估器中改一行后继续解释旧权重。

验收：固定初始状态和动作序列，逐步对照队列中的命令、物理引擎实际动作与模型输入；D=0 和 D=2 分别检查。无非零候选命令实际执行前，各候选的真值未来前缀应相同。

### 2 保存的分支存在共同前缀差异

采集代码对每个候选都初始化两个零动作，因此同一起点各候选的前两步实际动作应相同。但现有 NPZ 中，训练 160/160 组、开发 64/64 组的末端位置前两步最大坐标差均超过 `1e-4 m`。训练组中位差约 5.31 mm、最大 14.45 mm；开发约 5.05 mm、最大 12.00 mm。

这里使用的是末端位置前三维，避开了四元数正负号对等价旋转的干扰。差异本身已在文件中确认；是否由控制器缓存、reset 后的内部状态、对象配置、随机数或其他采集行为引起，需要运行仿真定位。

原 `smoke_env.py` 重复测试使用重新加载 XML 的路径；采集内层使用 `restore_demo(..., xml=False)`，因此历史 smoke 通过不能覆盖这个问题。

修正实验先取同一 demo 的同一中间状态，按采集的真实恢复路径重复执行完全相同序列，检查初始观测、控制器状态、实际动作、前缀状态和进度标签。再随机打乱候选顺序，要求每个候选结果在容差内不受顺序影响。通过后才重新生成分支和重训，旧分支与旧结果保留为历史版本。

### 3 完整研究验证

在新数据和接口通过检查后，对 Full、Plain、Direct 使用相同数据、BC、候选、更新预算和闭环参数，运行 17、23、41 三个训练种子。先将“固定 BC，仅更换世界模型种子”的问题与“BC 也换种子”的问题分开。补充去门控、去风险评分，以及 D=0、D=2 和预先声明的噪声条件。

当前目录已有的其他种子及 100-demo 结果使用了不同回退配置，不能当作当前 k=1 主表的三种子重复。现有 sealed_test 已公开并被本轮读取，可用于历史复跑；如果据此修改算法，新方法的最终确认应另设未用于开发的仿真起点和扰动种子。

当前输入含物体真实状态，属于低维特权状态诊断。`--score-only` 控制决策使用学习分数，不等于系统已经不依赖物体真值观测；门控分数差也不是经过校准的置信度。视觉编码器、实机部署和具有校准意义的不确定性估计均属于后续新增工作。

## 六 执行顺序和交付验收

| 阶段 | 完成条件 | 输出 |
|---|---|---|
| 环境 | pip check、CUDA 运算和环境 smoke 通过 | 当前版本锁、兼容与回放检查 JSON |
| 权重运行 | 2 个开发回合完整结束 | 独立 smoke 结果 |
| 历史复跑 | 开发扫描和主表、消融均有完整逐回合记录 | 新目录的评估 JSON、与历史的逐 demo 差异 |
| 原训练复跑 | 原数据上的 BC 或 WM 训练可完成，检查点选择可追溯 | 新权重、config、log、闭环结果 |
| 修正实验 | 动作接口、重复恢复、共同前缀和候选顺序测试通过 | 版本化新数据与新模型 |
| 正式评价 | 匹配的三种子对比、预声明条件和新确认集 | 自动生成的 CSV、统计量和图 |

旧机器日志显示主线采集约 49 秒加 20 秒，BC 与 Full 训练各约 37 秒，一组 30 回合评估约 42 至 63 秒。这些仅是历史运行记录，不是当前机器耗时承诺；首次安装、编译和问题定位通常才是主要用时。用本机两回合运行和一次小训练测量后再估算总时长。

你现在的下一步是第二节的依赖安装。环境通过后，先执行第三节的两回合检查，再进入 30 回合评估；不要一开始就重采集全部数据或更改模型。
