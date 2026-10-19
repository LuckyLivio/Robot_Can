# v19 实验与交付报告

**小测试门槛未通过；保留候选和负结果，未进入大规模消融、开发或独立确认。**

本轮在完整v18上检查A：有界过渡窗口、B：可选候选预算和C：持物终端收敛。八组为本轮实际重跑的v17、完整v18、v15仅预算，以及完整v18分别加A、B、C、AB和ABC（完整v19）。A/B/C/AB均保留完整v18和所有历史模块，不能称为从v17单独新增一项。没有AC/BC两组，不声称完整三因子交互估计。原预算组同样实际重跑，但未启用后来加入的持物保护，仅作成功数约束参考，不能整体回退采用。旧版本、权重与原始结果保留；本轮不训练、不写论文。

**执行前已发现的静态风险：** 执行前对同一保存输入调用搜索器：12000036旧step276状态由v18搜索器的198 work / 13调用降为126 work / 9调用；demo87的局部inset机会保留。但12000011旧第二次step311状态的搬运证书不完整，新规则不准入inset，由v18搜索器的39 work / 3调用变成125 work / 9调用。这些不是各版本本轮回合的实际规划时间，也不是普遍省时保证；已准入可选候选仍可花满48 work后无结果，实际作用须以本轮完整闭环执行判断。 [离线原始记录](analysis/candidate_static_a.json)。

## 约束与信息范围

400 控制步、20 Hz、D2 FIFO、最多两次抓取，规划和等待均计入总步数。沿用9 mm/0.08 rad到位、5帧稳定、0.04 rad局部IK关节余量、1 mm手/箱路径、3 mm规划手/物体、1 mm执行手/物体及原开度/位姿保护。闭合与释放时长不缩短。控制只使用当前观测、历史和当前关节，不使用接触、奖励、成功标签或未来状态。

## 已完成执行与门槛

| 阶段 | 实际 v17 | 完整 v18 | v15 仅预算 | A · 过渡窗口 | B · 候选预算 | C · 终端收敛 | A+B | v19 · A+B+C | 结果及核验 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| smoke_a | 3/9 | 2/9 | 7/9 | 2/9 | 2/9 | 2/9 | 2/9 | 2/9 | 结果门槛未通过 |

完整阶段累计 **72 次闭环执行**。不同修订与变体共享诊断条件；不得将这些执行数解释为独立起点数或合并成总体成功率。

**小测试的9个条件不等于9个独立起点。** 其中8个为原标准条件，另1个是复用 demo6000005 的 clearance-only 父配置 profile。该专用 profile 在八组中按登记的继承配置配对，用于检查预算退步；图表将它单列。单轮小测试72次、后续消融752次、开发v17/v18/v19各240次合计720次、独立确认1440次；只有实际完成并核验的记录才计入成果。

| 后续阶段 | 预定本轮执行数 | 完整执行数 | 状态 |
|---|---:|---:|---|
| 已知条件消融 | 752 | 0 | 未运行 |
| 开发对照 | 720 | 0 | 未运行 |
| 独立确认 | 1440 | 0 | 未运行 |

**小测试失败后，752次消融、720次开发对照（v17/v18/v19各240）及1440次独立确认均未运行。** 计划文件或运行入口的存在不代表实验已执行，也没有独立确认支持采用v19。

## 最新小测试：三项目标逐项核对

| 目标 / profile | 实际 v17 | 完整 v18 | v15 仅预算 | A · 过渡窗口 | B · 候选预算 | C · 终端收敛 | A+B | v19 · A+B+C |
|---|---|---|---|---|---|---|---|---|
| 斜靠抓取后搬运 / demo_13000021 | [未完成，400步](smoke_a/v17_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v18_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/budget_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/transition_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/candidate_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/settling_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/ab_known13_bc_k2_noise005_demo_13000021/result.json) | [未完成，400步](smoke_a/v19_known13_bc_k2_noise005_demo_13000021/result.json) |
| 箱沿分段接近 / demo_13000022 | [未完成，400步](smoke_a/v17_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v18_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/budget_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/transition_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/candidate_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/settling_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/ab_known13_full_s41_noise005_demo_13000022/result.json) | [未完成，400步](smoke_a/v19_known13_full_s41_noise005_demo_13000022/result.json) |
| 预算专用 profile / demo_6000005 | [未完成，400步](smoke_a/v17_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/v18_clearance_profile_6000005/result.json) | [成功，382步](smoke_a/budget_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/transition_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/candidate_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/settling_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/ab_clearance_profile_6000005/result.json) | [未完成，400步](smoke_a/v19_clearance_profile_6000005/result.json) |

