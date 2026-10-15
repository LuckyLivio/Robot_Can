"""Copy existing figures and their compact source evidence; never execute models or plots."""
from pathlib import Path
import csv, hashlib, html, json, shutil

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

def item(gid, number, chapter, role, source, target, title, caption, supports, limits, data, plot, issues="未见遮挡、乱码或截断；按原文件复制。"):
    return dict(group_id=gid, suggested_number=number, chapter=chapter, role=role,
                source_stem=source, target_stem=target, title=title, caption=caption,
                supports=supports, cannot_support=limits, data_sources=data,
                plotting_source=plot, visual_review=issues)

DC="reproduction/figures_deepcheck_20261014_01"
MS="reproduction/multiseed_20261012_01"
CF="reproduction/confirmation_20261012_01"
EX="reproduction/extensions_20261012_01"
V5="reproduction/recovery_v5_20261012_01"
CO="reproduction/consolidation_20261012_01"
G=[]
def deep(gid,num,chapter,role,name,title,caption,supports,limits,data,issues="已视觉检查；数据与轴标签按2026-10-14第二轮复核表达。"):
    G.append(item(gid,num,chapter,role,f"{DC}/figures/{name}",f"study_world_model_deepcheck/{name}",title,caption,supports,limits,data,f"{DC}/plot_review.py",issues))

deep("F01","图4-1","第四章","方法草图；可据此重新排版，不是实验结果","figure_method_diagram","延迟一致的候选预测与门控选择流程",
     "基于23维含物体真值的低维状态，固定BC输出k=0、1、2、3四个动作块索引候选；将真实D=2 FIFO前缀及后续重复候选组成H=8想象序列，输入GRU预测未来状态并估计进展与失抓评分。评分S=p(H)+0.5 mean(p)−0.5 max(r)，与k=2分数相比不足0.02时回退；每次只提交一个新动作，并在执行队首动作后重新观测。本图对应原世界模型确认，不含后续共享恢复。",
     "系统数据流、FIFO与候选序列一致性、单步执行重规划。",
     "不是实际预测轨迹；r不是通用失败概率；k=2是动作块索引，不是单独训练的最佳模型；本图不证明性能。",
     ["evaluate_delay.py","world_model.py","common.py",f"{CF}/design.json"],
     "结构关系可以解释；留白较大、公式及中文文字较密，作为草图保留。正式稿排版可重绘，但不得改变两路输入、FIFO和回退语义。")

deep("F02","图6-1","第六章 训练与泛化诊断","主图候选","figure_training_curves","三个训练种子的固定训练/开发集误差演变",
     "列为随机种子17、23、41，横轴为已完成优化器更新次数250至3000，每250步一份已保存权重，共36个checkpoint；行分别为全固定集总损失、归一化23维状态MSE及物体位置平均欧氏误差(mm)。总损失=MSE+进展BCE+0.5风险BCE+0.2排序损失。蓝实线为160组/20父轨迹训练集，橙虚线为64组/8父轨迹开发集，竖点线为原选定的2750、1250、2750步。曲线由10月14日既存CPU离线复核得到；本次打包未重新推理。",
     "训练拟合改善；开发全状态误差没有同步改善且s23总损失后期上升；物体位置误差仍下降，指标覆盖维度不同。",
     "不是随机批次日志曲线、不是epoch、不是独立测试集或闭环成功率；不能根据此图再改原确认模型。",
     [f"{DC}/checkpoint_metrics.csv",f"{DC}/diagnostics.json","figures/figure_data.json"],
     "九子图已视觉检查；缩到半页可能字小，建议整页或拆成三行/三个子图。真实开发平台和上升保留，不能美化成单调下降。")

