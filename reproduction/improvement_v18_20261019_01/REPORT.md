# v18 实验与交付报告

**小测试门槛未通过；保留候选和负结果，未进入大规模消融、开发或独立确认。**

本轮检查接近到下降的指令衔接，以及保留保护条件的短搬运路线选择。六组为本轮实际重跑的v16、完整v17、v15仅预算C，完整v17分别加下降衔接/短路线单项修复，以及两项全开的v18。两个单项修复均加在完整v17之上；原预算组同样实际重跑，但未启用后来加入的持物保护，仅作成功数参考，不能整体回退采用。旧版本、权重与原始结果保留；本轮不训练、不写论文。

**执行前已发现的静态风险：** 执行前短路线离线检查中，旧 route / 12000036 的 step330 保存状态在新增候选上累计尝试73 work 后，out15 仅余58步，低于59步估计而被拒。current_rotation_inset 虽在4个保存状态获选，这不是4次任务成功，也不构成净改善证据；本轮效果必须以正式54次小测试及后续门槛为准。 [离线原始记录](analysis/short_route_static_a.json)。

## 约束与信息范围

400 控制步、20 Hz、D2 FIFO、最多两次抓取，规划和等待均计入总步数。沿用9 mm/0.08 rad到位、5帧稳定、0.04 rad局部IK关节余量、1 mm手/箱路径、3 mm规划手/物体、1 mm执行手/物体及原开度/位姿保护。闭合与释放时长不缩短。控制只使用当前观测、历史和当前关节，不使用接触、奖励、成功标签或未来状态。

## 已完成执行与门槛

| 阶段 | 旧基线 v16 | 完整 v17 | v15 仅预算 C | v17 + 下降衔接 | v17 + 短路线 | 完整 v18 | 结果及核验 |
|---|---:|---:|---:|---:|---:|---:|---|
| smoke_a | 2/9 | 3/9 | 7/9 | 2/9 | 2/9 | 2/9 | 结果门槛未通过 |

完整阶段累计 **54 次闭环执行**。不同修订与变体共享诊断条件；不得将这些执行数解释为独立起点数或合并成总体成功率。

**小测试的9个条件不等于9个独立起点。** 其中8个为原标准条件，另1个是复用 demo6000005 的 clearance-only 父配置 profile。该专用 profile 在六组中按登记的继承配置配对，用于检查预算退步；图表将它单列。单轮小测试54次、后续消融564次、开发v16/v17/v18各240次合计720次、独立确认1440次；只有实际完成并核验的记录才计入成果。

| 后续阶段 | 预定本轮执行数 | 完整执行数 | 状态 |
|---|---:|---:|---|
| 已知条件消融 | 564 | 0 | 未运行 |
| 开发对照 | 720 | 0 | 未运行 |
| 独立确认 | 1440 | 0 | 未运行 |

**小测试失败后，564次消融、720次开发对照（v16/v17/v18各240）及1440次独立确认均未运行。** 计划文件或运行入口的存在不代表实验已执行，也没有独立确认支持采用v18。

## 最新小测试：三项目标逐项核对

| 目标 / profile | 旧基线 v16 | 完整 v17 | v15 仅预算 C | v17 + 下降衔接 | v17 + 短路线 | 完整 v18 |
|---|---|---|---|---|---|---|
| 斜靠抓取后搬运 / demo_13000021 | [未完成，400步](smoke_a/v16_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v17_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/budget_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/handoff_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/short_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v18_known13_bc_k2_noise005_demo_13000021/result.json) |
| 箱沿分段接近 / demo_13000022 | [未完成，400步](smoke_a/v16_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v17_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/budget_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/handoff_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/short_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v18_known13_full_s41_noise005_demo_13000022/result.json) |
| 预算专用 profile / demo_6000005 | [未完成，400步](smoke_a/v16_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/v17_clearance_profile_6000005/result.json) | [成功，382步](smoke_a/budget_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/handoff_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/short_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/v18_clearance_profile_6000005/result.json) |

原v14失败目标的完成数：0 / 3。预算profile已在v15和预算候选中成功，不能把重复完成说成相对这些版本的新救回。只有整回合成功才计作完成，抓住、抬起、路径证书通过或局部误差变小都不能替代这个判据。

- 相对 v17 的已配对成功退步：1；配对覆盖 9 个条件。 条件：known_full_s23_clean_demo_12000036/demo_12000036。
- 相对 v16 的已配对成功退步：0；配对覆盖 9 个条件。
- 相对 budget 的已配对成功退步：5；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v15 的已配对成功退步：2；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；clearance_profile_6000005/demo_6000005。
- 相对 v14 的已配对成功退步：4；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021。
- 相对 v13 的已配对成功退步：5；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v6 的已配对成功退步：7；配对覆盖 8 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；known13_bc_k2_noise005_demo_13000021/demo_13000021；known13_full_s41_noise005_demo_13000022/demo_13000022；clearance_profile_6000005/demo_6000005。

