# 论文图表目录与图注

36张图，600 dpi PNG / 矢量PDF / 路径字体SVG / 数据CSV。旧图保留，F编号沿用旧图包主题，不是最终论文编号。每张宽180.3 mm，标签9 pt、刻度与图例8 pt；正文不需要全部插入。

[解释异常曲线](CURVE_EXPLANATIONS.md) · [提纲映射](THESIS_OUTLINE_REVIEWED.md) · [来源哈希](PLOT_SOURCES.json)

旧F02拆成F02a–c；F12、F15、F18拆分；旧F19与F09同数据，合并F09。A01原始批次、A02开发恢复、A03–A05 v6、A06 v10、A07–A09 v11。共19个旧主题全部对应，未用新图伪造新实验。

## F01｜延迟一致的世界模型候选选择

用途：正文；[PNG](figures/F01.png) · [PDF](figures/F01.pdf) · [SVG](figures/F01.svg) · [CSV](figures/F01.csv)

图注：结构示意：世界模型确认配置，23维状态含物体真值，D=2，H=8，K=4。r监督失抓，不是通用失败概率。每次仅提交一个动作。

限制：此图不含后续规则恢复，也不证明性能。

数据来源：`common.py`；`evaluate_delay.py`；`reproduction/confirmation_20261012_01/design.json`；`world_model.py`。本图导出0条测量/统计值。

## F02a｜固定集总损失：训练与开发集

用途：正文；[PNG](figures/F02a.png) · [PDF](figures/F02a.pdf) · [SVG](figures/F02a.svg) · [CSV](figures/F02a.csv)

图注：36个既存权重的固定数据集评估；每种子12个采样点（250至3000，每250更新一次），未平滑。训练160组/20父轨迹，开发64组/8父轨迹。竖点线为原选择权重，未重新选点。固定集总损失；不是批次损失或闭环成功率。

限制：总损失、全状态MSE与平均欧氏位置误差不同；真实泛化差距保留。

数据来源：`figures/figure_data.json`；`reproduction/figures_deepcheck_20261014_01/checkpoint_metrics.csv`；`reproduction/figures_deepcheck_20261014_01/diagnostics.json`。本图导出72条测量/统计值。

## F02b｜归一化状态 MSE：训练与开发集

用途：正文；[PNG](figures/F02b.png) · [PDF](figures/F02b.pdf) · [SVG](figures/F02b.svg) · [CSV](figures/F02b.csv)

图注：36个既存权重的固定数据集评估；每种子12个采样点（250至3000，每250更新一次），未平滑。训练160组/20父轨迹，开发64组/8父轨迹。竖点线为原选择权重，未重新选点。归一化状态 MSE；不是批次损失或闭环成功率。

限制：总损失、全状态MSE与平均欧氏位置误差不同；真实泛化差距保留。

数据来源：`figures/figure_data.json`；`reproduction/figures_deepcheck_20261014_01/checkpoint_metrics.csv`；`reproduction/figures_deepcheck_20261014_01/diagnostics.json`。本图导出72条测量/统计值。

## F02c｜物体位置平均欧氏误差（mm）：训练与开发集

用途：正文；[PNG](figures/F02c.png) · [PDF](figures/F02c.pdf) · [SVG](figures/F02c.svg) · [CSV](figures/F02c.csv)

图注：36个既存权重的固定数据集评估；每种子12个采样点（250至3000，每250更新一次），未平滑。训练160组/20父轨迹，开发64组/8父轨迹。竖点线为原选择权重，未重新选点。物体位置平均欧氏误差（mm）；不是批次损失或闭环成功率。

限制：总损失、全状态MSE与平均欧氏位置误差不同；真实泛化差距保留。

数据来源：`figures/figure_data.json`；`reproduction/figures_deepcheck_20261014_01/checkpoint_metrics.csv`；`reproduction/figures_deepcheck_20261014_01/diagnostics.json`。本图导出72条测量/统计值。

## A01｜原始批次训练日志

