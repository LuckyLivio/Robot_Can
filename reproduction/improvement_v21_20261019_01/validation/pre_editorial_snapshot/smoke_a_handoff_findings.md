# v21 小测试只读控制诊断

9个条件复用8个物理起点；重定位/控制器回放另计，均不增加实验样本。事件进入时刻与实际执行时刻分列。
预算组本轮真实重跑但保护不同；此处是已知条件描述，不能据此宣称泛化或完整采用。

| 条件 | 版本 | 成功/步数 | DESCEND→CLOSE | CARRY→PLACE→RELEASE | 首提交/执行开爪 | 重定位控制 |
|---|---|---|---|---|---|---|
| regression_6000005 | v19 | False/400 | 299→328 | 362→None→None | None/None | 10 |
| regression_6000005 | v20 | False/400 | 299→None | None→None→None | None/None | 25 |
| regression_6000005 | budget | True/383 | 288→302 | 337→350→373 | 374/376 | 0 |
| regression_6000005 | recenter | False/400 | 299→328 | 362→None→None | None/None | 9 |
| regression_6000005 | place | False/400 | 299→328 | 362→None→None | None/None | 10 |
| regression_6000005 | v21 | False/400 | 299→328 | 362→None→None | None/None | 9 |
| known_bc_k2_clean_demo_12000011 | v19 | False/400 | 166→180 | 220→396→None | None/None | 0 |
| known_bc_k2_clean_demo_12000011 | v20 | False/400 | 166→180 | 220→None→None | None/None | 0 |
| known_bc_k2_clean_demo_12000011 | budget | True/295 | 163→175 | 215→268→285 | 286/288 | 0 |
| known_bc_k2_clean_demo_12000011 | recenter | False/400 | 166→180 | 220→396→None | None/None | 0 |
| known_bc_k2_clean_demo_12000011 | place | False/400 | 166→180 | 220→396→None | None/None | 0 |
| known_bc_k2_clean_demo_12000011 | v21 | False/400 | 166→180 | 220→396→None | None/None | 0 |
| known_full_s23_clean_demo_12000036 | v19 | False/400 | 223→236 | 277→363→391 | 392/394 | 0 |
| known_full_s23_clean_demo_12000036 | v20 | True/400 | 223→236 | 277→363→390 | 391/393 | 0 |
| known_full_s23_clean_demo_12000036 | budget | True/340 | 211→223 | 264→312→329 | 330/332 | 0 |
| known_full_s23_clean_demo_12000036 | recenter | False/400 | 223→236 | 277→363→391 | 392/394 | 0 |
| known_full_s23_clean_demo_12000036 | place | False/400 | 223→236 | 277→363→391 | 392/394 | 0 |
| known_full_s23_clean_demo_12000036 | v21 | False/400 | 223→236 | 277→363→391 | 392/394 | 0 |
| known13_bc_k2_noise005_demo_13000021 | v19 | False/400 | 271→290 | 332→None→None | None/None | 0 |
| known13_bc_k2_noise005_demo_13000021 | v20 | False/400 | 271→290 | 332→None→None | None/None | 0 |
| known13_bc_k2_noise005_demo_13000021 | budget | False/400 | 258→269 | 311→None→None | None/None | 0 |
| known13_bc_k2_noise005_demo_13000021 | recenter | False/400 | 271→290 | 332→None→None | None/None | 0 |
| known13_bc_k2_noise005_demo_13000021 | place | False/400 | 271→290 | 332→None→None | None/None | 0 |
| known13_bc_k2_noise005_demo_13000021 | v21 | False/400 | 271→290 | 332→None→None | None/None | 0 |
| known13_full_s41_noise005_demo_13000022 | v19 | False/400 | 387→None | None→None→None | None/None | 6 |
| known13_full_s41_noise005_demo_13000022 | v20 | False/400 | 387→None | None→None→None | None/None | 6 |
| known13_full_s41_noise005_demo_13000022 | budget | False/400 | None→None | None→None→None | None/None | 0 |
| known13_full_s41_noise005_demo_13000022 | recenter | False/400 | 387→None | None→None→None | None/None | 6 |
| known13_full_s41_noise005_demo_13000022 | place | False/400 | 387→None | None→None→None | None/None | 6 |
| known13_full_s41_noise005_demo_13000022 | v21 | False/400 | 387→None | None→None→None | None/None | 6 |
| clearance_profile_6000005 | v19 | False/400 | 299→328 | 362→None→None | None/None | 10 |
| clearance_profile_6000005 | v20 | False/400 | 299→None | None→None→None | None/None | 25 |
| clearance_profile_6000005 | budget | True/382 | 287→301 | 337→349→372 | 373/375 | 0 |
| clearance_profile_6000005 | recenter | False/400 | 299→328 | 362→None→None | None/None | 9 |
| clearance_profile_6000005 | place | False/400 | 299→328 | 362→None→None | None/None | 10 |
| clearance_profile_6000005 | v21 | False/400 | 299→328 | 362→None→None | None/None | 9 |

五帧只用于原CARRY路径到位；PLACE仍使用原物体XY/高度/age释放条件。
handoff21风险反馈仅是当前观测启发式，不是未来几何或成功证明；相同输入逐位比较仅限保存的共同状态/队列前缀。
详细手指脉冲、D2队列、位姿误差、连续到位帧与每次阶段目标见同名JSON；精确重定位五谓词见独立recenter回放回执。