原v14失败目标的完成数：0 / 3。预算profile已在v15和预算候选中成功，不能把重复完成说成相对这些版本的新救回。只有整回合成功才计作完成，抓住、抬起、路径证书通过或局部误差变小都不能替代这个判据。

- 相对 v17 的已配对成功退步：1；配对覆盖 9 个条件。 条件：known_full_s23_clean_demo_12000036/demo_12000036。
- 相对 v18 的已配对成功退步：0；配对覆盖 9 个条件。
- 相对 budget 的已配对成功退步：5；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v16 的已配对成功退步：0；配对覆盖 9 个条件。
- 相对 v15 的已配对成功退步：2；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；clearance_profile_6000005/demo_6000005。
- 相对 v14 的已配对成功退步：4；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021。
- 相对 v13 的已配对成功退步：5；配对覆盖 9 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；clearance_profile_6000005/demo_6000005。
- 相对 v6 的已配对成功退步：7；配对覆盖 8 个条件。 条件：regression_6000005/demo_6000005；known_bc_k2_clean_demo_12000011/demo_12000011；known_full_s23_clean_demo_12000036/demo_12000036；known_full_s23_noise005_demo_12000021/demo_12000021；known13_bc_k2_noise005_demo_13000021/demo_13000021；known13_full_s41_noise005_demo_13000022/demo_13000022；clearance_profile_6000005/demo_6000005。

## 具体失败原因与下一步

### 局部节省没有变成任务救回

72回合完整配对：实际v17为3/9，v18为2/9，旧预算候选7/9；A/B/C/AB和完整v19均2/9。完整v19相对v18无新增成功，相对v17仍丢失12000036，三个预定目标0/3。每组9个profile只有8个不同起点，不是整个项目总体成功率。预算组保护不同，不能整体采用。

**下一步方案：** 保留本轮负结果和原正式成果；停止752回合扩展、每版240回合开发、冻结及新起点确认，不把静态检查或局部提速写成任务成功。

依据：[smoke_a.json](analysis/smoke_a.json) / [PLAN.md](protocols/PLAN.md)

### 12000036省了时间，仍晚一步释放

同输入的B搜索从198work/13调用降为126work/9调用，仍选择相同out15目标。A将下降19步减到13步。AB/完整v19因此在363进入PLACE、391进入RELEASE；实际v17分别为362和390，最终第400步成功，而完整v19第400步仍失败。C没有缩短这里的三段CARRY执行5/17/55步。

**下一步方案：** 先逐帧比较那1步上游差及释放后的实际物理轨迹，检验有依据的衔接触发条件；不加第401步、不缩短确认、不事后改成功定义。

依据：[smoke_a_route_diagnosis.json](analysis/smoke_a_route_diagnosis.json) / [smoke_a_control_diagnosis.json](analysis/smoke_a_control_diagnosis.json)

### 固定三步窗口会让箱沿回正重新出现

6000005中，A在窗口后恢复比例进展，310时钟再次触发回正，随后有1步IK检查和9步PATH_RECENTER；下降由v18的25步变为29步，进入CARRY从358延后至362。缩小作用范围有副作用，不能只用12000036的提速证明它合适。

**下一步方案：** 下一轮先考虑按抓取轴进展与横向偏移分别控制，以当前可观测误差界定作用范围；仍保留原动作变化限制、几何认证、姿态和回正保护。先做同状态诊断，再决定是否改控制器。

依据：[smoke_a_control_diagnosis.json](analysis/smoke_a_control_diagnosis.json)

### 积分制动有效执行，稳定保持仍不够

C单项84次、完整v19共85次积分制动提案全部实际提交。6000005中C单项把389–391的连续3帧延长到389–392的4帧，但393位置误差10.748mm又越过9mm阈值。完整v19相对AB最多仍只有3帧连续满足，末步误差6.084mm只是本段第2帧；单帧误差小不能替代连续5帧到达。

**下一步方案：** 优先诊断观测速度、D2在途动作与停车后的保持过程，设计提前制动与稳定保持的单项候选，再做消融；不削弱9mm/0.08rad和连续5帧要求。

