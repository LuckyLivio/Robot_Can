# v21 实验与交付报告

**小测试门槛未通过；保留候选和负结果，未进入大规模消融、开发或独立确认。**

本轮在完整实际v19上检查A：保留入口反馈并延长风险方向的重定位衔接，B：仅在实际PLACE启用积分制动。六组为本轮实际重跑的v19、v20、原预算候选，以及完整v19分别加A、B和A+B（完整v21）。实际v17仅作已存在的历史配对参考，本轮没有重跑。v19/A/B/A+B构成已知条件上的配对二因素2×2诊断。两个单项和组合均保留完整v19及全部继承配置，不能称为从v17单独新增一项。原预算组同样实际重跑，但未启用后来加入的持物保护，仅作成功数约束参考，不能整体回退采用。旧版本、权重与原始结果保留；本轮不训练、不写论文。

**静态证据的适用范围：** A完整保留原v19下降入口前三帧反馈，随后仅在远离或名义跨越目标的风险方向保留反馈；B复用v20的积分规则，但仅在实际模式与调用phase均为PLACE且held时启用。CARRY全部子段、terminal carry及已进入RELEASE的末帧沿用实际v19接口。末帧仍可携带之前B已实际提交的积分记忆；接口回退不等于新闭环整条轨迹与历史v19相同。二者只使用当前观测与已有控制历史，保留原比例项和一次速度阻尼。D2名义外推和目标带都是控制启发式，不能替代真实未来状态、几何认证或连续5帧到位。执行前静态检查只能证实公式、输入边界和保护机制，不能证明闭环提速或成功救回。 [A静态记录](analysis/transition_static_a.json) / [B静态记录](analysis/place_scope_static_b.json)。

## 约束与信息范围

400 控制步、20 Hz、D2 FIFO、最多两次抓取，规划和等待均计入总步数。路径阶段沿用9 mm/0.08 rad到位及5帧稳定；PLACE仍使用原物体位置、高度和阶段时钟释放判据，不能把路径的5帧规则套用于PLACE。保持0.04 rad局部IK关节余量；空手路径沿用1 mm手/箱、3 mm规划手/物体及1 mm执行手/物体间隙；持物路径的手/箱与所持物/箱均保留1 mm间隙，并保留原开度/位姿保护。闭合与释放时长不缩短。控制只使用当前观测、历史和当前关节，不使用接触、奖励、成功标签或未来状态。

## 已完成执行与门槛

| 阶段 | 实际 v19 | 实际 v20 | 原预算候选 | A · 重定位衔接 | B · 仅放置制动 | v21 · A+B | 结果及核验 |
|---|---:|---:|---:|---:|---:|---:|---|
| smoke_a | 2/9 | 3/9 | 7/9 | 2/9 | 2/9 | 2/9 | 结果门槛未通过 |

完整阶段累计 **54 次闭环执行**。不同修订与变体共享诊断条件；不得将这些执行数解释为独立起点数或合并成总体成功率。

**小测试的9个条件不等于9个独立起点。** 其中8个为原标准条件，另1个是复用 demo6000005 的 clearance-only 父配置 profile。该专用 profile 在六组中按登记的继承配置配对，用于检查预算退步；图表将它单列。单轮小测试54次按预定顺序分为36次与18次两批，同一锁定实现且不得批间改动；全部54次完成才形成阶段结论。后续消融564次、开发v19/v20/v21各240次合计720次、独立确认v6/v20/v21各480次合计1440次；只有实际完成并核验的记录才计入成果。

| 后续阶段 | 预定本轮执行数 | 完整执行数 | 状态 |
|---|---:|---:|---|
| 已知条件消融 | 564 | 0 | 未运行 |
| 开发对照 | 720 | 0 | 未运行 |
| 独立确认 | 1440 | 0 | 未运行 |

**小测试失败后，564次消融、720次开发对照（v19/v20/v21各240）及1440次独立确认均未运行。** 计划文件或运行入口的存在不代表实验已执行，也没有独立确认支持采用v21。

## 最新小测试：三项目标逐项核对

| 目标 / profile | 实际 v19 | 实际 v20 | 原预算候选 | A · 重定位衔接 | B · 仅放置制动 | v21 · A+B |
|---|---|---|---|---|---|---|
| 斜靠抓取后搬运 / demo_13000021 | [未完成，400步](smoke_a/v19_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v20_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/budget_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/recenter_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/place_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v21_known13_bc_k2_noise005_demo_13000021/result.json) |
| 箱沿分段接近 / demo_13000022 | [未完成，400步](smoke_a/v19_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v20_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/budget_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/recenter_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/place_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v21_known13_full_s41_noise005_demo_13000022/result.json) |
| 预算专用 profile / demo_6000005 | [未完成，400步](smoke_a/v19_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/v20_clearance_profile_6000005/result.json) | [成功，382步](smoke_a/budget_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/recenter_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/place_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/v21_clearance_profile_6000005/result.json) |

