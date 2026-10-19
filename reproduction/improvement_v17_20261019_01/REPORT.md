# v17 实验与交付报告

**小测试门槛未通过；保留候选和负结果，未进入大规模消融、开发或独立确认。**

本轮检查公共路径复用与短转向选择、箱沿位置收敛，以及持物指令变化和残差控制。七组为实际v15、完整v16、v15仅预算C、完整v16分别加路径/箱沿/持物单项修复，以及三项全开的v17。三个单项修复是在完整v16上增加；预算候选仍为原v15仅预算C。旧版本、权重与原始结果保留；本轮不训练、不写论文。

## 约束与信息范围

400 控制步、20 Hz、D2 FIFO、最多两次抓取，规划和等待均计入总步数。沿用9 mm/0.08 rad到位、5帧稳定、0.04 rad局部IK关节余量、1 mm手/箱路径、3 mm规划手/物体、1 mm执行手/物体及原开度/位姿保护。闭合与释放时长不缩短。控制只使用当前观测、历史和当前关节，不使用接触、奖励、成功标签或未来状态。

## 已完成执行与门槛

| 阶段 | 旧基线 v15 | 完整 v16 | v15 仅预算 C | v16 + 路径修复 | v16 + 箱沿修复 | v16 + 持物修复 | 完整 v17 | 结果及核验 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| smoke_a | 4/9 | 2/9 | 7/9 | 2/9 | 2/9 | 2/9 | 3/9 | 结果门槛未通过 |

完整阶段累计 **63 次闭环执行**。不同修订与变体共享诊断条件；不得将这些执行数解释为独立起点数或合并成总体成功率。

**小测试的9个条件不等于9个独立起点。** 其中8个为原标准条件，另1个是复用 demo6000005 的 clearance-only 父配置 profile。该专用 profile 在七组中使用相同继承配置，用于检查预算退步；图表将它单列。

| 后续阶段 | 预定本轮执行数 | 完整执行数 | 状态 |
|---|---:|---:|---|
| 已知条件消融 | 658 | 0 | 未运行 |
| 开发对照 | 720 | 0 | 未运行 |
| 独立确认 | 1440 | 0 | 未运行 |

**小测试失败后，658次消融、720次开发对照（v15/v16/v17各240）及1440次独立确认均未运行。** 计划文件或运行入口的存在不代表实验已执行，也没有独立确认支持采用v17。

## 最新小测试：三项目标逐项核对

| 目标 / profile | 旧基线 v15 | 完整 v16 | v15 仅预算 C | v16 + 路径修复 | v16 + 箱沿修复 | v16 + 持物修复 | 完整 v17 |
|---|---|---|---|---|---|---|---|
| 斜靠抓取后搬运 / demo_13000021 | [未完成，400步](smoke_a/v15_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v16_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/budget_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/route_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/edge_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/held_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v17_known13_bc_k2_noise005_demo_13000021/result.json) |
| 箱沿分段接近 / demo_13000022 | [未完成，400步](smoke_a/v15_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v16_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/budget_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/route_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/edge_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/held_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v17_known13_full_s41_noise005_demo_13000022/result.json) |
| 预算专用 profile / demo_6000005 | [成功，397步](smoke_a/v15_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/v16_clearance_profile_6000005/result.json) | [成功，382步](smoke_a/budget_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/route_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/edge_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/held_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/v17_clearance_profile_6000005/result.json) |

原v14失败目标的完成数：0 / 3。预算profile已在v15和预算候选中成功，不能把重复完成说成相对这些版本的新救回。只有整回合成功才计作完成，抓住、抬起、路径证书通过或局部误差变小都不能替代这个判据。