deep("F03","图7-1或附图A-1","第七章或附录","讨论/附录","figure_regret_diagnostic","稀疏开发组对候选选择遗憾的影响",
     "左图为三个种子的64组开发集平均regret随更新次数变化，regret定义为同组最大真实短期分数减去模型argmax候选的真实分数。右图比较s23整体均值与全局组5(demo_105、point=195)对均值的贡献regret_5/64，编号从0开始。该组在step1500贡献约0.005103，整体约0.005604，约占91%。数据来自10月14日既存checkpoint复核。",
     "小开发集少数有区分度候选组会支配评分选择指标，解释跳变并揭示覆盖不足。",
     "不是训练发散或闭环成功率的直接证明；相邻点连线没有表示每一次更新都被观测；不能从单组支配推断唯一因果机制。",
     [f"{DC}/checkpoint_metrics.csv",f"{DC}/diagnostics.json"],
     "已视觉检查；右图标题的“第5号组”指全局组5，不是demo_105内部第5个组。正式图注必须写清。")

deep("F04","图6-2","第六章 开发消融","主图候选","figure_ablation","三个训练种子的开发集消融结果",
     "固定30个开发起点，在无噪声与位置执行噪声σ=0.05下，比较BC k=2、Full、无排序Plain、参数近似匹配Direct、仅预测+物理代价、部署去风险评分与去门控。除固定BC外为种子17、23、41均值；点为均值，横线为原分析对父轨迹和种子交叉配对bootstrap得到的描述性95%区间。每条件BC成功25/30、24/30，Full均值78.89%、82.22%，Plain80.00%、84.44%。",
     "Full在开发集并非最优；门控及评分设计需要受控分析；保留负结果。",
     "不能称独立确认；去风险评分没有去掉训练风险监督；仅预测模型全程回退k=2，相同成功率不证明预测器提高控制；物理代价尺度不同，不能视为纯单因素评分消融。",
     [f"{MS}/analysis/summary.csv",f"{MS}/analysis/paired_comparisons.csv",f"{MS}/analysis/controller_usage.csv"],
     "已视觉检查；横轴为容纳右侧文字延伸到100%以上，所有数据仍≤100%。原样复制，正式排版可将数字移到轴外并固定0—100，不应解读为成功率超过100%。")

deep("F05","图6-3","第六章 原世界模型独立确认","主图候选","figure_success_rate","冻结方法在60个新起点上的独立确认成功率",
     "原世界模型确认批次confirmation_20261012_01：同60个冻结后新原生起点、两个共享起点的噪声条件，400步预算、D=2、H=8、K=4，BC固定权重，Full/Plain分别使用17、23、41三个固定训练种子；14任务共840次执行，独立起点数仍为60。无噪声BC/Full/Plain为85.00/90.00/88.33%，噪声0.05为81.67/86.11/83.89%。点为成功率均值，线为20000次起点与种子交叉bootstrap的描述性95%区间。",
     "在这批预锁定起点上Full具有正向结果，且区间体现有限起点抽样不确定性。",
     "三个种子成功数相同不意味着无不确定性；不能从两个单独区间是否重叠判断配对差异；此图不含规则恢复，不能与v5不同批次直接相减。",
     [f"{CF}/analysis/summary.csv",f"{CF}/analysis/analysis.json"],
     "已视觉检查；右侧百分数字段导致坐标留白超过100%，是排版范围不是观测值；正文优先搭配F10配对效应图。")

deep("F06","附图A-2a","附录 配对明细","附录","figure_paired_clean","原世界模型无噪声确认的逐种子配对计数",
     "原确认同60起点；列为双方成功、仅Full成功、仅BC成功、双方失败，三行分别s17、s23、s41，均为[51,3,0,6]。BC为同一固定k=2基线，三行共用起点，成功集合相同但步骤向量和权重不同。",
     "把总成功率还原为同一起点的救回/退步与共同失败，解释看似重复的数据。",
     "三行不是180个独立起点；本批零退步不能保证所有状态安全；色深不是另一个指标。",
     ["figures/figure_data.json",f"{DC}/diagnostics.json",f"{CF}/analysis/paired_per_seed.csv"])

deep("F07","附图A-2b","附录 配对明细","附录","figure_paired_noise005","原世界模型噪声确认的逐种子配对计数",
     "原确认同60起点、执行位置噪声σ=0.05，BC固定k=2。s17与s23四类配对数均为[49,3,0,8]，s41为[49,2,0,9]；列顺序为双方成功、仅Full成功、仅BC成功、双方失败。所有方法同一起点使用同一逐步噪声序列。",
     "配对优势集中于少量困难起点；显示种子间仍有差异和共同失败。",
     "只覆盖每起点一个冻结噪声实现，不能推广所有噪声种子；三行共用起点。",
     ["figures/figure_data.json",f"{DC}/diagnostics.json",f"{CF}/analysis/paired_per_seed.csv"])

