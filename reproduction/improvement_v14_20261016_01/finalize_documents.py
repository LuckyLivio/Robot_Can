"""Update nine active entry docs, always preserve exact prior copies."""
from pathlib import Path
import json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];REL=RUN.relative_to(ROOT).as_posix()
DOCS=['README.md','index.html','STATUS.md','DEMO_GUIDE.md','RESULTS.md','EVIDENCE_INDEX.md','PROJECT_NAVIGATION.md','THESIS_HANDOFF_LATEST.md','PROGRAM_GUIDE.md']
SUMMARY='v14 两轮小测试共64次；最终 v13 / T / C / v14 为6/8、6/8、5/8、6/8。门槛未通过，未采用；未运行大规模消融、240次开发或全新起点确认。'
LINKS=f'[本轮检查报告]({REL}/REPORT.md) · [v14前端]({REL}/index.html) · [执行前协议]({REL}/protocols/PLAN.md) · [v13原报告](reproduction/improvement_v13_20261016_01/REPORT.md)'
START=f'''```powershell
Set-Location 'C:\\Users\\Livio\\Desktop\\robot_can'
& '.\\.venv\\Scripts\\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\\Users\\Livio\\Desktop\\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/{REL}/index.html** 。如果8766服务已经运行，直接打开即可；终端保持运行，Ctrl+C关闭。
'''
if __name__=='__main__':
    assert json.loads((RUN/'SUMMARY.json').read_text(encoding='utf8'))['status']=='smoke_gate_failed_not_adopted'
    for name in DOCS:assert (RUN/'before'/name).exists(),name
    root_readme=f'''# CAN LAB · 机器人世界模型与恢复控制

本项目研究延迟控制下的机器人罐体抓取搬运：冻结BC策略产生候选，世界模型预测并评分，恢复控制器处理抓取失效、姿态变化和路径约束。实验使用仿真中的特权当前状态，不等同于视觉输入或实机验证。

## 当前状态（2026-10-16）

**{SUMMARY}**

斜靠案例的首次接近、抓取和抬升已改善；剩余失败为持物搬运的关节可达性与箱沿路径耗时。C单独消融还损失一个旧成功，不能宣称总体改善。既有正式成果、v13及全部旧代码、权重和结果保留。本轮没有训练，也没有论文正文。

{LINKS}

## 启动前端

{START}

页面展示两轮四组结果、两个同起点真实动作回放、失败原因与门槛。视频双方均如实显示400步未完成。旧v13页面仍可直接访问：http://127.0.0.1:8766/reproduction/improvement_v13_20261016_01/index.html 。

## 导航

- [项目分类导航](PROJECT_NAVIGATION.md)
- [环境与运行指南](PROGRAM_GUIDE.md)
- [当前状态与门槛](STATUS.md)
- [结果索引](RESULTS.md)
- [证据索引](EVIDENCE_INDEX.md)
- [前端演示指南](DEMO_GUIDE.md)
- [写作材料交接状态](THESIS_HANDOFF_LATEST.md)
- [本轮目录及复查命令]({REL}/README.md)
- [此前README原样快照]({REL}/before/README.md)

当前v14不可替换已经封存的对照结果。实验完成、保存输入回放、物理回放与预先准备的作业分别计数；失败记录不删除，缺失实验不以图表补成成功。
'''
    (ROOT/'README.md').write_text(root_readme,encoding='utf8')
    (ROOT/'STATUS.md').write_text(f'''# 当前项目状态

{SUMMARY}

{LINKS}

| 项目 | 当前证据 |
|---|---|
| v14小测试与局部四组消融 | smoke_a、smoke_b共64次，完整保留 |
| 动作与物理核验 | 64次、22,174步，精确通过；不新增统计样本 |
| 新代码机制检查 | 25项，88项继承配置不变 |
| 372次大规模消融 | 门槛未过，未运行 |
| 240次开发对照 | 未运行 |
| 全新起点确认 | 未运行，起点尚未生成 |
| 采用 / 冻结用于确认 | 未采用 / 未冻结 |
| 泛化训练、论文正文 | 本轮均未进行 |

下一步应先验证持物搬运姿态与分段箱沿路径，保持400步及原保护。回正模块必须消除额外耗时造成的旧成功退步。详见报告第6节。

历史状态：[v13报告](reproduction/improvement_v13_20261016_01/REPORT.md)；[此前状态原样快照]({REL}/before/STATUS.md)。历史主成果不因本轮局部改善而自动替换。
''',encoding='utf8')
    (ROOT/'DEMO_GUIDE.md').write_text(f'''# 前端与机器人演示

{START}

建议演示顺序：先看“未通过门槛”及四组结果，再播放斜靠和箱沿两段同起点对比，最后查看原始证据与改进计划。两段都是预先指定的已知难例，均未在400步完成；它们解释失败机制，不能充当总体成功率证据。

每个视频20fps对应20Hz控制，421帧、21.05秒；逐步重放实际动作，末尾保持终点，无平滑插帧。页面支持浏览器原生播放、暂停与进度定位。演示前端不启动训练或新物理控制实验。

{LINKS}

历史演示说明：[此前DEMO_GUIDE快照]({REL}/before/DEMO_GUIDE.md)。
''',encoding='utf8')
    (ROOT/'PROGRAM_GUIDE.md').write_text(f'''# 项目运行指南（当前入口）

{SUMMARY}

## 环境

使用项目现有 `.venv\\Scripts\\python.exe`。在PyCharm将项目解释器设置为该文件；沿用现有依赖和数据路径，不需要为本轮重新安装或替换权重。

## 启动展示

{START}

## 实验与检查

本轮控制代码在 `{REL}/recovery/`，运行器、逐步动作审计、物理回放和完整度检查均在同一目录。[本轮README]({REL}/README.md)提供只读核验和新目录复跑命令。[执行前协议]({REL}/protocols/PLAN.md)定义阶段门槛。

`protocols/pilot_jobs.json`代表已准备的372次作业，当前并未运行。开发冻结脚本会拒绝未过关的小测试；不要绕过它启动开发或独立确认。全新起点必须在版本冻结后生成，本轮尚未生成。

{LINKS}

早期数据、训练和历史复现实验说明保留在[此前完整指南快照]({REL}/before/PROGRAM_GUIDE.md)。它们对应各自冻结版本，请按原版本目录运行，不能与v14的64次诊断混为同一实验。
''',encoding='utf8')
    for name,title in [('RESULTS.md','实验结果索引'),('EVIDENCE_INDEX.md','证据索引'),('PROJECT_NAVIGATION.md','项目导航'),('THESIS_HANDOFF_LATEST.md','写作材料交接状态')]:
        old=(RUN/'before'/name).read_text(encoding='utf8')
        extra=('\n既有跨设备写作包是历史封存材料，不包含本轮v14新增文件。当前不更新论文正文或把v14写成已确认优势；若之后写作，使用本轮报告准确说明门槛失败。\n' if name=='THESIS_HANDOFF_LATEST.md' else '')
        header=f'# {title} · 当前入口\n\n**{SUMMARY}**\n\n{LINKS}\n{extra}\n[本轮原始配对表]({REL}/analysis/smoke_b_pairs.csv) · [本轮图表]({REL}/figures/CATALOG.json) · [完整度检查脚本]({REL}/verify_integrity.py)\n\n## 历史内容（以下为此前文档，按原版本时间解释）\n\n'
        (ROOT/name).write_text(header+old,encoding='utf8')
    (ROOT/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={REL}/index.html"><title>CAN LAB · v14 诊断</title><a href="{REL}/index.html">打开v14诊断报告（未采用）</a></html>',encoding='utf8')
    (RUN/'document_changes.json').write_text(json.dumps({'updated':DOCS},indent=2),encoding='utf8')
    print('Updated 9 active entries; all prior bytes preserved in before/.')