用途：附录；[PNG](figures/A01.png) · [PDF](figures/A01.pdf) · [SVG](figures/A01.svg) · [CSV](figures/A01.csv)

图注：每250次更新采样当前随机批次，每种子12个点。虚线仅连接已记录点；不是每步连续轨迹或全训练集平均。

限制：稀疏、不同批次与多损失项会造成折线抖动；不插值、不平滑。

数据来源：`figures/figure_data.json`。本图导出108条测量/统计值。

## F03｜离散候选选择造成的 regret 跳变

用途：附录；[PNG](figures/F03.png) · [PDF](figures/F03.pdf) · [SVG](figures/F03.svg) · [CSV](figures/F03.csv)

图注：64组来自8父轨迹。regret为同组最优真实短期分数减所选候选的真实分数。s23在1500步，组5贡献约0.005103/整体0.005604≈91%。点线仅连接12个权重评估点。

限制：不是每步连续测量或闭环成功率；39个有效候选对不足以支持稳定泛化。

数据来源：`reproduction/figures_deepcheck_20261014_01/diagnostics.json`。本图导出60条测量/统计值。

## F04｜开发集公平消融

用途：正文；[PNG](figures/F04.png) · [PDF](figures/F04.pdf) · [SVG](figures/F04.svg) · [CSV](figures/F04.csv)

图注：每条件30个共同起点；BC固定权重，其余方法三个训练种子。点为均值，线为原分析20000次起点/种子交叉bootstrap的95%区间。成功率轴严格0–100%。

限制：开发集不可称独立确认；方法差异看配对差值区间，不能用种子SD替代抽样CI。

数据来源：`reproduction/multiseed_20261012_01/analysis/summary.csv`。本图导出14条测量/统计值。

## F05｜原世界模型独立确认

用途：正文；[PNG](figures/F05.png) · [PDF](figures/F05.pdf) · [SVG](figures/F05.svg) · [CSV](figures/F05.csv)

图注：每条件60个共同起点；BC固定权重，其余方法三个训练种子。点为均值，线为原分析20000次起点/种子交叉bootstrap的95%区间。成功率轴严格0–100%。

限制：原确认不含共享恢复；三个种子共享同批起点；方法差异看配对差值区间，不能用种子SD替代抽样CI。

数据来源：`reproduction/confirmation_20261012_01/analysis/summary.csv`。本图导出6条测量/统计值。

## F06｜相同起点的配对结果 · clean

用途：附录；[PNG](figures/F06.png) · [PDF](figures/F06.pdf) · [SVG](figures/F06.svg) · [CSV](figures/F06.csv)

图注：每行60个相同起点，三行共享起点与固定BC k=2。计数相同不表示权重或动作相同；三行不是180个独立起点。

限制：按上述批次与分母解释，不跨阶段合并。

数据来源：`figures/figure_data.json`。本图导出12条测量/统计值。

## F07｜相同起点的配对结果 · noise005

用途：附录；[PNG](figures/F07.png) · [PDF](figures/F07.pdf) · [SVG](figures/F07.svg) · [CSV](figures/F07.csv)

图注：每行60个相同起点，三行共享起点与固定BC k=2。计数相同不表示权重或动作相同；三行不是180个独立起点。

限制：按上述批次与分母解释，不跨阶段合并。

数据来源：`figures/figure_data.json`。本图导出12条测量/统计值。

## F08｜双方成功交集的完成步数差

用途：附录；[PNG](figures/F08.png) · [PDF](figures/F08.pdf) · [SVG](figures/F08.svg) · [CSV](figures/F08.csv)

图注：负值表示Full更快；阶梯是整数步数的经验分布，不是画图错误。包含全部长尾：clean每种子51个共同成功，noise每种子49个。

限制：成功交集条件分析，不能代表全体起点效率，不能把失败400步当真实完成时间。

数据来源：`figures/figure_data.json`。本图导出386条测量/统计值。

## F09｜位置 RMSE 与持续性弱基线

