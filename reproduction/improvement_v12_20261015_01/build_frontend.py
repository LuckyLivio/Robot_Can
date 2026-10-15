"""Publish actual completed phases only; preserve the earlier demo page."""
from pathlib import Path
import html,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def load(p):return json.loads(p.read_text(encoding='utf8'))
cards=[];details=[]
for stage,title in [('smoke_a','小测试'),('pilot_a','已知条件消融'),('dev_a','开发对照'),('confirmation','新起点确认')]:
    p=RUN/'analysis'/f'{stage}.json'
    if p.exists():
        d=load(p);variants=d.get('variants',{})
        content=' / '.join(f"{k}：{v['success']}/{v['episodes']}" for k,v in variants.items())
        cards.append(f'<article><small>{title}</small><h3>已完成</h3><p>{html.escape(content)}</p><a href="analysis/{stage}.json">原始汇总 ↗</a></article>')
        if stage=='dev_a':
            for p in sorted((RUN/stage).glob('*/result.json')):
                r=load(p);j=r['job'];suffix=j['id'].split('_',1)[1]
                b=load(ROOT/f'reproduction/improvement_v6_20261015_01/dev_a/v6_{suffix}/result.json')
                details.append(f"<tr><td>{html.escape(suffix)}</td><td>{sum(x['success'] for x in b['records'])}/30</td><td>{sum(x['success'] for x in r['records'])}/30</td></tr>")
    else:
        running=(RUN/stage/'started.json').exists()
        cards.append(f'<article><small>{title}</small><h3>{"运行中" if running else "待门槛通过"}</h3><p>按预先登记的阶段顺序推进。</p></article>')
confirmation=''
if (RUN/'analysis/confirmation.json').exists():
    d=load(RUN/'analysis/confirmation.json');effect=d['statistics']['v12_minus_v6'];ci=effect['ci95_percent']
    headline='通过预设对照门槛' if d['adoption_gate_passed'] else '未通过预设对照门槛'
    inference='配对区间高于零，支持本批次条件内成功率提升。' if d['positive_primary_ci'] else '配对区间未高于零，尚不能证明总体成功率提升。'
    rows=''.join(f"<tr><td>{html.escape(r['condition'])}</td><td>{r['v6_success']}/60</td><td>{r['v12_success']}/60</td></tr>" for r in d['conditions'])
    confirmation=f'<section id="confirmation"><h2>独立确认 · {headline}</h2><p>60个新起点，v6/v12各480次执行。配对差值 {effect["estimate_percent"]:+.2f} 个百分点，95%区间 [{ci[0]:.2f}, {ci[1]:.2f}]。{inference} 救回 {len(d["rescues"])} 次，退步 {len(d["regressions"])} 次。</p><p>v12等待抓持转换触发 {d["variants"]["v12"]["wait_transfers"]} 次；无触发不能证明该分支的泛化效果。独立对照是整个v12与v6的比较；新增分支的归因来自前面的v11/history/v12消融。</p><div class="scroll"><table><tr><th>新起点条件</th><th>v6</th><th>v12</th></tr>{rows}</table></div></section>'
if confirmation and (RUN/'analysis/confirmation_attribution.json').exists():
    a=load(RUN/'analysis/confirmation_attribution.json')
    note=f'<p>进一步归因：冻结v11在v12保存输入上回放，{a["v11_commands_identical_entire_trajectory"]}/{a["episodes"]}条完整轨迹、{a["control_steps"]}步命令一致。这是保存输入回放，不是新增闭环实验；退步集中于继承的箱沿/倾斜姿态阻断。详见<a href="analysis/confirmation_attribution.json">归因记录</a>和整体报告。</p>'
    confirmation=confirmation.replace('</section>',note+'</section>')
video=''
if (RUN/'demo/held_wait.mp4').exists():
    video='<section id="demo"><h2>同一起点，逐控制步对比</h2><p>Full s41 · 动作噪声0.05 · 已知 demo87。20 fps，真实保存动作回放；成功后保持终点，不新增实验样本。</p><video controls preload="metadata" poster="demo/poster.png" src="demo/held_wait.mp4"></video></section>'
