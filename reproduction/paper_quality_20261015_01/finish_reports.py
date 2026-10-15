"""Write audit findings from measured receipts; no project mutations."""
from pathlib import Path
import json,csv,collections
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def read(name):return json.loads((RUN/name).read_text(encoding='utf8'))
def main():
    inv=read('inventory_summary.json');assets=read('binary_numeric_assets.json');tr=read('jsonl_validation.json');results=read('result_validation.json');fig=read('validation/figure_validation.json');changes=read('document_changes.json')['updated']
    counts=collections.Counter()
    unique=collections.Counter()
    for r in assets['files']:counts[r['type']]+=len(r['paths']);unique[r['type']]+=1
    before=read('before_manifest.json');old=json.loads((ROOT/'reproduction/project_audit_20261015_01/before_manifest.json').read_text())
    prior=json.loads((ROOT/'reproduction/project_audit_20261015_01/media_validation.json').read_text())
    checked=[]
    for r in prior['files']:
        for p in r['paths']:assert before[p]==old[p];checked.append(p)
    (RUN/'media_hash_continuity.json').write_text(json.dumps({'passed':True,'paths':len(checked),'unique_videos':prior['unique_videos'],'prior_full_decode_passed':prior['passed'],'new_full_decode':False,'scope':'Full current file hashes equal the assets previously decoded successfully; no new playback samples.'},indent=2),encoding='utf8')
    scratch=[]
    for rel in ['builds/release_01','builds/TRANSFER_DRAFT_01','validation/relocated/run_01','validation/relocated/run_02']:
        p=ROOT/'reproduction/portable_delivery_20261015_01'/rel
        scratch.append({'path':p.relative_to(ROOT).as_posix(),'exists':p.exists(),'bytes':sum(q.stat().st_size for q in p.rglob('*') if q.is_file()),'deleted':False})
    cleanup={'deleted_files':0,'temporary_candidates':scratch,'candidate_bytes':sum(r['bytes'] for r in scratch),'prior_cleanup_rejected':True,'rejection_reason':'Tool returned blocked by policy without a detailed reason; no bypass retry.','latest_8767_listener_observed':False,'protected':'All old experiments, models, raw traces, negative results, protocols, environment and writing archives.'}
    (RUN/'cleanup_inventory.json').write_text(json.dumps(cleanup,ensure_ascii=False,indent=2),encoding='utf8')
    cleanupmd='# 清理候选与保留理由\n\n本轮删除0个文件。以下为可评估的临时副本，不是实验资产；所有旧代码、权重、结果保留。\n\n| 路径（项目根下） | MiB | 处理状态 |\n|---|---:|---|\n'+''.join(f'| `{r["path"]}` | {r["bytes"]/2**20:.2f} | 保留，待清理条件满足 |\n' for r in scratch)
    cleanupmd+=f'\n合计 **{cleanup["candidate_bytes"]/2**20:.2f} MiB**。旧run_02曾承担8767服务；本轮检查未观察到8767监听，仍应在实际清理时重新检查占用、release_02/最终迁移包完整性与路径范围。\n\n前次自动审批拒绝过这四处临时清理与服务交接的组合命令，工具仅返回“blocked by policy”，未给详细原因。本轮没有重试删除，也没有换工具绕过。\n\n项目之外/环境内部不清理。项目字节缓存5个文件约38 KiB可再生；Git临时对象曾记录约2.68 MiB，必须在无Git写入时单独确认，不递归删除objects、dangling恢复对象或整个.git。\n\n原始JSONL约8.26 GiB是主要体积来源，权重315种内容/684路径、冻结快照、旧WRITING/FULL ZIP、652份gzip、v7中断记录及失败视频都不能按“重复/失败”批量删除。当前`.venv`继续保留。新图表目录的输入快照、逐图CSV和PDF渲染检查图是可追溯交付的一部分，不属于这次临时清理名单。\n'
    (RUN/'CLEANUP.md').write_text(cleanupmd,encoding='utf8')
    checklist=[
        ('A01','全仓基线哈希','通过',f'{inv["tracked_files"]}个修改前登记路径；FILE_INVENTORY.csv'),
        ('A02','Python/JSON语法','通过',f'{inv["syntax_files"]}个Python、{inv["json_files"]}个JSON无解析错误'),
        ('A03','JSONL数值结构','通过',f'{tr["unique_files"]}个唯一文件，{tr["unique_lines"]}行，无非法JSON/非有限常量'),
        ('A04','权重/数值/图像读取','通过',f'{assets["unique_assets"]}个唯一资产；含{counts[".pt"]}权重路径/{unique[".pt"]}唯一内容'),
        ('A05','任务输出完整性','通过','82份任务注册表，无缺失明确输出'),
        ('A06','历史中断','有解释','3份v7 pilot_a running保留；pilot_b完整148执行，未纳入主实验'),
        ('A07','主线记录与CI重算','通过','2640记录、42行区间、135来源哈希一致'),
        ('A08','冻结输入与父轨迹划分','通过','原确认30、v5确认47、v11开发8冻结输入一致；train20/dev8父轨迹不重叠'),
        ('A09','当前环境与模型前向','通过','pip check/CUDA/BC+Full Plain六模型前向；没有闭环实验'),
        ('A10','历史视频','哈希续验通过','35路径/23内容与前次完整解码文件相同；本轮不重复解码全部视频'),
        ('F01','重新生成论文用图','通过',f'{fig["figures"]}张；600dpi PNG、PDF、SVG、CSV；19个旧主题全部映射'),
        ('F02','图表来源/数值','通过',f'46来源校验、{fig["plotted_rows"]}条导出测量/统计值；不平滑、不造点'),
        ('F03','PDF矢量与字体','通过','36份全部实际渲染；嵌入字体；无内嵌位图'),
        ('F04','逐图视觉验收','通过','六页接触表覆盖36图；修订F13/A03单图复查，无缺字、截断或图例覆盖关键信息'),
        ('D01','活动文档更新','通过',f'{len(changes)}个当前文档/页面修改，均有原样备份'),
        ('D02','论文提纲证据映射','通过','八章提纲、RQs、图表、分母、贡献与限制匹配；无论文正文'),
        ('D03','历史文档版本边界','保留','冻结提纲、协议、before与历史写作包不改；失效相对链接只作分类记录'),
        ('P01','目标电脑实际运行','待完成','本机干净标准库/中文路径已验证；第二电脑安装及物理一致性未实测'),
        ('P02','持物等待控制缺陷','待改进','v11已持物仍等待，建议独立v12按机制/37诊断/240开发门槛推进'),
        ('P03','WM泛化和排序优势','证据有限','开发弱于强BC、Full−Plain区间跨零；图表重绘不解决学习问题'),
        ('P04','v5同批关闭恢复对照','现有证据缺口','旧v2/v3四组不可代替；现定位可保留为局限，若做因果优势需新实验'),
        ('P05','学校格式/文献深读/许可','待作者落实','无正式模板；相关工作不等于首创证明；不替作者选择代码许可'),
        ('C01','临时文件清理','未执行',f'约{cleanup["candidate_bytes"]/2**20:.1f}MiB候选；前次自动审批拒绝，未绕过'),
    ]
    with (RUN/'CHECKLIST.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['id','item','status','evidence']);w.writerows(checklist)
    (RUN/'CHECKLIST.md').write_text('# 检查清单\n\n| ID | 项目 | 状态 | 凭据/边界 |\n|---|---|---|---|\n'+''.join('| '+' | '.join(r)+' |\n' for r in checklist),encoding='utf8')
    report=f'''# 全项目复查、论文图表整改与提纲评估

2026-10-15。起始提交f6acd284a423fe323f2cbd76c5f5724ec9f64eb1。用户先收到完整计划，然后执行本轮整理。没有新训练、物理实验、权重替换或论文正文。

## 判断

**现有主要实验和证据可支撑系统设计与实验分析型本科毕业论文。项目不完美，也没有稳定的新世界模型算法优势证明。** 原世界模型无恢复确认与v5恢复确认为主文；v6—v11按明确版本作为机制/局限分析。学校任务书和评分细则未提供，不能代替导师或学校认定毕业资格。

## 全项目检查范围与结果

| 检查 | 结果 |
|---|---|
| 修改前受管理文件 | {inv['tracked_files']}个，{inv['tracked_bytes']/2**30:.2f} GiB；全部重新计算SHA-256 |
| 代码/JSON | {inv['syntax_files']}个Python、{inv['json_files']}个JSON解析通过 |
| JSONL | {tr['unique_files']}个唯一文件，{tr['unique_lines']:,}行，读取与非有限常量检查通过 |
| 数值/图像资产 | {assets['unique_assets']}个唯一资产读取通过；权重{counts['.pt']}路径/{unique['.pt']}内容，HDF5/NPZ及图像/CSV均检查 |
| 保存的结果 | 1,505份：1,372 complete、130旧格式未记录状态、3份已知早期中断；不把无状态自动视为通过全部运行 |
| 任务输出 | 82份注册表无缺失明确输出 |
| 统计 | 2,640记录、42行原规则bootstrap区间重新核算一致；135来源哈希一致 |
| 冻结契约 | 原WM确认30、v5确认47、v11开发8个输入哈希一致；父轨迹划分不交叉 |
| 当前环境 | pip check、CUDA和7个主模型保存观测前向通过；不是新闭环实验 |
| 历史视频 | 35路径/23内容哈希与前次完整解码通过的文件一致；本轮没有声称重新完整解码全部视频 |

三份v7中断由序列化问题产生，后续pilot_b完整148执行已替代，不算主线遗漏；未过推进门槛的独立确认没有启动，不应补造结果。桌面原model.pt/policy_15000.pt已不在原路径，但项目保留权重仍与最初导入凭据SHA一致。

这是全仓资产扫描、数据重计和关键实现/文档的证据复核，不是逐行形式化证明，也没有按默认参数执行全部历史训练脚本。历史脚本中本机绝对路径与跨版本继承仍是维护成本；直接克隆不等于在任意电脑完成物理复现。

## 图片整改

36张图全部重新由保存数据生成，108份PNG/PDF/SVG和36份CSV；PNG600 dpi，PDF字体嵌入，全部PDF实际渲染且没有内嵌位图，SVG文字为路径。图宽180.3 mm，标签9 pt、刻度8 pt；终稿应按学校版心检查缩放。

- 覆盖旧19图主题：拆开密集图，合并重复F09/F19，补全v6/v10/v11诊断，共导出{fig['plotted_rows']:,}条测量或统计值。
- 训练主图改为固定全训练/开发集三项指标分开；原随机批次12点留作A01。不插值、不平滑、不删除负结果。
- H/K离散配置改为种子点与均值，成功率轴0–100%；ECDF仍为正确阶梯；阶段类别改为时间条。
- F13把动力学逐值一致的Full/control/calibrated合并成Full线，明确不是丢弃不同结果；Plain保留。
- v11退步的目标XY距离从保存状态提取到新CSV，补齐旧图画了但旧CSV没有的变量。
- 六张汇总检查图覆盖全部36图，并单独复核修订后的F13/A03。未发现乱码、裁切或遮挡关键信息；这种视觉验收不等于已按学校终稿模板排版。

完整见[图注目录](FIGURE_CATALOG.md)、[曲线解释](CURVE_EXPLANATIONS.md)、[图形校验](validation/figure_validation.json)和[PLOT_SOURCES](PLOT_SOURCES.json)。

## 文档发现与处理

共更新{len(changes)}个活动文档/页面，原样备份在before；不改历史协议或旧迁移包。

1. DELIVERY_CHECKLIST仍将v6—v11增补标未完成：改为本机完成、目标设备待验收。
2. GITHUB_UPLOAD/PROJECT_NAVIGATION使用旧清单数量和校验入口：切换本轮verify及10,270修改前基线。
3. 根提纲和若干协议/统计文档页尾保留10月12版本却已有15日更新：区分当前文档复核日期与旧实验协议日期。
4. WORKSPACE可见路径文字仍指旧consolidation页面；论文分类只通向旧包：修正当前入口并保留历史标签。
5. 根提纲把当前视频与旧evidence清单并列易误解来源范围：新提纲按版本说明来源，不用旧manifest证明v11。
6. README/PROGRAM_GUIDE/STATUS与新图入口、当前完整性命令、迁移说明统一。原figures目录只加新入口，不覆盖旧图片。

修改前全仓Markdown扫描发现794条失效相对链接，集中在复制的历史文档/快照及旧README_before；原根活动文档没有失效链接。冻结副本中的相对链接不等于源资产丢失，不通过重写历史档案“修绿”。本轮活动文档和新页面链接另做实际校验。

## 提纲与论文可行性

[当前详细提纲](THESIS_OUTLINE_REVIEWED.md)把8章、3个研究问题、数据分母、图片与负结果逐项对应。当前贡献在延迟一致性、可复核实验体系和预算内共享恢复，不把公共数据、框架、BC权重或11个版本数当原创算法贡献。

必须保留：Full−BC联合+4.72[0.56,10.28]百分点的批次条件；Full−Plain+1.94[−0.56,6.11]不确定；v5−v4+1.46[0,4.17]仅2起点7执行救回；v11开发235/240未采用。原WM确认与v5确认不能跨批相减，旧v2/v3四组分析不能代替v5关闭恢复实验。

已有基础8篇及后补RTC/REMAC阅读层级写清；本轮未做新的全面文献检索或全球新颖性证明。正式写作前补直接相关方法阅读、学校格式与来源声明。

## 仍待整改

优先顺序见[下一步计划](PLAN_AND_NEXT_STEPS.md)：目标设备验收与作者确认题目范围；若继续控制优化，另建v12处理持物等待，再按37诊断/240开发门槛推进；希望更强学习贡献时再扩父轨迹覆盖。绘图本身不能修复泛化或恢复失败。

约{cleanup['candidate_bytes']/2**20:.1f} MiB临时副本可评估清理，但本轮删除0文件。前次自动审批拒绝清理组合命令，未绕过。原JSONL、权重、失败、冻结版本与旧包不是垃圾。具体路径见[清理清单](CLEANUP.md)。

当前前端新增论文图表入口，并替换本页使用的v10/v11轨迹与RMSE图；旧视频和统计保持原样。本轮另建图表/提纲ZIP，旧三ZIP保持原样。所有实际验收记录见validation目录；当前历史保全用verify.py，旧verify绑定旧文档版本，不要改旧清单绕过差异。
'''
    (RUN/'REPORT.md').write_text(report,encoding='utf8')
    print(json.dumps({'checklist_items':len(checklist),'documents':len(changes),'cleanup_candidate_mib':cleanup['candidate_bytes']/2**20,'assets_by_path':dict(counts)},ensure_ascii=False))
if __name__=='__main__':main()