用途：正文；[PNG](figures/F09.png) · [PDF](figures/F09.pdf) · [SVG](figures/F09.svg) · [CSV](figures/F09.csv)

图注：64开发分支组/8父轨迹，K=4，H=8。点为各训练种子，横杠为均值；持续性为单个无参数预测器。数值与旧F19相同，合并为一张。

限制：RMSE不等于平均欧氏误差。已用于选点的开发数据，不是独立测试。

数据来源：`reproduction/extensions_20261012_01/offline_metrics.json`。本图导出14条测量/统计值。

## F10｜原世界模型确认的配对差值

用途：正文；[PNG](figures/F10.png) · [PDF](figures/F10.pdf) · [SVG](figures/F10.svg) · [CSV](figures/F10.csv)

图注：60个共同起点，BC固定，Full/Plain各3种子。95%起点/种子交叉bootstrap区间。联合Full−BC为+4.72[0.56,10.28]百分点；Full−Plain为+1.94[−0.56,6.11]。

限制：排序相对Plain的区间跨零；联合条件仍共享60起点。

数据来源：`reproduction/confirmation_20261012_01/analysis/paired_comparisons.csv`。本图导出9条测量/统计值。

## F11｜持续性与真值短期评分候选对照

用途：正文；[PNG](figures/F11.png) · [PDF](figures/F11.pdf) · [SVG](figures/F11.svg) · [CSV](figures/F11.csv)

图注：30个共同开发起点。Full/Plain为3个冻结权重均值，其他策略每条件一次；95%配对bootstrap区间。真值候选使用特权无噪声短期反事实、H=8与相同门控。

限制：oracle是局部短期评分诊断，不是任务成功上界；并不保证长期最佳。

数据来源：`reproduction/extensions_20261012_01/analysis/summary.json`。本图导出10条测量/统计值。

## F12a｜预测时域配置敏感性

用途：正文；[PNG](figures/F12a.png) · [PDF](figures/F12a.pdf) · [SVG](figures/F12a.svg) · [CSV](figures/F12a.csv)

图注：空心点为各冻结种子，短横线为均值；每条件30开发起点，成功率轴0–100%。离散配置不连折线。H包含D=2 FIFO前缀；H=1尚不能看到新提交动作。K=8同时扩展到训练外索引。

限制：K改变了候选内容，不能解释为纯数量因果效应；没有在确认集选配置。

数据来源：`reproduction/extensions_20261012_01/analysis/summary.json`。本图导出32条测量/统计值。

## F12b｜候选集合配置敏感性

用途：正文；[PNG](figures/F12b.png) · [PDF](figures/F12b.pdf) · [SVG](figures/F12b.svg) · [CSV](figures/F12b.csv)

图注：空心点为各冻结种子，短横线为均值；每条件30开发起点，成功率轴0–100%。离散配置不连折线。H包含D=2 FIFO前缀；H=1尚不能看到新提交动作。K=8同时扩展到训练外索引。

限制：K改变了候选内容，不能解释为纯数量因果效应；没有在确认集选配置。

数据来源：`reproduction/extensions_20261012_01/analysis/summary.json`。本图导出28条测量/统计值。

## F13｜不同预测步的位置误差

用途：附录；[PNG](figures/F13.png) · [PDF](figures/F13.pdf) · [SVG](figures/F13.svg) · [CSV](figures/F13.csv)

图注：64个已知开发组/8父轨迹。线为三个训练种子的均值，阴影为种子样本SD（ddof=1），不是95%CI。横轴是真实预测步。评分头续训control/calibrated的动力学与Full逐值完全一致，合并显示Full线，未删除不同结果。

限制：此指标是平均欧氏距离，不是F09的RMSE。重叠的相同预测不构成三份独立证据。

数据来源：`reproduction/multiseed_20261012_01/offline/prediction_horizons.csv`。本图导出128条测量/统计值。

## F14｜共享恢复的独立确认

用途：正文；[PNG](figures/F14.png) · [PDF](figures/F14.pdf) · [SVG](figures/F14.svg) · [CSV](figures/F14.csv)