- 相对 v16 的已配对成功退步：0；配对覆盖 9 个条件。
- 相对 v15 的已配对成功退步：2；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；clearance_profile_6000005/demo_6000005。
- 相对 budget 的已配对成功退步：4；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v14 的已配对成功退步：3；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_noise005_demo_12000021/demo_12000021。
- 相对 v13 的已配对成功退步：4；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v6 的已配对成功退步：6；配对覆盖 8 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_noise005_demo_12000021/demo_12000021；known13_bc_k2_noise005_demo_13000021/demo_13000021；known13_full_s41_noise005_demo_13000022/demo_13000022；clearance_profile_6000005/demo_6000005。

## 具体失败原因与下一步

### 有局部改善，但完整 v17 未通过采用门槛

七组 v15 / v16 / 仅预算 C / 路径 / 箱沿 / 持物 / 完整 v17 的任务成功数为 4 / 2 / 7 / 2 / 2 / 2 / 3（各 9 个配置）。这些配置复用 8 个起点，不是新增的独立确认样本。完整 v17 比 v16 多完成 12000036，恰好在第 400 步成功；三项预登记目标仍未完成，并且 6000005 的两个配置退步于原 v15 和预算组。候选保留为负结果，不采用，不启动后续 658 / 720 / 1440 次实验。

**下一步方案：** 保留目前所有版本和结果。下一轮只在新目录登记一个可检验的窄改动，先消除目标失败和已有成功退步，再讨论规模更大的消融、开发与全新起点确认。

依据：[smoke_a.json](analysis/smoke_a.json) / [smoke_a_carry_diagnosis.json](analysis/smoke_a_carry_diagnosis.json)

### 箱沿：减少了独占开度等待，仍受旋转位置残差和下降跟踪限制

Full seed41 噪声起点 13000022 中，edge 与完整 v17 轨迹相同：第一次预平移在 189 步完成，比 v16 的 204 步提前 15 步，独占开度等待从 21 步降至 0。首次旋转仍耗满 70 步，259 步位置误差 14.601 mm、角误差 0.054542 rad，260 步超时。第二次在 387 步达到 3.525 mm、0.031295 rad，余隙 5.170 mm，并完成原五帧确认进入下降；398 步旧回正段的 hand-can 几何下界降为 -0.912 mm，被原 1 mm 保护拦截，最终停在 POSE_WAIT。证书通过不等于 D2 下实际轨迹必然跟踪到位。

**下一步方案：** 优先离线检查旋转时位置误差与已提交但尚未执行的 D2 指令，并为下降与回正的阶段交接保留同一动态参考。任何更改都应继续保持原 1 / 3 mm 余隙、9 mm / 0.08 rad 到位条件和五帧确认；不能以放宽门槛消除失败。

依据：[smoke_a_edge_diagnosis.json](analysis/smoke_a_edge_diagnosis.json) / [result.json](smoke_a/v17_known13_full_s41_noise005_demo_13000022/result.json)

### 6000005：前段省时被下降回正消耗，搬运启动仍太晚

标准与预算专用 6000005 配置中，edge / v17 的预平移由 v16 的 39 步降为 20 步，独占开度等待从 16 步降为 0；但下降阶段从 325–340 的 16 步变成 300–339 的 40 步。进入 CARRY 仅从 376 提前到 373，仍只剩很少预算。完整 v17 在 373 / 374 步两次预算停搜后 EXHAUSTED；原预算组分别在 383 / 382 步成功。这两个 profile 共享同一起点，不能计为两次独立泛化成功或失败。

**下一步方案：** 先解决接近结束到下降开始的控制连续性及回正耗时，再验证剩余预算估计。不要简单继续早停或缩短原闭合、释放、稳定确认时间，也不要增加 400 步预算。

依据：[smoke_a_edge_diagnosis.json](analysis/smoke_a_edge_diagnosis.json) / [smoke_a_carry_diagnosis.json](analysis/smoke_a_carry_diagnosis.json)

### 搬运：缓存实际收益有限，末段误差和部分失抓仍存在