deep("F08","图6-4或附图A-3","第六章 效率或附录","补充主图/附录","figure_success_steps","双方成功交集的配对完成步数差分布",
     "原世界模型确认，横轴为Full完成步数减BC k=2完成步数，负值表示Full更快；纵轴为经验累计比例。两条件分别使用双方均成功的交集，各种子无噪声n=51、噪声n=49。阶梯来自整数步数，没有平滑或剔除离群点。无噪声三个种子中位差为0、1、−1步；噪声下均为0。",
     "成功率改善不等于普遍更快；完整分布保留长尾和相同步数。",
     "成功交集存在条件选择，不能代表所有起点效率或把失败400步直接当真实完成时间；不能据中位数零证明等效。",
     ["figures/figure_data.json",f"{DC}/diagnostics.json",f"{CF}/analysis/episodes.csv"])

G.append(item("F09","图6-5","第六章 离线预测诊断","主图候选",f"{EX}/analysis/prediction","study_supplemental_development/prediction","持续性基线与学习预测器的位置RMSE",
     "使用既有开发64组、8父轨迹，每组4候选×8预测步。位置RMSE定义为1000√mean(||x_hat−x||²)，不是逐样本欧氏距离的算术均值。Full/Plain柱为17/23/41三个训练种子RMSE的算术均值，点为各种子，持续性为一个无参数预测器(未来状态恒为当前)。末端RMSE持续性/Full/Plain=59.1708/31.0427/29.9575 mm；物体=52.0276/34.9498/26.9733 mm。",
     "Full相对持续性物体RMSE减少约32.8%，学习动力学具有局部预测价值；Plain的位置RMSE更低。",
     "这些分支参与过选点，不是独立泛化测试；三种子均值不是把所有误差先合并再开方；不能据位置RMSE直接断言闭环成功更高或排序有效。",
     [f"{EX}/offline_metrics.json"],f"{EX}/plot_results.py"))

G.append(item("F10","图6-6","第六章 原世界模型独立确认","主图候选",f"{CF}/analysis/paired_effects","study_world_model_confirmation/paired_effects","原世界模型确认的配对成功率差值",
     "原确认60个新起点、Full/Plain三种子、固定BC k=2，无噪声和σ=0.05分别绘制。点为左方法减右方法成功率百分点差，横线为20000次起点与种子交叉配对bootstrap描述性95%区间。Full−BC分别+5.00[0,11.67]、+4.44[0,10.00]；Full−Plain分别+1.67[0,5]、+2.22[−1.11,6.67]。预设两条件等权联合Full−BC为+4.72[0.56,10.28]，Full−Plain+1.94[−0.56,6.11]；联合值不在此图内，应在表格/正文补报。",
     "直接展示配对改善与不确定性；原确认Full相对BC联合指标有正向证据。",
     "区间是逐项描述性区间，非多重比较同时区间；分条件触零；没有证明排序可靠优于Plain；不能把此无恢复批次用于v5直接归因。",
     [f"{CF}/analysis/paired_comparisons.csv",f"{CF}/analysis/analysis.json"],f"{CF}/analyze_confirmation.py",
     "已视觉检查；右侧留白较多、图中仅六个分条件效应，联合结果必须另表列出；源绘图入口以复制的实际脚本为准。"))

