from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2];OLD=ROOT/'reproduction/progress_v9_20261015_01';NEW=ROOT/'reproduction/progress_v10_20261015_01'
NEW.mkdir(exist_ok=True)
if not (NEW/'demo').exists():shutil.copytree(OLD/'demo',NEW/'demo')
text=(NEW/'demo/index.html').read_text(encoding='utf8')
text=text.replace('v9 · 本轮迭代','v10 · 箱沿接近').replace('id="v9-state"','id="v10-state"')
text=text.replace('../figures/prediction_rmse_mobile.svg','../../consolidation_20261012_01/figures/prediction_rmse_mobile.svg')
text=text.replace('关节限位下的等价姿态选择与规划耗时。','箱沿物体的接近高度、有限倾斜与分段路径。')
text=text.replace('v9 的共享恢复器额外读取七个关节角度，BC 与 Full 使用同一规则。400 步包含规划等待。首轮曾发现末端坐标系偏置，修复后的 pilot_b 才用于本轮结论；全过程保留。','v10 只处理已识别的直立箱沿支撑；BC 与 Full 使用相同规则。400 步包含规划等待。静态可达、实际抓起与完成搬运分别核验；全部失败批次保留。下方视频为历史回放，不代表 v10。')
text=text.replace('<div class="progress-links">','<div class="progress-links"><a href="../../improvement_v10_20261015_01/REPORT.md">v10 结果与限制 ↗</a><a href="../../improvement_v10_20261015_01/protocols/PLAN.md">v10 执行前协议 ↗</a>')
(NEW/'demo/index.html').write_text(text,encoding='utf8')
script=(OLD/'update_progress.py').read_text().replace('improvement_v9_20261015_01','improvement_v10_20261015_01').replace("'v9':current","'v10':current").replace("['smoke_a','pilot_a','pilot_b','dev_a']","['smoke_a','smoke_b','pilot_a','dev_a']")
(NEW/'update_progress.py').write_text(script,encoding='utf8')
js=(OLD/'demo/progress.js').read_text().replace('d.v9','d.v10').replace('v9-state','v10-state')
start=js.index('    if(d.v10.timing)');end=js.index("    document.getElementById('progress-error')",start)
js=js[:start]+"    if(d.v10.summary) document.getElementById('progress-metrics').textContent=d.v10.summary;\n"+js[end:]
(NEW/'demo/progress.js').write_text(js,encoding='utf8')
index=(ROOT/'index.html').read_text(encoding='utf8').replace('progress_v9_20261015_01','progress_v10_20261015_01')
(ROOT/'index.html').write_text(index,encoding='utf8')
readme=(ROOT/'README.md').read_text(encoding='utf8')
readme=readme.replace('progress_v9_20261015_01','progress_v10_20261015_01').replace('当前整合版包含 v9 的实验状态','当前整合版包含 v10 的实验状态')
readme='> 当前 v10 箱沿接近实验正在核验，旧成果完整保留。前端入口：<http://127.0.0.1:8766/>。新结果与状态见 [v10 报告](reproduction/improvement_v10_20261015_01/REPORT.md)。\n\n'+readme
(ROOT/'README.md').write_text(readme,encoding='utf8')
