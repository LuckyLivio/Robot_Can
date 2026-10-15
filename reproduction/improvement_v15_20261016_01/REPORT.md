# v15 实验与交付报告

**小测试门槛未通过；保留候选和负结果，未进入大规模消融、开发或独立确认。**

本轮分别检查持物搬运姿态可达性 A、箱沿分段路径 B，以及回正与接近阶段的预算安排 C。五组为实际重跑的父版本 v14、仅 A、仅 B、仅 C、组合 v15。旧版本、权重与原始结果保留；本轮不训练、不写论文。

## 约束与信息范围

400 控制步、20 Hz、D2 FIFO、最多两次抓取，规划和等待均计入总步数。沿用9 mm/0.08 rad到位、5帧稳定、0.04 rad局部IK关节余量、1 mm手/箱路径、3 mm规划手/物体、1 mm执行手/物体及原开度/位姿保护。闭合与释放时长不缩短。控制只使用当前观测、历史和当前关节，不使用接触、奖励、成功标签或未来状态。

## 已完成执行与门槛

| 阶段 | 父版本 v14 | 仅搬运 A | 仅分段 B | 仅预算 C | 组合 v15 | 结果及核验 |
|---|---:|---:|---:|---:|---:|---|
| smoke_a | 6/9 | 3/9 | 6/9 | 7/9 | 4/9 | 结果门槛未通过 |

完整阶段累计 **45 次闭环执行**。不同修订与变体共享诊断条件；不得将这些执行数解释为独立起点数或合并成总体成功率。

**小测试的9个条件不等于9个独立起点。** 其中8个为原标准条件，另1个是复用 demo6000005 的 clearance-only 父配置 profile。该专用 profile 在五组中使用相同父配置，用于检查预算退步；图表将它单列。

| 后续阶段 | 预定本轮执行数 | 完整执行数 | 状态 |
|---|---:|---:|---|
| 已知条件消融 | 470 | 0 | 未运行 |
| 开发对照 | 480 | 0 | 未运行 |
| 独立确认 | 1440 | 0 | 未运行 |

**小测试失败后，470次消融、480次开发对照（v14/v15各240）及1440次独立确认均未运行。** 计划文件或运行入口的存在不代表实验已执行，也没有独立确认支持采用v15。

## 最新小测试：三项目标逐项核对

| 目标 / profile | 父版本 v14 | 仅搬运 A | 仅分段 B | 仅预算 C | 组合 v15 |
|---|---|---|---|---|---|
| 斜靠抓取后搬运 / demo_13000021 | [未完成，400步](smoke_a/v14_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/carry_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/edge_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/budget_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v15_known13_bc_k2_noise005_demo_13000021/result.json) |
| 箱沿分段接近 / demo_13000022 | [未完成，400步](smoke_a/v14_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/carry_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/edge_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/budget_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v15_known13_full_s41_noise005_demo_13000022/result.json) |
| 预算专用 profile / demo_6000005 | [未完成，400步](smoke_a/v14_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/carry_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/edge_clearance_profile_6000005/result.json) | [成功，382步](smoke_a/budget_clearance_profile_6000005/result.json) | [成功，397步](smoke_a/v15_clearance_profile_6000005/result.json) |

救回目标数：1 / 3。只有整回合成功才计作救回，抓住、抬起、路径证书通过或局部误差变小都不能替代这个判据。

- 相对 v14 的已配对成功退步：3；配对覆盖 9 个条件。 条件：known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021。
- 相对 v13 的已配对成功退步：3；配对覆盖 9 个条件。 条件：known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021。
- 相对 v6 的已配对成功退步：5；配对覆盖 8 个条件。 条件：known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；known13_bc_k2_noise005_demo_13000021/demo_13000021；known13_full_s41_noise005_demo_13000022/demo_13000022。

## 具体失败原因与下一步

### 搬运 A：姿态有可行证书，但闭环转向没有按时收敛

smoke_a斜靠目标从311到321步规划，占11步；327–396步转向共70步，其中回正34步、旋转36步。末帧角误差0.081448 rad、位置误差9.682 mm，仍未同时满足0.08 rad/9 mm。搬运期间保持稳定抓持，最小关节余量0.477321 rad；这里主要是延迟下回正与转向切换耗时，不是重新失抓。此外三个旧成功在carry与组合中退步，局部终点IK/路径未确认导致长搜索与重试；例如12000011首次搜索53步、723个工作单元。IK迭代未确认不能写成数学上的不可达。

**下一步方案：** 暂不采用搬运A。后续独立修订应先限定无进展搜索和重复搜索的预算，检查局部IK的初值与候选顺序；再单测D2下回正/转向切换与提前制动，保留全部到位、碰撞和关节阈值。旧成功必须逐项保住后才能扩大测试。

依据：[smoke_a_carry_diagnosis.json](analysis/smoke_a_carry_diagnosis.json) / [smoke_a_carry_rotation_diagnosis.json](analysis/smoke_a_carry_rotation_diagnosis.json)

