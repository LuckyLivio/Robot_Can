from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OLD=ROOT/'reproduction/progress_v9_20261015_01';NEW=ROOT/'reproduction/progress_v10_20261015_01'
s=(OLD/'verify_frontend.py').read_text().replace('improvement_v9_20261015_01','improvement_v10_20261015_01').replace("['v9']","['v10']").replace("=='pilot_b'","=='pilot_a'")
s=s.replace("if k in ['src','href'] and v:links.append(v)","if k in ['src','href','srcset'] and v:links.append(v)")
(NEW/'verify_frontend.py').write_text(s,encoding='utf8')
p=NEW/'demo/index.html';s=p.read_text(encoding='utf8')
s=s.replace('小测试和消融达标后才进入 240 回合开发对照，保持 400 步预算。','小测试和消融已完成；成功率未达门槛，未进入240回合开发。全部保持400步预算。')
s=s.replace('不同阶段分开统计；37 条件为已知诊断，不是独立确认。','不同阶段分开统计；37 条件为已知诊断，不是独立确认。表内救回与退步均相对历史v6。')
p.write_text(s,encoding='utf8')
