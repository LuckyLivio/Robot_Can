"""Publish stage-separated results only after independent evaluation is checked."""
from pathlib import Path
import csv,json,shutil
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def load(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,s):p.write_text(s,encoding='utf8')
if __name__=='__main__':
    if (RUN/'REPORT.md').exists():
        raise SystemExit('Final report already exists; do not overwrite reviewed delivery or prepend duplicate banners.')
    d=load(RUN/'analysis/confirmation.json');dev=load(RUN/'analysis/dev_a.json');pilot=load(RUN/'analysis/pilot_a.json')
    diag=load(RUN/'analysis/confirmation_diagnosis.json');attribution=load(RUN/'analysis/confirmation_attribution.json');eff=d['statistics']['v12_minus_v6'];lo,hi=eff['ci95_percent']
    a=d['variants']['v12']['success'];b=d['variants']['v6']['success'];events=d['variants']['v12']['wait_transfers']
    gate='通过' if d['adoption_gate_passed'] else '未通过'
    inference='配对区间高于零，支持本批次条件内成功率改善。' if d['positive_primary_ci'] else '配对区间没有高于零，不能宣称总体成功率提升。'
    table='\n'.join(f"| {r['condition']} | {r['v6_success']}/60 | {r['v12_success']}/60 | {len(r['rescues'])} | {len(r['regressions'])} |" for r in d['conditions'])
    validation=[]
    for stage in ['smoke_a','pilot_a','dev_a','confirmation']:
        v=load(RUN/'analysis'/f'{stage}_verification.json');p=load(RUN/'analysis'/f'{stage}_physics.json')
        assert v['passed'] and p['passed'];validation.append(f"| {stage} | {v['episodes']}回合/{v['controls']}步 | {p['episodes']}回合/{p['steps']}步 |")
    negative='\n'.join(f"- `{r['job']}` / `{r['demo']}`：最终 `{r['last_mode']}`，罐体高度 {r['object_z_m']:.3f}m，目标水平距离 {r['goal_xy_m']:.3f}m，尝试 {r['attempts']} 次。" for r in diag['failure_records'] if r['job'].startswith('v12_'))
    report=f'''# v12整体评估：等待抓持修复与独立确认

2026-10-15。完成9次小测试、114次三组消融、240次开发和960次独立确认，共1323次实际评估执行。物理回放核验和视频回放不计作新增统计样本。没有训练、替换旧权重或撰写论文正文。

## 结论

已知“抓住后仍等待”被修复：Full s41、噪声0.05、demo87在149步确认抓持、264步完成，原v11为400步失败。开发从v11的235/240恢复到236/240，与v6持平，无v6原成功退步。

全新60起点确认：v12 **{a}/480**，v6 **{b}/480**；净差 **{eff['estimate_percent']:+.3f}个百分点，95%配对区间[{lo:.3f}, {hi:.3f}]**，救回{len(d['rescues'])}次、退步{len(d['regressions'])}次。预设“不低于v6且无配对退步”门槛**{gate}**。{inference} 不以一批内零退步证明普遍安全或总体等价。

**本轮不采用v12替换正式版本。** 旧v5冻结主成果继续保留；本批未配对重跑v5，不能跨批声称v12优于v5。v6与v12比较包含继承v7—v11的变化；新增等待分支的单独归因来自v11/history/v12消融。

## 1. 最小实现及限制

仅新目录 `recovery/recovery_controller.py` 继承原v11。在POSE_WAIT/POSE_BLOCKED维护历史；RETRACT已有历史更新，不重复采样。原抓持规则要求上一步执行夹爪闭合或已有确认，而等待阶段保持开度的动作是0，因此仅补历史不够。

完整v12允许在连续多步中心位置、有效开度、无张爪、物体/夹爪共同抬升至少20mm、4mm相对跟随误差条件满足后，保留当前朝向转入原LIFT/CARRY。真实失抓仍进入原恢复路径。400步、20Hz、D2队列、最多两次尝试不变；没有删除未知可行性或路径保护。控制器不读取接触、奖励、成功标签或未来仿真。

这是基于观测的抓持代理，不是力闭合证明。外部支撑与夹爪完全同步移动产生观测等价时，有限状态信号不能保证区分；合成机制测试只覆盖明确构造的情形，不等于真实世界安全验证。

## 2. 小测试、消融和开发

| 阶段 | v11 | 仅补历史 | v12 |
|---|---:|---:|---:|
| 小测试 | 2/3 | 2/3 | 3/3 |
| 37旧条件 + 已知demo87 | 31/38 | 31/38 | 32/38 |
| 开发240（历史v11参考） | 235/240 | 未运行 | 236/240 |

旧37条件三组均31成功；v12保留v6/v11原成功。其37条实际轨迹与v11逐动作、逐状态一致；唯一变化是新增demo87。开发240中239轨迹与v11逐值一致，唯一变化仍是demo87。从最小范围修复机制缺陷，但没有新增解决v6原失败。

关闭新开关的38个案例/10816步精确回归；合成测试覆盖持物、贴近未持物、支撑运动、碰撞、偏心、开口过大、张爪和失抓。详见 [机制检查](analysis/mechanisms_a.json)、[消融](analysis/pilot_a.json)、[开发](analysis/dev_a.json)。

开发剩余四次失败为BC干净demo124、Full s23干净demo188/demo97、Full s41干净demo97：涉及失抓后掉出区域及没有通过可行性检查的侧倒/箱格抓取。没有用等待修复覆盖这些问题。

## 3. 独立确认：先冻结，再生成新起点

在开发及物理核验通过后，锁定60个原生reset随机种子和配对噪声。全部保留，无结果筛选。与既有HDF5初始状态逐一比较无重合；第二个原生环境逆序再生成精确一致，第三个环境核验序列化恢复。登记：[冻结](protocols/freeze_before_states.json)、[起点校验](analysis/confirmation_state_validation.json)、[最终锁](protocols/confirmation_lock.json)。

| 条件 | v6 | v12 | 救回 | 退步 |
|---|---:|---:|---:|---:|
{table}

480是每版本执行次数，独立起点是60；BC是一个固定权重，Full是三个固定训练种子。每起点八条件作为一组bootstrap，20000次、种子2026101512。不是480个独立起点，也不代表任意重新训练的不确定性；分项区间不做多重比较校正。

v12等待抓持转换在确认中触发 **{events}** 次。该批没有证明新增分支的泛化效果。冻结v11在这批v12保存输入上回放，**{attribution['v11_commands_identical_entire_trajectory']}/480条完整轨迹、62700步命令逐值相同**；支持将退步归于继承逻辑，不归于本次新增抓持转换。此为保存输入的命令回放，不冒充另跑480次v11闭环实验。

9次退步集中在3个起点：demo12000011占7次，demo12000036和demo12000021各1次。它们进入POSE_WAIT后到POSE_BLOCKED，未再执行抓取。终态静态几何诊断中7次为侧倒箱沿支撑族不支持、1次未识别到水平支撑、1次为倾斜姿态族不支持。这里的unknown表示现有几何规则无法验证，不等于物理上必然抓不到；v6在对应条件完成了任务。进一步扩大可行域必须补路径证书与碰撞验证，不能简单取消保护。事件和逐例几何见 [确认诊断](analysis/confirmation_diagnosis.json)、[继承归因](analysis/confirmation_attribution.json)。

配对明细：[CSV](analysis/confirmation_pairs.csv)；完整汇总：[JSON](analysis/confirmation.json)。

## 4. 核验、计算与图像

| 阶段 | 命令/FIFO/状态与预算核验 | 物理逐步回放 |
|---|---|---|
{chr(10).join(validation)}

物理样本包含每任务首起点、全部失败及所有等待抓持事件。计时含BC/WM和监督器，不含物理、渲染及写日志；四进程并行，开发与视频渲染有部分重叠，因此不作纯算法加速或硬实时保证。

新增4张600dpi图及矢量PDF/SVG和CSV，[图目录](figures/CATALOG.json)。曲线使用每个真实控制步，不平滑，不延长成功曲线。demo87的v11与history曲线逐值一致，合并显示；噪声造成的微小起伏保留。视频20fps/20Hz、421帧，成功后保持终点，保存动作物理回放逐步一致。[视频核验](analysis/demo_replay.json)。

运行期间只有评估调度器增加了调用既有v6对照的分支，发生在开发冻结之前；v12控制器从小测试到确认没有修改。图像检查脚本曾因Poppler工具路径定位失败，改用已有PATH查找后通过，未改变图数据或实验。没有事后调参、改起点、调低门槛或覆盖失败。

## 5. 保全、论文价值与下一步

旧代码、权重、结果及历史写作包保留；当前导航文档改前原样存入before。新控制器、协议、源码快照、逐步轨迹、统计、失败、视频与图均在本目录。最新完整性检查为 `verify_integrity.py`；旧检查清单绑定旧版根文档，应按历史快照解释，不改旧清单消除差异。

项目仍适合系统设计与实验分析型本科论文：本轮增加了一个可归因、可回放的恢复状态转换修复。它不证明新的世界模型算法优势，也未解决开发泛化、所有侧倒/箱格抓取或掉出工作区。论文正文和泛化训练均未开始。

建议先收束本轮。若继续v13，优先检查支撑识别里的两个硬性限制：箱沿只接受直立、部分倾斜姿态一律当作未稳定；并检查支撑识别使用物体包围盒中心是否遗漏部分箱沿接触。先用保存状态区分保守误拒和真实不可行，再为已稳定的侧倒箱沿/斜靠物体生成受限抓取候选，保留手指/箱体/物体间隙、关节限位和完整路径核验。未知或未通过路径检查仍不能下降；撤退后允许有界重评估，防止剩余200多步只停在BLOCKED。v6、v11和v12都保留为对照，只改这一因素。不得使用本次独立确认起点继续调参后仍称其为独立测试；如纳入下轮开发，须标明已知并另锁新确认起点。以上是后续方案，本轮没有实施v13。

## 独立确认未完成任务记录（状态描述，不擅自推断根因）

{negative or '本批v12没有失败。有限批次全成功不等于普遍成功保证。'}
'''
    write(RUN/'REPORT.md',report)
    headline=f'v12已完成：开发236/240；全新60起点确认v12 {a}/480、v6 {b}/480；救回{len(d["rescues"])}、退步{len(d["regressions"])}。对照门槛{gate}；{inference}'
    banner=f'> **v12更新（2026-10-15）**：{headline} [报告](reproduction/improvement_v12_20261015_01/REPORT.md) · [新前端](reproduction/improvement_v12_20261015_01/index.html)。旧v5冻结证据及全部旧资产保留。\n\n'
    docs=['README.md','index.html','STATUS.md','DEMO_GUIDE.md','RESULTS.md','EVIDENCE_INDEX.md','PROJECT_NAVIGATION.md','THESIS_HANDOFF_LATEST.md','PROGRAM_GUIDE.md']
    for n in docs:
        p=ROOT/n;backup=RUN/'before'/n
        if not backup.exists():shutil.copy2(p,backup)
        if n=='index.html':continue
        s=p.read_text(encoding='utf8')
        if n=='README.md' and s.startswith('> **v12 进行中'):s=s.split('\n\n',1)[1]
        s=s.replace('2026-10-15论文图表复查：','历史阶段：2026-10-15论文图表复查：')
        s=s.replace('reproduction\\paper_quality_20261015_01\\verify.py','reproduction\\improvement_v12_20261015_01\\verify_integrity.py')
        s=s.replace('[当前校验](reproduction/paper_quality_20261015_01/verify.py)','[当前校验](reproduction/improvement_v12_20261015_01/verify_integrity.py)')
        if n=='README.md':
            s=s.replace('也可以[直接打开成果页面](http://127.0.0.1:8766/reproduction/progress_v11_20261015_01/demo/index.html)。','也可以[直接打开v12成果页面](http://127.0.0.1:8766/reproduction/improvement_v12_20261015_01/index.html)。')
            s=s.replace('当前整合版包含 v11','历史整合版包含 v11').replace('| 当前整合版，推荐 |','| 历史完整整合版 |')
            s=s.replace('## 最新优化进展（2026-10-15）','## 历史优化进展（2026-10-15，v12之前）')
            s=s.replace('本轮箱沿与开发结果见','历史箱沿与开发结果见')
            s=s.replace('当前36张论文图','此前36张论文图')
        if n=='STATUS.md':
            s=s.replace('最新开发候选为v11，未采用。','最新完成候选为v12；本批结果见页首。v11曾未通过开发门槛。')
            s=s.replace('持物等待分支的状态切换；','剩余侧倒/箱格抓取可行性和掉出区域问题；')
            s=s.replace('v12控制修复未开始。','v12控制修复及新起点确认已完成，见页首报告。')
            s=s.replace('reproduction/progress_v11_20261015_01/demo/index.html','reproduction/improvement_v12_20261015_01/index.html')
            s=s.replace('reproduction/paper_quality_20261015_01/verify.py','reproduction/improvement_v12_20261015_01/verify_integrity.py')
        if n=='DEMO_GUIDE.md':
            s=s.replace('当前成果展示与讲解顺序','此前v11完整展示与讲解顺序')
            s=s.replace('1. 先看最新进展：','1. 回顾此前进展：')
            s='先打开页首v12前端：核对四阶段结果 → 播放demo87同起点20fps对比 → 查看60起点配对确认与失败边界 → 再进入下方历史完整展示。\n\n'+s
        if n=='EVIDENCE_INDEX.md':
            s=s.replace('[当前展示](reproduction/progress_v11_20261015_01/demo/index.html)','[当前展示](reproduction/improvement_v12_20261015_01/index.html)')
        if n=='THESIS_HANDOFF_LATEST.md':
            s='**本轮v12尚未打入旧ZIP。换设备时还须带上 `reproduction/improvement_v12_20261015_01/` 或使用同步后的完整Git项目；不能拿旧包声称包含本轮实验。**\n\n'+s
        write(p,banner+s)
    write(RUN/'document_changes.json',json.dumps({'updated':docs},indent=2))
    write(RUN/'SUMMARY.json',json.dumps({'headline':headline,'new_executions':1323,'independent_starts':60,'adoption_gate_passed':d['adoption_gate_passed'],'positive_primary_ci':d['positive_primary_ci']},ensure_ascii=False,indent=2))
    print(headline)
