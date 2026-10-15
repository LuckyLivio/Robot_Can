# 本科毕业论文提纲与参考资料

## 建议题目

主标题建议用：**面向动作延迟的风险门控世界模型控制**。

副标题可写：**基于 PickPlaceCan 机器人抓取任务的研究**。

这个标题比“面向稀疏交互事件的轻量视觉世界模型与模型预测控制”短，直接点出要解决的工程问题、核心算法和验证场景。若最终补上图像编码器，可将主标题改为“面向动作延迟的轻量视觉世界模型控制”；若没有视觉实验，不要在题目中提前承诺“视觉”。

## 摘要应回答的四件事

1. 工业机器人控制链存在通信、控制器和执行器延迟，固定提前动作依赖一个手工调好的延迟值，在执行噪声和状态变化下缺少风险判断。
2. 本文把问题形式化为 FIFO 动作延迟下的候选动作选择，训练 action-conditioned GRU 世界模型递归预测未来状态，并用进度/失败风险评分加门控回退。
3. 在 Can PH 的 PickPlaceCan 仿真上，开发集先冻结最强固定偏移 `k=1`，封存测试中 WM 在干净条件为 23/30，对比 21/30；位置噪声 σ=0.05 时为 23/30，对比 19/30。
4. 结论应限定为：世界模型在执行不确定性下提供了状态依赖的候选筛选收益；低维仿真结果是机制验证，不等同于真实机器人或完整视觉系统结论。

## 第一章 绪论

### 1.1 研究背景

介绍机器人策略部署中的观测、推理、通信和执行延迟；说明行为克隆只学习“当前观测到动作”，通常没有显式未来状态预测；说明工业抓取中失败代价高于一次动作选择的计算开销。

### 1.2 问题定义

给出状态 `s_t`、候选动作块 `a_{t:t+H}`、FIFO 队列 `q_t` 和延迟 `D`。目标是在每个决策时刻从候选集合中选择一条命令，最大化任务完成率并降低失败风险。

### 1.3 研究内容和贡献

建议写成三点，避免夸大：

- 构造一个可复现的延迟抓取闭环基准，明确区分开发集模型选择和封存测试。
- 提出“递归未来状态预测 + 进度/风险评分 + 固定先验门控”的轻量世界模型控制器。
- 通过固定偏移扫描、结构消融、噪声鲁棒性和成对回合比较，验证世界模型收益集中在执行不确定性场景。

### 1.4 论文结构

逐章说明第二章基础，第三章问题与数据，第四章方法，第五章实验，第六章讨论，第七章结论。

## 第二章 相关理论与工作

### 2.1 行为克隆和动作块策略

说明 BC 的监督目标和分布偏移；解释动作 chunk 可以降低抖动，但固定时间偏移仍然是静态规则。

### 2.2 世界模型

介绍状态转移模型 `\hat{s}_{t+1}=f_θ(s_t,a_t)`、递归 rollout 和模型预测控制。区分 latent world model 与本研究使用的低维状态动力学诊断模型。

### 2.3 模型预测控制与风险门控

说明 MPC 通过候选动作的预测结果选动作；本文使用短 horizon 和少量候选，重点是延迟补偿而不是通用规划器。定义安全先验和门控阈值。

### 2.4 机器人延迟和执行噪声

将动作命令延迟、执行噪声与闭环性能联系起来，解释为什么固定 `k=D` 在某些设置中很强但不一定对所有状态都合适。

### 2.5 小结

指出已有工作通常关注通用控制、像素预测或 latent planning；本文聚焦本科可复现的“延迟候选筛选”小问题。

## 第三章 任务、数据和评测协议

### 3.1 PickPlaceCan 场景

说明 robosuite 1.5.1、MuJoCo 3.3.0、OSC_POSE 相对控制、20 Hz、Can PH 数据。展示机器人、罐子和目标盒的示意图，图可由环境渲染截图补充。

### 3.2 数据划分

Can PH 共 200 条父轨迹；固定为 140 train、30 dev、30 sealed_test。所有分支从父轨迹继承划分，禁止按帧随机拆分。列出数据文件、SHA256 和环境配置。

### 3.3 延迟执行接口

给出 FIFO 伪代码：新动作入队，队首动作执行；执行后再观测。明确 `D=2`、候选 `k=0..3`、预测 horizon=8、动作位置噪声 σ=0/0.05/0.10。

### 3.4 指标