依据：[smoke_a_control_diagnosis.json](analysis/smoke_a_control_diagnosis.json)

### 限制可选搜索的收益与代价都存在

B/AB/完整v19每组各1次inset准入并获选，耗43work；各7次按准入条件仅耗1work后标记未知，48work上限未在真实轨迹触顶。demo87保留短路成功，C使已成功回合283→282步。12000011第二次却改选out15，AB/完整v19直到396才进入PLACE；13000021仍无通过所有原检查的完整路线。13000022进入DESCEND的事件时钟仍为387，未进入搬运搜索，后端改动无法解决它的上游接近超时。

**下一步方案：** 保留候选限额作为未采用的局部候选；分别处理真实的可选路线准入漏失、接近阶段耗时和末端保持。暂不再叠更多模块，也不开展泛化训练。

依据：[smoke_a_route_diagnosis.json](analysis/smoke_a_route_diagnosis.json) / [smoke_a_control_diagnosis.json](analysis/smoke_a_control_diagnosis.json) / [candidate_static_a.json](analysis/candidate_static_a.json)


## 核验与证据边界

- 保存输入动作/FIFO/噪声核验：已通过记录合计 27,140 控制步。
- 物理回放：已通过记录合计 72 回合、27,140 步；不增加统计样本。
- 每一轮源代码快照和结果保留；本报告校验快照哈希并从原始result重新核对成功数与分析汇总。
- 关闭开关一致性、静态几何/IK、完整决策回放、物理回放是不同验证范围，不能相互替代。
- [candidate_static_a.json](analysis/candidate_static_a.json)：通过；源哈希与当前版本一致；静态/机制诊断，具体检查范围与限制见原记录；不增加闭环评估样本
- [components_a.json](analysis/components_a.json)：通过；源哈希与当前版本一致；v19 integration with saved v18 final-descent state and explicit geometry/predicate/search stubs. Independent helper static and subsequent physical/decision gates are still required.
- [mechanisms_a.json](analysis/mechanisms_a.json)：通过；历史诊断，不能作为当前源码的通过凭证；Three new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [mechanisms_b.json](analysis/mechanisms_b.json)：通过；源哈希与当前版本一致；Three new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.
- [settling_static_a.json](analysis/settling_static_a.json)：通过；源哈希与当前版本一致；Static mathematical/geometry tests and original saved-observation proposals only. No simulator, future-state rollout, controller clock/counter mutation or new closed-loop outcome.
- [transition_static_a.json](analysis/transition_static_a.json)：通过；源哈希与当前版本一致；Saved poses with synthetic existing-phase ages; no new physics, sample, timing or performance claim.

图表为真实数据的分类计数或目标矩阵，输出600 dpi PNG及矢量PDF/SVG，附CSV和来源SHA-256。没有平滑、没有把任意案例排序连成折线，也没有给已挑选小测试附加泛化置信区间。图片实际外观、PDF字体、前端显示、链接与Git同步须由交付验证另行确认；生成文件本身不等于这些检查已经通过。

## 整体评估

本轮可以形成可追溯的实现、组件对照与失败分析材料，能够补充本科毕业设计。是否达到学校或导师的正式毕业标准，仍需按实际要求审定。历史项目证据没有被本轮替换；若本轮门槛未过，只能把v19作为探索和负结果，不能作为已确认的新增性能成果。

仍需区分局部规划可行与实际执行完成、共享恢复贡献与世界模型独有贡献，以及已知诊断条件和独立确认。不应宣称项目完美、总体优于强基线或已获得完整机械臂安全保证。

## 复核入口

- [执行前协议](protocols/PLAN.md)
- [机器可读汇总](SUMMARY.json)
- [前端证据页](index.html)
- [图表来源目录](figures/CATALOG.json)
- [v18原报告](../improvement_v18_20261019_01/REPORT.md)
- [v14既有历史演示](../improvement_v14_20261016_01/index.html#demo)

本轮页面没有新增或冒用机器人视频；上面的演示链接明确指向v14历史记录。
- [smoke_a原始分析](analysis/smoke_a.json) / [作业条件](smoke_a/jobs.json)

每份机制/静态检查仅对应其记录的源哈希；以实际阶段快照和逐步核验确认受测源码，不把早期检查的通过自动转移到后续修订。