原v14失败目标的完成数：0 / 3。预算profile已在v15和预算候选中成功，不能把重复完成说成相对这些版本的新救回。只有整回合成功才计作完成，抓住、抬起、路径证书通过或局部误差变小都不能替代这个判据。

- 相对 v19 的已配对成功退步：0；配对覆盖 9 个条件。
- 相对 v20 的已配对成功退步：1；配对覆盖 9 个条件。 条件：known_full_s23_clean_demo_12000036/demo_12000036。
- 相对 budget 的已配对成功退步：5；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v18 的已配对成功退步：0；配对覆盖 9 个条件。
- 相对 v17 的已配对成功退步：1；配对覆盖 9 个条件。 条件：known_full_s23_clean_demo_12000036/demo_12000036。
- 相对 v16 的已配对成功退步：0；配对覆盖 9 个条件。
- 相对 v15 的已配对成功退步：2；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；clearance_profile_6000005/demo_6000005。
- 相对 v14 的已配对成功退步：4；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021。
- 相对 v13 的已配对成功退步：5；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v6 的已配对成功退步：7；配对覆盖 8 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；known13_bc_k2_noise005_demo_13000021/demo_13000021；known13_full_s41_noise005_demo_13000022/demo_13000022；clearance_profile_6000005/demo_6000005。

## 全部小测试条件（保留失败）

| 条件 / 配置 | 实际 v19 | 实际 v20 | 原预算候选 | A · 重定位衔接 | B · 仅放置制动 | v21 · A+B |
|---|---|---|---|---|---|---|
| regression_6000005 / standard | [未完成 · 400步](smoke_a/v19_regression_6000005/result.json) | [未完成 · 400步](smoke_a/v20_regression_6000005/result.json) | [成功 · 383步](smoke_a/budget_regression_6000005/result.json) | [未完成 · 400步](smoke_a/recenter_regression_6000005/result.json) | [未完成 · 400步](smoke_a/place_regression_6000005/result.json) | [未完成 · 400步](smoke_a/v21_regression_6000005/result.json) |
| known_side_s17 / standard | [成功 · 341步](smoke_a/v19_known_side_s17/result.json) | [成功 · 341步](smoke_a/v20_known_side_s17/result.json) | [成功 · 299步](smoke_a/budget_known_side_s17/result.json) | [成功 · 341步](smoke_a/recenter_known_side_s17/result.json) | [成功 · 341步](smoke_a/place_known_side_s17/result.json) | [成功 · 341步](smoke_a/v21_known_side_s17/result.json) |
| held_wait_demo87 / standard | [成功 · 282步](smoke_a/v19_held_wait_demo87/result.json) | [成功 · 282步](smoke_a/v20_held_wait_demo87/result.json) | [成功 · 264步](smoke_a/budget_held_wait_demo87/result.json) | [成功 · 282步](smoke_a/recenter_held_wait_demo87/result.json) | [成功 · 282步](smoke_a/place_held_wait_demo87/result.json) | [成功 · 282步](smoke_a/v21_held_wait_demo87/result.json) |
| known_bc_k2_clean_demo_12000011 / standard | [未完成 · 400步](smoke_a/v19_known_bc_k2_clean_demo_12000011/result.json) | [未完成 · 400步](smoke_a/v20_known_bc_k2_clean_demo_12000011/result.json) | [成功 · 295步](smoke_a/budget_known_bc_k2_clean_demo_12000011/result.json) | [未完成 · 400步](smoke_a/recenter_known_bc_k2_clean_demo_12000011/result.json) | [未完成 · 400步](smoke_a/place_known_bc_k2_clean_demo_12000011/result.json) | [未完成 · 400步](smoke_a/v21_known_bc_k2_clean_demo_12000011/result.json) |
| known_full_s23_clean_demo_12000036 / standard | [未完成 · 400步](smoke_a/v19_known_full_s23_clean_demo_12000036/result.json) | [成功 · 400步](smoke_a/v20_known_full_s23_clean_demo_12000036/result.json) | [成功 · 340步](smoke_a/budget_known_full_s23_clean_demo_12000036/result.json) | [未完成 · 400步](smoke_a/recenter_known_full_s23_clean_demo_12000036/result.json) | [未完成 · 400步](smoke_a/place_known_full_s23_clean_demo_12000036/result.json) | [未完成 · 400步](smoke_a/v21_known_full_s23_clean_demo_12000036/result.json) |
| known_full_s23_noise005_demo_12000021 / standard | [未完成 · 400步](smoke_a/v19_known_full_s23_noise005_demo_12000021/result.json) | [未完成 · 400步](smoke_a/v20_known_full_s23_noise005_demo_12000021/result.json) | [成功 · 377步](smoke_a/budget_known_full_s23_noise005_demo_12000021/result.json) | [未完成 · 400步](smoke_a/recenter_known_full_s23_noise005_demo_12000021/result.json) | [未完成 · 400步](smoke_a/place_known_full_s23_noise005_demo_12000021/result.json) | [未完成 · 400步](smoke_a/v21_known_full_s23_noise005_demo_12000021/result.json) |
| known13_bc_k2_noise005_demo_13000021 / standard | [未完成 · 400步](smoke_a/v19_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成 · 400步](smoke_a/v20_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成 · 400步](smoke_a/budget_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成 · 400步](smoke_a/recenter_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成 · 400步](smoke_a/place_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成 · 400步](smoke_a/v21_known13_bc_k2_noise005_demo_13000021/result.json) |
| known13_full_s41_noise005_demo_13000022 / standard | [未完成 · 400步](smoke_a/v19_known13_full_s41_noise005_demo_13000022/result.json) | [未完成 · 400步](smoke_a/v20_known13_full_s41_noise005_demo_13000022/result.json) | [未完成 · 400步](smoke_a/budget_known13_full_s41_noise005_demo_13000022/result.json) | [未完成 · 400步](smoke_a/recenter_known13_full_s41_noise005_demo_13000022/result.json) | [未完成 · 400步](smoke_a/place_known13_full_s41_noise005_demo_13000022/result.json) | [未完成 · 400步](smoke_a/v21_known13_full_s41_noise005_demo_13000022/result.json) |
| clearance_profile_6000005 / clearance_only_parent | [未完成 · 400步](smoke_a/v19_clearance_profile_6000005/result.json) | [未完成 · 400步](smoke_a/v20_clearance_profile_6000005/result.json) | [成功 · 382步](smoke_a/budget_clearance_profile_6000005/result.json) | [未完成 · 400步](smoke_a/recenter_clearance_profile_6000005/result.json) | [未完成 · 400步](smoke_a/place_clearance_profile_6000005/result.json) | [未完成 · 400步](smoke_a/v21_clearance_profile_6000005/result.json) |