图注：60个共同起点；每版本每起点8个执行条件，Full固定3种子。点/线为成功率和按起点重采样95%区间。v5原生确认464/480，不能当480个独立样本。

限制：与原无恢复世界模型确认是不同批次；不能直接相减估计恢复效应。

数据来源：`reproduction/recovery_v5_20261012_01/analysis_confirmation/summary.json`。本图导出20条测量/统计值。

## A02｜共享恢复的开发对照

用途：附录；[PNG](figures/A02.png) · [PDF](figures/A02.pdf) · [SVG](figures/A02.svg) · [CSV](figures/A02.csv)

图注：30个已知开发起点，每版本240次执行；v5与后续v6均236/240。起点bootstrap，不能写成独立确认。

限制：与原无恢复世界模型确认是不同批次；不能直接相减估计恢复效应。

数据来源：`reproduction/recovery_v5_20261012_01/analysis_dev_a/summary.json`。本图导出20条测量/统计值。

## F15a｜v5 起点配对效应与模块对照

用途：正文；[PNG](figures/F15a.png) · [PDF](figures/F15a.pdf) · [SVG](figures/F15a.svg) · [CSV](figures/F15a.csv)

图注：同60起点，20000次起点bootstrap、逐项95%区间。原预设执行混合v5−v4=+1.46[0,4.17]百分点：7次执行改善仅来自2个起点；三个训练种子固定。

限制：区间未多重比较校正，包含零不能称显著普遍优势；无v5同批关闭恢复组。

数据来源：`reproduction/recovery_v5_20261012_01/analysis_confirmation/summary.json`。本图导出5条测量/统计值。

## F15b｜v5 起点配对效应与模块对照

用途：正文；[PNG](figures/F15b.png) · [PDF](figures/F15b.pdf) · [SVG](figures/F15b.svg) · [CSV](figures/F15b.csv)

图注：同60起点，20000次起点bootstrap、逐项95%区间。原预设执行混合v5−v4=+1.46[0,4.17]百分点：7次执行改善仅来自2个起点；三个训练种子固定。

限制：区间未多重比较校正，包含零不能称显著普遍优势；无v5同批关闭恢复组。

数据来源：`reproduction/recovery_v5_20261012_01/analysis_confirmation/summary.json`。本图导出3条测量/统计值。

## F16｜独立几何分层压力测试

用途：正文；[PNG](figures/F16.png) · [PDF](figures/F16.pdf) · [SVG](figures/F16.svg) · [CSV](figures/F16.csv)

图注：四个人工几何层，每层4起点，共16；5版本共80次执行。固定静止开爪提议、第80步强制恢复，400步上限；v5合计12/16。

限制：小样本描述计数；不能合并原生确认，也不能称一般分布成功率。

数据来源：`reproduction/recovery_v5_20261012_01/analysis_geometry_confirmation/summary.json`。本图导出20条测量/统计值。

## F17｜已知开发案例的控制阶段时间线

用途：附录；[PNG](figures/F17.png) · [PDF](figures/F17.pdf) · [SVG](figures/F17.svg) · [CSV](figures/F17.csv)

图注：从既有机制回放记录提取；案例73与124已知，不是独立确认。阶段是离散类别，因此用时间条而非数字折线。成功轨迹在真实结束步停止。

限制：只说明机制，不把单例效果推广至所有起点。

数据来源：`reproduction/recovery_v5_20261012_01/mechanism_physics.json`。本图导出1527条测量/统计值。

## F18a｜既有四组效应：v2批次 / v2恢复

用途：附录；[PNG](figures/F18a.png) · [PDF](figures/F18a.pdf) · [SVG](figures/F18a.svg) · [CSV](figures/F18a.csv)

图注：既有两批各60起点的事后分析；后两图共用v3批次。Full平均三个固定权重，按起点配对95%逐项区间。浮点负零规范显示为0，未改变数据。

限制：不能拼成v5因果对照；不进行跨批次择优或宣称三次独立确认。