G.append(item("F11","图6-7a","第六章 补充开发诊断","主图候选",f"{EX}/analysis/controls","study_supplemental_development/controls","持续性与真实短期评分oracle对照",
     "同30开发起点、400步、D=2，clean与σ=0.05两条件。Full/Plain为三个冻结种子均值，BC、持续性和短期oracle各一次/条件。BC与持续性成功25/30、24/30；Full78.89/82.22%，Plain80.00/84.44%，真实短期oracle25/30、25/30。横线为原配对bootstrap描述性95%区间。oracle每步从完整相同状态模拟4候选各8步，以真实进展/失抓标签评分，仍保留0.02门控与k=2回退。",
     "消除短期预测和评分估计误差后仍存在失败，失败不能全归因于模型；持续性作为弱预测器而非弱闭环策略。",
     "oracle是使用真实未来的诊断，不可部署，也不是长期成功率数学上界；噪声执行下oracle使用名义无噪声未来；开发对照不是独立确认；相同成败的[0,0]bootstrap不证明总体等效。",
     [f"{EX}/analysis/summary.json",f"{EX}/analysis/paired_comparisons.csv"],f"{EX}/plot_results.py"))

G.append(item("F12","图6-7b","第六章 补充开发诊断","主图候选",f"{EX}/analysis/sensitivity","study_supplemental_development/sensitivity","预测时域与候选数量敏感性",
     "同30开发起点、两噪声条件、Full冻结三种子；左图H=1/3/4/8、K=4，H包含D=2 FIFO；右图H=8，候选集合为K=1:{2}、K=2:{0,2}、K=4:{0,1,2,3}、K=8:{0,…,7}。曲线为均值，散点为实际种子值；K=1为固定策略不伪造三种子。H=1看不到新候选执行、全程回退；H=3改选约0.6%；K=8超出原训练候选0…3支持范围。",
     "时域与延迟的关系必须显式处理；扩大候选没有在此开发诊断中稳定改善成功率。",
     "不是独立确认或只增加计算预算的纯因果比较；纵轴45—100%截取，视觉差距不能代替绝对值；散点不是新增独立起点。",
     [f"{EX}/analysis/summary.json",f"{EX}/analysis/paired_comparisons.csv",f"{EX}/protocol.json"],f"{EX}/plot_results.py",
     "保留原图；曲线只有四个设置点，连线为可读性，不能解读为连续扫描；纵轴下限45%应在图注注明。"))

G.append(item("F13","附图A-4","附录 物理预测分时域诊断","附录",f"{MS}/offline/physical_prediction","study_multiseed_offline/physical_prediction","逐预测步的平均欧氏位置误差",
     "固定开发64组、8父轨迹，横轴预测步1至8；每个训练种子先对各候选的欧氏位置误差取均值(mm)，再绘制三种子均值及±样本标准差(ddof=1)。比较Full、Plain(无排序)、仅预测。此图为mean(||error||)，与F09/F19的√mean(||error||²)不是同一指标。评分头续训/校准共享Full动力学，所以不重复绘制；Direct无状态预测。",
     "误差随开环预测步增长；位置误差较小的Plain不等于更高闭环成功率。",
     "阴影是3个种子的样本标准差，不是95%置信区间或父轨迹抽样误差；不是独立测试。",
     [f"{MS}/offline/prediction_horizons.csv",f"{MS}/offline/metrics.json"],f"{MS}/evaluate_offline.py",
     "已视觉检查；Full物体误差阴影较宽是真实三种子分散，不应当作CI；与RMSE图并用时须分清名称。"))

G.append(item("F14","图6-8","第六章 共享恢复独立确认","主图候选",f"{V5}/analysis_confirmation/success_comparison","study_recovery_v5_confirmation/success_comparison","共享恢复版本的原生独立确认成功率",
     "v5新确认批次，60个冻结后新原生起点，五版v2、v4、时间T、侧倒间隙S、组合TS(v5)，BC k=2和Full三固定种子分别评估，clean与σ=0.05两条件。共2400执行，每版480执行来自60起点×[1固定BC+3固定Full]×2条件。总成功数457、457、463、458、464；v5为96.67%。v5 BC为60/60、58/60，Full为176/180、170/180；图中Full柱为三种子均值，不是180个独立起点。",
     "时间安排及组合控制器在这批困难原生任务有局部增益；共享恢复后的BC仍很强，Full均值低于BC。",
     "不是原世界模型840回合批次，不能跨批次直接相减；此图柱没有不确定区间，应配F15；共享规则收益不是世界模型预测变强；没有v5同批关闭恢复组。",
     [f"{V5}/analysis_confirmation/summary.json",f"{V5}/analysis_confirmation/episodes.csv"],f"{V5}/analyze_stage.py",
     "已视觉检查；柱形接近天花板且无CI，必须配效应图解释有限样本；图例与百分数正常，不能用视觉小差断言等效。"))

