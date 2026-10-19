# v20 实验与交付报告

**小测试门槛未通过；保留候选和负结果，未进入大规模消融、开发或独立确认。**

本轮在完整实际v19上检查A：按方向分解下降衔接，B：持物目标带内的延迟制动与积分保持。六组为本轮实际重跑的v17、v19、原预算候选，以及完整v19分别加A、B和A+B（完整v20）。v19/A/B/A+B构成已知条件上的配对二因素2×2诊断。两个单项和组合均保留完整v19及全部继承配置，不能称为从v17单独新增一项。原预算组同样实际重跑，但未启用后来加入的持物保护，仅作成功数约束参考，不能整体回退采用。旧版本、权重与原始结果保留；本轮不训练、不写论文。

**静态证据的适用范围：** A按规划抓取轴拆分正常进展和必要横向制动；B在持物目标带中暂停或清除满足条件的积分，保留原比例项和一次速度阻尼。二者只使用当前观测与已有控制历史。D2名义外推和目标带都是控制启发式，不能替代真实未来状态、几何认证或连续5帧到位。执行前静态检查只能证实公式、输入边界和保护机制，不能证明闭环提速或成功救回。 [A静态记录](analysis/transition_static_a.json) / [B静态记录](analysis/settling_static_a.json)。

## 约束与信息范围

400 控制步、20 Hz、D2 FIFO、最多两次抓取，规划和等待均计入总步数。路径阶段沿用9 mm/0.08 rad到位及5帧稳定；PLACE仍使用原物体位置、高度和阶段时钟释放判据，不能把路径的5帧规则套用于PLACE。保持0.04 rad局部IK关节余量、1 mm手/箱路径、3 mm规划手/物体、1 mm执行手/物体及原开度/位姿保护。闭合与释放时长不缩短。控制只使用当前观测、历史和当前关节，不使用接触、奖励、成功标签或未来状态。

## 已完成执行与门槛

| 阶段 | 实际 v17 | 实际 v19 | 原预算候选 | A · 方向衔接 | B · 延迟制动 | v20 · A+B | 结果及核验 |
|---|---:|---:|---:|---:|---:|---:|---|
| smoke_a | 3/9 | 2/9 | 7/9 | 2/9 | 3/9 | 3/9 | 结果门槛未通过 |

完整阶段累计 **54 次闭环执行**。不同修订与变体共享诊断条件；不得将这些执行数解释为独立起点数或合并成总体成功率。

**小测试的9个条件不等于9个独立起点。** 其中8个为原标准条件，另1个是复用 demo6000005 的 clearance-only 父配置 profile。该专用 profile 在六组中按登记的继承配置配对，用于检查预算退步；图表将它单列。单轮小测试54次、后续消融564次、开发v17/v19/v20各240次合计720次、独立确认1440次；只有实际完成并核验的记录才计入成果。

| 后续阶段 | 预定本轮执行数 | 完整执行数 | 状态 |
|---|---:|---:|---|
| 已知条件消融 | 564 | 0 | 未运行 |
| 开发对照 | 720 | 0 | 未运行 |
| 独立确认 | 1440 | 0 | 未运行 |

**小测试失败后，564次消融、720次开发对照（v17/v19/v20各240）及1440次独立确认均未运行。** 计划文件或运行入口的存在不代表实验已执行，也没有独立确认支持采用v20。

## 最新小测试：三项目标逐项核对

| 目标 / profile | 实际 v17 | 实际 v19 | 原预算候选 | A · 方向衔接 | B · 延迟制动 | v20 · A+B |
|---|---|---|---|---|---|---|
| 斜靠抓取后搬运 / demo_13000021 | [未完成，400步](smoke_a/v17_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v19_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/budget_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/directional_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/braking_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v20_known13_bc_k2_noise005_demo_13000021/result.json) |
| 箱沿分段接近 / demo_13000022 | [未完成，400步](smoke_a/v17_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v19_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/budget_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/directional_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/braking_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v20_known13_full_s41_noise005_demo_13000022/result.json) |
| 预算专用 profile / demo_6000005 | [未完成，400步](smoke_a/v17_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/v19_clearance_profile_6000005/result.json) | [成功，382步](smoke_a/budget_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/directional_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/braking_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/v20_clearance_profile_6000005/result.json) |

原v14失败目标的完成数：0 / 3。预算profile已在v15和预算候选中成功，不能把重复完成说成相对这些版本的新救回。只有整回合成功才计作完成，抓住、抬起、路径证书通过或局部误差变小都不能替代这个判据。

