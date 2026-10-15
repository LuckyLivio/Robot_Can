"""Build a current evidence view from saved results; never invent pending outcomes."""
from pathlib import Path
from itertools import zip_longest
import html,json,re
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
LABELS={'v6':'v6 参考','v13':'v13 父版本','track':'仅跟踪 T','clearance':'仅间隙 C','v14':'组合 v14'}
ORDER=['v6','v13','track','clearance','v14']
FAMILIES=[('smoke','小测试与组件对照'),('pilot','已知条件消融'),('dev','开发对照'),('confirmation','全新起点确认')]
def esc(value):return html.escape(str(value),quote=True)
def load(p):return json.loads(p.read_text(encoding='utf8'))
def exists_link(rel,label,cls=''):
    return f'<a class="{cls}" href="{esc(rel)}">{esc(label)} ↗</a>' if (RUN/rel).is_file() else f'<span class="pending-link">{esc(label)} · 待发布</span>'
def stage_sort(name):
    family=next((i for i,(prefix,_) in enumerate(FAMILIES) if name==prefix or name.startswith(prefix+'_')),99)
    return family,[int(x) if x.isdigit() else x for x in re.split(r'([0-9]+)',name)]
def discover():
    out={}
    for p in sorted((RUN/'analysis').glob('*.json')):
        if not re.fullmatch(r'(?:smoke|pilot|dev)_[a-z0-9]+|confirmation',p.stem):continue
        d=load(p)
        if 'variants' not in d or not (RUN/p.stem/'completed.json').is_file():continue
        assert d.get('stage')==p.stem and all(s['episodes']>0 and 0<=s['success']<=s['episodes'] for s in d['variants'].values())
        out[p.stem]=d
    return out
def audits(stage):
    flags=[]
    for suffix in ['verification','physics']:
        p=RUN/'analysis'/f'{stage}_{suffix}.json'
        flags.append(bool(p.exists() and load(p).get('passed')))
    return all(flags)
def outcome(d):return d.get('adoption_gate_passed') if d['stage']=='confirmation' else d.get('outcome_gate_passed')
def gate_markup(stage,d):
    if outcome(d) is False:return '<span class="badge failed">未达标 · 保留负结果</span>'
    if outcome(d) is True and audits(stage):return '<span class="badge passed">门槛与回放核验通过</span>'
    if outcome(d) is True:return '<span class="badge pending">结果达标 · 回放核验中</span>'
    return '<span class="badge pending">描述结果 · 尚无通过结论</span>'
def metrics(d):
    return '<div class="metric-list">'+''.join(f'<div class="metric-row"><span>{esc(LABELS.get(v,v))}</span><strong>{s["success"]}<em> / {s["episodes"]}</em></strong></div>' for v in ORDER if (s:=d['variants'].get(v)) is not None)+'</div>'