## 具体失败原因与下一步

### 本轮小测试未达门槛，v21不采用

六组各9个已知条件的成功数为实际v19 2、实际v20 3、原预算7、A重定位衔接2、B仅PLACE 2、完整v21 2。没有新增成功，12000036未保留实际v20的成功；三个预登记目标仍未完成。54次物理执行共20255步，9个条件复用8个物理起点。原预算本轮实际重跑但保护不同，不能凭7/9整体采用。另10条原输入重定位回放共4000步仅验证原轨迹与谓词，不增加实验分母。

**下一步方案：** 按原门槛停止564次扩展、720次开发及1440次独立确认；保留全部版本与本轮失败证据，不做泛化训练。后续仅按已定位瓶颈建立独立候选，重新通过小测试后才恢复大规模阶段。

依据：[smoke_a.json](analysis/smoke_a.json) / [control_conclusions_a.json](analysis/control_conclusions_a.json) / [smoke_a_recenter_diagnosis.json](analysis/smoke_a_recenter_diagnosis.json) / [development_gate.json](validation/development_gate.json)

### A恢复了重定位五帧，但没有提前进入搬运

6000005两配置的A/完整组在300–302步与实际v19具有相同观测、D2队列和逐位相同命令；首次命令差在304步，首次观测差在307步。精确原输入回放确认，A/完整组和v19均在316–320连续5帧满足原重定位全部条件，320步退出；实际v20仅出现4帧，335步年龄25超过24而撤回。A在320步侧误差7.077mm、固定回中心距离7.890mm，均小于9mm。重定位相关帧（含规划/退出）为v19/place 10、v20 25、A/v21 9；纯PATH_RECENTER命令分别9、23、8。A晚一控制进入重定位、仍同在320步完成，因此少一相关帧不等于任务净省一步；各新组仍328步CLOSE、362步CARRY。

**下一步方案：** 保留前三步原反馈作为必要对照，继续使用原9mm、5帧、24步与D2。A可以作为恢复已知重定位进展的候选，但当前证据不支持整体采用或宣称已提高成功率。后续优先处理搬运稳定性和完整阶段预算。