### 箱沿 B：预平移完成，首次旋转仍少一帧稳定确认

smoke_a箱沿目标的分段路径通过静态检查并完成预平移，但首次旋转最多连续4帧同时满足原到位与开度要求，达不到5帧。第250步角误差已降到0.032294 rad，位置却漂到16.465 mm；随后按70步保护超时。该次旋转关节最小余量0.183844 rad，当前证据指向位置稳定性而非关节限位触发。第二次到385步才进入下降，只剩15步；第400步停在PATH_RECENTER，没有完成恢复抓取。

**下一步方案：** 暂不采用分段B。下一轮只针对转向结束时的D2位置漂移检查制动与连续5帧联合确认，并在接受路径前为下降、闭合、搬运和释放预留预算；不能把4帧当5帧、扩大9mm容差或增加400步总预算。

依据：[smoke_a_edge_diagnosis.json](analysis/smoke_a_edge_diagnosis.json)

### 预算 C：专用配置有改善，尚未证明普遍收益

smoke_a预算profile：父版本400步未完成，仅C382步成功，组合397步成功。这是同一旧起点的专用配置，不能折算为独立泛化成功；组合仍受搬运退步和箱沿超时影响。

**下一步方案：** 保留C作为待确认候选。若以后继续，优先独立复核C是否保护全部旧成功，再按预登记顺序做更大消融和开发对照；本轮组合门槛失败，470/480/1440阶段停止。

依据：[result.json](smoke_a/v14_clearance_profile_6000005/result.json) / [result.json](smoke_a/budget_clearance_profile_6000005/result.json) / [result.json](smoke_a/v15_clearance_profile_6000005/result.json)


## 核验与证据边界

- 保存输入动作/FIFO/噪声核验：已通过记录合计 16,367 控制步。
- 物理回放：已通过记录合计 45 回合、16,367 步；不增加统计样本。
- 每一轮源代码快照和结果保留；本报告校验快照哈希并从原始result重新核对成功数与分析汇总。
- 关闭开关一致性、静态几何/IK、完整决策回放、物理回放是不同验证范围，不能相互替代。
- [budget_early_static.json](analysis/budget_early_static.json)：通过；Exact saved-input replay and offline geometry/IK checks; no new physical episodes.
- [carry_path_offline_a.json](analysis/carry_path_offline_a.json)：通过；静态/机制诊断，具体检查范围与限制见原记录；不增加闭环评估样本
- [carry_path_offline_b.json](analysis/carry_path_offline_b.json)：通过；静态/机制诊断，具体检查范围与限制见原记录；不增加闭环评估样本
- [carry_path_offline_c.json](analysis/carry_path_offline_c.json)：通过；静态/机制诊断，具体检查范围与限制见原记录；不增加闭环评估样本
- [components_a.json](analysis/components_a.json)：通过；Focused enabled control-flow tests. Geometry/IK stubs are explicitly identified; no claim of physical success, generality, or full-arm safety.
- [mechanisms_a.json](analysis/mechanisms_a.json)：通过；Three new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [mechanisms_b.json](analysis/mechanisms_b.json)：通过；Three new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [mechanisms_c.json](analysis/mechanisms_c.json)：通过；Three new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [segmented_edge_static.json](analysis/segmented_edge_static.json)：通过；Offline saved-input replay, fixed geometry and bounded IK only; no new physics or success claim.

图表为真实数据的分类计数或目标矩阵，输出600 dpi PNG及矢量PDF/SVG，附CSV和来源SHA-256。没有平滑、没有把任意案例排序连成折线，也没有给已挑选小测试附加泛化置信区间。图片实际外观、PDF字体、前端显示、链接与Git同步须由交付验证另行确认；生成文件本身不等于这些检查已经通过。

## 整体评估

本轮可以形成可追溯的实现、组件对照与失败分析材料，能够补充本科毕业设计。是否达到学校或导师的正式毕业标准，仍需按实际要求审定。历史项目证据没有被本轮替换；若本轮门槛未过，只能把v15作为探索和负结果，不能作为已确认的新增性能成果。

仍需区分局部规划可行与实际执行完成、共享恢复贡献与世界模型独有贡献，以及已知诊断条件和独立确认。不应宣称项目完美、总体优于强基线或已获得完整机械臂安全保证。

## 复核入口

- [执行前协议](protocols/PLAN.md)
- [机器可读汇总](SUMMARY.json)
- [前端证据页](index.html)
- [图表来源目录](figures/CATALOG.json)
- [v14原报告](../improvement_v14_20261016_01/REPORT.md)
- [v14既有历史演示](../improvement_v14_20261016_01/index.html#demo)

本轮页面没有新增或冒用机器人视频；上面的演示链接明确指向v14历史记录。
- [smoke_a原始分析](analysis/smoke_a.json) / [作业条件](smoke_a/jobs.json)

诊断修订范围见[修订索引](validation/diagnostic_revisions.json)。最终受测源码对应 mechanisms_c、components_a 和 carry_path_offline_c；更早回执仅对应其记录的源哈希。
