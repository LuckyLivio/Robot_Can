from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2];OLD=ROOT/'reproduction/progress_v10_20261015_01';NEW=ROOT/'reproduction/progress_v11_20261015_01'
NEW.mkdir(exist_ok=False);shutil.copytree(OLD/'demo',NEW/'demo')
p=NEW/'demo/index.html';s=p.read_text(encoding='utf8')
s=s.replace('v10 · 箱沿接近','v11 · 罐体接近空间').replace('id="v10-state"','id="v11-state"')
s=s.replace('箱沿物体的接近高度、有限倾斜与分段路径。小测试和消融已完成；成功率未达门槛，未进入240回合开发。全部保持400步预算。','联合选择倾斜方向、手指闭合方向和抓取高度，验证罐体进入两指之间的空间。保持400步，先做小测试与消融。')
s=s.replace('四组均30/37；未进入240回合开发，主版本仍为v5。','本轮正在验证。历史结果不代表v11结果；主版本仍为v5。')
s=s.replace('箱沿失败：轨迹和真实接触','v10历史诊断：轨迹和真实接触')
s=s.replace('v10 只处理已识别的直立箱沿支撑；BC 与 Full 使用相同规则。','v11 只处理已识别的直立箱沿支撑；BC 与 Full 使用相同规则。').replace('下方视频为历史回放，不代表 v10。','下方视频与v10诊断图为历史记录，不代表v11。')
s=s.replace('<div class="progress-links">','<div class="progress-links"><a href="../../improvement_v11_20261015_01/REPORT.md">v11 当前报告 ↗</a><a href="../../improvement_v11_20261015_01/protocols/PLAN.md">v11 执行前协议 ↗</a>')
p.write_text(s,encoding='utf8')
s=(OLD/'demo/progress.js').read_text().replace('d.v10','d.v11').replace('v10-state','v11-state').replace('v8 · 历史合用','v10 · 历史合用')
(NEW/'demo/progress.js').write_text(s,encoding='utf8')
s=(OLD/'update_progress.py').read_text().replace('improvement_v10_20261015_01','improvement_v11_20261015_01').replace("'v10':current","'v11':current").replace("'pilot_a','dev_a'","'pilot_a','pilot_b','dev_a'")
(NEW/'update_progress.py').write_text(s,encoding='utf8')
p=ROOT/'index.html';p.write_text(p.read_text(encoding='utf8').replace('progress_v10_20261015_01','progress_v11_20261015_01'),encoding='utf8')
p=ROOT/'README.md';s=p.read_text(encoding='utf8');first=s.index('\n\n')
s='> v11罐体接近空间实验进行中，旧资产保留，主版本仍为v5。[本轮报告](reproduction/improvement_v11_20261015_01/REPORT.md) · [当前前端](http://127.0.0.1:8766/)。'+s[first:]
s=s.replace('progress_v10_20261015_01/demo/','progress_v11_20261015_01/demo/').replace('当前整合版包含 v10 的实验状态','当前整合版包含 v11 的实验状态')
p.write_text(s,encoding='utf8')