G.append(item("F15","图6-9","第六章 共享恢复独立确认","主图候选",f"{V5}/analysis_confirmation/paired_effects","study_recovery_v5_confirmation/paired_effects","v5相对v4的起点配对效应与模块消融",
     "与F14同一60新起点；左侧为v5−v4各基础策略/噪声条件及预设八执行混合差值，右侧为T、S、TS相对v4混合差。混合权重按1个BC与3个固定Full种子、2条件共八执行等权，不是BC/Full两个家族等权。v5整体+1.46个百分点[0,4.17]，T+1.25[0,3.75]、S+0.21[0,0.625]。以起点为重采样单位20000次bootstrap，固定随机种子20261016；三个训练种子在此作为固定权重，区间不包含任意重训不确定性。",
     "v5多救回7次执行且相对v4无新增失败，但集中在两个不同起点；T是主要增益，S增益很局部。",
     "逐项95%区间触零、未多重比较校正，不能声称普遍/显著优越；不是三个种子标准差；不能只报7次而忽略独立起点只有2个。",
     [f"{V5}/analysis_confirmation/summary.json"],f"{V5}/plot_confirmation_effects.py"))

G.append(item("F16","图6-10","第六章 独立几何压力测试","主图候选",f"{V5}/analysis_geometry_confirmation/geometry_comparison","study_recovery_v5_confirmation/geometry_comparison","独立几何分层压力测试",
     "16个冻结后新人工几何起点，每类4个：远端对齐、目标角落、源箱侧倒、目标箱侧倒。使用静止张爪提议，在第80控制步强制恢复，400步上限；五版共80执行，不使用BC/Full种子作为额外独立样本。v2/v4/T/S/v5总成功8/11/12/11/12；v5四层为4/3/4/1(各/4)。",
     "展示角落与侧倒失败边界，v5对v4仅多一个远端时间案例；该新压力集上S无新增成功。",
     "人工分层每类4例，不能当真实场景发生频率或与原生确认合并；静态间隙可行不等于路径无碰撞/抓持稳定。",
     [f"{V5}/analysis_geometry_confirmation/summary.json",f"{V5}/geometry_confirmation_design.json"],f"{V5}/analyze_geometry_confirmation.py"))

G.append(item("F17","图5-2或附图B-1","第五章 机制说明或附录","已知开发案例图",f"{V5}/timing_mechanism","study_recovery_v5_mechanism/timing_mechanism","剩余预算控制的已知案例阶段时间线",
     "从pilot_b既有demo_73和demo_124日志及当时精确物理回放提取，分别比较v4与时间模块T。色块合并NORMAL、接近、抓持验证、搬运、放置释放等阶段，横轴为控制步，400步虚线为预算上限；T在351、376步成功，v4均400步未完成。图为已知小测试案例，不是新原生确认demo_10000029。",
     "解释预算控制如何为后续搬运释放留出步数，给出可读事件案例。",
     "事后选出的已知开发案例不能证明总体收益；本次独立原生确认收益主要来自预算紧张下的移动安排，不能把提前启动一并当作新确认已证明有效。",
     [f"{V5}/mechanism_physics.json"],f"{V5}/probe_mechanisms.py",
     "已视觉检查；原图没有写“已知小测试”，正式使用必须加本图注，避免混成冻结后新确认。"))