依据：[smoke_a_handoff_diagnosis.json](analysis/smoke_a_handoff_diagnosis.json) / [smoke_a_recenter_diagnosis.json](analysis/smoke_a_recenter_diagnosis.json) / [control_conclusions_a.json](analysis/control_conclusions_a.json)

### 6000005的瓶颈转到搬运稳定与剩余预算

A/完整组在364–400执行直接搬运，严格到位区间为387–389三帧、397–400四帧；最大连续帧数由v19的3提高到4，400步位置误差6.084→2.595mm、角误差0.03321→0.02583rad，但仍未满5帧、没有进入PLACE。两配置共享同一物理起点，不能当成两个独立新救回。B严格仅PLACE，在这两配置从未被调用。即使下一步能达到第五帧，也仍有PLACE和RELEASE，不能说整回合只差一步成功，更不能假设400步之后会持续到位。

**下一步方案：** 下一候选应提前获得稳定的五帧并为PLACE/RELEASE留出预算：先检查末段实测速度、积分和在途D2命令与出入9mm球的关系，再做独立局部消融。保持400步和原全部阈值，不延长回合、不减少确认帧。

依据：[smoke_a_handoff_diagnosis.json](analysis/smoke_a_handoff_diagnosis.json) / [control_conclusions_a.json](analysis/control_conclusions_a.json)

### 只把B放进PLACE没有复现v20的一步释放收益

12000036中A与v19的400步命令及状态完全相同。B/完整组与v19直到382步保持相同输入轨迹，383步才首次命令不同、386步才首次观测不同；但均391步进入RELEASE，392步提交开爪、D2后394步首次执行，截至400步7次已执行开爪，均失败。实际v20仍390/391/393，尾部8次且400步成功。虽然v19/v20/A/B/完整组均CARRY277、PLACE363及搬运段5/17/55步相同，实际v20与完整v21在PLACE入口EEF位置已差2.630mm、物体位置差2.679mm。390步B/完整组物体高度0.900665m，尚未满足原<0.900m；实际v20为0.899141m，已经满足。B/完整组391步输出标签仍PLACE但实际模式已RELEASE，正确回到父版；该尾帧回退发生在当前释放判据通过之后，不能倒推成390步高度不达标的原因。

**下一步方案：** 不要把旧成功简单归因于一个可独立移植的PLACE开关。下一步先对齐并检查PLACE入口位姿、实测速度、抓持相对位姿及在途命令，分别隔离搬运末段与PLACE作用范围；只有经过同条件闭环对照才能判断尾帧规则或控制状态的因果作用。

依据：[control_conclusions_a.json](analysis/control_conclusions_a.json) / [smoke_a_handoff_diagnosis.json](analysis/smoke_a_handoff_diagnosis.json) / [trace.jsonl](smoke_a/place_known_full_s23_clean_demo_12000036/trace.jsonl) / [trace.jsonl](smoke_a/v20_known_full_s23_clean_demo_12000036/trace.jsonl)

### B范围收窄消除了旧搬运退步，但12000011仍太晚

12000011的v19/v20/A/B/完整组第一次220步进入CARRY，首次转向241–310持续70步未到位，311步保护后312步再次进入CARRY。v19/A/B/完整组第二次规划后321–325执行clearance、326–335执行reorient、336–395执行transport，396才进入PLACE；实际v20相应为10/13/57步，400步仍在transport。B单项在此例的整段命令和状态与v19逐位相同，396–400仅5次PLACE提案，积分制动规则没有触发。完整组也未释放，故这是保留父版搬运进度，不能称为任务成功修复。本轮B单项和完整组各92次PLACE提案均实际提交，各27次触发新积分规则；均限实际mode=PLACE且held，未扩散到CARRY或已进入RELEASE的末帧。

**下一步方案：** 优先解决首次大转向长期不收敛和第二次搬运所消耗的预算，保留原关节、相对位姿、几何、70步阶段限制及400步总预算。PLACE范围收窄可保留为消融条件，但当前没有净成功收益，不能单独推荐采用。

依据：[smoke_a_handoff_diagnosis.json](analysis/smoke_a_handoff_diagnosis.json) / [control_conclusions_a.json](analysis/control_conclusions_a.json)

### 另外两个预登记目标仍由上游问题限制

13000021在v19/v20/A/B/完整组仍332步进入CARRY，336步首次路径未确认后重试，337步再次进入CARRY，341步耗尽尝试。13000022的v19/v20/A/B/完整组仍387步才进入DESCEND，截至400步仍PATH_RECENTER，尚未搬运。局部搜索未确认不等于物理不可达；下游PLACE制动也无法解决未进入PLACE的轨迹。本文的持物位姿五帧统计适用于CARRY路径；EDGE与recenter也各自保留原五帧，PLACE释放继续使用原物体XY、高度及年龄条件。

