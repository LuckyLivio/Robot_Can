from pathlib import Path
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];OLD=ROOT/'reproduction/improvement_v9_20261015_01'
s=(OLD/'verify_run.py').read_text().replace('audited_v9','audited_v10')
s=s.replace("from reproduction.improvement_v8_20261015_01.recovery.recovery_controller import RecoveryController as V8,Config as V8Config","from reproduction.improvement_v9_20261015_01.recovery.recovery_controller import RecoveryController as V9,Config as V9Config")
s=s.replace("legacy.controller_class=lambda v:(V6,V6Config) if v=='v6' else ((V8,V8Config) if v=='v8' else (Audited,m.Config))","legacy.controller_class=lambda v:(V9,V9Config) if v=='v9' else (Audited,m.Config)")
s=s.replace("if j['version'] not in ['v6','v8']:","if j['version']!='v9':")
s=s.replace("assert r['geometry_events']==c.geometry_events","assert r['geometry_events']==c.geometry_events and r['edge_events']==c.edge_events")
(RUN/'verify_run.py').write_text(s,encoding='utf8')
s=(OLD/'verify_physics.py').read_text().replace("['v6','v8','joint','bounded','v9']","['v9','height','path','v10']")
(RUN/'verify_physics.py').write_text(s,encoding='utf8')
s=(OLD/'analyze_pilot.py').read_text().replace("['v6','v8','joint','bounded','v9']","['v9','height','path','v10']")
s=s.replace("summary={}\n", "baseline={}\n    for f in (RUN.parents[1]/'reproduction/improvement_v9_20261015_01/pilot_b').glob('v6_*/result.json'):\n        d=json.loads(f.read_text());j=d['job']\n        for r in d['records']:baseline[(j['id'].split('_',1)[1],r['demo'])]=r\n    summary={}\n")
s=s.replace("b=rows['v6'].get(k)","b=baseline.get(k)")
(RUN/'analyze_pilot.py').write_text(s,encoding='utf8')