- 相对 v17 的已配对成功退步：0；配对覆盖 9 个条件。
- 相对 v19 的已配对成功退步：0；配对覆盖 9 个条件。
- 相对 budget 的已配对成功退步：4；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v18 的已配对成功退步：0；配对覆盖 9 个条件。
- 相对 v16 的已配对成功退步：0；配对覆盖 9 个条件。
- 相对 v15 的已配对成功退步：2；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；clearance_profile_6000005/demo_6000005。
- 相对 v14 的已配对成功退步：3；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_noise005_demo_12000021/demo_12000021。
- 相对 v13 的已配对成功退步：4；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v6 的已配对成功退步：6；配对覆盖 8 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_noise005_demo_12000021/demo_12000021；known13_bc_k2_noise005_demo_13000021/demo_13000021；known13_full_s41_noise005_demo_13000022/demo_13000022；clearance_profile_6000005/demo_6000005。

## 全部小测试条件（保留失败）

| 条件 / 配置 | 实际 v17 | 实际 v19 | 原预算候选 | A · 方向衔接 | B · 延迟制动 | v20 · A+B |
|---|---|---|---|---|---|---|
| regression_6000005 / standard | [未完成 · 400步](smoke_a/v17_regression_6000005/result.json) | [未完成 · 400步](smoke_a/v19_regression_6000005/result.json) | [成功 · 383步](smoke_a/budget_regression_6000005/result.json) | [未完成 · 400步](smoke_a/directional_regression_6000005/result.json) | [未完成 · 400步](smoke_a/braking_regression_6000005/result.json) | [未完成 · 400步](smoke_a/v20_regression_6000005/result.json) |
| known_side_s17 / standard | [成功 · 342步](smoke_a/v17_known_side_s17/result.json) | [成功 · 341步](smoke_a/v19_known_side_s17/result.json) | [成功 · 299步](smoke_a/budget_known_side_s17/result.json) | [成功 · 341步](smoke_a/directional_known_side_s17/result.json) | [成功 · 341步](smoke_a/braking_known_side_s17/result.json) | [成功 · 341步](smoke_a/v20_known_side_s17/result.json) |
| held_wait_demo87 / standard | [成功 · 300步](smoke_a/v17_held_wait_demo87/result.json) | [成功 · 282步](smoke_a/v19_held_wait_demo87/result.json) | [成功 · 264步](smoke_a/budget_held_wait_demo87/result.json) | [成功 · 282步](smoke_a/directional_held_wait_demo87/result.json) | [成功 · 282步](smoke_a/braking_held_wait_demo87/result.json) | [成功 · 282步](smoke_a/v20_held_wait_demo87/result.json) |
| known_bc_k2_clean_demo_12000011 / standard | [未完成 · 400步](smoke_a/v17_known_bc_k2_clean_demo_12000011/result.json) | [未完成 · 400步](smoke_a/v19_known_bc_k2_clean_demo_12000011/result.json) | [成功 · 295步](smoke_a/budget_known_bc_k2_clean_demo_12000011/result.json) | [未完成 · 400步](smoke_a/directional_known_bc_k2_clean_demo_12000011/result.json) | [未完成 · 400步](smoke_a/braking_known_bc_k2_clean_demo_12000011/result.json) | [未完成 · 400步](smoke_a/v20_known_bc_k2_clean_demo_12000011/result.json) |
| known_full_s23_clean_demo_12000036 / standard | [成功 · 400步](smoke_a/v17_known_full_s23_clean_demo_12000036/result.json) | [未完成 · 400步](smoke_a/v19_known_full_s23_clean_demo_12000036/result.json) | [成功 · 340步](smoke_a/budget_known_full_s23_clean_demo_12000036/result.json) | [未完成 · 400步](smoke_a/directional_known_full_s23_clean_demo_12000036/result.json) | [成功 · 400步](smoke_a/braking_known_full_s23_clean_demo_12000036/result.json) | [成功 · 400步](smoke_a/v20_known_full_s23_clean_demo_12000036/result.json) |
| known_full_s23_noise005_demo_12000021 / standard | [未完成 · 400步](smoke_a/v17_known_full_s23_noise005_demo_12000021/result.json) | [未完成 · 400步](smoke_a/v19_known_full_s23_noise005_demo_12000021/result.json) | [成功 · 377步](smoke_a/budget_known_full_s23_noise005_demo_12000021/result.json) | [未完成 · 400步](smoke_a/directional_known_full_s23_noise005_demo_12000021/result.json) | [未完成 · 400步](smoke_a/braking_known_full_s23_noise005_demo_12000021/result.json) | [未完成 · 400步](smoke_a/v20_known_full_s23_noise005_demo_12000021/result.json) |
| known13_bc_k2_noise005_demo_13000021 / standard | [未完成 · 400步](smoke_a/v17_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成 · 400步](smoke_a/v19_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成 · 400步](smoke_a/budget_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成 · 400步](smoke_a/directional_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成 · 400步](smoke_a/braking_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成 · 400步](smoke_a/v20_known13_bc_k2_noise005_demo_13000021/result.json) |
| known13_full_s41_noise005_demo_13000022 / standard | [未完成 · 400步](smoke_a/v17_known13_full_s41_noise005_demo_13000022/result.json) | [未完成 · 400步](smoke_a/v19_known13_full_s41_noise005_demo_13000022/result.json) | [未完成 · 400步](smoke_a/budget_known13_full_s41_noise005_demo_13000022/result.json) | [未完成 · 400步](smoke_a/directional_known13_full_s41_noise005_demo_13000022/result.json) | [未完成 · 400步](smoke_a/braking_known13_full_s41_noise005_demo_13000022/result.json) | [未完成 · 400步](smoke_a/v20_known13_full_s41_noise005_demo_13000022/result.json) |
| clearance_profile_6000005 / clearance_only_parent | [未完成 · 400步](smoke_a/v17_clearance_profile_6000005/result.json) | [未完成 · 400步](smoke_a/v19_clearance_profile_6000005/result.json) | [成功 · 382步](smoke_a/budget_clearance_profile_6000005/result.json) | [未完成 · 400步](smoke_a/directional_clearance_profile_6000005/result.json) | [未完成 · 400步](smoke_a/braking_clearance_profile_6000005/result.json) | [未完成 · 400步](smoke_a/v20_clearance_profile_6000005/result.json) |