def main():
    evidence=discover();latest={prefix:max([n for n in evidence if n==prefix or n.startswith(prefix+'_')],key=stage_sort,default=None) for prefix,_ in FAMILIES}
    started=sorted([p.name for p in RUN.iterdir() if p.is_dir() and (p/'started.json').exists() and re.fullmatch(r'(?:smoke|pilot|dev)_[a-z0-9]+|confirmation',p.name)],key=stage_sort)
    waiting=[s for s in started if s not in evidence]
    evaluation_count=sum(sum(s['episodes'] for s in d['variants'].values()) for d in evidence.values())
    stopped_at_smoke=bool(latest['smoke'] and outcome(evidence[latest['smoke']]) is False and not waiting and not any(latest[k] for k in ['pilot','dev','confirmation']))
    status='本轮实现与小测试正在推进；尚未形成独立确认结论。';status_kind='pending'
    highest=next((latest[k] for k,_ in reversed(FAMILIES) if latest[k]),None)
    if highest:
        d=evidence[highest]
        if outcome(d) is False:
            status=f'{highest} 未通过预设门槛，保留为候选，不替换正式成果。';status_kind='failed'
        elif not audits(highest):status=f'{highest} 的描述结果已达标，动作与物理回放核验尚未全部完成。'
        elif highest=='confirmation':
            status='独立确认达到采用门槛；版本采用与结论边界见整体报告。';status_kind='passed'
        else:status=f'{highest} 的结果门槛与回放核验已通过；后续阶段仍按协议推进。';status_kind='passed'
    if waiting:status+=' '+', '.join(waiting)+' 尚无完整汇总。'
    if stopped_at_smoke:status+=' 本轮按协议停在小测试，未启动 372 回合消融、240 回合开发或 1440 回合独立确认。'
    cards=[]
    for prefix,label in FAMILIES:
        stage=latest[prefix]
        if stage:
            d=evidence[stage];body=metrics(d)+gate_markup(stage,d)
            footer=f'<a href="analysis/{stage}.json">完整统计 ↗</a> <a href="{stage}/jobs.json">条件清单 ↗</a>'
            title=stage
        else:
            active=[s for s in waiting if s==prefix or s.startswith(prefix+'_')]
            title=active[-1] if active else ('本轮未运行' if stopped_at_smoke else '等待前阶段通过')
            body='<p>运行中或待核验，尚无完整结论。</p>' if active else ('<p>小测试未达标，按协议停止后续大批量实验。</p>' if stopped_at_smoke else '<p>不提前填入成功率，不跨越预设门槛。</p>')
            footer='<span class="muted">400 步 / D2 / 原保护阈值</span>'
        cards.append(f'<article><small>{label}</small><h3>{esc(title)}</h3>{body}<div class="card-footer">{footer}</div></article>')
    revision_rows=[]
    for stage in sorted(set(started)|set(evidence),key=stage_sort):
        d=evidence.get(stage)
        counts=' · '.join(f'{LABELS.get(v,v)} {s["success"]}/{s["episodes"]}' for v,s in d['variants'].items()) if d else '暂无完整汇总，不计作已完成实验'
        gate=gate_markup(stage,d) if d else '<span class="badge pending">未完成或待汇总</span>'
        links=[]
        for path,label in [(f'analysis/{stage}.json','统计'),(f'{stage}/jobs.json','作业'),(f'{stage}/started.json','源代码哈希'),(f'analysis/{stage}_verification.json','动作回放'),(f'analysis/{stage}_physics.json','物理回放')]:
            if (RUN/path).exists():links.append(f'<a href="{esc(path)}">{label}</a>')
        revision_rows.append(f'<tr><th scope="row">{esc(stage)}</th><td>{esc(counts)}</td><td>{gate}</td><td>{" · ".join(links)}</td></tr>')
    history='<div class="scroll"><table><thead><tr><th>实验阶段</th><th>真实成功数 / 执行数</th><th>状态</th><th>复核入口</th></tr></thead><tbody>'+''.join(revision_rows)+'</tbody></table></div>' if revision_rows else '<p>尚未产生完整实验记录。</p>'
    target_section=''
    if latest['smoke']:
        stage=latest['smoke'];d=evidence[stage];jobs=load(RUN/stage/'jobs.json');rows=[]
        targets=[('斜靠接近 / BC + 噪声','known13_bc_k2_noise005_demo_13000021','demo_13000021'),('箱沿下降 / Full s41 + 噪声','known13_full_s41_noise005_demo_13000022','demo_13000022')]
        for label,suffix,demo in targets:
            cells=[]
            for v in ['v13','track','clearance','v14']:
                j=next((j for j in jobs if j['id']==v+'_'+suffix),None)
                if j is None:cells.append('<td>未纳入</td>');continue
                path=f'{stage}/{j["id"]}/result.json';raw=load(RUN/path)
                r=next(r for r in raw['records'] if r['demo']==demo)
                cells.append(f'<td><a href="{esc(path)}">{"成功" if r["success"] else "未完成"} · {r["steps"]} 步</a></td>')
            rows.append(f'<tr><th scope="row">{esc(label)}<small class="case-id">{esc(demo)}</small></th>{"".join(cells)}</tr>')
        target_section=f'<section><div class="section-heading"><span class="eyebrow">KNOWN DIAGNOSTICS</span><h2>两类问题，逐项复核。</h2></div><p>最新完整小测试 {esc(stage)}。下列起点已经用于定位问题，是已知诊断案例，不能用于独立泛化结论。</p><div class="scroll"><table><thead><tr><th>目标案例</th><th>v13</th><th>仅 T</th><th>仅 C</th><th>v14</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>'
    confirmation=''
    if 'confirmation' in evidence:
        d=evidence['confirmation'];s=d['statistics']['v14_minus_v6'];lo,hi=s['ci95_percent']
        pairs='；'.join(f'相对 {v} 救回 {len(d["rescues"][v])} 次、退步 {len(d["regressions"][v])} 次' for v in ['v6','v13'])
        inference='主要差值区间完全高于零。' if d['positive_primary_ci'] else '主要差值区间未完全高于零，不能宣称总体成功率改善。'
        rows=''.join('<tr><th scope="row">'+esc(r['condition'])+'</th>'+''.join(f'<td>{r[v+"_success"]}/{r["episodes"]}</td>' for v in ['v6','v13','v14'])+'</tr>' for r in d['conditions'])
        confirmation=f'<section><div class="section-heading"><span class="eyebrow">INDEPENDENT CONFIRMATION</span><h2>冻结后，再检验。</h2></div><p>60 个全新起点；每个起点包含八个固定条件，每版本 480 次执行。主比较 v14 − v6 为 {s["estimate_percent"]:+.2f} 个百分点，95% 区间 [{lo:.2f}, {hi:.2f}]。</p><p>{esc(pairs)}。{inference}采用门槛与总体提升主张分别判断。</p><div class="scroll"><table><thead><tr><th>条件</th><th>v6</th><th>v13</th><th>v14</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
    diagnosis=''
    if latest['smoke']=='smoke_b' and (RUN/'analysis/path_diagnosis.json').is_file():
        assert load(RUN/'analysis/path_diagnosis.json')['passed']
        jobs=load(RUN/'smoke_b/jobs.json');combined=[j for j in jobs if j['version']=='v14'];identical=0;clearance_events=0
        fields=['demo','step','state_before','state_after','submitted_action','executed_action']
        for job in combined:
            saved=load(RUN/'smoke_b'/job['id']/'result.json');clearance_events+=sum(len(r.get('clearance14_events',[])) for r in saved['records'])
            peer='track_'+job['id'].split('_',1)[1]
            with (RUN/'smoke_b'/job['id']/'trace.jsonl').open(encoding='utf8') as fa,(RUN/'smoke_b'/peer/'trace.jsonl').open(encoding='utf8') as fb:
                same=True
                for sa,sb in zip_longest(fa,fb):
                    if sa is None or sb is None:same=False;break
                    ra,rb=json.loads(sa),json.loads(sb)
                    if any(ra[k]!=rb[k] for k in fields):same=False;break
            identical+=int(same)
        attribution=f'组合 v14 的 {identical}/{len(combined)} 个条件与仅 T 的动作和状态逐步完全相同；组合中的 C 事件数为 {clearance_events}。'
        if identical==len(combined) and clearance_events==0:attribution+='本批组合结果只能体现 T 的作用，不能把改善归功于 C，也没有证明 T+C 的额外收益。'
        diagnosis=f'''<section><div class="section-heading"><span class="eyebrow">WHAT DID NOT WORK</span><h2>接近有进展，任务仍未完成。</h2></div><p>T 是路径跟踪：根据实际运动与关节余量调整接近，并核验替代路径。C 是下降间隙处理：间隙不足时停下、居中或撤退，再重新核验。</p><div class="findings-grid"><article><small>斜靠 / BC</small><h3>抓住了，仍未搬到目标。</h3><p>修订 B 在第 258 步进入下降，294 步进入抬升，311 步进入搬运。末段保持抓持，但搬运时接近关节限位，400 步内仍未成功。</p></article><article><small>箱沿 / Full s41</small><h3>旋转接近仍然超时。</h3><p>第一次旋转阶段仍在第 231 步超时。后续重规划消耗剩余预算，接近末端才靠近目标位姿，未在预算内开始下降。</p></article><article><small>间隙组件 / C</small><h3>额外恢复也会消耗时间。</h3><p>仅 C 让旧案例 demo6000005 退步：居中后完成抓取和搬运，却到第 392 步才开始释放，400 步结束时尚未成功。</p></article></div><div class="note"><strong>组件归因必须受证据限制</strong><p>{esc(attribution)}</p></div><p><a href="analysis/path_diagnosis.json">保存轨迹诊断 ↗</a> · <a href="analysis/path_diagnosis_observations.csv">逐步诊断数据 ↗</a></p><h3>下一轮建议 · 尚未执行</h3><p>优先检查持物搬运阶段的关节余量与经过核验的等价路径；箱沿旋转应更早识别无进展；间隙处理需要为抬升、搬运和释放保留剩余步数。继续保持 400 步和全部原保护阈值，先通过同一小测试与组件对照，再考虑大批量实验。</p></section>'''
    videos=[]
    for name in ['leaning','edge']:
        folder=RUN/'demo'/name
        if not (folder/'comparison.mp4').is_file() or not (folder/'caption.json').is_file():continue
        caption=load(folder/'caption.json');receipt=RUN/'analysis'/f'demo_replay_{name}.json'
        assert receipt.is_file() and load(receipt)['passed']
        failure='<span class="badge failed">两版本均在 400 步内未完成</span>' if caption.get('both_failed_at_400_steps') else ''
        videos.append(f'<article class="video-card"><div class="video-caption"><small>{esc(caption["source_stage"])} · 同起点保存动作</small><h3>{esc(caption["caption"])}</h3>{failure}</div><video controls preload="metadata" poster="demo/{name}/poster.png" src="demo/{name}/comparison.mp4" aria-label="{esc(caption["caption"])} 的 v13 与 v14 对比"></video><p>20 Hz 保存动作逐步物理重放，视频 20 fps。已知诊断失败案例，不增加统计样本，不代表总体成功率。<a href="analysis/demo_replay_{name}.json">重放核验 ↗</a></p></article>')
    video_section='<section id="demo"><div class="section-heading"><span class="eyebrow">SAME-START REPLAY</span><h2>把未完成的过程展示清楚。</h2></div><p>左侧 v13，右侧 v14。保留实际动作和任务终点，不以局部抓取成功代替完整任务成功。</p><div class="video-grid">'+''.join(videos)+'</div></section>' if videos else ''
    figures=[];catalog=RUN/'figures/CATALOG.json'
    if catalog.exists():
        for item in load(catalog):
            stem=item['id'];files=[RUN/'figures'/f'{stem}.{ext}' for ext in ['svg','pdf','png','csv']]
            if not all(p.is_file() for p in files):continue
            figures.append(f'<figure><img loading="lazy" src="figures/{esc(stem)}.svg" alt="{esc(item["caption"])}"><figcaption>{esc(item["caption"])}<div class="figure-links"><a href="figures/{esc(stem)}.pdf">矢量 PDF</a><a href="figures/{esc(stem)}.png">600 dpi PNG</a><a href="figures/{esc(stem)}.csv">绘图数据 CSV</a></div></figcaption></figure>')
    figure_body=''.join(figures) if figures else '<div class="empty-state">图表将在完整阶段结果生成后发布。图像由真实统计绘制，不填充缺失实验。</div>'
    style=re.search(r'<style>(.*?)</style>',(ROOT/'reproduction/improvement_v13_20261016_01/index.html').read_text(encoding='utf8'),re.S).group(1)
    style+='''
html{scroll-behavior:smooth;scroll-padding-top:90px}body{background:radial-gradient(ellipse at 85% 0%,#14242e 0,transparent 40%),#080b10}nav strong{font-size:13px;letter-spacing:2px}nav span{display:flex;gap:20px;font-size:13px}header{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:48px;align-items:center;padding:94px 0 58px}.hero-copy p{max-width:720px}.hero-panel{border:1px solid #35434e;border-radius:28px;padding:28px;background:linear-gradient(145deg,#18252d99,#0e141b);box-shadow:0 24px 70px #0005}.hero-panel .large-number{font-size:76px;line-height:1.1;letter-spacing:-5px;font-weight:500;color:#e8f5f2}.hero-panel .unit{color:#aebac6;font-size:13px;letter-spacing:2px}.constraint{padding:15px 0;border-top:1px solid #34414b;display:flex;justify-content:space-between;font-size:13px}.constraint strong{color:#d9ece7}.hero-status{font-size:16px;color:#e1d5af;font-weight:600;padding:14px 0;border-top:1px solid #33424d;line-height:1.7}.grid{grid-template-columns:repeat(4,minmax(0,1fr));align-items:stretch}article{display:flex;flex-direction:column;min-height:300px;padding:22px;background:#10171fe8}article h3{font-size:21px;letter-spacing:-.4px;overflow-wrap:anywhere}.metric-list{margin:12px 0 20px}.metric-row{gap:8px}.metric-row strong{font-size:19px}.metric-row em{font-size:13px;font-style:normal;color:#9ba9b8}.card-footer{margin-top:auto;padding-top:18px;font-size:12px;display:flex;flex-wrap:wrap;gap:12px}.badge{font-size:11px;line-height:1.5;display:inline-block;padding:5px 10px;border:1px solid;border-radius:7px;align-self:flex-start}.badge.failed{color:#f4b8a6;border-color:#65483d;background:#281c18}.badge.passed{color:#b5e6d9;border-color:#3b6055;background:#14241f}.badge.pending{color:#d7caa9;border-color:#5b5340;background:#26231b}.pending-link{display:inline-block;color:#82909e;font-size:13px;margin:14px 12px 0 0}.muted{color:#8797a8}.section-heading h2{margin-top:9px}.note{border-radius:0 16px 16px 0;margin-top:30px}.note p:last-child{margin-bottom:0}.scroll{border:1px solid #293641;border-radius:15px}table{font-size:13px}thead{background:#121b24}th{font-weight:500}.case-id{display:block;font-size:10px;letter-spacing:.3px;color:#8497a8;margin-top:4px}.figure-links{display:flex;flex-wrap:wrap;gap:18px;margin-top:10px}.empty-state{border:1px dashed #34424e;border-radius:16px;padding:30px;color:#93a2b2}.footer-grid{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;padding-top:25px;border-top:1px solid #27333f}section{margin-top:68px}figure{padding:26px;margin:28px 0}figcaption{line-height:1.8}a:focus-visible{outline:2px solid #b5e6d9;outline-offset:5px}
.findings-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.findings-grid article{min-height:0}.findings-grid h3{font-size:22px}.findings-grid p{font-size:14px}.video-grid{display:grid;gap:24px}.video-card{padding:0;overflow:hidden;min-height:0}.video-caption{padding:24px 26px}.video-caption h3{margin:10px 0 14px}.video-card video{border-radius:0;display:block;width:100%}.video-card>p{padding:0 26px 18px;max-width:none;font-size:13px}
@media(max-width:1000px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}header{grid-template-columns:minmax(0,1fr) 230px;gap:28px}.hero-panel{padding:22px}.hero-panel .large-number{font-size:65px}.findings-grid{grid-template-columns:1fr}}@media(max-width:650px){main{padding:0 18px 45px}header{grid-template-columns:1fr;padding-top:55px;gap:24px}.hero-panel{display:none}.grid{grid-template-columns:1fr}article{min-height:250px}h1{letter-spacing:-1px}h2{font-size:25px}nav{padding:13px 18px}nav span{gap:14px;flex-wrap:wrap}figure{padding:12px}td,th{padding:11px 9px;white-space:nowrap}section{margin-top:48px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
'''
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>CAN LAB · v14 路径跟踪与下降间隙</title><style>{style}</style></head><body>
<nav><strong>CAN LAB / RECOVERY 14</strong><span><a href="../improvement_v13_20261016_01/index.html">v13 成果</a><a href="#experiments">实验记录</a><a href="#evidence">图表与数据</a></span></nav><main>
<header id="top"><div class="hero-copy"><div class="eyebrow">TRACKING · CLEARANCE · REPLAN</div><h1>跟踪接近路径，<br>守住下降间隙。</h1><p>改进斜靠物体的接近与关节限位处理，以及箱沿路径跟踪和下降间隙。T、C 两个组件分别对照，再检验组合 v14。</p><p class="hero-status">{esc(status)}</p>{exists_link('protocols/PLAN.md','执行前协议','button')}{exists_link('REPORT.md','整体评估报告','button')}</div><aside class="hero-panel" aria-label="固定实验约束"><div class="large-number">400</div><p class="unit">CONTROL STEPS · 固定预算</p><div class="constraint"><span>执行延迟</span><strong>D2 FIFO</strong></div><div class="constraint"><span>仿真频率</span><strong>20 Hz</strong></div><div class="constraint"><span>抓取尝试</span><strong>≤ 2 次</strong></div><div class="constraint"><span>保护阈值</span><strong>保持原值</strong></div></aside></header>
<div class="grid">{''.join(cards)}</div><section class="note"><strong>证据边界</strong><p>本页完整阶段累计 {evaluation_count} 次实际评估执行；同一条件在修订和变体间重复，不能把执行总数当作独立起点数。机制测试、保存输入回放与物理重放另计，不增加实验样本。</p><p>原 BC 与世界模型权重冻结；已知诊断和开发数据用于筛选。只有冻结后全新起点上的配对确认才用于独立评估。小测试改善不能直接代表泛化改善，共享恢复收益也不等于世界模型独有收益。</p><p>旧代码、权重、实验和失败修订全部保留。本轮不做泛化训练，不写论文，不降低保护阈值。</p></section>
{target_section}{diagnosis}{video_section}{confirmation}<section id="experiments"><div class="section-heading"><span class="eyebrow">TRACEABLE EXPERIMENTS</span><h2>每轮结果，都留下依据。</h2></div><p>各阶段的样本规模与用途不同，不合并成一个成功率。未达标修订保留原始数据；只有通过前阶段门槛才进入后续大批量实验。</p>{history}</section>
<section id="evidence"><div class="section-heading"><span class="eyebrow">FIGURES &amp; SOURCE DATA</span><h2>图形简洁，数据完整。</h2></div><p>分类条件使用条形或散点，不把任意案例顺序连成趋势线。已知条件只报告描述统计；独立确认区间按起点成组重采样。每幅图附 600 dpi 位图、矢量文件和数据表。</p>{exists_link('figures/CATALOG.json','图表说明与来源哈希')}{figure_body}</section>
<footer class="footer-grid"><span>400 steps · D2 FIFO · 20 Hz · ≤2 attempts</span><span>旧成果保留 · 权重冻结 · 新版本按门槛评估</span></footer></main></body></html>'''
    (RUN/'index.html').write_text(page,encoding='utf8');print(json.dumps({'status':status,'completed_analyses':list(evidence),'figures':len(figures)},ensure_ascii=False))
if __name__=='__main__':main()