本轮 23 次实际 v17 路径搜索出现 6 次 IK 缓存命中、2 次几何命中，累计只避免 2 个 IK 工作单元，current_exact 短路线未选中；静态合成探针的 94 work 不能作为真实闭环收益。13000021 的 held 单项仅把重定向从 41 步减为 40 步，400 步仍距搬运目标 324.534 mm；完整 v17 又因接近较慢，在 CARRY 332 步开始后预算不足。12000021 的完整版本始终保持抓持，但 400 步末端误差仍为 10.22 mm，未达 9 mm 五帧确认；route / held 单项在该条件仍失抓。

**下一步方案：** 先按真实目标距离、旋转幅度和闭合 / 释放固定成本检查预算模型，再研究更短且完整认证的持物路线；拒绝没有达到到位条件的提前放置。持物变化限幅需要配对轨迹证据，不能因为单例未失抓就称为问题已解决。

依据：[smoke_a_carry_diagnosis.json](analysis/smoke_a_carry_diagnosis.json) / [smoke_a_edge_diagnosis.json](analysis/smoke_a_edge_diagnosis.json)

### 旧预算组成功数较高，不能据此整体回退

仅预算 C 的 7 / 9 是任务成功记录，该组未启用后来加入的实时持物路径保护。成功的 12000011 在 CARRY / PLACE 分别有 31 / 17 帧关节余量低于 0.04 rad，最小 -0.001626 rad；12000021 的 PLACE 有 4 帧低于该阈值，最小 0.006468 rad。6000005 两配置的 CARRY / PLACE / RELEASE 最小余量约 0.396 / 0.399 rad，可以作为局部轨迹参考，但仍不能据此声称完整几何或全臂安全已证明。12000036 的低余量仅发生于 RELEASE，应与当前持物保护适用阶段区分。

**下一步方案：** 仅提取 6000005 等满足局部保护条件的路线特点，在相同现行保护下重新验证；不整体关闭后来加入的保护来追求更高成功数。

依据：[smoke_a_budget_reference.json](analysis/smoke_a_budget_reference.json)

### 一致性审计通过，效果门槛与实时性仍需分别判断

63 次执行、23934 控制步的动作审计与独立物理回放均通过。箱沿与搬运专项只读诊断额外重放 28 次已保存执行的 11159 控制步，动作、D2 队列、噪声与事件一致，新增物理样本为 0。全量动作审计记录 200 个全开度包络控制步、2551 个 v17 已提交证书动作和 135 个 v17 搜索步；terminal_carry 修补在本轮闭环触发数为 0，只有组件正负例覆盖，不能宣称已经闭环验证成功。专项 28 次执行的原始策略加监督计时 p95 为 24.237 ms、最大 57.512 ms，其中 8 帧超过 20 Hz 对应的 50 ms；工作单元有界不等于硬实时保证。

**下一步方案：** 保留分层验证：静态几何、控制机制、动作回放、物理回放、效果门槛各自说明范围。后续对尚未触发的终端搬运路径使用事先登记的机制测试；以原始端到端计时评估性能，不能用只读回放耗时代替。

依据：[smoke_a_verification.json](analysis/smoke_a_verification.json) / [smoke_a_physics.json](analysis/smoke_a_physics.json) / [smoke_a_edge_diagnosis.json](analysis/smoke_a_edge_diagnosis.json) / [components_c.json](analysis/components_c.json)


## 核验与证据边界

