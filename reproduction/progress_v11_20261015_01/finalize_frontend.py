"""Reconcile the new page with completed v11 evidence; never modify historical pages."""
from pathlib import Path
import json
RUN=Path(__file__).resolve().parent
ROOT=RUN.parents[1]
STUDY=ROOT/'reproduction/improvement_v11_20261015_01'

def main():
    page=RUN/'demo/index.html'
    html=page.read_text(encoding='utf8')
    assert 'id="edge-v11"' not in html
    html=html.replace('联合选择倾斜方向、手指闭合方向和抓取高度，验证罐体进入两指之间的空间。保持400步，先做小测试与消融。',
        '已知箱沿380步完成；开发235/240，低于v6的236/240。局部修复保留，整体未采用；下一步处理已持物却仍等待支撑的问题。')
    html=html.replace('本轮正在验证。历史结果不代表v11结果；主版本仍为v5。','本轮已完成397次实验执行。主版本仍为v5。')
    marker='<details class="progress-details"><summary>v10历史诊断：轨迹和真实接触</summary>'
    extra='''<details class="progress-details"><summary>开发240回合：全部八种条件</summary>
<p>冻结后执行；30个已有开发起点 × BC / Full三种子 × 两种噪声。历史v6与v11逐起点配对，不是240个独立起点。</p>
<div class="table-scroll"><table><thead><tr><th>条件</th><th>历史v6 /30</th><th>v11 /30</th></tr></thead><tbody id="development-table"></tbody></table></div>
<p>新箱沿模块触发0次。唯一退步为Full seed41、噪声0.05、demo_87；全部240回合用冻结v10回放命令完全一致，问题属于继承的等待分支。未进入新的独立确认。</p></details>
<div id="edge-v11" class="edge-evidence">
<div class="latest-heading"><div><p class="eyebrow">V11 / 同状态原始回放</p><h2>箱沿这一例，完成了。</h2></div><a href="#v11-diagnosis">也看开发退步 ↓</a></div>
<p class="version-note">BC k=2 · 噪声0.05 · demo_6000005。左侧v10失败400步，右侧v11成功380步。这个已知案例用于诊断，不代表整体成功率提升，也不是新的独立确认。</p>
<video id="edge-player" class="recovery-player" src="v11_edge20/bc_wall_edge.mp4" poster="v11_edge20/poster.png" controls playsinline preload="metadata" aria-label="v10与v11箱沿同起点对比"></video>
<div class="recovery-select"><button id="edge-play" class="text-button" type="button">播放箱沿对比 ▶</button><a href="v11_edge20/bc_wall_edge.mp4" download>下载原视频 ↓</a><a href="../edge_replay_validation.json">查看回放核验 ↗</a></div>
<p id="edge-error" hidden role="alert">视频暂时无法播放，请使用下载链接或检查本地服务。</p>
<p class="selection-note">逐控制步渲染20 fps，保存状态、奖励和成功标记逐步一致；未平滑动作。成功后保持真实终点。原始曲线在成功步停止，视频停帧不新增实验样本。</p>
<details class="progress-details"><summary>四组消融：原始高度、目标距离与开度曲线</summary><p>v10 / axis / guard各30/37，合用v11为31/37。axis也抓起并搬运，但400步时未完成放置，不能解释为单纯未抓住。</p>
<a href="../../improvement_v11_20261015_01/analysis/wall_edge_comparison.png"><img class="evidence-plot" src="../../improvement_v11_20261015_01/analysis/wall_edge_comparison.png" loading="lazy" alt="四组箱沿原始轨迹：合用v11在380步成功，其余三组到400步未完成"></a>
<a href="../../improvement_v11_20261015_01/analysis/wall_edge_trajectories.csv">下载逐步数据 ↗</a></details>
<details id="v11-diagnosis" class="progress-details"><summary>开发退步：抓住了，为什么还在等？</summary>
<p>罐子随夹爪升起后，旧姿态变化保护进入等待；等待分支没有更新抓持判断，仍在等罐子落到水平支撑面。180–400步二者相对位置最大波动仅约0.3 mm，却没有进入搬运。这是继承逻辑问题；本轮新箱沿模块未触发。</p>
<a href="../../improvement_v11_20261015_01/analysis/development_regression.png"><img class="evidence-plot" src="../../improvement_v11_20261015_01/analysis/development_regression.png" loading="lazy" alt="同一起点v6在358步完成，v11持物等待至400步失败；相对距离稳定但未向目标搬运"></a>
<p>下一步：等待和撤退期间持续确认抓持，确认后转入搬运，同时保留未知支撑保护。尚未实施。</p><a href="../../improvement_v11_20261015_01/analysis/development_regression_diagnosis.json">查看240回合命令一致性与诊断数值 ↗</a></details></div>
'''
    assert marker in html
    html=html.replace(marker,extra+marker)
    html=html.replace('下方视频与v10诊断图为历史记录，不代表v11。','本节为v11新证据；后续原始、v6/v8视频与v4/v5动画保持历史版本标签。')
    html=html.replace('本区尚不是 v9 的机器人视频。','本区不包含 v9–v11；v11新视频见上方箱沿对比。')
    html=html.replace('尚不是 v6、v7 或 v8 / v9 的动画。','不包含 v6–v11 的动画。')
    html=html.replace('本次整合没有新训练或策略回合。结果与图来自已冻结资产；旧根文档、旧页面、权重和记录保留。','本段链接为历史主线资料；本轮v11新增397次实际实验执行，详见页面顶部报告。未进行新训练，旧文档、页面、权重和记录保留。')
    page.write_text(html,encoding='utf8')
    css=RUN/'demo/progress.css'
    with css.open('a',encoding='utf8') as f:f.write('\n.edge-evidence{margin-top:42px;padding-top:32px;border-top:1px solid #e5e7eb;scroll-margin-top:90px}.evidence-plot{display:block;width:100%;height:auto;border-radius:12px;margin:20px 0}.edge-evidence .recovery-select{justify-content:center}#v11-diagnosis{scroll-margin-top:90px}\n')
    doc=ROOT/'README.md';s=doc.read_text(encoding='utf8')
    s=s.replace('v11罐体接近空间实验进行中，旧资产保留，主版本仍为v5。','v11实验已完成：箱沿案例修复，开发235/240低于v6的236/240，未采用。旧资产保留，主版本仍为v5。')
    s=s.replace('当前整合版包含 v11 的实验状态、20 fps 历史机器人视频、世界模型与 v5 冻结主结果，以及 v6/v8 同起点历史恢复对比。','当前整合版包含 v11 最终结果、v10/v11同起点箱沿20 fps新视频、原始轨迹与开发退步诊断，以及世界模型与v5冻结主结果、v6/v8历史恢复对比。')
    s=s.replace('| `reproduction/improvement_v10_20261015_01/` | 箱沿高度/路径消融、接触诊断与完整核验 |','| `reproduction/improvement_v10_20261015_01/` | 箱沿高度/路径消融、接触诊断与完整核验 |\n| `reproduction/improvement_v11_20261015_01/` | 罐体包络、四组消融、240回合开发和持物等待诊断 |')
    s=s.replace('本轮箱沿接近结果见 [v10 完整报告](reproduction/improvement_v10_20261015_01/REPORT.md)','本轮箱沿与开发结果见 [v11 完整报告](reproduction/improvement_v11_20261015_01/REPORT.md)，历史箱沿接近见 [v10 报告](reproduction/improvement_v10_20261015_01/REPORT.md)')
    s=s.replace('reproduction\\improvement_v10_20261015_01\\verify_integrity.py','reproduction\\improvement_v11_20261015_01\\verify_integrity.py').replace('9,435 个路径','9,787 个路径')
    s+='''\n## v11 进展（2026-10-15）\n\n联合倾斜/闭合方向、抓取高度和罐体包络开度检查。9回合小测试、148回合四组消融与240回合开发均完成，共397次执行。已知诊断v11为31/37，v10/axis/guard均30/37；箱沿已知失败在380步完成，但未超过历史v6的31/37。\n\n冻结后的开发v11为235/240，v6为236/240；一例Full seed41噪声条件退步。全部240回合新箱沿模块未触发，冻结v10回放产生完全相同的命令。已定位为继承的“已经持物，却仍等待水平支撑”状态转换问题。v11未采用，未进入独立确认；主版本仍为v5。\n\n[完整报告与原始证据](reproduction/improvement_v11_20261015_01/REPORT.md) · [新视频与前端说明](reproduction/progress_v11_20261015_01/README.md)。本轮根文件改前原样备份在 `reproduction/improvement_v11_20261015_01/before/`，旧代码、权重和结果保留。\n'''
    doc.write_text(s,encoding='utf8')
    print('Final page and root navigation updated; experimental sources unchanged.')

if __name__=='__main__':main()