## 具体失败原因与下一步

### v18 未通过采用门槛，停止扩大实验

六组实际 v16 / v17 / 原预算 C / 衔接单项 / 短路线单项 / 完整 v18 的成功数为 2 / 3 / 7 / 2 / 2 / 2（各 9 个条件）。三个预登记目标全部未完成，完整 v18 相对 v17 丢失 12000036 的成功。9 条件只使用 8 个不同起点；这些刻意选择的困难案例不能当作整个项目或独立泛化成功率。三组实际基线的成功和步数均与历史记录一致。

**下一步方案：** 保留本轮正负结果并不采用 v18；564 次扩展、三版各 240 次开发和 1440 次独立确认均不启动。后续先修复已定位的退步，再用相同门槛验证；不增加 400 步、不放宽保护、不训练或写论文。

依据：[smoke_a.json](analysis/smoke_a.json) / [smoke_a_pairs.csv](analysis/smoke_a_pairs.csv)

### 12000036：衔接多 7 步、搜索多 4 步，挤占任务末段

实际 v17 在事件时钟 235 关爪、276 搬运、362 放置、390 释放，第 400 步成功。衔接单项将下降从 12 步延长到 19 步，之后各阶段晚 7 步；短路线单项维持原抓取，但新增候选未收敛，多耗 73 work，规划从 125 work / 9 次调用增到 198 / 13 次，最终仍选原 outward_15_inset。其执行各段时长相同，放置和释放均晚 4 步。完整 v18 两项叠加，373 才进入放置，400 仍未释放。此前静态晚期状态的失选是另一条轨迹，不混为本次失败。

**下一步方案：** 候选方案：将连续交接限制为一个短过渡段，再恢复原下降进度规律；对新增路线设置不得挤占既有候选及放置、释放时间的验证预算。先分开做消融，不能靠减少原到位确认或释放时间补偿。上述方案尚未实现或验证。

依据：[smoke_a_handoff_diagnosis.json](analysis/smoke_a_handoff_diagnosis.json) / [smoke_a_route_findings.json](analysis/smoke_a_route_findings.json) / [short_route_static_a.json](analysis/short_route_static_a.json)

### 6000005：短路线已选中，瓶颈转为末端连续到位

衔接单项和完整 v18 在两个 6000005 配置中都消除原 18 步回正，关爪由 339 提前到 324，搬运由 373 提前到 358。358–359 用 25 work / 2 次调用选中原 current_exact，并执行到 400；这不是新增内移候选的贡献。41 步搬运均保持抓持，关节余量至少 0.4165 rad。末帧位置误差 8.899 mm、角误差 0.04165 rad，但 9 mm / 0.08 rad 到位条件最长只连续满足 3 帧，末帧仅第 1 帧，未达到原 5 帧要求。物体已接近目标不等于末端连续到位。选择时名义估计需 59 步、剩余 41 步，最低命令安排 35 步只是一项过滤规则，无法保证真实完成。

**下一步方案：** 在保持原精度与五帧确认条件下，单独检查 D2 下持物末端接近目标时的收敛和在途指令；为放置、释放保留原预算。只把满足现行条件的旧成功片段作为参考，不整体关闭保护或直接提前放置。

依据：[smoke_a_route_findings.json](analysis/smoke_a_route_findings.json) / [smoke_a_handoff_diagnosis.json](analysis/smoke_a_handoff_diagnosis.json) / [smoke_a_route_diagnosis.json](analysis/smoke_a_route_diagnosis.json)

### 新增内移短路线有局部收益，但没有新增成功案例

新内移候选在本轮共获选 4 次：short 和完整 v18 各自在 demo87、12000011 第二次搜索获选。demo87 原本成功，结束由 300 提前到 283 步；12000011 仍未完成。新路线是改变端点家族，不能写为修复了 IK 求解器。旧保存状态中精确短路的 23 次拒绝为预算 8、局部 IK 未收敛 13、真实余量不足 2；更细的 IK 延续没有新增通过，因此未改求解容差。实际 full 的新候选搜索总 work 高于 v17，不能只报告更短的已选路线。

**下一步方案：** 保留局部加速证据，但先控制失败候选的验证成本；优先保证已有可行路线不因探索耗尽预算。局部 IK 未收敛应继续标为未知，关节余量不合格的路线继续拒绝。

依据：[smoke_a_route_findings.json](analysis/smoke_a_route_findings.json) / [smoke_a_route_diagnosis.json](analysis/smoke_a_route_diagnosis.json) / [short_route_diagnosis_a.json](analysis/short_route_diagnosis_a.json)

### 另外两项目标仍有更早阶段的限制