主指标为成功率；次指标为 stage reward、ever grasped、成功回合步数、固定先验选择比例和平均决策时间。增加 Wilson 区间或 bootstrap 作为统计补充，但不要把 30 个回合写成大规模统计证明。

## 第四章 风险门控世界模型方法

### 4.1 候选动作构造

BC 输出基础动作块 `b_t`，对前四个时间索引构造四个重复动作候选。延迟队列前缀与候选首动作拼接，保持训练和部署接口一致。

### 4.2 Action-conditioned GRU 世界模型

给出：

`h_{t+1}=GRUCell([s_t,a_t],h_t)`，

`\hat{s}_{t+1}=g_s(h_{t+1})`，

`[\hat{p}_{t+1},\hat{r}_{t+1}]=g_y(\hat{s}_{t+1})`。

强调 `future_only=True` 时进度和风险头只能读取递归预测状态，避免把当前观测直接旁路到 readout。

### 4.3 训练目标

写出状态归一化 MSE、进度 BCE、风险 BCE 和同一初始状态内的 pairwise ranking loss：正确候选分数应高于失败候选。说明 `rank_weight=0.2`、风险权重 0.5 是代码中的冻结配置。

### 4.4 评分和门控

可写成：

`J_i = last_progress_i + 0.5 mean_progress_i - 0.5 max_risk_i`。

固定偏移 `k=1` 为安全先验。只有 `J_best - J_prior >= 0.02` 才覆盖先验，否则继续执行先验。该设计将世界模型的收益限制在有足够置信度的状态，减少模型误判造成的回退风险。

### 4.5 复杂度

报告 GRU 宽度、参数量、horizon=8、候选数 4 和平均决策时间；与一次环境步相比说明计算开销仍适合仿真和后续小型实验。

## 第五章 实验与结果

### 5.1 实验设置

列出 GPU、Python、PyTorch、robosuite、训练步数、随机种子、数据文件和所有冻结参数。说明阈值和固定偏移只在 dev 选择。

### 5.2 基线

至少报告：

- 普通 BC（`k=0`）；
- 固定偏移 `k=0,1,2,3`，其中 `k=1` 是开发集选出的强基线，`k=2` 是传统的延迟长度诊断；
- 不门控 WM；
- Plain future（去排序损失）；
- Direct scorer（无递归未来状态）；
- 完整 WM + 风险门控。

### 5.3 主要结果

放 `figures/figure_success_rate.pdf` 和对应表格。核心句子是：完整方法在干净封存测试 23/30 对 21/30，在 σ=0.05 为 23/30 对 19/30；提升分别为 2 和 4 个回合。

### 5.4 消融结果

放 `figure_ablation.pdf`。解释：direct 在噪声封存测试 22/30，plain 23/30，完整模型 23/30。开发集完整模型为 25/30，高于 plain 20/30、direct 21/30；封存集没有完全复现差距，因此排序损失只能作为机制证据，不能写成稳定显著增益。

### 5.5 成对和鲁棒性分析

放 `figure_paired_clean.pdf`、`figure_paired_noise005.pdf` 和 `figure_success_steps.pdf`。报告 WM 独胜/固定偏移独胜回合数（干净为 3/1，σ=0.05 为 4/0）以及成功步数分布。σ=0.10 作为压力测试，当前固定偏移和主模型均约 24/30，说明收益存在适用范围。

### 5.6 训练诊断

放 `figure_training_curves.pdf`；讨论状态预测、排序和开发集指标是否收敛。不要只展示 loss，要把闭环成功率作为最终依据。

### 5.7 统计和可复现性

对 30 个共同起点报告成对差异；可以用 bootstrap 重采样起点给出差异区间。补充 100-demo 三种子结果，但清楚标注它们使用了 `k=2` 回退配置，不能替代主表。

## 第六章 讨论、局限和改进

### 6.1 为什么世界模型有用

固定偏移只编码一个时间规则；世界模型把当前状态、队列和候选动作映射到未来进度/风险，因此在噪声导致同一偏移不再稳定时可以拒绝高风险候选。门控保证预测不确定时回到简单先验。

### 6.2 为什么提升不大

PickPlaceCan 的状态空间、固定起点和短延迟使固定偏移已经很强；候选集合窄，世界模型只负责局部筛选；30 个封存起点有限。这个解释比宣称普遍优越更可信。

### 6.3 局限

当前实验使用低维特权状态和仿真，未验证相机遮挡、真实通信抖动、不同物体和实体机器人；世界模型预测误差和数据分布外状态仍可能造成错误门控。

### 6.4 后续工作

