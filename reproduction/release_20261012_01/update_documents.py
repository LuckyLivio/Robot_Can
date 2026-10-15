"""Build current documentation from frozen evidence; archive already exists."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
CONF=ROOT/'reproduction/confirmation_20261012_01';MULTI=ROOT/'reproduction/multiseed_20261012_01'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def csvread(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows)

def main():
    a=read(CONF/'analysis/analysis.json');env=read(CONF/'environment.json');design=read(RUN/'demo_design.json')
    def summ(m,c):return next(x for x in a['summary'] if x['method']==m and x['condition']==c)
    labels={'bc_k2':'BC k=2','full':'Full','plain':'Plain（去排序）'}
    primary=[]
    for m in labels:
        row=[labels[m]]
        for c in ('clean','noise005'):
            x=summ(m,c)
            counts=str(x['success_s17_or_fixed_bc']) if m=='bc_k2' else '、'.join(str(x[k]) for k in ('success_s17_or_fixed_bc','success_s23','success_s41'))
            row.append(f"{counts}；{x['mean_success_percent']:.2f}%")
        primary.append(row)
    primary_table=table(['方法','干净：成功数；平均成功率','噪声0.05：成功数；平均成功率'],primary)
    effects=table(['比较','条件','平均差（百分点）','描述性95%配对区间'],[
        [f"{labels[x['left']]} − {labels[x['right']]}",x['condition'],f"{x['mean_difference_pp']:+.2f}",f"[{x['paired_crossed_bootstrap_low_pp']:+.2f}, {x['paired_crossed_bootstrap_high_pp']:+.2f}]"] for x in a['paired']])
    dev=csvread(MULTI/'analysis/summary.csv');devrows=[]
    names={'bc_k0':'BC k=0','bc_k1':'BC k=1','bc_k2':'BC k=2','full':'Full','plain':'Plain','direct':'Direct（匹配参数量）','prediction_only':'只预测+物理代价','head_control':'评分头续训对照','calibrated':'评分头校准','no_risk_score':'去部署风险惩罚','no_gate':'去门限','horizon4':'H=4'}
    for m,label in names.items():
        row=[label]
        for noise in (0.,.05):
            d=next(x for x in dev if x['method']==m and float(x['noise'])==noise)
            counts='、'.join(d[k] for k in ('success_s17','success_s23','success_s41') if d[k])
            row.append(f"{counts}；{float(d['mean_success_percent']):.2f}%")
        devrows.append(row)
    dev_table=table(['方法','开发集干净：成功数；均值','开发集噪声：成功数；均值'],devrows)
    banner='版本：2026-10-12 冻结确认后的文档整理版。历史文档完整保存在 [previous_documents](reproduction/release_20261012_01/previous_documents/)。\n'
    evidence='[三种子开发消融](reproduction/multiseed_20261012_01/analysis/report.txt) · [独立确认报告](reproduction/confirmation_20261012_01/analysis/report.txt) · [冻结哈希清单](reproduction/release_20261012_01/frozen_results.json)'
    docs={}
    docs['README.md']=f'''# 动作延迟下的机器人世界模型控制

{banner}
Panda 机械臂在 PickPlaceCan 仿真中抓取罐子并放入目标箱。固定 BC 动作块策略提供候选；世界模型预测候选后果并用进度/抓持丢失评分选择动作，通过 FIFO 执行队列模拟 2 步延迟。

**当前范围是包含物体真值的23维低维状态控制，未实现纯视觉或真机验证。** 已完成三种子公平消融及冻结后的60个新起点确认。本仓库是实现、复现与实验分析项目，未证明各条件均显著领先或排序模块具有稳定独立增益。

## 当前入口

- [PROGRAM_GUIDE](PROGRAM_GUIDE.md)：环境、模块和可复制命令。
- [RESULTS](RESULTS.md)：当前结果，开发与确认分表。
- [STATISTICS](STATISTICS.md)：统计单位、区间和解释边界。
- [THESIS_OUTLINE](THESIS_OUTLINE.md)：更新后的论文提纲与证据映射。
- [DEMO_GUIDE](DEMO_GUIDE.md)：相同起点机器人对比演示及讲解顺序。
- [STATUS](STATUS.md)：已完成、未完成及交付边界。

## 冻结确认摘要

每个控制器/条件60回合；Full、Plain按训练种子17、23、41列出成功数。BC为一个固定权重。

{primary_table}

Full相对BC在干净、加噪条件的平均提升分别为5.00、4.44个百分点；分条件95%配对区间均接触零。预登记两条件等权综合提升4.72个百分点，描述性区间[0.56,10.28]；仍应结合小样本和Full−Plain结果解释。{evidence}

## 保存约定

不覆盖 models、policy、data、既有reproduction和figures中的原始文件。新演示位于 `reproduction/release_20261012_01/demo/`。冻结表示哈希锁定与防覆盖流程，并非修改文件系统只读属性。

根目录 `make_figures.py`、`RESULTS_TABLE.csv` 及旧 `figures/` 是历史产物，不用于当前主结论；本轮图表在 [确认图目录](reproduction/confirmation_20261012_01/analysis/) 和 [三种子图目录](reproduction/multiseed_20261012_01/analysis/)。
'''
    docs['RESULTS.md']=f'''# 当前实验结果与论文表述

{banner}
{evidence}

## 1. 冻结后的独立确认（论文主结果）

60个新起点按原生环境初始化规则预先生成，保存XML、完整初始状态和逐步执行噪声后锁定。运行14组、840条回合记录，实际独立起点为60个。Full、Plain各保留三个训练种子17、23、41，固定BC只运行一次/条件。未根据确认结果调参、换种子或再训练。

{primary_table}

每个成功数的分母均为60。确认设置：D=2、H=8、K=4、k=2回退、门限0.02、风险惩罚权重0.5、400步上限、干净/归一化位置动作噪声标准差0.05。

{effects}

`joint_equal_weight`是预登记的干净/加噪等权综合指标，不是新增独立样本。Full的三个种子在两种条件下都高于BC和对应Plain；干净相对BC每个种子独胜3、独败0，加噪独胜3/3/2、独败0。改善集中在少数起点，不能把综合bootstrap区间为正写成所有条件均显著或通用性能保证。

## 2. 三种子公平消融（开发证据）

下表每个成功数分母30；三数依次对应17、23、41。开发集参与过方法分析，不与新确认集合并。共60组、1800条相关回合记录，不是1800个独立任务。

{dev_table}

Full/Plain/只预测使用同架构和配对初始化、训练批次；Direct宽度251，总参数87364，Full为87321。基础模型统一3000次更新、每批16组、Adam学习率0.0003；每250步按预登记开发分支指标选点。评分头续训和校准各额外3000次更新，应只在同预算两组间比较，不冒充与基础模型等预算。

解读：开发集Full并未稳定超过Plain；新确认Full的点估计较好，Full−Plain区间仍接触/跨越零，因此排序项增益未确立。评分头校准降低离线误差但未提高相对续训对照的闭环成功率。去门限的加噪开发表现较弱，可作为有利趋势，不能当作安全保证。只预测对照全程选k=2，与BC重合，不能用来证明预测监督完全无用。去风险仅移除部署惩罚，训练风险监督仍保留。

## 3. 历史结果与当前结果的关系

旧恢复/分支采集不一致已修复；`fixed_20261011_*`、queue覆盖、同状态候选真值、headcal和tailprobe保留为探索轨迹。旧sealed_test已经查看和用于分析，不能继续称为完全未见；旧k=1主表不能替换当前k=2强基线。`RESULTS_TABLE.csv`和旧图是历史快照，原文件保留，不参与本表计算。

## 4. 可用结论

可以写：实现并验证了延迟队列、世界模型候选评分和保守回退闭环；三种子新起点确认观察到相对强固定偏移基线的正向趋势，并明确了小样本不确定性与模块局限。

不能写：显著击败所有基线；首次提出世界模型/排序监督；评分头校准已稳定改善控制；纯视觉控制或真机安全已经验证；对演示案例的选择构成新独立测试。
'''
    docs['STATISTICS.md']=f'''# 当前统计口径

{banner}
## 样本与配对

开发阶段是30个父轨迹起点，确认阶段是另外60个原生随机起点。两者分别汇报。Full/Plain训练种子17、23、41使用固定训练数据，因此可评价初始化/训练随机性，不能代替新的训练数据采样。BC只有一个固定权重，在配对计算中共享，不计作三个独立训练结果。

确认阶段7个控制器×2个条件×60起点=840回合。相同起点和同条件的噪声逐步配对；干净/加噪也共享起点。每个起点只有一个加噪序列，不外推至所有随机扰动。

## 指标

主指标为400步内首次达到环境成功；达到即停止，失败完整运行400步。平均步数须说明失败按400截断；只统计成功回合会产生选择偏差。门限覆盖比例按实际步骤加权。并行运行的决策计时含日志等开销且通常不含BC前向，不作为完整控制环的实时性基准。

## 区间算法

按[冻结设计](reproduction/confirmation_20261012_01/design.json)，使用NumPy default_rng(2026101203)，20000次交叉bootstrap：有放回抽3个训练种子和60个起点；所有方法共享抽样索引，同一轮中所有种子共享起点索引。先计算同一起点的成功差，再求均值；取2.5%和97.5%分位数。综合指标先将两个条件等权平均，再用相同配对方案重采样。

这是描述性区间，不是所有比较的同时置信区间或等效性检验。仅3个种子及少量独胜/独败起点使离散percentile区间较粗；区间接触零不能证明无效，综合区间为正也不自动证明严格显著性。禁止把840回合展开为独立伯努利样本来缩窄区间。

{effects}

## 验证证据

新旧评估核心530步历史轨迹一致；60个状态可按种子精确重生成；另两组QA起点反向重放40步误差为0。正式确认提前选定前两个起点做全方法轨迹记录，共9061步FIFO和噪声逐值核对通过。见[验证记录](reproduction/confirmation_20261012_01/analysis/result_validation.json)。

演示是结果已知后的说明性选择，按规则选取最小编号，重新运行只用于复核与渲染，不计入以上统计。
'''
    docs['PROTOCOL.md']=f'''# 项目协议与冻结版本索引

{banner}
本文档统一当前研究范围和证据入口；2026-10-08原始协议已[原样归档](reproduction/release_20261012_01/previous_documents/PROTOCOL.md)。本次文档修订发生在实验完成之后，不是追溯性预注册。真正的执行前登记保留在各实验design/protocol/lock JSON中，不作修改。

## 研究问题与边界

在PickPlaceCan低维特权状态仿真中，固定BC动作块与FIFO延迟D=2下，学习的动作条件世界模型能否通过候选评分改善强BC k=2基线？排序监督、风险惩罚和门限各提供什么证据？预测/评分误差改善是否转化为闭环成功率？

部署输入包含物体真实位置/姿态。候选真实未来后果只用于离线采集或诊断，不作为部署选择输入。演示图像只用于展示；未完成视觉或真机实验。模型预测进度/抓持丢失，评分门限不是校准后的置信概率。

## 数据与公平性

Can PH：200条示范，父轨迹划分140训练/30开发/30历史sealed；相关窗口和分支不跨父轨迹划分。修复控制器缓存/观测刷新与FIFO实际执行序列后，采用 `branches_{{train,dev}}_queuepair_20261012_01_real`：训练20父轨迹160组，开发8父轨迹64组，每组4候选×8步。

保留有竞争力的BC k=2；模型比较控制训练数据、候选集合、时域、预算和初始化。所有种子均汇报，不能只取最优种子。使用共同初始状态与扰动做成对比较。若确认后改方法，建立新版本与新确认样本，不复用本轮起点冒充未见。

## 当前执行记录

| 阶段 | 预登记/锁定文件 | 用途 |
| --- | --- | --- |
| 三种子公平消融 | [protocol.json](reproduction/multiseed_20261012_01/protocol.json) | 固定17/23/41，匹配预算，开发分析 |
| 新起点确认设计 | [design.json](reproduction/confirmation_20261012_01/design.json) | 状态生成之前确定60种子与规则 |
| 确认执行锁定 | [lock.json](reproduction/confirmation_20261012_01/lock.json) | 全部确认评估之前哈希锁定 |
| 当前成果冻结 | [frozen_results.json](reproduction/release_20261012_01/frozen_results.json) | 文档/演示阶段保护全部既有权重与结果 |

## 未完成项

原始探索清单中的弱持续性基线、全面真值排序、视觉扩展、多任务/真机验证没有全部完成；不得根据已有3种子与60起点就宣布所有原始计划均完成。当前论文范围收束为已实测的实现、复现与实验分析。正式学校/导师要求尚未提供。

当前[方法协议](DELAY_PROTOCOL.md)、[结果](RESULTS.md)、[统计](STATISTICS.md)为阅读入口。早期[执行偏差适应协议](ADAPTIVE_PROTOCOL.md)作为另一条历史探索线保留，不混入本轮主表。
'''
    docs['DELAY_PROTOCOL.md']=f'''# 动作延迟下的世界模型控制：当前方法说明

{banner}
这是对已锁定实现的说明，原预登记文件见[PROTOCOL](PROTOCOL.md)。

## 输入与时序

输入23维状态：末端位置/四元数、夹爪关节位置、物体相对及绝对状态，含物体真值。BC是宽度512、5个混合分量的动作块策略，产生8×7动作。`policy_15000.pt`固定不动。索引k=2表示选BC预测动作块的第3个动作，不是读取真实未来，也不保证精确抵消动力学延迟。

控制频率20Hz；FIFO长度D=2，名义100ms。每回合队列以两条全零动作初始化；每步先提交新命令，再执行队首，随后获取新观测并重规划。噪声加在实际出队动作的前三个归一化分量，标准差0或0.05，然后clip到[-1,1]；不是0.05米物体位置噪声。

## 预测与选择

四个候选为BC索引0、1、2、3的动作。预测序列由当前两条待执行命令加重复候选命令组成，截取H=8。预测假设重复候选，真实执行只承诺本步新命令；下一观测再规划，这一短期想象与长期闭环后果的差别需讨论。

归一化状态z=(x−mean)/scale；h=init(z)。逐步更新h=GRUCell([z,a],h)，z←z+0.1·delta(h)，输出物理状态z·scale+mean。宽度128、87321参数；`future_only=True`时评分头只读预测的归一化状态z。

令p、r为进度和风险头sigmoid输出，J=p末步+0.5·mean(p)−0.5·max(r)。先选择最大J候选；若其不是k=2且J最佳−J₂<0.02，则回退k=2。门限是预测评分差，不是概率置信度，也没有安全保证。

训练标签：进度取环境成功时1，否则分阶段奖励最大值；风险为“初始分支已抓持、之后失去抓持且未成功”。它不是碰撞、掉落、任何失败的通用概率。环境阶段信息和成功检查用于训练/日志/终止；候选部署评分不查询真实分支后果，但当前状态仍含物体真值。

## 配对训练与消融

Full损失=归一化状态MSE+进度BCE+0.5风险BCE+0.2组内排序损失。Plain仅去排序项。排序使用真实候选评分差绝对值>0.025的组内成对样本，softplus温度0.1，不等价于只给成功/失败候选排序。

17、23、41三个种子；Full/Plain初始化和训练批次配对。Adam 0.0003，3000次更新，每批16组，梯度裁剪10；每250步用开发分支平均评分遗憾选点，平局取最早。Direct参数量匹配，但没有状态预测；只预测对照按开发状态MSE选点；额外评分头训练预算另计。详见[开发登记](reproduction/multiseed_20261012_01/protocol.json)。

## 评价

独立确认仅含BC k=2、Full和Plain全部三个种子，各在60个共同新起点下运行干净和加噪条件。400步内环境首次成功为主指标。原开发/历史sealed结果不并入确认。主表与统计解释见[RESULTS](RESULTS.md)和[STATISTICS](STATISTICS.md)。
'''
    docs['STATUS.md']=f'''# 项目当前状态

{banner}
## 已完成

- 本地`.venv`环境及仿真运行验证；Python {env['python'].split()[0]}、PyTorch {env['packages']['torch']}、robosuite {env['packages']['robosuite']}、MuJoCo {env['packages']['mujoco']}。
- 分支恢复与FIFO采集一致性修复；相同状态下候选预测/真实后果诊断。
- 三种子公平训练、参数匹配Direct、同预算评分头对照与开发消融。
- 冻结BC k=2、Full、Plain后的60个新起点确认，14组840回合及配对统计。
- 当前成果哈希锁定，旧文档归档，项目文档/论文提纲统一；同起点演示及其验收入口见[DEMO_GUIDE](DEMO_GUIDE.md)。

## 结论边界

Full确认均值为干净90.00%、噪声86.11%，BC为85.00%、81.67%，Plain为88.33%、83.89%。观察到正向趋势；分条件和排序项比较不足以支持稳定显著优势。校准离线改善不等价于闭环提升。完整数值见[RESULTS](RESULTS.md)。

## 尚需完成

论文正文、正式参考文献格式、学校模板排版、导师审阅及答辩材料仍未完成。本轮是提纲和演示整理，不生成或宣称完成全文。题目建议“考虑动作延迟的机器人世界模型控制方法实现与实验分析”；未提供正式任务书，不能据此保证毕业审核通过。

纯视觉、真机、多任务、更多独立训练数据集不在当前已完成范围。无需为包装结果继续围绕已看过的60个确认起点调参。若另立性能研究，需先新版本/新协议，再使用新的确认起点。

## 当前证据入口

{evidence}

[原始总体评估](reproduction/confirmation_20261012_01/analysis/overall_assessment.txt)是本次文档整理之前的冻结历史快照，其中“旧文档未更新/演示未完成”描述的是当时状态；交付现状以本页及[release验收](reproduction/release_20261012_01/release_validation.json)为准。
'''
    docs['PROGRAM_GUIDE.md']=f'''# 项目运行与模块指南

{banner}
项目路径：`C:\\Users\\Livio\\Desktop\\robot_can`。PyCharm解释器使用已有`.venv\\Scripts\\python.exe`，工作目录设为项目根目录；不重建或替换环境。

## 1. 当前环境

Python {env['python'].split()[0]}；PyTorch {env['packages']['torch']}；NumPy {env['packages']['numpy']}；robosuite {env['packages']['robosuite']}；MuJoCo {env['packages']['mujoco']}。训练使用既有GPU；确认评估使用CPU，每进程2个torch线程。完整配置见[environment.json](reproduction/confirmation_20261012_01/environment.json)。视频使用当前机器已有FFmpeg和Pillow/OpenCV，不改变训练依赖。

```powershell
Set-Location 'C:\\Users\\Livio\\Desktop\\robot_can'
$PY = '.\\.venv\\Scripts\\python.exe'
& $PY -X utf8 -B -u '.\\reproduction\\release_20261012_01\\verify_release.py'
```

该命令核对冻结文件、演示及文档验收清单，不重新训练。

## 2. 模块职责

| 模块 | 作用 |
| --- | --- |
| common.py | 数据/环境构造、23维状态打包、恢复仿真和控制器缓存、BC加载 |
| train_policy.py | 示范学习动作块BC；本轮沿用冻结policy_15000.pt |
| collect_rollout_branches.py | 回放完整动作历史，同状态/真实FIFO下采集候选分支与标签 |
| world_model.py | GRU残差动力学、未来状态评分头、组内排序损失、Direct对照 |
| train_world.py / multiseed目录train_suite.py | 基础训练入口 / 已验证的配对种子训练编排 |
| evaluate_delay.py | 延迟队列与候选门限闭环；原始核心保留 |
| diagnose_candidate_truth.py / calibrate_score_head.py | 真实后果诊断 / 评分头校准探索 |
| confirmation目录prepare_states.py、evaluate_confirmation.py | 锁定新起点 / 调用不变的评估核心 |
| confirmation目录analyze_confirmation.py | 从原始JSON生成配对统计和PNG/PDF |
| release目录make_demo.py | 重复运行核对、精确动作回放、并排视频及本地展示页 |

## 3. 直接看当前成果

先读[结果](RESULTS.md)，再打开[演示页面](reproduction/release_20261012_01/demo/index.html)。使用本地服务的方法和逐段讲解见[DEMO_GUIDE](DEMO_GUIDE.md)。主图为[确认成功率](reproduction/confirmation_20261012_01/analysis/confirmation_success.png)与[配对差异](reproduction/confirmation_20261012_01/analysis/paired_effects.png)，无需重新计算。

## 4. 核对已完成确认任务

```powershell
& $PY -X utf8 -B -u '.\\reproduction\\confirmation_20261012_01\\run_confirmation.py'
```

完整任务会核对输入及输出哈希后跳过，不覆盖结果；发现中断日志会停止要求检查。确认数据、全部7个权重及控制参数见[design.json](reproduction/confirmation_20261012_01/design.json)与[lock.json](reproduction/confirmation_20261012_01/lock.json)。不能为了重跑而删除原输出或改锁定清单。

## 5. 另开目录重跑开发训练（可选，不是看演示的前置步骤）

```powershell
& '.\\reproduction\\multiseed_20261012_01\\rerun.ps1' -Tag ('multiseed_repeat_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
```

该命令训练并评估整套开发消融，耗时明显较长；自动新建目录，不替换当前权重。后续若改算法，需要另立预登记确认实验，不能把目前60个起点再次当未见数据。

## 6. 权重与旧文件

BC：`policy/bc_chunk_dev_v4/policy_15000.pt`。Full/Plain：`models/multiseed_20261012_01_{{full,plain}}_s{{17,23,41}}/model.pt`。不将某个确认表现最好种子提升为全局默认。

用户最初提供的`model.pt`仍保留为旧版本权重；其用途和当时哈希见[首次检查归档](reproduction/release_20261012_01/previous_documents/REPRODUCTION_PLAN.md)。旧`make_figures.py`包含历史固定数组，旧`RESULTS_TABLE.csv`和`figures/`不作当前图表入口。所有既有文件保留，历史试验与当前主表分开。
'''
    docs['REPRODUCTION_PLAN.md']=f'''# 复现阶段验收与后续交付

{banner}
2026-10-11的首次检查、环境安装和旧权重核对计划已[完整归档](reproduction/release_20261012_01/previous_documents/REPRODUCTION_PLAN.md)。其中“环境未装依赖”等描述仅对应当时；当前`.venv`已经完成训练、仿真和评估。运行入口以[PROGRAM_GUIDE](PROGRAM_GUIDE.md)为准。

## 当前已走完的复现链

1. 核对原始数据、用户权重、环境与父轨迹划分。
2. 修复状态恢复时控制器缓存/观测刷新，以及分支采集实际FIFO动作的一致性。
3. 在开发集进行队列覆盖、相同状态候选真实后果、评分头校准和预测动作续接诊断，保留正负结果。
4. 采用17、23、41三个训练种子，配对数据、初始化、训练批次与预算，完成核心公平消融。
5. 冻结BC k=2、Full、Plain；执行预登记60个新起点、两扰动条件的独立确认，保存840条记录和配对区间。
6. 冻结现有结果，归档旧文档，统一当前说明和论文提纲，制作相同起点下的并排机器人案例演示。

## 验收边界

历史数值原样复跑、修复后的科学复核和论文交付是三个不同目标。当前已验证工程链路与本阶段实验设计，观察到Full在新起点上的正向趋势；未证明全部条件显著领先，未完成所有早期探索条目，未完成论文全文、视觉或真机验证。

不合并旧开发/历史sealed与新确认以增加样本量。新确认已读结果，之后再次使用只可称复核或演示。视频里的成功与失败案例按规则选取，不计入新的成功率统计。

## 下一阶段

依据[THESIS_OUTLINE](THESIS_OUTLINE.md)写正文；正文按章节引用原始证据、开发消融与独立确认分表。核查文献全文与正式书目信息，完成学校模板排版。按照[DEMO_GUIDE](DEMO_GUIDE.md)展示同状态控制过程及失败边界，再由导师确认题目、范围与学校要求。
'''
    old=(RUN/'previous_documents/ADAPTIVE_PROTOCOL.md').read_text(encoding='utf-8')
    docs['ADAPTIVE_PROTOCOL.md']='# 历史探索说明\n\n本文件以下内容为早期执行偏差适应路线，保留作为研究过程记录，**不是当前FIFO延迟论文主协议，也不是当前独立确认的结果**。当前入口见[PROTOCOL](PROTOCOL.md)与[DELAY_PROTOCOL](DELAY_PROTOCOL.md)。旧文原件在[文档归档](reproduction/release_20261012_01/previous_documents/ADAPTIVE_PROTOCOL.md)。\n\n---\n\n'+old
    docs['THESIS_OUTLINE.md']=f'''# 本科论文提纲：考虑动作延迟的机器人世界模型控制方法实现与实验分析

{banner}
这是依据当前代码与已完成实验的可写提纲，不是全文或学校格式认证。用户未提供正式任务书/评分标准；`criteria_binding_unavailable`。建议中文正文约10000字，仅为写作分配参考，最终以学校/导师要求为准。采用“问题—方法—工程复核—开发消融—独立确认—局限”的实证结构。

## 研究问题与贡献口径

- RQ1：在23维状态输入、D=2与固定BC下，预测后果选择候选是否改善BC k=2？用冻结新起点确认回答。
- RQ2：排序监督、风险惩罚和门限是否分别改善控制？用匹配三种子开发消融及Full/Plain确认回答，承认不确定性。
- RQ3：状态恢复一致性、预测/评分误差与长期闭环效果如何关联？用恢复验证、同状态真值诊断与校准对照回答，避免把相关观察写成因果证明。

贡献定位为可复核的机器人延迟控制实现、实验一致性修复和受控分析。世界模型、候选排序与风险评分均有既有研究，不宣称首次发明；不把低维特权状态实验写成纯视觉或真机方法。

## 第一章 绪论（约1000字）

1.1 机器人指令延迟和执行扰动的实际问题；本实验仅模拟固定延迟与指定噪声，不冒充真实网络/硬件测量。1.2 世界模型预测后果与行为克隆的联系。1.3 明确RQ1—RQ3、实现范围与贡献。1.4 章节安排。

证据：环境/控制器代码和[当前方法协议](DELAY_PROTOCOL.md)。本章引出强固定偏移基线的重要性，进入相关工作。

## 第二章 相关工作与基础（约1500字）

2.1 从离线人类示范学习机器人行为；数据质量和评估方式。2.2 学习动力学与模型预测控制：像素潜变量规划和本文23维状态递归预测的区别。2.3 决策相关模型学习与排序目标：把预测误差转化为控制改善不是自动成立的。2.4 视觉世界模型背景及本文未完成的视觉扩展。2.5 对比表列输入信息、预测对象、规划方式、训练目标与评估范围，不引用未经核实的跨论文成功率比较。

文献入口见末尾已核对的四个官方摘要/出版页；它们用于结构定位，详细技术论断仍须读原文及定位页码，不声称已经完成系统综述。承接到本文任务定义。

## 第三章 任务、系统实现与复现一致性（约1800字）

3.1 PickPlaceCan、Panda、OSC_POSE、20Hz与23维特权状态；图3-1采用实际仿真截图，注明图像只用于展示。3.2 Can PH的200条父轨迹及140/30/30划分；分支继承父轨迹，历史sealed已使用。3.3 长度2的FIFO初始化、入队出队时序、噪声施加位置与400步成功定义。3.4 恢复仿真、控制器缓存和相对观测的同步；说明为何仅恢复MuJoCo平面状态不足以重建中途分支。3.5 完整历史回放采集真实队列分支，给出一致性验证与代码模块图。

证据：`common.py`、`collect_rollout_branches.py`、[确认状态验证](reproduction/confirmation_20261012_01/state_validation.json)、[确认轨迹验收](reproduction/confirmation_20261012_01/analysis/result_validation.json)。只报告验证实际覆盖的范围，不把全部潜在恢复情形写成已证明。

## 第四章 候选预测评分与门限控制（约1800字）

4.1 BC混合密度动作块，H=8、7维动作；解释k=2是预测动作块偏移，不是读取真实未来。4.2 四个候选k=0..3，预测序列由当前FIFO前缀与重复候选构成；每步只提交一个命令，下一观测重规划。4.3 GRU归一化状态残差递推：h′=GRU([z,a],h)，z′=z+0.1·delta(h′)；未来状态评分头只读z′。4.4 Full损失及Plain去排序；排序阈值0.025/温度0.1，进度为软标签，风险为初始抓持条件下的抓持丢失。4.5 J=p末步+0.5均值p−0.5最大r，若最佳非k=2且J差<0.02则回退；不能将评分差称为校准置信度。4.6 预测时域内重复候选与实际滚动控制的差异。

证据：`world_model.py`、`collect_branches.py`、`evaluate_delay.py`及[三种子登记](reproduction/multiseed_20261012_01/protocol.json)。输入物体真值的权限必须明确；真实候选未来后果只用于训练/诊断。

## 第五章 实验设计与结果（约2500字）

5.1 实验环境、数据规模和预算。Full/Plain各87321参数，Direct匹配到87364；17/23/41，3000次基础更新，开发选点；评分头实验额外预算单列。5.2 开发集基线与公平消融，使用[RESULTS开发表](RESULTS.md)，解释校准离线改善未稳定转化为闭环成功。5.3 60个新起点的事前生成/锁定、相同噪声与全部种子确认；列design、lock及代码/权重哈希。5.4 主结果和成对区间，开发与确认分表不合并。5.5 同起点演示：明确事后说明性分类选择、固定种子17、统一时间轴、成功后停帧，并展示共同失败。5.6 验证与统计限制。

主表每个成功数分母60，三数顺序17/23/41：

{primary_table}

必须同时写出：Full−BC干净+5.00个百分点，95%描述性区间[0.00,11.67]；加噪+4.44，[0.00,10.00]。等权综合+4.72，[0.56,10.28]；Full−Plain干净+1.67，[0.00,5.00]，加噪+2.22，[-1.11,6.67]。支持正向趋势，未满足预先设定的跨条件、对BC与Plain均为正区间的较强优势标准。

说明840条记录共用60起点，BC未独立训练三个种子，bootstrap采用配对训练种子/起点交叉重采样。只有3训练种子、少量独胜起点；区间不是多重比较校正或等效性证明。决策耗时不是完整控制环延迟基准。

## 第六章 讨论与局限（约1000字）

6.1 新确认的正向趋势与开发集波动，明确权重未改变。6.2 排序标签区分度与短时评分/长时任务后果之间的距离，列证据和未验证假说。6.3 门限的作用与局限，不能承诺安全。6.4 固定数据、单任务、低维真值、单种加噪实现和小样本统计限制。6.5 若继续研究，应另设开发目标与新确认；视觉/真实机器人是未来工作。

证据：[总体评估](reproduction/confirmation_20261012_01/analysis/overall_assessment.txt)、[开发分析](reproduction/multiseed_20261012_01/analysis/overall_assessment.txt)、[同状态诊断目录](reproduction/candidate_truth_20261012_01/)。不能用精选演示证明普遍优势。

## 第七章 总结（约400字）

按RQ1—RQ3回顾已实现、已观察和仍不确定的内容。结论应与第五章数值一致；不把提纲、运行验证或视频包装成完成了视觉/真机研究。列出可复现资产与后续论文交付任务。

## 图表与证据映射

| 图表 | 章节/RQ | 证据或已有图 |
| --- | --- | --- |
| 图3-1 同状态机器人画面 | 第三章/RQ3 | [演示页面](reproduction/release_20261012_01/demo/index.html)，截图和视频均来源实际仿真 |
| 图4-1 FIFO、候选与预测评分流程 | 第四章/RQ1 | common/world_model/evaluate_delay实际调用关系；旧k=1流程图不复用 |
| 表5-1 环境、参数和训练预算 | 第五章/RQ1—3 | [环境](reproduction/confirmation_20261012_01/environment.json)、[模型元数据](reproduction/multiseed_20261012_01/analysis/model_metadata.csv) |
| 表5-2/图5-1 三种子开发消融 | 第五章/RQ2 | [开发原表](reproduction/multiseed_20261012_01/analysis/summary.csv)、[开发图](reproduction/multiseed_20261012_01/analysis/multiseed_success.png) |
| 表5-3/图5-2 独立确认主结果 | 第五章/RQ1 | [确认原表](reproduction/confirmation_20261012_01/analysis/summary.csv)、[确认图](reproduction/confirmation_20261012_01/analysis/confirmation_success.png) |
| 图5-3 配对效果区间 | 第五章/RQ1—2 | [配对原表](reproduction/confirmation_20261012_01/analysis/paired_comparisons.csv)、[区间图](reproduction/confirmation_20261012_01/analysis/paired_effects.png) |
| 图5-4 逐时域位置预测误差 | 第五章/RQ3 | [物理预测图](reproduction/multiseed_20261012_01/offline/physical_prediction.png) |
| 表5-4 演示案例规则及胜负 | 第五章/RQ1—3 | [事后案例选择登记](reproduction/release_20261012_01/demo_design.json)、DEMO_GUIDE |

## 已核对的文献入口（2026-10-12）

1. Ajay Mandlekar等，*What Matters in Learning from Offline Human Demonstrations for Robot Manipulation*，CoRL 2021。已核对标题、作者列表、会议说明和摘要；用于示范学习/评估背景。[原始摘要页](https://arxiv.org/abs/2108.03298)
2. Danijar Hafner等，*Learning Latent Dynamics for Planning from Pixels*，arXiv:1811.04551，2018提交、2019修订。用于学习动力学与在线规划的背景，不能据此称本项目为像素输入实现。[原始摘要页](https://arxiv.org/abs/1811.04551)
3. Amir-Massoud Farahmand、Andre Barreto、Daniel Nikovski，*Value-Aware Loss Function for Model-based Reinforcement Learning*，AISTATS/PMLR54，1486–1494，2017。用于决策相关模型损失的背景；本文排序损失不是VAML原算法复现。[正式出版页](https://proceedings.mlr.press/v54/farahmand17a.html)
4. Gaoyue Zhou、Hengkai Pan、Yann LeCun、Lerrel Pinto，*DINO-WM: World Models on Pre-trained Visual Features enable Zero-shot Planning*，arXiv:2411.04983，2024提交、2025修订。用于视觉特征预测/规划背景；本项目没有实现DINO视觉编码器。[原始摘要页](https://arxiv.org/abs/2411.04983)

核验范围为上述页面的元信息与摘要；未在本轮逐页审核全文，也不声称用户已阅读。正式论文需继续核验具体技术论断、页码和学校参考文献格式。删除旧提纲中不存在的本地papers路径；原阅读清单仍在历史归档，不作已读/已核实证据。
'''
    for name,content in docs.items():(ROOT/name).write_text(content,encoding='utf-8')
    (RUN/'documentation_sources.json').write_text(json.dumps({'primary':str(CONF.relative_to(ROOT)),'development':str(MULTI.relative_to(ROOT)),'updated':list(docs),'references_checked':'4 primary abstract/publication pages; full texts not audited','paper_scope':'outline-only; no full manuscript or institution conformity certification'},indent=2),encoding='utf-8')
    print('updated_documents',len(docs))

if __name__=='__main__':main()
