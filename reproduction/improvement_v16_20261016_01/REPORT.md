# v16 实验与交付报告

**小测试门槛未通过；保留候选和负结果，未进入大规模消融、开发或独立确认。**

本轮检查局部IK连续求解、持物转向协同收敛，以及箱沿位置稳定性。七组为实际v14、完整v15、v15仅预算C、完整v15分别加IK/持物/箱沿单项修复，以及三项全开的v16。三个单项修复是在完整v15上增加，不能解释为从v14单独增加一个组件。旧版本、权重与原始结果保留；本轮不训练、不写论文。

## 约束与信息范围

400 控制步、20 Hz、D2 FIFO、最多两次抓取，规划和等待均计入总步数。沿用9 mm/0.08 rad到位、5帧稳定、0.04 rad局部IK关节余量、1 mm手/箱路径、3 mm规划手/物体、1 mm执行手/物体及原开度/位姿保护。闭合与释放时长不缩短。控制只使用当前观测、历史和当前关节，不使用接触、奖励、成功标签或未来状态。

## 已完成执行与门槛

| 阶段 | 旧基线 v14 | 完整 v15 | v15 仅预算 C | v15 + IK修复 | v15 + 持物修复 | v15 + 箱沿修复 | 完整 v16 | 结果及核验 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| smoke_a | 6/9 | 4/9 | 7/9 | 2/9 | 4/9 | 2/9 | 2/9 | 结果门槛未通过 |

完整阶段累计 **63 次闭环执行**。不同修订与变体共享诊断条件；不得将这些执行数解释为独立起点数或合并成总体成功率。

**小测试的9个条件不等于9个独立起点。** 其中8个为原标准条件，另1个是复用 demo6000005 的 clearance-only 父配置 profile。该专用 profile 在七组中使用相同继承配置，用于检查预算退步；图表将它单列。

| 后续阶段 | 预定本轮执行数 | 完整执行数 | 状态 |
|---|---:|---:|---|
| 已知条件消融 | 658 | 0 | 未运行 |
| 开发对照 | 720 | 0 | 未运行 |
| 独立确认 | 1440 | 0 | 未运行 |

**小测试失败后，658次消融、720次开发对照（v14/v15/v16各240）及1440次独立确认均未运行。** 计划文件或运行入口的存在不代表实验已执行，也没有独立确认支持采用v16。

## 最新小测试：三项目标逐项核对

| 目标 / profile | 旧基线 v14 | 完整 v15 | v15 仅预算 C | v15 + IK修复 | v15 + 持物修复 | v15 + 箱沿修复 | 完整 v16 |
|---|---|---|---|---|---|---|---|
| 斜靠抓取后搬运 / demo_13000021 | [未完成，400步](smoke_a/v14_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v15_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/budget_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/ik_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/held_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/edge_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v16_known13_bc_k2_noise005_demo_13000021/result.json) |
| 箱沿分段接近 / demo_13000022 | [未完成，400步](smoke_a/v14_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v15_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/budget_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/ik_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/held_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/edge_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v16_known13_full_s41_noise005_demo_13000022/result.json) |
| 预算专用 profile / demo_6000005 | [未完成，400步](smoke_a/v14_clearance_profile_6000005/result.json) | [成功，397步](smoke_a/v15_clearance_profile_6000005/result.json) | [成功，382步](smoke_a/budget_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/ik_clearance_profile_6000005/result.json) | [成功，397步](smoke_a/held_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/edge_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/v16_clearance_profile_6000005/result.json) |

救回目标数：0 / 3。只有整回合成功才计作救回，抓住、抬起、路径证书通过或局部误差变小都不能替代这个判据。

- 相对 v14 的已配对成功退步：4；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021。
- 相对 v15 的已配对成功退步：2；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；clearance_profile_6000005/demo_6000005。
- 相对 budget 的已配对成功退步：5；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v13 的已配对成功退步：5；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v6 的已配对成功退步：7；配对覆盖 8 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；known13_bc_k2_noise005_demo_13000021/demo_13000021；known13_full_s41_noise005_demo_13000022/demo_13000022；clearance_profile_6000005/demo_6000005。

## 具体失败原因与下一步

### 局部 IK 有进展，但旧成功并非都能在原关节保护下直接复制

连续 IK 与原接受范围内的目标选择，在四个保存状态上找到完整分段证书，分别使用17、9、9、12次规划调用。旧成功轨迹中有两例关节余量曾低于0.04 rad，因此不能把所有拒绝都当成数值误判。闭环 IK 单项仍未救回三个旧成功，其中12000036到394步才切换RELEASE状态，395步开始提交释放命令，400步尚未成功。静态4/4证书不等于闭环4/4成功。

**下一步方案：** 把路径可达、保护约束和实际执行时间分别检查。优先保留经过验证且不需要额外转向的原路径；新路径在执行前估计完整抓取、转向、运输和释放所需步数，不扩大成功范围或降低关节余量。

依据：[ik_continuation_a.json](analysis/ik_continuation_a.json) / [ik_continuation_b.json](analysis/ik_continuation_b.json) / [smoke_a_carry_diagnosis.json](analysis/smoke_a_carry_diagnosis.json)

### 持物转向部分达标，后续运输和抓持仍是限制