数据来源：`reproduction/consolidation_20261012_01/factorial_analysis.json`。本图导出10条测量/统计值。

## F18b｜既有四组效应：v3批次 / v2恢复

用途：附录；[PNG](figures/F18b.png) · [PDF](figures/F18b.pdf) · [SVG](figures/F18b.svg) · [CSV](figures/F18b.csv)

图注：既有两批各60起点的事后分析；后两图共用v3批次。Full平均三个固定权重，按起点配对95%逐项区间。浮点负零规范显示为0，未改变数据。

限制：不能拼成v5因果对照；不进行跨批次择优或宣称三次独立确认。

数据来源：`reproduction/consolidation_20261012_01/factorial_analysis.json`。本图导出10条测量/统计值。

## F18c｜既有四组效应：v3批次 / v3恢复

用途：附录；[PNG](figures/F18c.png) · [PDF](figures/F18c.pdf) · [SVG](figures/F18c.svg) · [CSV](figures/F18c.csv)

图注：既有两批各60起点的事后分析；后两图共用v3批次。Full平均三个固定权重，按起点配对95%逐项区间。浮点负零规范显示为0，未改变数据。

限制：不能拼成v5因果对照；不进行跨批次择优或宣称三次独立确认。

数据来源：`reproduction/consolidation_20261012_01/factorial_analysis.json`。本图导出10条测量/统计值。

## A03｜v6 开度与不可行处理消融

用途：附录；[PNG](figures/A03.png) · [PDF](figures/A03.pdf) · [SVG](figures/A03.svg) · [CSV](figures/A03.csv)

图注：37个已知诊断条件的R1/R2消融；开发240次执行共享30起点，v5与v6均236/240，没有开发成功率改善。

限制：按上述批次与分母解释，不跨阶段合并。

数据来源：`reproduction/improvement_v6_20261015_01/analysis/dev_comparison.json`；`reproduction/improvement_v6_20261015_01/analysis/pilot_b.json`。本图导出6条测量/统计值。

## A04｜恢复开度：观测与计划不一致

用途：附录；[PNG](figures/A04.png) · [PDF](figures/A04.pdf) · [SVG](figures/A04.svg) · [CSV](figures/A04.csv)

图注：已知侧倒失抓案例11000013；采用原图state_before语义，每控制步一个原始观测，无平滑。

限制：控制命令不等于实际开度，不能仅凭目标值判断抓取空间。

数据来源：`traces/v6_aperture_v5.json`；`traces/v6_aperture_v6.json`。本图导出134条测量/统计值。

## A05｜无可行候选时的离散控制阶段

用途：附录；[PNG](figures/A05.png) · [PDF](figures/A05.pdf) · [SVG](figures/A05.svg) · [CSV](figures/A05.csv)

图注：Full s23、无噪声、demo188：双方都未完成。新保护减少重复下降，但没有创造可行抓取。空白为其他控制阶段，CSV保留全部阶段。

限制：按上述批次与分母解释，不跨阶段合并。

数据来源：`traces/v6_infeasible_v5.json`；`traces/v6_infeasible_v6.json`。本图导出800条测量/统计值。

## A06a｜v10 箱沿已知案例：末端高度（m）/物体高度（m）

用途：附录；[PNG](figures/A06a.png) · [PDF](figures/A06a.pdf) · [SVG](figures/A06a.svg) · [CSV](figures/A06a.csv)

图注：demo6000005，BC k=2、噪声0.05；同起点同噪声。逐步观测，不平滑；v6成功后在实际结束步停止。

限制：轨迹复杂不是绘图插值；v6的完成来自BC接管，不应声称新恢复抓持。

数据来源：`reproduction/improvement_v10_20261015_01/analysis/wall_edge_trajectories.csv`。本图导出3022条测量/统计值。

## A06b｜v10 箱沿已知案例：物体到目标XY距离（m）/物体轴倾角（°）