最小可行视觉扩展是用 ResNet/小型 CNN 编码 frontview 图像，冻结或轻量微调编码器，再保持相同 GRU、候选、门控和评测协议；先做 8/30 起点 smoke test，再决定是否扩大。

## 第七章 结论

总结问题、方法、数据和两条主结果；明确本文证明的是“风险门控世界模型在延迟和执行噪声下具有状态依赖的候选选择收益”，而不是所有机器人控制场景都优于固定规则。

## 论文图表清单

- 图 3-1：PickPlaceCan 场景和 FIFO 延迟示意。
- 图 4-1：`figure_method_diagram`，BC chunk → 候选偏移 → GRU rollout → 风险评分 → 门控回退流程。
- 图 5-1：`figure_success_rate`，开发集偏移扫描与封存对比。
- 图 5-2：`figure_ablation`，结构消融。
- 图 5-3：`figure_paired_clean` 与 `figure_paired_noise005`，成对回合。
- 图 5-4：`figure_success_steps`，成功步数分布。
- 图 5-5：`figure_training_curves`，训练诊断。
- 表 3-1：环境、数据和划分。
- 表 4-1：模型层、维度、损失权重和门控参数。
- 表 5-1：主结果；表 5-2：消融；表 5-3：噪声和种子敏感性。

## 参考资料和阅读顺序

### 第一组：先读，直接决定本文写法

1. Hafner et al., **Learning Latent Dynamics for Planning from Pixels (PlaNet)**, ICML 2019。理解“学习动力学模型并用短 rollout 规划”；本地文件：`papers/original/2018_Hafner_PlaNet.pdf`；论文页：[arXiv:1811.04551](https://arxiv.org/abs/1811.04551)。
2. Ha & Schmidhuber, **World Models**, NeurIPS 2018 workshop。理解世界模型、记忆状态和控制器的基本分工；本地文件：`papers/original/2018_Ha_WorldModels.pdf`。
3. Hafner et al., **Dreamer** / **DreamerV3**。理解 latent imagination 和 actor-critic 世界模型路线；本地文件：`papers/original/2019_Hafner_Dreamer.pdf`、`papers/original/2023_Hafner_DreamerV3.pdf`。
4. robomimic 数据集文档。核对 demonstration、PH/Can、低维 observation 和轨迹切分；本地 `papers/` 之外直接看官方文档：[robomimic datasets overview](https://robomimic.github.io/docs/datasets/overview.html)。

### 第二组：理解控制和近邻方法

5. Hansen et al., **TD-MPC** 和 **TD-MPC2**。理解 latent dynamics + short-horizon model predictive control；本地文件：`papers/original/2023_Hansen_TDMPC.pdf`、`papers/original/2023_Hansen_TDMPC2.pdf`。
6. Hansen et al., **Temporal Difference Learning for Model Predictive Control** 的代码和补充实验。重点看 rollout horizon、uncertainty 和 action selection，不必复现完整算法。
7. Robine et al., **TWM: World Models for Generalization in Control**。理解世界模型泛化和任务变化；本地文件：`papers/original/2023_Robine_TWM.pdf`。
8. Micheli et al., **IRIS**。理解 tokenized image world model 的另一条路线；本地文件：`papers/original/2022_Micheli_IRIS.pdf`。

### 第三组：视觉世界模型的背景和后续扩展

9. Bruce et al., **Genie: Generative Interactive Environments**；本地文件：`papers/original/2024_Bruce_Genie.pdf`。
10. Bardes et al., **V-JEPA** 与 Assran et al., **V-JEPA 2**；本地文件：`papers/original/2024_Bardes_VJEPA.pdf`、`papers/original/2025_Assran_VJEPA2.pdf`。重点理解 latent feature prediction 与动作/视频预测的区别。
11. Zhou et al., **DINO-WM: World Models on Pre-trained Visual Features**。与本文最接近的阅读角度是“冻结视觉表征 + 学习局部动力学 + MPC”；官方页面：[dino-wm.github.io](https://dino-wm.github.io/)，论文：[arXiv:2411.04983](https://arxiv.org/abs/2411.04983)。
12. Hafner et al., **Dreamer4**，本地文件：`papers/original/2025_Hafner_Dreamer4.pdf`。作为最新路线背景阅读，不作为本科复现目标。

阅读顺序建议是 1→4→5→7→11；每篇只摘取“问题、状态/latent、训练目标、规划方式、评测环境、与本文差异”六项，形成两页文献卡片即可。
