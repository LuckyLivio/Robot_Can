"""Publish auditable findings in CSV/Markdown/HTML, independent of frozen demos."""
from pathlib import Path
import csv,json,html,collections
RUN=Path(__file__).resolve().parent
rows=[
('A01','验收','通过','全仓资产','10146个Git文件已哈希建档；未发现主资产丢失','before_manifest.json','保持原路径与哈希'),
('A02','验收','通过','源码语法','891个Python文件语法通过；不是全部运行路径证明','syntax.json','历史默认入口不自动执行'),
('A03','验收','通过','JSON/逐步日志','3983份JSON、1358份JSONL/2335802行通过','jsonl_validation.json','原日志保留'),
('A04','验收','通过','权重与数值数据','684权重路径及HDF5/NPZ读取与有限性检查通过','binary_numeric_assets.json','不删除历史checkpoint'),
('A05','验收','通过','当前环境与前向','pip/CUDA小张量、BC与6个WM单观测前向通过','environment_and_inference.json','跨机器另验'),
('A06','验收','通过','原统计与图源','2640条主线记录、42区间重算；135源文件哈希一致','statistics_validation.json','不同批次不拼接'),
('A07','验收','通过','任务登记输出','82份登记列表，显式声明输出无缺失','job_output_validation.json','完整度按阶段解读'),
('A08','历史','已解释','v7中断记录','3份running为pilot_a序列化中断，pilot_b完整148回合','../improvement_v7_20261015_01/REPORT.md','不改complete、不计入正式主表'),
('A09','验收','通过','主输入冻结','原确认30项、v5确认47项、v11开发8项全匹配','contracts.json','历史源码/协议不改'),
('A10','验收','通过','视频/图像','35视频路径完整解码；图像/CSV/SVG可读','media_validation.json','不把解码通过写成运动平滑'),
('A11','验收','通过','旧迁移包','4158文件、652压缩轨迹、40表/19图组通过','handoff_verification.json','保留历史包'),
('D01','P1','已修正','活动文档滞后','运行指南/状态/索引/演示/校验入口已统一','document_changes.json','后续每轮同步当前状态'),
('D02','P1','已修正','最新与历史混用','主版本v5、v11未采用、旧迁移包范围已明确','../../THESIS_HANDOFF_LATEST.md','不能只凭目录日期判断最新'),
('D03','历史','已解释','629条归档相对链接','全部在备份/快照/图源副本；活动原路径无缺失','missing_markdown_links.json','保留归档字节，用当前导航访问'),
('C01','P1','待改进','持物等待状态转换','v11开发235/240低于v6的236/240；已持物仍等支撑','../improvement_v11_20261015_01/analysis/development_regression_diagnosis.json','新目录最小开关修复、小测/消融/开发门槛'),
('R01','P1','主张受限','世界模型优势不稳定','开发/恢复后不稳定优于强BC；排序对Plain未确立','../../RESULTS.md','系统分析定位；更强主张需新研究'),
('R02','P2','待改进','开发覆盖与评分敏感','训练20父轨迹/开发8；稀疏有效排序对','../figures_deepcheck_20261014_01/REPORT.md','独立父轨迹覆盖实验，先不混改控制器'),
('R03','条件项','未运行','v5同批关闭恢复对照','旧v2/v3有四组；v5缺自身同批无恢复组','../consolidation_20261012_01/FACTORIAL_REVIEW.md','仅需精确归因v5独立贡献时补'),
('P01','P1','待交付','干净安装与跨设备','当前环境可用，但第二台电脑完整运行未验证','IMPROVEMENT_PLAN.md','新环境验收；不直接复制.venv'),
('P02','P1','待交付','最新迁移增补包','旧包c8bbe86，不含v6—v11；gzip/ZIP不随克隆','../../THESIS_HANDOFF_LATEST.md','新建增补包，不覆盖旧包'),
('P03','P2','待改进','脚本默认值与CI','旧默认参数非冻结协议，jobs命令机器绑定，无CI','portability_summary.json','新增显式入口和轻量只读CI'),
('P04','P2','待选择','代码许可','未设置根LICENSE，外部资产来源需随发布列清','portability_summary.json','作者决定许可；不替作者自动选择'),
('F01','P3','清理候选','缓存与Git临时对象','38KB字节缓存、3个2.68MiB临时对象；无损坏对象证据','CLEANUP.md','备份后精确处理，本轮未删'),
('F02','P2','待优化','发布体积','约8.99GiB受管文件；8.26GiB为轨迹','inventory_summary.json','单独轻量发行包，不破坏研究归档'),
('T01','交付','待完成','正式论文','具备工程/实验证据；未提供学校标准/正文/导师审阅','../../THESIS_OUTLINE.md','确认范围、写作与引用校核，非本轮正文任务'),
('T02','范围','不冒充完成','视觉/真机/多任务','当前只有单任务低维真值仿真','../../CONTRIBUTIONS.md','按题目边界说明，不自动列本科必补项'),
]
if __name__=='__main__':
    fields=['id','priority','status','area','finding','evidence','action']
    with (RUN/'CHECKLIST.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(fields);w.writerows(rows)
    with (RUN/'CHECKLIST.md').open('x',encoding='utf8') as f:
        f.write('# 全项目检查清单\n\n状态是本轮核实结论，不把待办计为完成。P1表示当前主题下优先，算法待办并非自动成为毕业必需项。\n\n| 编号 | 优先级 | 状态 | 检查项 | 发现/结论 | 方案 |\n|---|---|---|---|---|---|\n')
        for ident,priority,status,area,finding,evidence,action in rows:f.write(f'| {ident} | {priority} | {status} | [{area}]({evidence}) | {finding} | {action} |\n')
    def e(s):return html.escape(str(s),quote=True)
    table=''.join(f'<tr><td>{e(a)}</td><td>{e(b)}</td><td><span class="status {"ok" if c in ["通过","已修正"] else "open"}">{e(c)}</span></td><td><a href="{e(f)}">{e(d)}</a><p>{e(g)}</p></td><td>{e(h)}</td></tr>' for a,b,c,d,g,f,h in rows)
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Robot_can · 全项目检查</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f5f6f8;color:#17202b;font:15px/1.75 system-ui,-apple-system,"Microsoft YaHei",sans-serif}}header{{background:#fff;border-bottom:1px solid #e0e5ea}}.wrap{{max-width:1160px;margin:auto;padding:24px}}header .wrap{{display:flex;justify-content:space-between;gap:20px}}a{{color:#2461b4;text-decoration:none}}a:hover{{text-decoration:underline}}h1{{font-size:clamp(30px,4vw,48px);line-height:1.2;letter-spacing:-.04em;margin:12px 0 20px}}h2{{font-size:24px}}.muted{{color:#617184}}.kicker{{letter-spacing:.16em;font-size:12px}}.hero{{padding-top:40px}}.lead{{max-width:840px;font-size:18px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin:26px 0}}.card,section{{background:white;border:1px solid #e1e6ed;border-radius:18px;padding:24px}}.card strong{{display:block;font-size:29px}}.card span{{font-size:13px;color:#617184}}.notice{{padding:22px 28px;border-radius:18px;background:#17202b;color:#edf1f7}}.notice p{{margin:0}}.links{{display:flex;gap:24px;flex-wrap:wrap;margin:24px 0}}section{{margin:24px 0}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{text-align:left;padding:14px 10px;border-bottom:1px solid #e8edf2;vertical-align:top}}td p{{margin:5px 0 0;color:#647184}}th{{white-space:nowrap}}.status{{white-space:nowrap;border-radius:20px;padding:4px 9px;font-size:12px}}.ok{{color:#176545;background:#e9f4ee}}.open{{color:#75501b;background:#faf1df}}footer{{padding:20px 0;color:#647184;font-size:13px}}@media(max-width:760px){{.cards{{grid-template-columns:repeat(2,1fr)}}.wrap{{padding:18px}}td:nth-child(4){{min-width:230px}}td:nth-child(5){{min-width:190px}}}}
</style></head><body><header><div class="wrap"><strong>CAN LAB / PROJECT AUDIT</strong><nav><a href="../../WORKSPACE/index.html">分类导航</a> · <a href="../progress_v11_20261015_01/demo/index.html">机器人展示</a></nav></div></header><main class="wrap"><div class="hero"><p class="kicker muted">2026.10.15 · 全仓检查 · 不新增实验</p><h1>资产完整。<br>结论有边界，改进有次序。</h1><p class="lead">具备本科系统设计与实验分析的基础。主版本仍为v5；v11箱沿局部修复成立，开发235/240未达到采用门槛。没有把负结果当作漏跑，也没有删除历史证据。</p></div>
<div class="cards"><div class="card"><strong>10,146</strong><span>原登记文件逐项建档</span></div><div class="card"><strong>233万+</strong><span>逐步JSONL记录解析</span></div><div class="card"><strong>684</strong><span>权重路径读取与有限性核查</span></div><div class="card"><strong>42</strong><span>原置信区间重新核对</span></div></div>
<div class="notice"><p>优先处理：持物等待的状态切换、跨设备交付与最新迁移增补。世界模型泛化改进应另开受控实验；不能靠更换图表或省略强BC来证明优势。</p></div>
<div class="links"><a href="REPORT.md">详细检查报告 ↗</a><a href="CHECKLIST.csv" download>下载清单CSV ↓</a><a href="IMPROVEMENT_PLAN.md">调整计划 ↗</a><a href="CLEANUP.md">文件清理建议 ↗</a><a href="FILE_INVENTORY.csv">完整文件台账 ↗</a></div>
<section><h2>逐项结果与待办</h2><p class="muted">语法/哈希/解码通过不等于所有运行路径或实机可靠性已经证明。下列计划事项尚未实施；本轮修正活动文档，保留全部旧代码、权重和结果。</p><div class="scroll"><table><thead><tr><th>编号</th><th>优先级</th><th>状态</th><th>检查项与结论</th><th>下一步</th></tr></thead><tbody>{table}</tbody></table></div></section>
<footer>审查基准39c0341 · 旧迁移包c8bbe86 · 未写论文正文 · 当前本地完整性入口：verify.py</footer></main></body></html>'''
    (RUN/'index.html').write_text(page,encoding='utf8')
    (RUN/'checklist_summary.json').write_text(json.dumps({'items':len(rows),'statuses':dict(collections.Counter(r[2] for r in rows))},ensure_ascii=False,indent=2),encoding='utf8')
    print('Checklist items',len(rows))