G.append(item("F18","附图B-2或图6-11","第六章 既有四组分析或附录","事后描述性证据",f"{CO}/figures/factorial_effects","study_existing_factorial/factorial_effects","世界模型与共享恢复的既有四组效应分解",
     "对已有v2/v3确认的两批各60起点进行事后描述分析；三行分别为v2批次的v2恢复、v3批次的v2恢复、同一v3批次的v3恢复。四组为BC/Full×关闭/开启同版恢复，Full平均三个固定权重；展示恢复对BC/Full的效应、无/有恢复时Full−BC，以及交互差分。每行两列为clean/σ=0.05，线为同起点配对bootstrap逐项描述性95%区间。后两行共用v3起点，不能算三批独立数据。",
     "已有恢复层会同时帮助BC与Full；世界模型净增益与恢复增益必须拆开解释，交互效应不稳定。",
     "不是新预注册确认，不是v5恢复四组；不能将v2/v3无恢复与v5开启恢复拼成最新交互检验；三个训练种子为固定权重，不代表任意重训。",
     [f"{CO}/factorial_analysis.json",f"{CO}/FACTORIAL_REVIEW.md"],f"{CO}/plot_factorial.py",
     "已视觉检查；三行六子图较密，建议整页或附录；存在−0.00浮点负零标签，按0.00解读，源数据未出现实质负效应。本包不重画，以保留现有证据。"))

G.append(item("F19","F09的简洁替代，不重复编号","第六章 离线预测诊断","备选主图，与F09择一",f"{CO}/figures/prediction_rmse","study_presentation_alternative/prediction_rmse","开发预测位置RMSE的简洁表达",
     "与F09完全同源：64组/8父轨迹的既有开发分支、Full/Plain三固定种子RMSE均值、无参数持续性单一预测器；末端59.17/29.96/31.04 mm、物体52.03/26.97/34.95 mm(依次持续性/Plain/Full)。此图为横向均值条，不展示各训练种子点。物体RMSE相对持续性降低32.8%来自同一数据计算。",
     "适合正文紧凑比较并明确Plain较低；可为32.8%提供测量来源。",
     "与F09是同一证据，不能计两次实验；不是独立泛化或成功率；要讨论种子离散时选F09或表格。",
     [f"{EX}/offline_metrics.json",f"{CO}/world_model_view.json"],f"{CO}/build_world_model_view.py"))

