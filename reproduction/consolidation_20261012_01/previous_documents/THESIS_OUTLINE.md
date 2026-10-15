# 本科论文提纲：考虑动作延迟的机器人世界模型控制方法实现与实验分析

版本：2026-10-12 冻结确认后的文档整理版。历史文档完整保存在 [previous_documents](reproduction/release_20261012_01/previous_documents/)。

这是依据当前代码与已完成实验的可写提纲，不是全文或学校格式认证。用户未提供正式任务书/评分标准；`criteria_binding_unavailable`。建议中文正文约10000字，仅为写作分配参考，最终以学校/导师要求为准。采用“问题—方法—工程复核—开发消融—独立确认—局限”的实证结构。

## 研究问题与贡献口径

- RQ1：在23维状态输入、D=2与固定BC下，预测后果选择候选是否改善BC k=2？用冻结新起点确认回答。
- RQ2：排序监督、风险惩罚和门限是否分别改善控制？用匹配三种子开发消融及Full/Plain确认回答，承认不确定性。
- RQ3：状态恢复一致性、预测/评分误差与长期闭环效果如何关联？用恢复验证、同状态真值诊断与校准对照回答，避免把相关观察写成因果证明。

贡献定位为可复核的机器人延迟控制实现、实验一致性修复和受控分析。世界模型、候选排序与风险评分均有既有研究，不宣称首次发明；不把低维特权状态实验写成纯视觉或真机方法。

## 第一章 绪论（约1000字）

1.1 机器人指令延迟和执行扰动的实际问题；本实验仅模拟固定延迟与指定噪声，不冒充真实网络/硬件测量。1.2 世界模型预测后果与行为克隆的联系。1.3 明确RQ1—RQ3、实现范围与贡献。1.4 章节安排。

证据：环境/控制器代码和[当前方法协议](DELAY_PROTOCOL.md)。本章引出强固定偏移基线的重要性，进入相关工作。

## 第二章 相关工作与基础（约1500字）

2.1 从离线人类示范学习机器人行为；数据质量和评估方式。2.2 学习动力学与模型预测控制：像素潜变量规划和本文23维状态递归预测的区别。2.3 决策相关模型学习与排序目标：把预测误差转化为控制改善不是自动成立的。2.4 视觉世界模型背景及本文未完成的视觉扩展。2.5 对比表列输入信息、预测对象、规划方式、训练目标与评估范围，不引用未经核实的跨论文成功率比较。

文献入口见末尾已核对的四个官方摘要/出版页；它们用于结构定位，详细技术论断仍须读原文及定位页码，不声称已经完成系统综述。承接到本文任务定义。

## 第三章 任务、系统实现与复现一致性（约1800字）

3.1 PickPlaceCan、Panda、OSC_POSE、20Hz与23维特权状态；图3-1采用实际仿真截图，注明图像只用于展示。3.2 Can PH的200条父轨迹及140/30/30划分；分支继承父轨迹，历史sealed已使用。3.3 长度2的FIFO初始化、入队出队时序、噪声施加位置与400步成功定义。3.4 恢复仿真、控制器缓存和相对观测的同步；说明为何仅恢复MuJoCo平面状态不足以重建中途分支。3.5 完整历史回放采集真实队列分支，给出一致性验证与代码模块图。

证据：`common.py`、`collect_rollout_branches.py`、[确认状态验证](reproduction/confirmation_20261012_01/state_validation.json)、[确认轨迹验收](reproduction/confirmation_20261012_01/analysis/result_validation.json)。只报告验证实际覆盖的范围，不把全部潜在恢复情形写成已证明。

## 第四章 候选预测评分与门限控制（约1800字）

4.1 BC混合密度动作块，H=8、7维动作；解释k=2是预测动作块偏移，不是读取真实未来。4.2 四个候选k=0..3，预测序列由当前FIFO前缀与重复候选构成；每步只提交一个命令，下一观测重规划。4.3 GRU归一化状态残差递推：h′=GRU([z,a],h)，z′=z+0.1·delta(h′)；未来状态评分头只读z′。4.4 Full损失及Plain去排序；排序阈值0.025/温度0.1，进度为软标签，风险为初始抓持条件下的抓持丢失。4.5 J=p末步+0.5均值p−0.5最大r，若最佳非k=2且J差<0.02则回退；不能将评分差称为校准置信度。4.6 预测时域内重复候选与实际滚动控制的差异。

证据：`world_model.py`、`collect_branches.py`、`evaluate_delay.py`及[三种子登记](reproduction/multiseed_20261012_01/protocol.json)。输入物体真值的权限必须明确；真实候选未来后果只用于训练/诊断。

## 第五章 实验设计与结果（约2500字）

5.1 实验环境、数据规模和预算。Full/Plain各87321参数，Direct匹配到87364；17/23/41，3000次基础更新，开发选点；评分头实验额外预算单列。5.2 开发集基线与公平消融，使用[RESULTS开发表](RESULTS.md)，解释校准离线改善未稳定转化为闭环成功。5.3 60个新起点的事前生成/锁定、相同噪声与全部种子确认；列design、lock及代码/权重哈希。5.4 主结果和成对区间，开发与确认分表不合并。5.5 同起点演示：明确事后说明性分类选择、固定种子17、统一时间轴、成功后停帧，并展示共同失败。5.6 验证与统计限制。

主表每个成功数分母60，三数顺序17/23/41：

