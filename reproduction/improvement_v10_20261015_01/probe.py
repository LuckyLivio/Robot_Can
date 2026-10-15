"""Read-only FK/IK diagnosis of frozen observations; no policy tuning by rollout."""
from pathlib import Path
import json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from reproduction.improvement_v9_20261015_01.recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK
from reproduction.improvement_v9_20261015_01.recovery.geometry import vertical_margin,general_path_margin
def snapshot(step=169):
    p=ROOT/'reproduction/improvement_v9_20261015_01/pilot_b/v9_regression_6000005'
    job=json.loads((p/'result.json').read_text())['job'];c=None;prev=np.zeros(7,np.float32)
    for row in map(json.loads,(p/'trace.jsonl').open()):
        x=np.array(row['state_before'],np.float32)
        if c is None:c=RecoveryController([.1975,.4025,.8],.8,x,True,Config(**job['config']))
        c.set_joint_positions(row['joint_positions'])
        if row['step']==step:return c,x,c.joints.copy()
        c.choose(x,np.array(row['original_proposal'],np.float32),prev);prev=np.array(row['executed_action'],np.float32)
def solve(q,p,r):
    s=IK(q,p,r,96)
    while not s.advance(16):pass
    return s.receipt()
if __name__=='__main__':
    c,x,q=snapshot();goal=c.grasp_target(x);rows=[]
    for flip in [0,1]:
        r=c.planned_rotation@np.diag([-1.,-1.,1.]) if flip else c.planned_rotation
        for dz in [0.,.04,.06,.08,.10,.128]:
            p=goal+np.array([0,0,dz]);a=solve(q,p,r);b=solve(np.array(a['q']),goal,r)
            rows.append({'flip':flip,'height_above_grasp_m':dz,'target':p.tolist(),'above':a,'grasp_from_above':b,'vertical_margin_m':vertical_margin(p,goal,r,.0655)})
    out={'source':'frozen v9 pilot_b demo_6000005 step169','state':x.tolist(),'q':q.tolist(),'rotation':c.planned_rotation.tolist(),'goal':goal.tolist(),'domain':{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in c.mesh_domain.items()},'rows':rows,'note':'96 iterations for diagnosis only; local failure does not prove global infeasibility'}
    with (RUN/'analysis/height_probe.json').open('x') as f:json.dump(out,f,indent=2)
    for r in rows:print(r['flip'],r['height_above_grasp_m'],r['above']['success'],round(r['above']['position_error_m'],4),r['grasp_from_above']['success'],round(r['grasp_from_above']['position_error_m'],4),round(r['vertical_margin_m'],4))