SOURCE_FILES = [
    "make_figures.py", "figures/figure_data.json",
    f"{DC}/plot_review.py", f"{DC}/REPORT.md", f"{DC}/manifest.json", f"{DC}/verification.json", f"{DC}/checkpoint_metrics.csv", f"{DC}/diagnostics.json",
    f"{MS}/analysis/summary.csv", f"{MS}/analysis/paired_comparisons.csv", f"{MS}/analysis/controller_usage.csv", f"{MS}/analysis/report.txt",
    f"{MS}/offline/prediction_horizons.csv", f"{MS}/offline/metrics.csv", f"{MS}/offline/metrics.json", f"{MS}/evaluate_offline.py",
    f"{CF}/analysis/summary.csv", f"{CF}/analysis/paired_comparisons.csv", f"{CF}/analysis/paired_per_seed.csv", f"{CF}/analysis/analysis.json", f"{CF}/analysis/report.txt",
    f"{EX}/analysis/summary.json", f"{EX}/analysis/paired_comparisons.csv", f"{EX}/offline_metrics.json", f"{EX}/plot_results.py", f"{EX}/offline.py", f"{EX}/REPORT.md", f"{EX}/protocol.json",
    f"{V5}/analysis_confirmation/summary.json", f"{V5}/analysis_geometry_confirmation/summary.json", f"{V5}/geometry_confirmation_design.json", f"{V5}/mechanism_physics.json", f"{V5}/plot_confirmation_effects.py", f"{V5}/analyze_stage.py", f"{V5}/analyze_geometry_confirmation.py", f"{V5}/probe_mechanisms.py", f"{V5}/ASSESSMENT.md",
    f"{CO}/factorial_analysis.json", f"{CO}/FACTORIAL_REVIEW.md", f"{CO}/plot_factorial.py", f"{CO}/world_model_view.json", f"{CO}/build_world_model_view.py",
]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def copy_existing(src, dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():
        assert digest(dst)==digest(src), f"Refusing to replace different file: {dst}"
    else:
        shutil.copy2(src,dst)
    assert digest(src)==digest(dst)
    return digest(src)

def main():
    files=[]
    for g in G:
        g["files"]=[]
        for ext in ("png","pdf","svg"):
            rel=f'{g["source_stem"]}.{ext}'
            src=ROOT/rel
            if not src.is_file():
                continue
            target=f'{g["target_stem"]}.{ext}'
            value=copy_existing(src,OUT/target)
            g["files"].append(target)
            files.append({"group_id":g["group_id"],"suggested_number":g["suggested_number"],"chapter":g["chapter"],"role":g["role"],"title":g["title"],"format":ext,"bundle_relative_path":target,"source_project_relative_path":rel,"source_absolute_path":str(src),"sha256":value,"bytes":src.stat().st_size,"data_sources":" | ".join(g["data_sources"]),"plotting_source":g["plotting_source"],"visual_review":g["visual_review"]})
        assert len(g["files"])>=2, g
    sources=[]
    all_sources = list(dict.fromkeys(SOURCE_FILES + [p for g in G for p in g['data_sources']] + [g['plotting_source'] for g in G]))
    for rel in all_sources:
        src=ROOT/rel
        assert src.is_file(), f"Missing declared figure source: {rel}"
        target=f"source_material/{rel}"
        sources.append({"source_project_relative_path":rel,"bundle_relative_path":target,"sha256":copy_existing(src,OUT/target),"bytes":src.stat().st_size})
    with (OUT/"FIGURE_PROVENANCE.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(files[0]));writer.writeheader();writer.writerows(files)
    (OUT/"FIGURE_GROUPS.json").write_text(json.dumps(G,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    (OUT/"SOURCE_MATERIAL_MANIFEST.json").write_text(json.dumps(sources,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    intro="""# 论文图包与逐图图注（2026-10-15）

本包复制已有图，不训练、不执行checkpoint推理、不跑仿真，也不修改原图。共19组、44个PNG/PDF/SVG文件；逐文件SHA-256见FIGURE_PROVENANCE.csv，所有文件与源字节一致。八组世界模型图优先采用2026-10-14第二轮deepcheck表达，而非10月9日旧稿或第一轮改稿。已有结果并不完美：泛化差距、排序不稳定、共享恢复后强BC不劣于Full、侧倒/角落失败均在图注保留。

## 在新设备使用

- 打开index.html可离线查看全部预览，不需要服务器或Python。Word先插PNG看版式，LaTeX优先PDF；SVG适合矢量编辑。路径均相对于本目录，整体复制即可。
- 图号按当前八章提纲给出建议，正式稿合并/删图后统一编号。F09与F19是同一RMSE数据的两种表达，正文择一，不能当两项独立证据。
- source_material保存绘图所用小型测量表/JSON、报告、已有绘图源码，仅作来源核验。evaluate_offline.py、offline.py、probe_mechanisms.py包含推理/仿真逻辑，**不要为写论文运行它们**。本次未执行任何源脚本。某些原绘图脚本依赖完整项目相对路径且拒绝覆盖，不是便携一键再绘制入口。
- verify_figures.py只使用Python标准库校验本包哈希，不加载权重，不运行物理仿真。它不能替代原始科学运行验收。

## 统一口径（插图前先看）

1. 开发消融30起点、原世界模型确认60起点、v5恢复确认另60起点、人工压力16起点属于不同研究批次。回合数不是独立起点数，不能把840/2400/480当独立样本数；确认评估后已成为已知数据。
2. 原世界模型区间对种子/起点交叉重采样；v5区间对起点重采样、三个训练权重固定；physical_prediction阴影为3种子样本SD。三者统计含义不同。
3. “归一化全状态MSE”“平均欧氏位置误差(mm)”和“位置RMSE(mm)”不是同一指标，不可接到一条曲线上。均值±SD不是95%CI，描述性CI也不是任意新种子/新任务的保证。
4. Full为有排序的世界模型；Plain无排序；Direct不预测状态；k是固定BC动作块索引，k=2不等于新的“最佳训练模型”。r是失抓监督标签，不是全部失败概率。
5. 原无恢复世界模型确认Full−BC两条件等权+4.72[0.56,10.28]个百分点；Full−Plain+1.94[−0.56,6.11]，不能证明排序可靠增益。v5混合对v4+1.46[0,4.17]，只2个起点救回7次执行；不能描述为全面解决或显著普遍优势。
6. 方法图/下方Mermaid是结构示意，曲线图才是测量；timing_mechanism为已知小测试，不可写成新确认案例。v5同批关闭恢复组不存在；旧v2/v3四组分析不得拼接成v5交互结论。

## 已发现但本次没有重绘的版式问题

- F04/F05横轴为右侧文本留白延伸超过100，数据没有超过100。论文重排时可把文字放轴外；本包按原文件保存。
- F18部分标签出现−0.00，是浮点负零，按0.00解释；不能把其当有意义负效应。
- F02、F18信息密集，建议整页或拆子图；F12纵轴截在45%，不要夸大视觉差异。
- F17原图未标“开发已知案例”，已在本目录图注明确；不要省略该限定。
- 本次视觉检查了19组PNG；PDF/SVG通过文件结构/格式与SHA复制核对，未重新逐页渲染。没有发现PNG乱码、缺曲线或截断。

## 推荐正文顺序

第三章用系统示意源码（非测量）；第四章F01；第五章F17仅作机制示例；第六章依次F02训练泛化、F04开发消融、F05+F10原独立确认、F09或F19预测诊断、F11/F12补充诊断、F14/F15恢复确认、F16压力边界。F03、F06—F08、F13、F18可进入讨论或附录。不是所有19组都必须塞进正文。

## 逐图组目录与可直接改写的中文图注

"""
    lines=[intro]
    for g in G:
        png=next(p for p in g["files"] if p.endswith(".png"))
        refs=" · ".join(f'[{Path(p).suffix[1:].upper()}]({p})' for p in g["files"])
        lines += [f'### {g["group_id"]}｜{g["suggested_number"]}｜{g["title"]}\n',f'章节：{g["chapter"]}。用途：{g["role"]}。{refs}\n',f'**建议图注：** {g["caption"]}\n',f'**可支持：** {g["supports"]}\n',f'**不能支持：** {g["cannot_support"]}\n',f'**视觉/标签检查：** {g["visual_review"]}\n',f'**原图路径：** `{g["source_stem"]}.{{png,pdf,svg(若有)}}`；绘图来源：`{g["plotting_source"]}`。\n',f'**测量来源：** '+"；".join(f'`{p}`' for p in g["data_sources"])+"。\n",f'![{g["group_id"]} {g["title"]}]({png})\n']
    (OUT/"FIGURE_CATALOG.md").write_text("\n".join(lines),encoding="utf8")
    cards=[]
    for g in G:
        png=next(p for p in g["files"] if p.endswith(".png"))
        cards.append(f'<section><h2>{html.escape(g["group_id"]+" · "+g["title"])}</h2><p>{html.escape(g["role"]+" / "+g["suggested_number"])}</p><a href="{png}"><img src="{png}" loading="lazy" alt="{html.escape(g["title"])}"></a><p>{html.escape(g["caption"])}</p><p class="limit">限制：{html.escape(g["cannot_support"])}</p></section>')
    page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>论文图包 2026-10-15</title><style>body{max-width:1100px;margin:40px auto;padding:0 20px;font:16px/1.8 system-ui,sans-serif;color:#17202b;background:#f5f5f7}h1{font-size:34px}section{background:white;padding:28px;margin:30px 0;border:1px solid #e4e7eb;border-radius:16px}img{display:block;width:100%;height:auto}p{white-space:pre-wrap}.limit{color:#71552a}a{color:#066dd9}</style><h1>论文图包与科学图注</h1><p>2026-10-15 · 19组44文件 · 仅复制既有图 · 未重跑实验/推理</p><p>详细来源、批次、单位、统计限定见 <a href="FIGURE_CATALOG.md">FIGURE_CATALOG.md</a>；逐文件哈希见 <a href="FIGURE_PROVENANCE.csv">FIGURE_PROVENANCE.csv</a>。</p>'+''.join(cards)+'</html>'
    (OUT/"index.html").write_text(page,encoding="utf8")
    print(json.dumps({"figure_groups":len(G),"figure_files":len(files),"source_files":len(sources),"new_experiments":0,"new_inference":0,"new_training":0},ensure_ascii=False))

if __name__=="__main__":
    main()