斜靠 13000021 的完整 v18 到 337 才进入搬运，比 v17 的 332 晚 5 步，仍未选出完整可执行路线。箱沿 13000022 仍到 387 才进入下降，394 触发回正，400 结束于 PATH_RECENTER，尚未关爪；其短路线模块从未调用。不能把未进入模块的案例归因为短路线失败，也不能把持续等待结束或保护动作执行称为任务成功。

**下一步方案：** 分别评估上游旋转与接近耗时、下降回正的连续参考。先用保存轨迹定位预算消耗，下一版每次只验证一个局部假设，避免新增模块相互抵消。

依据：[smoke_a_handoff_diagnosis.json](analysis/smoke_a_handoff_diagnosis.json) / [smoke_a_route_diagnosis.json](analysis/smoke_a_route_diagnosis.json)

### 证据完整度与效果分开判断

400 步、D2、106 个继承字段和现有保护保持；全关 9 条件 / 3442 步精确复现 v17，11 组组件与两份静态检查通过。衔接单项和完整 v18 各 138 条最终动作认证并实际提交；本轮没有触发新增关节或几何拒绝、脉冲回滚，其负路径仅有组件测试覆盖。静态诊断、动作核验和物理回放均不增加评估样本。预算组 7/9 的保护条件不同，不能据成功数整体回退采用。

**下一步方案：** 继续把配置/机制正确、轨迹可复核和任务效果分开报告；只有预登记效果门槛通过，才进入开发与冻结后的全新起点确认。

依据：[mechanisms_a.json](analysis/mechanisms_a.json) / [components_a.json](analysis/components_a.json) / [handoff_static_a.json](analysis/handoff_static_a.json) / [short_route_static_a.json](analysis/short_route_static_a.json) / [smoke_a_handoff_diagnosis.json](analysis/smoke_a_handoff_diagnosis.json) / [smoke_a_budget_reference.json](../improvement_v17_20261019_01/analysis/smoke_a_budget_reference.json)


## 核验与证据边界

- 保存输入动作/FIFO/噪声核验：已通过记录合计 20,367 控制步。
- 物理回放：已通过记录合计 54 回合、20,367 步；不增加统计样本。
- 每一轮源代码快照和结果保留；本报告校验快照哈希并从原始result重新核对成功数与分析汇总。
- 关闭开关一致性、静态几何/IK、完整决策回放、物理回放是不同验证范围，不能相互替代。
- [components_a.json](analysis/components_a.json)：通过；源哈希与当前版本一致；v18 integration with saved v17 final-descent state and explicit geometry/predicate/search stubs. Independent helper static and subsequent physical/decision gates are still required.
- [handoff_static_a.json](analysis/handoff_static_a.json)：通过；源哈希与当前版本一致；Pure stateless handoff helper, saved-state offline geometry and mechanical negative tests only; central integration and closed-loop outcomes remain separate.
- [handoff_static_preflight_a.json](analysis/handoff_static_preflight_a.json)：通过；历史诊断，不能作为当前源码的通过凭证；Pure stateless handoff helper, saved-state offline geometry and mechanical negative tests only; central integration and closed-loop outcomes remain separate.
- [mechanisms_a.json](analysis/mechanisms_a.json)：通过；源哈希与当前版本一致；Two new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [short_route_static_a.json](analysis/short_route_static_a.json)：通过；源哈希与当前版本一致；静态/机制诊断，具体检查范围与限制见原记录；不增加闭环评估样本

图表为真实数据的分类计数或目标矩阵，输出600 dpi PNG及矢量PDF/SVG，附CSV和来源SHA-256。没有平滑、没有把任意案例排序连成折线，也没有给已挑选小测试附加泛化置信区间。图片实际外观、PDF字体、前端显示、链接与Git同步须由交付验证另行确认；生成文件本身不等于这些检查已经通过。

## 整体评估

本轮可以形成可追溯的实现、组件对照与失败分析材料，能够补充本科毕业设计。是否达到学校或导师的正式毕业标准，仍需按实际要求审定。历史项目证据没有被本轮替换；若本轮门槛未过，只能把v18作为探索和负结果，不能作为已确认的新增性能成果。

仍需区分局部规划可行与实际执行完成、共享恢复贡献与世界模型独有贡献，以及已知诊断条件和独立确认。不应宣称项目完美、总体优于强基线或已获得完整机械臂安全保证。

## 复核入口

- [执行前协议](protocols/PLAN.md)
- [机器可读汇总](SUMMARY.json)
- [前端证据页](index.html)
- [图表来源目录](figures/CATALOG.json)
- [v17原报告](../improvement_v17_20261019_01/REPORT.md)
- [v14既有历史演示](../improvement_v14_20261016_01/index.html#demo)

本轮页面没有新增或冒用机器人视频；上面的演示链接明确指向v14历史记录。
- [smoke_a原始分析](analysis/smoke_a.json) / [作业条件](smoke_a/jobs.json)

每份机制/静态检查仅对应其记录的源哈希；以实际阶段快照和逐步核验确认受测源码，不把早期检查的通过自动转移到后续修订。