figures=''.join(f'<figure><img loading="lazy" src="figures/{p.name}" alt="{html.escape(p.stem)}"><figcaption>{html.escape(p.stem)} · <a href="figures/{p.stem}.pdf">矢量 PDF</a> · <a href="figures/{p.stem}.csv">数据 CSV</a></figcaption></figure>' for p in sorted((RUN/'figures').glob('*.svg')))
report='<a class="button" href="REPORT.md">整体评估报告 ↗</a>' if (RUN/'REPORT.md').exists() else ''
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>CAN LAB · v12 抓持恢复</title><style>
:root{color-scheme:dark;--muted:#aab5c4;--accent:#b5e6d9}*{box-sizing:border-box}body{margin:0;background:#080b10;color:#f2f5fa;font-family:Inter,-apple-system,BlinkMacSystemFont,"Microsoft YaHei",sans-serif;line-height:1.7}nav{position:sticky;top:0;z-index:2;display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;padding:16px max(5vw,20px);background:#080b10ed;border-bottom:1px solid #26303b;backdrop-filter:blur(16px)}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}main{max-width:1180px;margin:auto;padding:0 28px 80px}header{padding:90px 0 60px}h1{font-size:clamp(36px,6vw,68px);line-height:1.18;font-weight:600;letter-spacing:-2px;margin:18px 0 24px}h2{font-size:30px;letter-spacing:-.5px}p{color:var(--muted);max-width:850px}small,.eyebrow{color:var(--accent);letter-spacing:2px;font-size:12px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:14px}article{padding:25px;background:#111822;border:1px solid #26313e;border-radius:18px}article h3{font-size:25px;margin:12px 0}section{margin-top:58px}.button{display:inline-block;border:1px solid #4b665f;border-radius:30px;padding:10px 22px;margin:14px 12px 0 0}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}td,th{text-align:left;padding:13px 10px;border-bottom:1px solid #29333e}figure{margin:24px 0;background:#fff;padding:20px;border-radius:14px;color:#222}figure img{display:block;width:100%;height:auto}figcaption{font-size:13px;margin-top:14px;color:#444}figcaption a{color:#075d80}video{width:100%;border-radius:18px;background:#111}.note{padding:22px;border-left:3px solid #b5e6d9;background:#111822}.scroll{overflow:auto}footer{margin-top:60px;color:var(--muted);font-size:13px}
</style><nav><strong>CAN LAB / RECOVERY 12</strong><span><a href="../progress_v11_20261015_01/demo/index.html">历史完整展示</a> &nbsp; <a href="../paper_quality_20261015_01/index.html">论文图表库</a> &nbsp; <a href="#evidence">本轮证据</a></span></nav><main><header><div class="eyebrow">OBSERVE · CONFIRM · TRANSPORT</div><h1>抓住之后，<br>继续完成搬运。</h1><p>v12 聚焦等待阶段的抓持确认。原世界模型与 BC 权重保持冻结；相同起点、相同噪声、相同 400 步预算，逐阶段检验是否改善。</p><a class="button" href="protocols/PLAN.md">执行前协议 ↗</a>REPORT</header><div class="grid">CARDS</div><section class="note"><strong>证据边界</strong><p>小测试和消融使用已知案例，开发集用于筛选。只有预先锁定的新起点才属于独立确认。旧 v5 成果继续保留；共享恢复改进不等同于世界模型的独立优势。</p></section>VIDEO<section id="evidence"><h2>实验与可复核数据</h2><div class="scroll"><table><thead><tr><th>开发条件</th><th>历史 v6</th><th>v12</th></tr></thead><tbody>ROWS</tbody></table></div>FIGURES</section><footer>400 steps · D=2 FIFO · 20 Hz · ≤2 recovery attempts<br>旧代码、权重、结果与失败案例保留。页面依据本轮保存数据生成。</footer></main></html>'''
page=page.replace('<section id="evidence">',confirmation+'<section id="evidence">')
if (RUN/'analysis/confirmation.json').exists() and not load(RUN/'analysis/confirmation.json')['adoption_gate_passed']:
    page=page.replace('</h1>','</h1><p style="color:#f0c887;font-weight:600">局部缺陷已修复；独立确认未通过采用门槛，v12不替换正式版本。</p>')
for key,value in [('REPORT',report),('CARDS',''.join(cards)),('VIDEO',video),('ROWS',''.join(details)),('FIGURES',figures)]:page=page.replace(key,value)
(RUN/'index.html').write_text(page,encoding='utf8')
print('Updated v12 frontend:',RUN/'index.html')