## 具体失败原因与下一步

### 局部收益来自B，完整v20尚未达标

六组各9个已知条件的成功数依次为v17 3、v19 2、原预算7、A 2、B 3、完整v20 3。B与组合均救回12000036并保留本轮v17/v19成功案例；三个预登记目标仍全部未完成，也未满足所有历史参考零退步要求。原预算保护不同，不能直接采用。54次执行共用8个物理起点，这不是项目总体成功率或独立泛化结果。

**下一步方案：** 保留B单项作为待验证候选；完整v20不采用，按执行前门槛停止564次扩展、各240次开发和独立确认。

依据：[smoke_a.json](analysis/smoke_a.json) / [smoke_a_pairs.csv](analysis/smoke_a_pairs.csv) / [development_gate.json](validation/development_gate.json)

### A的动态衔接未稳住原重定位过程

6000005两配置在v19第328步进入CLOSE、第362步进入CARRY；A与组合则在335步因重定位超时撤回，400步仍为EDGE_APPROACH。第300步首次命令差异发生在相同状态：轴向误差80.828mm、运动−0.849mm/步，新规则未用轴向或横向阻尼；真实D2使第303步才首次出现观测差异。A前11次下降提案全部通过原混合几何保护，但recenter共23步而v19为9步。精确旧输入回放确认v19在316–320连续5帧到位，A只有316–319四帧；320步侧误差9.128mm、固定回中心距离9.604mm超出原9mm，角度、路径间隙和开度仍合格，335步recenter_age=25超过原24。此处是抓持进展回退，两配置在v19本来也失败，不能夸大成新增成功转失败。

**下一步方案：** 先保留v19衔接作为对照，单独验证轴向远离时保留原反馈、重定位进入状态与D2剩余运动的关系。不得放宽9mm、5帧或24步，也不能把同一保存输入上的方向判断当作动态稳定证明。

依据：[transition_diagnosis_a.json](analysis/transition_diagnosis_a.json) / [transition_diagnosis_a.csv](analysis/transition_diagnosis_a.csv) / [recenter_predicates_a.json](analysis/recenter_predicates_a.json)

### B救回12000036，但没有加快搬运段

v19/A与B/组合均在277步进入CARRY、363步进入PLACE，三个搬运段仍为5/17/55步。B与组合把RELEASE事件从391提前到390，首次提交开爪392→391、经过真实D2后的首次执行394→393；截至400步实际开爪由7次变8次，并在400步获得任务成功。原PLACE释放判据未改，不能把该变化说成放宽路径5帧标准。demo87在v19/A/B/组合中均为282步成功，无步数收益。

**下一步方案：** 单独保留终端放置阶段的B候选，并核对PLACE和RELEASE所需剩余预算；这只证明当前已知案例的局部收益，尚不证明任意案例多一步即可成功。

依据：[smoke_a_control_findings.json](analysis/smoke_a_control_findings.json) / [smoke_a_control_diagnosis.json](analysis/smoke_a_control_diagnosis.json) / [transition_diagnosis_a.csv](analysis/transition_diagnosis_a.csv)

### 提前清积分仍不足以稳定保持，并有阶段耗时副作用

B在6000005于386/387步分别提前清x/z积分，旧版为388，但391步位置误差仍回到9.476mm，最大连续到位与v19同为3帧；400步末连续帧数2→3，仍未达5且未进入PLACE。A/组合在此例没有进入CARRY，B根本没有调用，不能把组合失败归因于B。12000011第二次搬运中，B/组合的clearance段5→10步、reorient段10→13步，400步仍在transport；v19/A已于396步进入PLACE，双方虽都失败，但B并非单调改善。B单项269次、组合229次新规则提案均实际提交；与旧settling19事件重叠74/64次，不能相加计独立控制次数。

