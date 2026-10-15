"""Publish current figure/navigation documents, preserving every replaced byte."""
from pathlib import Path
import csv, html, json, re, shutil, hashlib, datetime, sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];REL=RUN.relative_to(ROOT).as_posix()
CHANGES=[]
def read(p):return p.read_text(encoding='utf8')
def write(p,s):
    if p.exists() and p.is_relative_to(ROOT) and not p.is_relative_to(RUN):
        rel=p.relative_to(ROOT);backup=RUN/'before'/rel
        if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,backup)
        if read(p)==s:return
        CHANGES.append(rel.as_posix())
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf8')
def root(name,transform):
    p=ROOT/name;write(p,transform(read(p)))
def link(label,file):return f'[{label}]({REL}/{file})'
def main():
    cat=json.loads(read(RUN/'figures/CATALOG.json'))['figures']
    intro=f'> 2026-10-15论文图表复查：{link("新图与数据总览","index.html")} · {link("全项目报告","REPORT.md")} · {link("当前提纲与证据映射","THESIS_OUTLINE_REVIEWED.md")}。36张图重新生成；没有新增训练、仿真或论文正文。\n\n'
    inventory=json.loads(read(RUN/'inventory_summary.json'))
    marks=sum(g['plotted_rows'] for g in cat)
    catalog=['# 论文图表目录与图注\n','36张图，600 dpi PNG / 矢量PDF / 路径字体SVG / 数据CSV。旧图保留，F编号沿用旧图包主题，不是最终论文编号。每张宽180.3 mm，标签9 pt、刻度与图例8 pt；正文不需要全部插入。\n','[解释异常曲线](CURVE_EXPLANATIONS.md) · [提纲映射](THESIS_OUTLINE_REVIEWED.md) · [来源哈希](PLOT_SOURCES.json)\n',
        '旧F02拆成F02a–c；F12、F15、F18拆分；旧F19与F09同数据，合并F09。A01原始批次、A02开发恢复、A03–A05 v6、A06 v10、A07–A09 v11。共19个旧主题全部对应，未用新图伪造新实验。\n']
    table=[];cards=[]
    for g in cat:
        id=g['id'];formats=' · '.join(f'[{e.upper()}](figures/{id}.{e})' for e in g['formats'])
        catalog.append(f'## {id}｜{g["title"]}\n\n用途：{g["role"]}；{formats}\n\n图注：{g["caption"]}\n\n限制：{g["limitations"] or "按上述批次与分母解释，不跨阶段合并。"}\n\n数据来源：'+ '；'.join(f'`{s}`' for s in g['sources'])+f'。本图导出{g["plotted_rows"]}条测量/统计值。\n')
        table.append({k:g[k] for k in ['id','title','role','old_group','plotted_rows','width_mm','height_mm','png_dpi']})
        formats_html=' · '.join(f'<a href="figures/{id}.{e}" download>{e.upper()}</a>' for e in g['formats'])
        cards.append(f'<article class="figure" id="{id}" data-role="{g["role"]}"><div class="eyebrow">{id} / {g["role"]}</div><h2>{html.escape(g["title"])}</h2><a href="figures/{id}.svg"><img src="figures/{id}.svg" loading="lazy" alt="{html.escape(g["title"])}"></a><p class="downloads">{formats_html}</p><p>{html.escape(g["caption"])}</p><p class="limit">{html.escape(g["limitations"])}</p><details><summary>测量来源与数据</summary><ul>'+''.join(f'<li><code>{html.escape(s)}</code></li>' for s in g['sources'])+f'</ul><p>{g["plotted_rows"]}条导出值；来源SHA见PLOT_SOURCES.json。</p></details></article>')
    write(RUN/'FIGURE_CATALOG.md','\n'.join(catalog))
    with (RUN/'FIGURE_INDEX.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f5f7;color:#1d1d1f;font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}a{color:#0067bb;text-decoration:none}a:hover{text-decoration:underline}nav{background:#ffffffeb;border-bottom:1px solid #ddd;padding:15px 5vw;display:flex;gap:24px;flex-wrap:wrap;position:sticky;top:0;z-index:2;backdrop-filter:blur(16px)}main{max-width:1120px;margin:auto;padding:54px 22px}h1{font-size:clamp(36px,5vw,64px);line-height:1.12;letter-spacing:-2px;margin:16px 0 28px}h2{font-size:24px;line-height:1.35;letter-spacing:-.5px}.eyebrow{font-size:12px;letter-spacing:2px;color:#69727d;font-weight:700}.lead{font-size:20px;color:#51545b;max-width:820px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:34px 0}.stats div{border-top:1px solid #cbd0d7;padding:18px 0}.stats b{font-size:30px;display:block}.notice{border-left:3px solid #788ba1;padding:12px 20px;background:#eaf0f6}.figure{background:white;border-radius:20px;padding:28px;margin:26px 0;box-shadow:0 3px 20px #00000005;scroll-margin-top:80px}.figure img{display:block;width:100%;height:auto;margin:22px 0}.figure p{font-size:15px}.downloads{font-weight:600}.limit{color:#6a4c34}details{border-top:1px solid #e2e4e7;padding-top:12px;overflow-wrap:anywhere}code{font-size:12px}button,input{padding:10px 15px;border:1px solid #ccd2d9;border-radius:9px;background:white;font:inherit}button{cursor:pointer}button[aria-pressed=true]{background:#1d1d1f;color:white}.filters{display:flex;gap:10px;flex-wrap:wrap;margin:25px 0}.figure[hidden]{display:none}footer{color:#68717c;font-size:13px;margin-top:40px}@media(max-width:600px){main{padding:30px 14px}.figure{padding:17px 10px}.stats{gap:12px}.stats b{font-size:24px}nav{gap:12px;font-size:14px}.figure h2,.figure p,.figure details{margin-left:8px;margin-right:8px}}@media print{nav,.filters,.downloads{display:none}.figure{break-inside:avoid;box-shadow:none;border-radius:0;padding:0}body{background:white}main{padding:0;max-width:none}}'''
    write(RUN/'style.css',css)
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CAN LAB · 论文图表与证据</title><link rel="icon" href="data:,"><link rel="stylesheet" href="style.css"><nav><b>CAN LAB / FIGURES</b><a href="#top">图表</a><a href="REPORT.md">检查报告</a><a href="THESIS_OUTLINE_REVIEWED.md">论文提纲</a><a href="CURVE_EXPLANATIONS.md">曲线解释</a><a href="README.md">使用说明</a></nav><main id="top"><p class="eyebrow">PAPER QUALITY / 2026.10.15</p><h1>图要清楚。<br>结论要有依据。</h1><p class="lead">从保存的实验数据重新绘制。训练泛化差距、共同失败与候选退步完整保留；没有新训练、仿真或论文正文。</p><div class="stats"><div><b>36</b>张重新生成的图</div><div><b>600 dpi</b>PNG + 矢量 PDF / SVG</div><div><b>19,140</b>条导出测量与统计值</div></div><p class="notice">主线仍为v5；v11开发235/240未采用。独立起点数与执行次数分开报告。图注、误差区间与版本边界随图提供。</p><p><a href="FIGURE_CATALOG.md">完整图注与旧新映射</a> · <a href="FIGURE_INDEX.csv">图表索引CSV</a> · <a href="builds/CAN_LAB_PAPER_FIGURES_20261015.zip" download>下载图表与提纲包</a> · <a href="PLAN_AND_NEXT_STEPS.md">下一步整改计划</a></p><div class="filters"><button aria-pressed="true" data-filter="全部">全部</button><button aria-pressed="false" data-filter="正文">正文候选</button><button aria-pressed="false" data-filter="附录">附录与诊断</button><input id="search" placeholder="搜索图号或主题" aria-label="搜索图表"></div><p>图片可点击放大。插入论文时优先PDF或SVG；PNG按原宽使用。36张是完整资料集，不要求全部放正文。</p>'''+''.join(cards)+'''<footer>固定来源与完整性：PLOT_SOURCES.json / MANIFEST.json。绘图输入可随本包迁移；不依赖权重或GPU。旧图片和历史协议保持原样。</footer></main><script>let selected='全部';const buttons=[...document.querySelectorAll('[data-filter]')];function filter(){let q=document.querySelector('#search').value.toLowerCase();document.querySelectorAll('.figure').forEach(x=>x.hidden=(selected!=='全部'&&x.dataset.role!==selected)||!x.textContent.toLowerCase().includes(q))}buttons.forEach(b=>b.addEventListener('click',()=>{selected=b.dataset.filter;buttons.forEach(x=>x.setAttribute('aria-pressed',String(x===b)));filter()}));document.querySelector('#search').addEventListener('input',filter)</script></html>'''
    write(RUN/'index.html',page.replace('19,140',f'{marks:,}'))
    if '--gallery-only' in sys.argv:
        print(json.dumps({'gallery_refreshed':True,'figures':len(cat),'exported_values':marks}));return
    # Update current docs; frozen historical copies intentionally remain unchanged.
    for name in ['README.md','STATUS.md','PROGRAM_GUIDE.md','EVIDENCE_INDEX.md','DEMO_GUIDE.md','ENVIRONMENT_GUIDE.md','THESIS_HANDOFF_LATEST.md','PROJECT_NAVIGATION.md']:
        root(name,lambda s:intro+s if not s.startswith(intro) else s)
    root('README.md',lambda s:s.replace('最新图表深查及固定训练/开发集复算见','历史图表深查及固定训练/开发集复算见').replace('reproduction\\portable_delivery_20261015_01\\launcher.py verify','reproduction\\paper_quality_20261015_01\\verify.py').replace('10,230 个路径','10,270 个路径'))
    root('STATUS.md',lambda s:s.replace('reproduction/portable_delivery_20261015_01/verify_delivery.py',REL+'/verify.py').replace('（2026-10-15审查版）','（2026-10-15图表与文档复查版）'))
    root('PROGRAM_GUIDE.md',lambda s:s.replace('reproduction\\portable_delivery_20261015_01\\launcher.py verify','reproduction\\paper_quality_20261015_01\\verify.py').replace('验证交付整理前10,230个登记文件','验证图表整改前10,270个登记文件'))
    root('GITHUB_UPLOAD.md',lambda s:intro+s.replace('最新图表深查在','历史图表深查在').replace('最新图表复核：http://127.0.0.1:8766/reproduction/figures_deepcheck_20261014_01/index.html','当前论文图表：http://127.0.0.1:8766/'+REL+'/index.html').replace('reproduction\\project_audit_20261015_01\\verify.py','reproduction\\paper_quality_20261015_01\\verify.py').replace('当前入口校验审查前10,146个受管理路径','当前入口校验本轮修改前10,270个受管理路径').replace('使用完整迁移包须另外传输FULL ZIP','仅写作/展示带WRITING及增补、展示ZIP即可；若需完整历史压缩快照，再单独带FULL ZIP'))
    root('DELIVERY_CHECKLIST.md',lambda s:intro+s.replace('- [ ] 新建v6—v11增补迁移包，旧c8bbe86写作包不覆盖。','- [x] v6—v11增补与独立展示包已在本机完成，旧c8bbe86写作包保留；另新增本轮论文图表/提纲增补包。').replace('当前仅单机环境与前向核对通过','本机干净标准库环境、中文路径和浏览器播放已验证；目标电脑仍待实测'))
    root('PROJECT_NAVIGATION.md',lambda s:s.replace('[当前审查前10,146文件索引](reproduction/project_audit_20261015_01/FILE_INVENTORY.csv)',f'[本轮修改前10,270文件索引]({REL}/FILE_INVENTORY.csv)').replace('建议在PyCharm中收藏WORKSPACE和THESIS_HANDOFF_20261015。图表可参考旧迁移包的详细图注，但它不含v6—v11；当前根THESIS_OUTLINE与最新交接说明补充候选版本边界。',f'建议收藏WORKSPACE及本轮目录`{REL}`。新图和当前提纲优先使用本轮版本；旧写作包用于既有40表与冻结资料，v6—v11另有增补。'))
    root('EVIDENCE_INDEX.md',lambda s:s.replace('reproduction/project_audit_20261015_01/verify.py',REL+'/verify.py').replace('| 写作迁移 | c8bbe86历史包，非v11最新整包 |','| 写作迁移 | c8bbe86旧主线 + fad3100候选增补 + 新图表提纲包 |').replace('reproduction/project_audit_20261015_01/FILE_INVENTORY.csv',REL+'/FILE_INVENTORY.csv').replace('reproduction/project_audit_20261015_01/RESULT_LEDGER.csv',REL+'/RESULT_LEDGER.csv'))
    root('THESIS_HANDOFF_LATEST.md',lambda s:s.replace('再使用[旧详细提纲]', '当前详细结构优先使用本轮提纲；[旧详细提纲]')+'\n本轮新增独立图表与提纲ZIP，见 '+link('下载与命令','README.md')+'。旧三ZIP不覆盖；换设备时额外带本轮ZIP，写作优先使用新图注和提纲。\n')
    root('ENVIRONMENT_GUIDE.md',lambda s:s.replace('本轮没有新建环境或运行闭环机器人。','本轮图表检查未新建仿真环境或运行闭环机器人；上一轮便携展示已在本机新标准库环境和中文移位目录验证。').replace('reproduction/project_audit_20261015_01/environment_and_inference.json',REL+'/environment_and_inference.json'))
    root('DEMO_GUIDE.md',lambda s:s+'\n图表讲解新增顺序：先F02固定集训练/开发差距，再F03候选切换，再F05/F10配对确认；A04展示真实开度振荡，A09展示持物等待。新版曲线没有平滑机器人动作，视频仍是已有回放。\n')
    for p in ROOT.glob('*.md'):
        s=read(p);old='版本：2026-10-12 成果整合版；旧根文档见 reproduction/consolidation_20261012_01/previous_documents/'
        if old in s:write(p,s.replace(old,'文档复核：2026-10-15；本页2026-10-12实验口径保持原协议。旧版归档：reproduction/consolidation_20261012_01/previous_documents/'))
    # Current outline now has one authoritative detailed counterpart.
    outline='''# 本科论文提纲：动作延迟下的机器人抓取搬运与失败恢复

更新：2026-10-15。建议题目：**考虑动作延迟的机器人抓取搬运与失败恢复系统设计及实验分析**。这是提纲与证据映射，不是论文正文；学校最终格式和题目仍待导师认可。

'''+f'完整逐章提纲、实验分母和图号映射见 {link("当前详细提纲","THESIS_OUTLINE_REVIEWED.md")}；图注见 {link("36张新图目录","FIGURE_CATALOG.md")}。旧写作包提纲保留为历史快照。\n\n'+'''| 章节 | 内容与证据边界 |
|---|---|
| 1 绪论 | 单任务低维仿真、固定延迟；系统、一致性修复与实验诊断贡献 |
| 2 相关工作 | 基础8篇与后补RTC/REMAC分阅读深度；正式写作继续补直接相关工作 |
| 3 系统与一致性 | 23维状态、公共数据、真实FIFO、状态/缓存/分支一致性；起点不等于执行次数 |
| 4 世界模型 | 动作块候选、GRU、进展/失抓头、排序、H=8/D=2/K=4门控；F01 |
| 5 共享恢复 | 冻结v5规则恢复和400步预算；v6—v11单列候选，不将待做v12写成成果 |
| 6 实验 | 训练/开发/确认分开；强BC、三WM种子、公平消融、900补充执行、v5原生与压力分别统计；F02–F16 |
| 7 讨论 | 泛化不足、排序区间跨零、恢复后强BC、共同失败与v11退步；F03/F17/F18及A系列 |
| 8 总结 | 只总结已有证据；视觉、真机、多任务与稳定新算法优势不属于已证实范围 |

核心结论：原WM联合Full−BC为+4.72[0.56,10.28]百分点，但Full−Plain为+1.94[−0.56,6.11]；v5−v4为+1.46[0,4.17]，7次救回仅来自2个起点。不得用不同批次直接相减，不能称普遍显著提升。

正文保留原世界模型确认与v5恢复确认；v6—v11以局部机制和负结果作为附录。旧40表按原批次使用，新36图不是36项独立实验。原视频和新轨迹来源按各自manifest，不能用旧整合manifest替代v11来源证明。

[贡献](CONTRIBUTIONS.md) · [相关工作](RELATED_WORK.md) · [当前成果索引](EVIDENCE_INDEX.md) · [统计规范](STATISTICS.md)。
'''
    write(ROOT/'THESIS_OUTLINE.md',outline)
    write(ROOT/'PROJECT_AUDIT.md',f'''# 当前项目完整度与论文适用性评估

更新：2026-10-15，论文图表复查版。**主实验与原始资产完整，适合以系统设计和实验分析为定位开展本科论文；不支持通用、稳定、无失败或普遍优于强BC的结论。** 学校评分细则未提供，不作毕业资格保证。

{link('完整报告','REPORT.md')} · {link('检查清单','CHECKLIST.csv')} · {link('下一步方案','PLAN_AND_NEXT_STEPS.md')} · {link('清理候选','CLEANUP.md')}。

本轮重新盘点修改前10,270个文件，912个Python、4,031个JSON解析通过；1,358个唯一JSONL / 2,335,802行、625个唯一数值/图像资产读取通过，环境与7模型前向通过。1,505份结果中三份v7早期中断保留并由后续完整pilot_b替代，82份任务表没有缺失声明输出。42行区间重新核算一致；36张论文图重新生成，逐图PDF渲染验收。

已修正活动文档的过期版本说明、缺失的交付包状态、旧校验入口及图表/提纲导航。旧图和历史代码/权重/结果全部保留。v6—v11增补已完成，不再作为未完成事项；目标电脑实际验收仍待完成。

未解决的研究问题：v11已持物等待状态转换；世界模型开发泛化与排序增益不稳定；v5没有同批关闭恢复组。前两项需要新代码/实验，不能靠改图修复；后一项是现有因果解释的边界。当前主线仍v5，v11未采用。
''')
    for sub in ['05_visualization','06_thesis_handoff']:
        p=ROOT/'WORKSPACE'/sub/'README.md';write(p,f'> 当前首选：[新图总览](../../{REL}/index.html) · [当前提纲](../../{REL}/THESIS_OUTLINE_REVIEWED.md) · [交付说明](../../THESIS_HANDOFF_LATEST.md)。下列旧包保留其版本范围。\n\n'+read(p))
    p=ROOT/'figures/README.md';write(p,f'> 当前论文用图已在新目录统一重绘：[图表与数据总览](../{REL}/index.html) · [曲线解释](../{REL}/CURVE_EXPLANATIONS.md)。本目录7组旧图及数值保留用于历史核查，写论文优先使用新版。\n\n'+read(p))
    root('WORKSPACE/index.html',lambda s:s.replace('<section><h2>跨设备交付</h2>',f'<section><h2>论文图表与当前提纲</h2><p>36张重绘图，600 dpi与矢量格式、逐图数据和解释；不新增实验。</p><a href="../{REL}/index.html">打开新图与数据</a> · <a href="../{REL}/THESIS_OUTLINE_REVIEWED.md">查看提纲</a> · <a href="../{REL}/REPORT.md">查看全项目复查</a></section><section><h2>跨设备交付</h2>').replace('<small>reproduction/consolidation_20261012_01/demo/index.html</small>','<small>reproduction/progress_v11_20261015_01/demo/index.html</small>'))
    # Change only current presentation HTML; do not modify archived demo or its data.
    p=ROOT/'reproduction/progress_v11_20261015_01/demo/index.html';s=read(p)
    s=s.replace('<main id="top">','<main id="top">'+f'<section class="wrap" style="padding-top:32px"><p class="eyebrow">PAPER FIGURES / 2026.10.15</p><h2>新版论文图表已完成。</h2><p>36张图重新绘制，附原始数据、图注与曲线解释；实验结果未改变。</p><p><a href="../../paper_quality_20261015_01/index.html">打开论文图表与数据 →</a> · <a href="../../paper_quality_20261015_01/REPORT.md">查看全项目复查</a></p></section>')
    for old,ids,alt in [('../../improvement_v11_20261015_01/analysis/wall_edge_comparison.png',['A08a','A08b'],'v11四组箱沿已知案例'),('../../improvement_v11_20261015_01/analysis/development_regression.png',['A09a','A09b'],'v6与v11持物等待开发退步'),('../../improvement_v10_20261015_01/analysis/wall_edge_comparison.png',['A06a','A06b'],'v10箱沿已知诊断')]:
        pattern=r'<a href="'+re.escape(old)+r'"><img\b[^>]*></a>'
        new=''.join(f'<a href="../../paper_quality_20261015_01/figures/{id}.svg"><img class="evidence-plot" style="width:100%;height:auto" src="../../paper_quality_20261015_01/figures/{id}.svg" loading="lazy" alt="{alt}：{id}，逐步原始数据未平滑"></a>' for id in ids)
        s,n=re.subn(pattern,new,s);assert n==1,(old,n)
    s=s.replace('../../consolidation_20261012_01/figures/prediction_rmse_mobile.svg','../../paper_quality_20261015_01/figures/F09.svg').replace('../../consolidation_20261012_01/figures/prediction_rmse.svg','../../paper_quality_20261015_01/figures/F09.svg')
    write(p,s)
    write(RUN/'document_changes.json',json.dumps({'updated':sorted(set(CHANGES)),'before_snapshots':'before/','historical_protocols_modified':False},ensure_ascii=False,indent=2))
    print(json.dumps({'updated_documents':len(set(CHANGES)),'figures':len(cat),'exported_values':marks},ensure_ascii=False))
if __name__=='__main__':main()