- 保存输入动作/FIFO/噪声核验：已通过记录合计 23,934 控制步。
- 物理回放：已通过记录合计 63 回合、23,934 步；不增加统计样本。
- 每一轮源代码快照和结果保留；本报告校验快照哈希并从原始result重新核对成功数与分析汇总。
- 关闭开关一致性、静态几何/IK、完整决策回放、物理回放是不同验证范围，不能相互替代。
- [carry_search_static_a.json](analysis/carry_search_static_a.json)：通过；历史诊断，不能作为当前源码的通过凭证；静态/机制诊断，具体检查范围与限制见原记录；不增加闭环评估样本
- [carry_search_static_b.json](analysis/carry_search_static_b.json)：通过；源哈希与当前版本一致；静态/机制诊断，具体检查范围与限制见原记录；不增加闭环评估样本
- [components_a.json](analysis/components_a.json)：通过；历史诊断，不能作为当前源码的通过凭证；Focused v17 integration branches using one saved observation and explicit support, geometry, hold and search stubs. Independent helper static tests and closed-loop gates remain necessary.
- [components_b.json](analysis/components_b.json)：通过；历史诊断，不能作为当前源码的通过凭证；Focused v17 integration branches using one saved observation and explicit support, geometry, hold and search stubs. Independent helper static tests and closed-loop gates remain necessary.
- [components_c.json](analysis/components_c.json)：通过；源哈希与当前版本一致；Focused v17 integration branches using one saved observation and explicit support, geometry, hold and search stubs. Independent helper static tests and closed-loop gates remain necessary.
- [components_preflight_a.json](analysis/components_preflight_a.json)：通过；历史诊断，不能作为当前源码的通过凭证；Focused v17 integration branches using one saved observation and explicit support, geometry, hold and search stubs. Independent helper static tests and closed-loop gates remain necessary.
- [mechanisms_a.json](analysis/mechanisms_a.json)：通过；历史诊断，不能作为当前源码的通过凭证；Three new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [mechanisms_b.json](analysis/mechanisms_b.json)：通过；历史诊断，不能作为当前源码的通过凭证；Three new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [mechanisms_c.json](analysis/mechanisms_c.json)：通过；源哈希与当前版本一致；Three new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [mechanisms_preflight_a.json](analysis/mechanisms_preflight_a.json)：通过；历史诊断，不能作为当前源码的通过凭证；Three new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [pose_servo_static_a.json](analysis/pose_servo_static_a.json)：通过；历史诊断，不能作为当前源码的通过凭证；Nominal geometric certificates, finite grids, explicit servo-state tests and proposals on saved old observations. No closed-loop improvement claim.
- [pose_servo_static_b.json](analysis/pose_servo_static_b.json)：通过；源哈希与当前版本一致；Nominal geometric certificates, finite grids, explicit servo-state tests and proposals on saved old observations. No closed-loop improvement claim.

图表为真实数据的分类计数或目标矩阵，输出600 dpi PNG及矢量PDF/SVG，附CSV和来源SHA-256。没有平滑、没有把任意案例排序连成折线，也没有给已挑选小测试附加泛化置信区间。图片实际外观、PDF字体、前端显示、链接与Git同步须由交付验证另行确认；生成文件本身不等于这些检查已经通过。

## 整体评估

本轮可以形成可追溯的实现、组件对照与失败分析材料，能够补充本科毕业设计。是否达到学校或导师的正式毕业标准，仍需按实际要求审定。历史项目证据没有被本轮替换；若本轮门槛未过，只能把v17作为探索和负结果，不能作为已确认的新增性能成果。

仍需区分局部规划可行与实际执行完成、共享恢复贡献与世界模型独有贡献，以及已知诊断条件和独立确认。不应宣称项目完美、总体优于强基线或已获得完整机械臂安全保证。

## 复核入口

- [执行前协议](protocols/PLAN.md)
- [机器可读汇总](SUMMARY.json)
- [前端证据页](index.html)
- [图表来源目录](figures/CATALOG.json)
- [v16原报告](../improvement_v16_20261016_01/REPORT.md)
- [v14既有历史演示](../improvement_v14_20261016_01/index.html#demo)

本轮页面没有新增或冒用机器人视频；上面的演示链接明确指向v14历史记录。
- [smoke_a原始分析](analysis/smoke_a.json) / [作业条件](smoke_a/jobs.json)

每份机制/静态检查仅对应其记录的源哈希；以实际阶段快照和逐步核验确认受测源码，不把早期检查的通过自动转移到后续修订。