**下一步方案：** 下一轮先做B仅作用于终端放置、CARRY保持父版的单项对照，防止每个路径节点都过早停止积分；同时保留12000011耗时和6000005完整搬运预算为约束，不能只优化最后几帧到位。

依据：[smoke_a_control_findings.json](analysis/smoke_a_control_findings.json) / [smoke_a_control_diagnosis.json](analysis/smoke_a_control_diagnosis.json)

### 另外两个预定目标仍受上游限制

13000021在各新组仍332步进入CARRY，两次有界候选搜索都未找到通过现有条件的路径。局部IK不收敛、可选候选未准入与名义时程不足均只表示此次搜索未确认，不能宣称物理不可达。13000022仍在387步进入DESCEND、388步才首次提交下降动作，没有进入搬运搜索，当前下游制动不能追回已经耗掉的接近时间。

**下一步方案：** 将搬运路线的局部IK/连续姿态验证与箱沿接近耗时分别定位，使用原成功轨迹作有条件参考；保持保护与400步预算。先完成这些局部否决项，再考虑新的大规模开发对照，不做泛化训练。

依据：[transition_diagnosis_a.json](analysis/transition_diagnosis_a.json) / [transition_diagnosis_a.csv](analysis/transition_diagnosis_a.csv) / [smoke_a_control_findings.json](analysis/smoke_a_control_findings.json)


## 核验与证据边界

- 保存输入动作/FIFO/噪声核验：已通过记录合计 20,274 控制步。
- 物理回放：已通过记录合计 54 回合、20,274 步；不增加统计样本。
- 每一轮源代码快照和结果保留；本报告校验快照哈希并从原始result重新核对成功数与分析汇总。
- 关闭开关一致性、静态几何/IK、完整决策回放、物理回放是不同验证范围，不能相互替代。

最新阶段A实际控制176次，其中横向制动90次、轴向制动0次；未触发分支只能引用对应静态或组件检查。B反馈调用1140次，新规则触发498次、实际提交498次。本轮混合几何拒绝0次、父保护替换0次；负路径测试不等于在真实闭环中触发。

- [components_a.json](analysis/components_a.json)：通过；源哈希与当前版本一致；v20 integration with saved v19 final-descent state and explicit geometry/predicate stubs. Independent helper static and subsequent physical/decision gates are still required.
- [mechanisms_a.json](analysis/mechanisms_a.json)：通过；源哈希与当前版本一致；Two new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [settling_static_a.json](analysis/settling_static_a.json)：通过；源哈希与当前版本一致；Exact reconstruction of frozen v19 held helper proposals, then changed proposals on those same saved observations and committed parent memory; synthetic boundary/guard/commit tests. No controller, clock, queue, settling-counter or physics execution.
- [transition_static_a.json](analysis/transition_static_a.json)：通过；源哈希与当前版本一致；Saved-input helper proposals and synthetic mathematical/geometry negatives only; no new closed-loop evaluation.

图表为真实数据的分类计数或目标矩阵，输出600 dpi PNG及矢量PDF/SVG，附CSV和来源SHA-256。没有平滑、没有把任意案例排序连成折线，也没有给已挑选小测试附加泛化置信区间。图片实际外观、PDF字体、前端显示、链接与Git同步须由交付验证另行确认；生成文件本身不等于这些检查已经通过。

## 整体评估

本轮可以形成可追溯的实现、组件对照与失败分析材料，能够补充本科毕业设计。是否达到学校或导师的正式毕业标准，仍需按实际要求审定。历史项目证据没有被本轮替换；若本轮门槛未过，只能把v20作为探索和负结果，不能作为已确认的新增性能成果。

仍需区分局部规划可行与实际执行完成、共享恢复贡献与世界模型独有贡献，以及已知诊断条件和独立确认。不应宣称项目完美、总体优于强基线或已获得完整机械臂安全保证。

## 复核入口

- [执行前协议](protocols/PLAN.md)
- [机器可读汇总](SUMMARY.json)
- [前端证据页](index.html)
- [图表来源目录](figures/CATALOG.json)
- [v19原报告](../improvement_v19_20261019_01/REPORT.md)
- [v14既有历史演示](../improvement_v14_20261016_01/index.html#demo)

本轮页面没有新增或冒用机器人视频；上面的演示链接明确指向v14历史记录。
- [smoke_a原始分析](analysis/smoke_a.json) / [作业条件](smoke_a/jobs.json)

每份机制/静态检查仅对应其记录的源哈希；以实际阶段快照和逐步核验确认受测源码，不把早期检查的通过自动转移到后续修订。
