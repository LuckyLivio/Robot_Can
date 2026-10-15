from pathlib import Path
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];OLD=ROOT/'reproduction/improvement_v10_20261015_01'
s=(OLD/'verify_run.py').read_text().replace('audited_v10','audited_v11')
s=s.replace('from reproduction.improvement_v9_20261015_01.recovery.recovery_controller import RecoveryController as V9,Config as V9Config','from reproduction.improvement_v10_20261015_01.recovery.recovery_controller import RecoveryController as V10,Config as V10Config')
s=s.replace("(V9,V9Config) if v=='v9'","(V10,V10Config) if v=='v10'").replace("j['version']!='v9'","j['version']!='v10'")
s=s.replace("if descending:assert not self.kinematic_blocked", "if descending:assert not self.kinematic_blocked\n            if info['mode']=='DESCEND' and self.cfg.can_guard and self.edge_plan is not None:\n                import numpy as np\n                from scipy.spatial.transform import Rotation\n                rot=Rotation.from_quat(x[3:7]).as_matrix();gap=abs(float(x[7]-x[8]))\n                assert m.object_margin(x[:3],self.grasp_target(x),rot,[gap-.001,gap+.001],x)>=.001\n                stats['can_guard_descents']=stats.get('can_guard_descents',0)+1")
(RUN/'verify_run.py').write_text(s,encoding='utf8')
s=(OLD/'verify_physics.py').read_text().replace("['v9','height','path','v10']","['v10','axis','guard','v11']")
# Capture the entire approach/closure/lift window of the new target case.
s=s.replace("270<=r['step']<=305","270<=r['step']<=330")
(RUN/'verify_physics.py').write_text(s,encoding='utf8')
s=(OLD/'analyze_pilot.py').read_text().replace("['v9','height','path','v10']","['v10','axis','guard','v11']")
(RUN/'analyze_pilot.py').write_text(s,encoding='utf8')