用途：附录；[PNG](figures/A06b.png) · [PDF](figures/A06b.pdf) · [SVG](figures/A06b.svg) · [CSV](figures/A06b.csv)

图注：demo6000005，BC k=2、噪声0.05；同起点同噪声。逐步观测，不平滑；v6成功后在实际结束步停止。

限制：轨迹复杂不是绘图插值；v6的完成来自BC接管，不应声称新恢复抓持。

数据来源：`reproduction/improvement_v10_20261015_01/analysis/wall_edge_trajectories.csv`。本图导出3022条测量/统计值。

## A07｜v11 开发集逐条件退步核对

用途：附录；[PNG](figures/A07.png) · [PDF](figures/A07.pdf) · [SVG](figures/A07.svg) · [CSV](figures/A07.csv)

图注：30个相同起点、8执行条件；Full s41噪声组少1次成功，v11未达到采用门槛，未独立确认。

限制：不能用颜色差或240执行次数夸大独立样本量。

数据来源：`reproduction/improvement_v11_20261015_01/analysis/development.json`。本图导出16条测量/统计值。

## A08a｜已知箱沿四组消融：末端世界高度（m）/物体世界高度（m）

用途：附录；[PNG](figures/A08a.png) · [PDF](figures/A08a.pdf) · [SVG](figures/A08a.svg) · [CSV](figures/A08a.csv)

图注：state_after原始每控制步数据，同起点验证通过，无平滑/补零/终点外推。BC k=2、噪声0.05、demo6000005；仅v11在380步完成。

限制：真实控制阶段/观测波动保留。逐点CSV补全了旧v11退步图未导出的目标XY距离。

数据来源：`traces/v11_edge_axis.json`；`traces/v11_edge_guard.json`；`traces/v11_edge_v10.json`；`traces/v11_edge_v11.json`。本图导出3160条测量/统计值。

## A08b｜已知箱沿四组消融：物体到目标XY距离（m）/观测指间距（mm）

用途：附录；[PNG](figures/A08b.png) · [PDF](figures/A08b.pdf) · [SVG](figures/A08b.svg) · [CSV](figures/A08b.csv)

图注：state_after原始每控制步数据，同起点验证通过，无平滑/补零/终点外推。BC k=2、噪声0.05、demo6000005；仅v11在380步完成。

限制：真实控制阶段/观测波动保留。逐点CSV补全了旧v11退步图未导出的目标XY距离。

数据来源：`traces/v11_edge_axis.json`；`traces/v11_edge_guard.json`；`traces/v11_edge_v10.json`；`traces/v11_edge_v11.json`。本图导出3160条测量/统计值。

## A09a｜持物等待开发退步：末端世界高度（m）/物体世界高度（m）

用途：附录；[PNG](figures/A09a.png) · [PDF](figures/A09a.pdf) · [SVG](figures/A09a.svg) · [CSV](figures/A09a.csv)

图注：state_after原始每控制步数据，同起点验证通过，无平滑/补零/终点外推。Full s41、噪声0.05、demo87；v6在358步成功，v11在400步失败；新箱沿模块未触发。

限制：真实控制阶段/观测波动保留。逐点CSV补全了旧v11退步图未导出的目标XY距离。

数据来源：`traces/v11_regression_v11.json`；`traces/v11_regression_v6.json`。本图导出1516条测量/统计值。

## A09b｜持物等待开发退步：物体到目标XY距离（m）/末端与物体距离（mm）

用途：附录；[PNG](figures/A09b.png) · [PDF](figures/A09b.pdf) · [SVG](figures/A09b.svg) · [CSV](figures/A09b.csv)

图注：state_after原始每控制步数据，同起点验证通过，无平滑/补零/终点外推。Full s41、噪声0.05、demo87；v6在358步成功，v11在400步失败；新箱沿模块未触发。

限制：真实控制阶段/观测波动保留。逐点CSV补全了旧v11退步图未导出的目标XY距离。

数据来源：`traces/v11_regression_v11.json`；`traces/v11_regression_v6.json`。本图导出1516条测量/统计值。
