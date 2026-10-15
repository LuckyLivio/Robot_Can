"""Refine only this new local presentation and its documentation."""
from pathlib import Path
RUN=Path(__file__).resolve().parent
ROOT=RUN.parents[1]

def main():
 p=RUN/'demo/index.html';s=p.read_text(encoding='utf8')
 if 'world-model.css' in s:
  raise SystemExit('This one-time presentation migration is already applied; current assets remain unchanged.')
 s=s.replace('机器人延迟控制与失败恢复：查看冻结实验、原始机器人视频、真实日志轨迹与研究证据。','世界模型驱动的延迟机器人操控：预测候选后果、同起点机器人对比、受控实验与论文改进贡献。')
 s=s.replace('CAN LAB · 控制、恢复与证据','CAN LAB · 世界模型驱动的机器人操控')
 s=s.replace('<link rel="stylesheet" href="consolidation.css">','<link rel="stylesheet" href="consolidation.css"><link rel="stylesheet" href="world-model.css">')
 s=s.replace('<script src="consolidation.js" defer></script>','<script src="consolidation.js" defer></script><script src="world-model-data.js" defer></script><script src="world-model.js" defer></script>')
 s=s.replace('跳到成果总览','跳到世界模型方法')
 s=s.replace('<a href="#overview">成果</a><a href="#demo">视频</a><a href="#recovery">恢复</a><a href="#evidence">文档</a>','<a href="#demo">演示</a><a href="#results">优势</a><a href="#innovation">贡献</a><a href="#evidence">证据</a>')
 start=s.index('  <section class="hero');end=s.index('  <section id="demo"')
 s=s[:start]+'''  <section class="hero wrap" aria-labelledby="hero-title">
    <div class="hero-text"><p class="eyebrow">WORLD MODEL / 世界模型驱动的延迟机器人操控</p>
      <h1 id="hero-title">先预测后果。<br><span>再决定动作。</span></h1>
      <p class="hero-copy">机器人发出的指令，要在 100 ms 后执行。<br>世界模型为四个候选预估未来，再选择下一步。</p>
      <div class="hero-actions"><a class="primary-link" href="#demo">看机器人对比 ↗</a><a href="#innovation">看论文改进与贡献 →</a></div>
      <p class="scope-line">Panda · PickPlaceCan · 23维低维仿真状态<br>400步预算 · 3个训练种子 · 原独立确认60个起点</p>
    </div>
    <div class="hero-visual"><div class="visual-top"><span>ACTION → FUTURE</span><span id="visual-stage">读取状态</span></div>
      <h2>同一个现在。<br>比较不同的未来。</h2>
      <svg class="branch-svg" viewBox="0 0 420 190" role="img" aria-labelledby="branch-title branch-desc">
        <title id="branch-title">世界模型候选展开机制示意</title><desc id="branch-desc">共同的两步FIFO命令前缀，接入四个不同动作候选，预测后结合进展与风险评分，再提交一个动作。线条是概念示意，不是实验轨迹。</desc>
        <defs><linearGradient id="branch-blue"><stop stop-color="#50afff"/><stop offset="1" stop-color="#95d3ff"/></linearGradient></defs>
        <rect x="2" y="63" width="105" height="65" rx="15" fill="#303746" stroke="#4a556a"/>
        <text x="54" y="88" text-anchor="middle" fill="#edf4ff" font-size="12">当前状态</text><text x="54" y="110" text-anchor="middle" fill="#9faec5" font-size="10">2步待执行命令</text>
        <g fill="none" stroke="#56667f" stroke-width="2"><path d="M107 96H130Q145 96 145 24H172"/><path d="M107 96H140Q153 96 153 71H172"/><path d="M107 96H140Q153 96 153 120H172"/><path d="M107 96H130Q145 96 145 167H172"/></g>
        <g fill="#d0dded" font-size="10"><text x="181" y="19">k=0</text><text x="181" y="66">k=1</text><text x="181" y="115">k=2</text><text x="181" y="162">k=3</text></g>
        <g fill="none" stroke-width="2.6" stroke-linecap="round"><path d="M174 27C216 27 227 42 286 28" stroke="#677589"/><path d="M174 75C215 75 234 58 286 69" stroke="url(#branch-blue)"/><path d="M174 124C221 124 232 116 286 123" stroke="#8996aa"/><path d="M174 171C221 171 235 146 286 166" stroke="#677589"/></g>
        <g fill="none" stroke="#51647c" stroke-width="1.7"><path d="M293 28H300Q315 28 315 91H329"/><path d="M293 69H306Q315 69 315 91H329"/><path d="M293 123H306Q315 123 315 99H329"/><path d="M293 166H300Q315 166 315 99H329"/></g>
        <rect x="329" y="62" width="87" height="66" rx="15" fill="#173b64" stroke="#468fd6"/>
        <text x="372" y="88" text-anchor="middle" fill="#e2f1ff" font-size="12">进展 / 风险</text><text x="372" y="110" text-anchor="middle" fill="#9dc4ee" font-size="10">门限 + 回退</text>
      </svg>
      <p class="visual-caption">4 个候选 · H=8（含2步队列前缀）· 提交1个动作<br>机制示意，线条不代表实际预测轨迹。</p>
    </div>
  </section>
  <div class="highlight-strip wrap" aria-label="世界模型证据概览">
    <article><h3>原独立确认 · 干净成功率</h3><div class="highlight-value"><span id="headline-success">90</span><small>%</small></div><p>Full 三种子均值<br>BC k=2：85%</p></article>
    <article><h3>原独立确认 · 两条件等权增益</h3><div class="highlight-value"><span id="headline-effect">+4.72</span><small> pp</small></div><p>Full 相对 BC k=2<br>95% 配对区间 [0.56, 10.28]</p></article>
    <article><h3>开发集诊断 · 物体预测误差</h3><div class="highlight-value">−<span data-object-gain>32.8</span><small>%</small></div><p>Full 相对状态保持弱基线<br><span class="metric-source">复用的8个开发父起点；非独立确认</span></p></article>
  </div>

  <section id="overview" class="wrap overview" aria-labelledby="overview-title">
    <div class="section-heading"><div><p class="eyebrow">01 / HOW IT WORKS</p><h2 id="overview-title">把动作，先放进模型里试一遍。</h2></div><a class="quiet-link" href="../../../CONTRIBUTIONS.md">方法与贡献边界 ↗</a></div>
    <div class="method-steps" role="group" aria-label="世界模型决策流程">
      <button type="button" data-model-step="0" aria-pressed="true"><span>01 / OBSERVE</span><strong>读取同一状态</strong><small>固定BC提出四个动作候选</small></button>
      <button type="button" data-model-step="1" aria-pressed="false"><span>02 / ALIGN DELAY</span><strong>还原实际延迟</strong><small>先展开队列里的两条命令</small></button>
      <button type="button" data-model-step="2" aria-pressed="false"><span>03 / IMAGINE</span><strong>预测候选后果</strong><small>未来8步，比较进展和失抓风险</small></button>
      <button type="button" data-model-step="3" aria-pressed="false"><span>04 / REPLAN</span><strong>执行，再规划</strong><small>优势足够才替换强BC回退</small></button>
    </div>
    <p class="method-note" id="model-step-detail" aria-live="polite"></p>
  </section>

'''+s[end:]
 s=s.replace('02 / ORIGINAL ROBOT VIDEOS','02 / SEE THE DIFFERENCE').replace('同一起点，三种选择。','这个起点，Full 完成了搬运。')
 s=s.replace('这是原始世界模型实验的冻结视频，未加入后续共享恢复。后面的 v5 以日志轨迹单独呈现。','默认展示 Full 独胜：同一起点，Full 在133步完成，BC k=2与Plain在400步内未完成。也可切换共同成功和失败，查看适用边界。视频均未加入后续共享恢复。')
 s=s.replace('data-case="shared_success" aria-pressed="true"','data-case="shared_success" aria-pressed="false"').replace('data-case="full_only_success" aria-pressed="false"','data-case="full_only_success" aria-pressed="true"')
 s=s.replace('原确认：有趋势，也有不确定性。','从一个案例，回到整组实验。')
 s=s.replace('    <p class="result-footnote">','    <div class="joint-result"><strong>+4.72 个百分点</strong><p>原确认的两种预设条件等权汇总：Full相对BC k=2为正向收益，95%配对区间[0.56,10.28]。60个独立起点、三训练种子；并不表示每个起点都改善。</p></div>\n    <p class="result-footnote">',1)
 pos=s.index('  <section id="recovery"')
 s=s[:pos]+'''  <section id="prediction" class="wrap prediction-section" aria-labelledby="prediction-title">
    <div class="section-heading"><div><p class="eyebrow">04 / PREDICTION EVIDENCE</p><h2 id="prediction-title">预测到动作后果，才有比较的依据。</h2></div><a class="quiet-link" href="../../extensions_20261012_01/offline_metrics.json">已有开发集测量 ↗</a></div>
    <div class="prediction-layout"><div><h3>会变化的物体，<br>不能只用“原地不动”预测。</h3><div class="prediction-gain">−<span data-object-gain>32.8</span><span>%</span></div><p>Full 的物体位置 RMSE<br>相对持续性弱基线降低</p><p>52.03 mm → 34.95 mm<br>开发机制诊断，三种子均值</p></div>
      <figure><img src="../figures/prediction_rmse.svg" alt="开发集位置RMSE，单位毫米：持续性末端59.17物体52.03；Plain末端29.96物体26.97；Full末端31.04物体34.95。越低越好。" loading="lazy"><figcaption>64组分支 · 8个已复用开发父起点 · 所有方法同时展示</figcaption></figure>
    </div>
    <p class="dataset-note">这些父起点参与过开发与检查点选择，不能证明独立泛化。Plain的这两项位置误差更低；状态误差更小，也不自动意味着任务成功率更高。</p>
    <details><summary>完整误差、短期真值对照与实验范围<span aria-hidden="true">+</span></summary><div class="detail-body"><div class="table-scroll"><table><thead><tr><th>方法</th><th>末端 RMSE /mm</th><th>物体 RMSE /mm</th><th>归一化状态 MSE</th></tr></thead><tbody id="prediction-table"></tbody></table></div><p>持续性将23维状态保持为当前观测，无动作依赖。真值短期候选排序、H=1与候选数扫描均已完成；完美的短期仿真也不能替代长期抓持和搬运。</p><a href="../../extensions_20261012_01/REPORT.md">查看补充实验与负结果 ↗</a></div></details>
  </section>

  <section id="innovation" class="innovation-section" aria-labelledby="innovation-title"><div class="wrap">
    <div class="section-heading"><div><p class="eyebrow">05 / THESIS CONTRIBUTIONS</p><h2 id="innovation-title">论文改进与贡献，落在具体问题上。</h2></div></div>
    <p class="section-intro">世界模型提供候选后果，项目把它接入有延迟的执行闭环，并通过对照定位收益和失败。以下是已有实现与证据支持的贡献范围。</p>
    <div class="innovation-grid">
      <article><span class="line-index">01 / 延迟一致的候选预测</span><h3>预测和真实执行，<br>使用同一条命令队列。</h3><p>把控制器、传感器与FIFO状态纳入分支恢复，修正采集不一致；模型先预测待执行命令，再比较候选。</p><span class="innovation-tag">系统实现与一致性验证</span></article>
      <article><span class="line-index">02 / 面向任务的候选评分</span><h3>比较任务进展，<br>也考虑失抓后果。</h3><p>结合动力学、进展与风险学习，加入候选排序和BC回退门限。三种子、Plain与真值对照检验机制；排序独立增益尚未确立。</p><span class="innovation-tag">方法设计与受控实验</span></article>
      <article><span class="line-index">03 / 有限预算的失败恢复</span><h3>确认抓持，<br>再安排剩余搬运。</h3><p>抓持确认、无进展检测与几何/剩余时间约束，在400步内最多恢复两次。BC和Full共享这层控制，收益单独报告。</p><span class="innovation-tag">工程扩展与边界分析</span></article>
    </div>
    <a class="detail-link" href="../../../CONTRIBUTIONS.md">查看贡献、外部来源与不能夸大的结论 ↗</a>
  </div></section>

'''+s[pos:]
 s=s.replace('04 / RECOVERY V5','06 / SHARED RECOVERY').replace('05 / OBSERVED TRAJECTORIES','07 / RECOVERY IN DETAIL').replace('06 / RESEARCH & DELIVERY','08 / RESEARCH & DELIVERY')
 s=s.replace('    <div class="recovery-summary">','    <p class="secondary-label">辅助模块 · 以下收益属于共享恢复控制</p>\n    <div class="recovery-summary">')
 s=s.replace('CAN LAB · CONTROL WITH EVIDENCE','CAN LAB · WORLD MODEL / ROBOTICS')
 p.write_text(s,encoding='utf8')
 p=RUN/'demo/app.js';s=p.read_text(encoding='utf8').replace("selectedCase='shared_success'","selectedCase='full_only_success'")
 s=s.replace("box.className='outcome';","box.className='outcome';")
 p.write_text(s,encoding='utf8')
 print('Refined only the new presentation; original sources and recordings preserved.')

if __name__=='__main__':main()