**下一步方案：** 后续把有界路径验证与箱沿接近耗时分开定位，沿用源绑定原轨迹、真实失败条件与相同保护进行小消融。先处理这些阶段性否决项，再考虑扩大测试；当前不写论文、不做泛化训练。

依据：[smoke_a_handoff_diagnosis.json](analysis/smoke_a_handoff_diagnosis.json) / [smoke_a_handoff_diagnosis.csv](analysis/smoke_a_handoff_diagnosis.csv) / [control_conclusions_a.json](analysis/control_conclusions_a.json)


## 核验与证据边界

- 保存输入动作/FIFO/噪声核验：已通过记录合计 20,255 控制步。
- 物理回放：已通过记录合计 54 回合、20,255 步；不增加统计样本。
- 每一轮源代码快照和结果保留；本报告校验快照哈希并从原始result重新核对成功数与分析汇总。
- 关闭开关一致性、静态几何/IK、完整决策回放、物理回放是不同验证范围，不能相互替代。

最新阶段A实际控制212次，入口窗口42次、窗口之后170次；轴向反馈56次、横向反馈132次。方向标记可在同一控制重叠，不能相加成独立控制数。B实际PLACE范围内提案184次、实际提交184次；其中积分规则触发54次、实际提交54次。范围提案数与积分触发数不同，不能相加。未触发分支只能引用对应静态或组件检查。本轮混合几何拒绝0次、父保护替换0次；负路径测试不等于在真实闭环中触发。

- [components_a.json](analysis/components_a.json)：通过；源哈希与当前版本一致；v21 integration with saved v19 final-descent state and explicit geometry/predicate stubs. Independent helper static and subsequent physical/decision gates are still required.
- [mechanisms_a.json](analysis/mechanisms_a.json)：通过；源哈希与当前版本一致；Two new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [place_scope_static_a.json](analysis/place_scope_static_a.json)：通过；历史诊断，不能作为当前源码的通过凭证；Actual V21.propose17 invoked on saved actual-v19 observations and parent committed memory; no choose/state-machine or physics replay.
- [place_scope_static_b.json](analysis/place_scope_static_b.json)：通过；源哈希与当前版本一致；Actual V21.propose17 invoked on saved actual-v19 observations and parent committed memory; no choose/state-machine or physics replay.
- [transition_static_a.json](analysis/transition_static_a.json)：通过；源哈希与当前版本一致；Saved-input helper proposals and synthetic mathematical/geometry negatives only; no new closed-loop evaluation.

早期B静态a记录保留，并有[元数据补充前的精确源码快照](validation/pre_metadata_snapshot/receipt.json)，快照逐字节匹配原a回执哈希；这是旧源追溯，不是重跑，也不能替代当前源码绑定的b回执。

图表为真实数据的分类计数或目标矩阵，输出600 dpi PNG及矢量PDF/SVG，附CSV和来源SHA-256。没有平滑、没有把任意案例排序连成折线，也没有给已挑选小测试附加泛化置信区间。图片实际外观、PDF字体、前端显示、链接与Git同步须由交付验证另行确认；生成文件本身不等于这些检查已经通过。

## 整体评估

本轮可以形成可追溯的实现、组件对照与失败分析材料，能够补充本科毕业设计。是否达到学校或导师的正式毕业标准，仍需按实际要求审定。历史项目证据没有被本轮替换；若本轮门槛未过，只能把v21作为探索和负结果，不能作为已确认的新增性能成果。

仍需区分局部规划可行与实际执行完成、共享恢复贡献与世界模型独有贡献，以及已知诊断条件和独立确认。不应宣称项目完美、总体优于强基线或已获得完整机械臂安全保证。

## 复核入口

- [执行前协议](protocols/PLAN.md)
- [机器可读汇总](SUMMARY.json)
- [前端证据页](index.html)
- [图表来源目录](figures/CATALOG.json)
- [v19原报告](../improvement_v19_20261019_01/REPORT.md)
- [v20前轮报告](../improvement_v20_20261019_01/REPORT.md)
- [v14既有历史演示](../improvement_v14_20261016_01/index.html#demo)

本轮页面没有新增或冒用机器人视频；上面的演示链接明确指向v14历史记录。
- [smoke_a原始分析](analysis/smoke_a.json) / [作业条件](smoke_a/jobs.json)

每份机制/静态检查仅对应其记录的源哈希；以实际阶段快照和逐步核验确认受测源码，不把早期检查的通过自动转移到后续修订。