| 方法 | 干净：成功数；平均成功率 | 噪声0.05：成功数；平均成功率 |
| --- | --- | --- |
| BC k=2 | 51；85.00% | 49；81.67% |
| Full | 54、54、54；90.00% | 52、52、51；86.11% |
| Plain（去排序） | 53、53、53；88.33% | 50、51、50；83.89% |

必须同时写出：Full−BC干净+5.00个百分点，95%描述性区间[0.00,11.67]；加噪+4.44，[0.00,10.00]。等权综合+4.72，[0.56,10.28]；Full−Plain干净+1.67，[0.00,5.00]，加噪+2.22，[-1.11,6.67]。支持正向趋势，未满足预先设定的跨条件、对BC与Plain均为正区间的较强优势标准。

说明840条记录共用60起点，BC未独立训练三个种子，bootstrap采用配对训练种子/起点交叉重采样。只有3训练种子、少量独胜起点；区间不是多重比较校正或等效性证明。决策耗时不是完整控制环延迟基准。

## 第六章 讨论与局限（约1000字）

6.1 新确认的正向趋势与开发集波动，明确权重未改变。6.2 排序标签区分度与短时评分/长时任务后果之间的距离，列证据和未验证假说。6.3 门限的作用与局限，不能承诺安全。6.4 固定数据、单任务、低维真值、单种加噪实现和小样本统计限制。6.5 若继续研究，应另设开发目标与新确认；视觉/真实机器人是未来工作。

证据：[总体评估](reproduction/confirmation_20261012_01/analysis/overall_assessment.txt)、[开发分析](reproduction/multiseed_20261012_01/analysis/overall_assessment.txt)、[同状态诊断目录](reproduction/candidate_truth_20261012_01/)。不能用精选演示证明普遍优势。

## 第七章 总结（约400字）

按RQ1—RQ3回顾已实现、已观察和仍不确定的内容。结论应与第五章数值一致；不把提纲、运行验证或视频包装成完成了视觉/真机研究。列出可复现资产与后续论文交付任务。

## 图表与证据映射

| 图表 | 章节/RQ | 证据或已有图 |
| --- | --- | --- |
| 图3-1 同状态机器人画面 | 第三章/RQ3 | [演示页面](reproduction/release_20261012_01/demo/index.html)，截图和视频均来源实际仿真 |
| 图4-1 FIFO、候选与预测评分流程 | 第四章/RQ1 | common/world_model/evaluate_delay实际调用关系；旧k=1流程图不复用 |
| 表5-1 环境、参数和训练预算 | 第五章/RQ1—3 | [环境](reproduction/confirmation_20261012_01/environment.json)、[模型元数据](reproduction/multiseed_20261012_01/analysis/model_metadata.csv) |
| 表5-2/图5-1 三种子开发消融 | 第五章/RQ2 | [开发原表](reproduction/multiseed_20261012_01/analysis/summary.csv)、[开发图](reproduction/multiseed_20261012_01/analysis/multiseed_success.png) |
| 表5-3/图5-2 独立确认主结果 | 第五章/RQ1 | [确认原表](reproduction/confirmation_20261012_01/analysis/summary.csv)、[确认图](reproduction/confirmation_20261012_01/analysis/confirmation_success.png) |
| 图5-3 配对效果区间 | 第五章/RQ1—2 | [配对原表](reproduction/confirmation_20261012_01/analysis/paired_comparisons.csv)、[区间图](reproduction/confirmation_20261012_01/analysis/paired_effects.png) |
| 图5-4 逐时域位置预测误差 | 第五章/RQ3 | [物理预测图](reproduction/multiseed_20261012_01/offline/physical_prediction.png) |
| 表5-4 演示案例规则及胜负 | 第五章/RQ1—3 | [事后案例选择登记](reproduction/release_20261012_01/demo_design.json)、DEMO_GUIDE |

## 已核对的文献入口（2026-10-12）

1. Ajay Mandlekar等，*What Matters in Learning from Offline Human Demonstrations for Robot Manipulation*，CoRL 2021。已核对标题、作者列表、会议说明和摘要；用于示范学习/评估背景。[原始摘要页](https://arxiv.org/abs/2108.03298)
2. Danijar Hafner等，*Learning Latent Dynamics for Planning from Pixels*，arXiv:1811.04551，2018提交、2019修订。用于学习动力学与在线规划的背景，不能据此称本项目为像素输入实现。[原始摘要页](https://arxiv.org/abs/1811.04551)
3. Amir-Massoud Farahmand、Andre Barreto、Daniel Nikovski，*Value-Aware Loss Function for Model-based Reinforcement Learning*，AISTATS/PMLR54，1486–1494，2017。用于决策相关模型损失的背景；本文排序损失不是VAML原算法复现。[正式出版页](https://proceedings.mlr.press/v54/farahmand17a.html)
4. Gaoyue Zhou、Hengkai Pan、Yann LeCun、Lerrel Pinto，*DINO-WM: World Models on Pre-trained Visual Features enable Zero-shot Planning*，arXiv:2411.04983，2024提交、2025修订。用于视觉特征预测/规划背景；本项目没有实现DINO视觉编码器。[原始摘要页](https://arxiv.org/abs/2411.04983)

核验范围为上述页面的元信息与摘要；未在本轮逐页审核全文，也不声称用户已阅读。正式论文需继续核验具体技术论断、页码和学校参考文献格式。删除旧提纲中不存在的本地papers路径；原阅读清单仍在历史归档，不作已读/已核实证据。
