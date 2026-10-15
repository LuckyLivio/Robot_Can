# 相关工作核查与项目定位

更新：2026-10-12。本页是选定文献的元信息、摘要及相关方法段核查和项目对照，不是论文正文、系统综述或“首次提出”证明。书目信息由官方页面的 citation 元数据获取，见 [原始元数据](reproduction/consolidation_20261012_01/references_metadata.json) 和 [BibTeX](reproduction/consolidation_20261012_01/references_verified.bib)。arXiv 年份采用首次提交年，不猜测会议发表年；正式参考文献格式需按学校要求调整。

## 选定相关工作与区别

| 文献与官方来源 | 已核查的相关内容 | 与当前项目的关系和区别 |
|---|---|---|
| Mandlekar 等，2021，[What Matters in Learning from Offline Human Demonstrations for Robot Manipulation](https://arxiv.org/abs/2108.03298) | 元信息、摘要，正文 §3–4 的数据集与对照表：离线人类示范、不同质量数据和学习方法的评价 | 本项目使用 robomimic Can PH 公共数据；仿真场景、数据和示范学习不是本项目原创。当前增加固定动作延迟和辅助候选选择，不能跨论文直接比较成功率 |
| Hafner 等，2018 首次提交，[Learning Latent Dynamics for Planning from Pixels](https://arxiv.org/abs/1811.04551) | 元信息、摘要，正文 §2–3：像素输入的潜变量动力学及在线规划，具有确定性和随机性成分 | 本项目预测23维物理观测，用有限BC候选评分；没有像素编码、随机潜变量或 PlaNet 的在线数据采集训练循环，不是 PlaNet 算法复现 |
| Farahmand、Barreto、Nikovski，2017，[Value-Aware Loss Function for Model-based Reinforcement Learning](https://proceedings.mlr.press/v54/farahmand17a.html) | 正式出版页与正文PDF第3页（页码1488）式(3)：动力学误差通过价值函数影响决策的损失定义 | 为“预测误差与控制效果不等价”提供理论背景；本项目的组内候选排序损失不是该式，不继承其理论界，也没有实现价值迭代 |
| Zhou 等，2024 首次提交，[DINO-WM](https://arxiv.org/abs/2411.04983) | 元信息、摘要，正文 §3.1.1：冻结DINOv2图像patch特征，预测特征并优化动作序列实现视觉目标 | 当前无DINO编码器或视觉目标优化，含物体真值的低维状态不能写成视觉零样本规划；本项目不复现其跨任务结论 |
| Zhao 等，2023，[Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware](https://arxiv.org/abs/2304.13705) | 元信息、摘要，正文图3与动作分块/时间集成段：ACT用Transformer与条件VAE预测动作序列 | 本项目BC是混合密度动作块网络，固定k=2为第3个预测动作；没有ACT的Transformer、CVAE或时间集成，不将动作块BC称作ACT复现 |
| Chua 等，2018，[Deep Reinforcement Learning in a Handful of Trials using Probabilistic Dynamics Models](https://arxiv.org/abs/1805.12114) | 官方元信息与摘要：PETS组合概率动力学集成和轨迹采样，处理模型不确定性 | 本项目是单个确定性残差预测器与有限候选选择，未实现概率模型集成或校准不确定性；评分差门限不能被称为PETS式不确定性估计 |
| Thananjeyan 等，2020 首次提交，[Recovery RL](https://arxiv.org/abs/2010.15920) | 元信息、摘要，正文 §IV-A/B：安全评论器定义恢复区域，学习的恢复策略接管任务策略 | 本项目恢复层是观测历史驱动的规则状态机，处理抓持、停滞、几何和时间预算；没有安全评论器或恢复策略RL训练，不声称安全约束保证 |
| Zhu 等，2020 首次提交，[robosuite](https://arxiv.org/abs/2009.12293) | 官方元信息、摘要及[项目页](https://robosuite.ai/)：MuJoCo机器人仿真框架、控制模块和任务环境 | Panda、OSC_POSE、PickPlaceCan与底层接触物理属于外部框架；本项目实现数据一致性检查、延迟执行、模型/规则控制和对照实验 |

## 可以陈述的项目贡献

1. 在固定延迟的机器人低维仿真任务中，构建从示范BC、真实FIFO分支采集、世界模型候选评分到共享恢复的可复查系统。
2. 修复仿真状态恢复时Python控制器缓存与传感器刷新、分支采集动作队列的一致性问题，并通过顺逆序回放与实际执行前缀核查。
3. 用强BC、配对三种子消融、真值短期候选排序及敏感性试验，揭示离线预测/评分改善与终局成功之间的差距。
4. 在原400步预算内实现时间安排和受几何约束的抓取恢复；报告新起点上的局部救回、退步和剩余失败。

以上是当前工程与实验贡献的定位，区别于已有工作的具体集成与受控分析。没有完成足以证明全球方法首创的文献检索，也没有证明世界模型稳定优于BC、视觉泛化或真机安全。

## 还需核查的文献问题

正式写作前，继续查找执行延迟补偿、抓取失败检测、状态机/行为树恢复与碰撞余量建模的直接相关研究，逐篇确认适用假设和本项目差异。当前8篇仅为可信的起点，不以“文献数量已足够”替代完整相关工作。

不要引用未经核实的书目、把arXiv提交年自动当会议年、用其他论文的成功率直接排名，或把网页摘要核查写成“全文均已审阅”。