13000021完整v16在325–365步用41步完成转向，但366–400的35步运输后物体仍距目标约344 mm；该持物执行阶段观测抓持证据持续成立，实际关节余量至少0.463 rad。12000011的等价大角转向达到70步上限，仍差约1.005 rad。12000036进入CARRY由v15的264步推迟至v16的330步。12000021则在375–378步失去抓持证据，379步由原失抓规则启动恢复。几何证书不能保证不打滑，也不能保证及时完成任务。

**下一步方案：** 先选择在剩余步数内能完成的短转向路径；在原保护范围内检查持物运动的变化幅度与抓持稳定性。不要把增加搜索候选当成解决运输迟缓或失抓的办法。

依据：[smoke_a_carry_diagnosis.json](analysis/smoke_a_carry_diagnosis.json)

### 箱沿仍受位置漂移与连续确认阻塞，不能放宽到位标准

13000022的edge与完整v16首次预平移用49帧，其中21帧单独调整夹爪开度；首次转向有效70帧后仍超时。第274步角误差已降至0.044759 rad，但位置误差15.115 mm，超过9 mm门槛，最多只有1个连续帧满足位姿与开度。第二次接近到400步仍为13.228 mm，D2预测误差14.530 mm；下降余隙4.423 mm。没有混合路径几何拒绝，主要限制是位置收敛和原连续确认。

**下一步方案：** 把新稳位干预限制在实际需要的路径阶段，分析位置残差、观测运动预测与OSC响应，再在同一保存状态上比较控制方案。保持9 mm/0.08 rad、连续5帧与下降3 mm检查，不删掉未满足的检查以增加成功数。

依据：[smoke_a_edge_diagnosis.json](analysis/smoke_a_edge_diagnosis.json)

### 预算候选仍最好；新增重复规划和等待抵消了局部进展

预算候选保持7/9，完整v16为2/9，相比v15新增两个条件失败。6000005两种profile复用同一起点，完整v16均到376步才进入CARRY，比v15晚24步；四个持物候选又对相同的首段抬升重复求解，消耗200工作单元、13个规划步而未确认路径。在已诊断的15次执行、5942步中，原始策略加监督器耗时最大37.180 ms，没有超过50 ms；这是本机本批测量，不能声称普遍实时性。当前更直接的问题是400步离散预算内的工作安排。

**下一步方案：** 优先缓存并共享候选的公共路径前缀，避免相同失败重复求解；区分必须等待的保护与不必要的新干预，按完整剩余任务安排预算。保留预算模块为候选，完整v16不采用；下一版先做这些最小验证，再重新评估能否进入开发和独立确认。

依据：[smoke_a.json](analysis/smoke_a.json) / [smoke_a_carry_diagnosis.json](analysis/smoke_a_carry_diagnosis.json) / [smoke_a_edge_diagnosis.json](analysis/smoke_a_edge_diagnosis.json)


## 核验与证据边界

- 保存输入动作/FIFO/噪声核验：已通过记录合计 23,635 控制步。
- 物理回放：已通过记录合计 63 回合、23,635 步；不增加统计样本。
- 每一轮源代码快照和结果保留；本报告校验快照哈希并从原始result重新核对成功数与分析汇总。
- 关闭开关一致性、静态几何/IK、完整决策回放、物理回放是不同验证范围，不能相互替代。
- [components_a.json](analysis/components_a.json)：通过；源哈希与当前版本一致；Focused enabled control-flow and nominal servo tests; all stubs stated. Does not establish physical recovery, independent generalization or full-arm collision safety.
- [mechanisms_a.json](analysis/mechanisms_a.json)：通过；源哈希与当前版本一致；Three new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [mechanisms_suffix_a.json](analysis/mechanisms_suffix_a.json)：通过；历史诊断，不能作为当前源码的通过凭证；Three new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [pose_servo_static.json](analysis/pose_servo_static.json)：通过；源哈希与当前版本一致；Static geometry, analytical arc bound, numerical product-grid checks and saved-observation proposals. Not controller replay, dynamic stability proof or performance evaluation.

图表为真实数据的分类计数或目标矩阵，输出600 dpi PNG及矢量PDF/SVG，附CSV和来源SHA-256。没有平滑、没有把任意案例排序连成折线，也没有给已挑选小测试附加泛化置信区间。图片实际外观、PDF字体、前端显示、链接与Git同步须由交付验证另行确认；生成文件本身不等于这些检查已经通过。

## 整体评估

本轮可以形成可追溯的实现、组件对照与失败分析材料，能够补充本科毕业设计。是否达到学校或导师的正式毕业标准，仍需按实际要求审定。历史项目证据没有被本轮替换；若本轮门槛未过，只能把v16作为探索和负结果，不能作为已确认的新增性能成果。

仍需区分局部规划可行与实际执行完成、共享恢复贡献与世界模型独有贡献，以及已知诊断条件和独立确认。不应宣称项目完美、总体优于强基线或已获得完整机械臂安全保证。

## 复核入口

- [执行前协议](protocols/PLAN.md)
- [机器可读汇总](SUMMARY.json)
- [前端证据页](index.html)
- [图表来源目录](figures/CATALOG.json)
- [v15原报告](../improvement_v15_20261016_01/REPORT.md)
- [v14既有历史演示](../improvement_v14_20261016_01/index.html#demo)

本轮页面没有新增或冒用机器人视频；上面的演示链接明确指向v14历史记录。
- [smoke_a原始分析](analysis/smoke_a.json) / [作业条件](smoke_a/jobs.json)

每份机制/静态检查仅对应其记录的源哈希；以实际阶段快照和逐步核验确认受测源码，不把早期检查的通过自动转移到后续修订。
