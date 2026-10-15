"""Render only saved evidence; pending stages never masquerade as results."""
from pathlib import Path
import html,json,re
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def load(p):return json.loads(p.read_text(encoding='utf8'))
style=re.search(r'<style>(.*?)</style>',(ROOT/'reproduction/improvement_v12_20261015_01/index.html').read_text(encoding='utf8'),re.S).group(1)
style+='\n.metric-row{display:flex;justify-content:space-between;gap:16px;padding:5px 0;color:#abb6c4}.metric-row strong{color:#eef3f9;font-variant-numeric:tabular-nums}.metric-list{margin:18px 0}\n'
cards=[]
for stage,label in [('smoke_e','最终小测试'),('pilot_a','四组消融'),('dev_a','开发对照'),('confirmation','全新起点确认')]:
    p=RUN/'analysis'/f'{stage}.json'
    if p.exists():
        d=load(p);labels={'support':'仅支撑 S','escape':'仅撤退 R'}
        body='<div class="metric-list">'+''.join(f'<div class="metric-row"><span>{html.escape(labels.get(v,v))}</span><strong>{s["success"]}/{s["episodes"]}</strong></div>' for v,s in d['variants'].items())+'</div>'
        title='已完成';link=f'<a href="analysis/{stage}.json">原始汇总 ↗</a>'
    else:
        title='运行已结束 · 核验中' if (RUN/stage/'completed.json').exists() else ('运行中' if (RUN/stage/'started.json').exists() else '待前阶段达标')
        body='<p>保持预设门槛和400步总预算。</p>';link=''
    cards.append(f'<article><small>{label}</small><h3>{title}</h3>{body}{link}</article>')
status='小测试已通过，正在逐阶段核验；尚未形成独立确认结论。'
if (RUN/'analysis/confirmation.json').exists():
    d=load(RUN/'analysis/confirmation.json')
    status='独立确认通过预设对照门槛；结论仅限本批起点和固定条件。' if d['adoption_gate_passed'] else '独立确认未通过采用门槛，保留为候选，不替换正式版本。'
elif (RUN/'analysis/dev_a.json').exists():
    status='开发对照已达标，等待完成全新起点独立确认。' if load(RUN/'analysis/dev_a.json')['outcome_gate_passed'] else '开发未通过门槛，未进入独立确认，不替换正式版本。'
elif (RUN/'analysis/pilot_a.json').exists():
    status='消融已达标，进入开发核验。' if load(RUN/'analysis/pilot_a.json')['outcome_gate_passed'] else '消融未通过门槛，未进入开发，不替换正式版本。'
details=''
if (RUN/'analysis/confirmation.json').exists():
    d=load(RUN/'analysis/confirmation.json');effect=d['statistics']['v13_minus_v6'];ci=effect['ci95_percent']
    rows=''.join('<tr><td>'+html.escape(r['condition'])+'</td>'+''.join(f'<td>{r[v+"_success"]}/60</td>' for v in ['v6','v12','v13'])+'</tr>' for r in d['conditions'])
    pairing='；'.join(f'相对{v}救回{len(d["rescues"][v])}次、新增失败{len(d["regressions"][v])}次' for v in ['v6','v12'])
    inference='主要区间完全高于零，支持本批固定条件下的成功率改善。' if d['positive_primary_ci'] else '主要区间未完全高于零，不能宣称总体成功率改善。'
    details=f'<section><h2>独立确认 · 60个新起点</h2><p>每版本480次执行，独立统计单位为60个起点。v13-v6配对差值 {effect["estimate_percent"]:+.2f} 个百分点，95%区间 [{ci[0]:.2f}, {ci[1]:.2f}]。</p><p>{pairing}。{inference}共享恢复收益与世界模型收益分别解释，不能跨批与v5直接相减。</p><table><tr><th>条件</th><th>v6</th><th>v12</th><th>v13</th></tr>{rows}</table></section>'
video=''
for p in sorted((RUN/'demo').glob('*/comparison.mp4')) if (RUN/'demo').exists() else []:
    rel=p.relative_to(RUN).as_posix();caption=load(p.parent/'caption.json')['caption']
    video+=f'<section><h2>同起点对比 · {html.escape(caption)}</h2><p>20fps / 20Hz，保存动作逐步物理回放。已知诊断案例，不作为独立泛化证据。</p><video controls preload="metadata" poster="{rel.replace("comparison.mp4","poster.png")}" src="{rel}"></video></section>'
figures=''.join(f'<figure><img loading="lazy" src="figures/{p.name}" alt="{p.stem}"><figcaption>{p.stem} · <a href="figures/{p.stem}.pdf">矢量PDF</a> · <a href="figures/{p.stem}.csv">绘图CSV</a></figcaption></figure>' for p in sorted((RUN/'figures').glob('*.svg'))) if (RUN/'figures').exists() else ''
report='<a class="button" href="REPORT.md">整体评估报告 ↗</a>' if (RUN/'REPORT.md').exists() else '<a class="button" href="README.md">本轮说明 ↗</a>'
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>CAN LAB · v13 支撑与重规划</title><style>{style}</style>
<nav><strong>CAN LAB / RECOVERY 13</strong><span><a href="../improvement_v12_20261015_01/index.html">v12成果</a> &nbsp; <a href="../progress_v11_20261015_01/demo/index.html">历史完整展示</a> &nbsp; <a href="#evidence">本轮证据</a></span></nav>
<main><header><div class="eyebrow">SUPPORT · RETREAT · REPLAN</div><h1>识别支撑，<br>重新规划。</h1><p style="color:#f0c887;font-weight:600">{status}</p><p>侧倒箱沿与斜靠物体的稳定支撑识别，长等待后的受检撤退与重规划。原BC/世界模型权重冻结，400步、D2、20Hz保持不变。</p><a class="button" href="protocols/PLAN.md">执行前协议 ↗</a>{report}</header><div class="grid">{''.join(cards)}</div>
<section class="note"><strong>证据边界</strong><p>v12确认中已查看的失败起点，本轮属于已知诊断。只有本轮冻结后新生成的起点才属于独立确认。支撑判定是候选资格，不是力闭合或全臂安全证明；未知状态不会默认下降。</p></section>{video}{details}
<section id="evidence"><h2>实验与可复核数据</h2><p>四组：v12、仅支撑组件S、仅等待撤退组件R、组合v13。S同时包含识别、候选家族与受检路径入口。<a href="FIGURE_GUIDE.md">图表与曲线解释 ↗</a></p><p>中间小测试和失败记录保留：<a href="protocols/SMOKE_B_AMENDMENT.md">B预算修订</a> · <a href="protocols/SMOKE_C_NOTE.md">C日志格式</a> · <a href="protocols/SMOKE_D_AMENDMENT.md">D路径入口</a> · <a href="protocols/SMOKE_E_AMENDMENT.md">E必要横移与路径重验</a>。原始轨迹未平滑；成功曲线按真实终点结束。规划仍有耗时峰值，20Hz仿真不等于严格实时保证。</p>{figures}</section><footer>400 steps · D2 FIFO · 20 Hz · ≤2 grasp attempts<br>保留旧代码、权重、结果；没有泛化训练或论文正文。</footer></main></html>'''
(RUN/'index.html').write_text(page,encoding='utf8');print(status)
