from pathlib import Path
import copy,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery.recovery_controller import RecoveryController,Config
from recovery.path_search import EdgeSearch
from reproduction.improvement_v10_20261015_01.probe import snapshot
from reproduction.improvement_v10_20261015_01.recovery.path_search import EdgeSearch as OldSearch
if __name__=='__main__':
    old,x,q=snapshot();old.cfg=Config();s=EdgeSearch(old,x,q)
    while not s.advance(16):pass
    checks=[]
    def create(plan):
        c=RecoveryController([.1975,.4025,.8],.8,x,True,Config());c.__dict__.update(copy.deepcopy(old.__dict__))
        c.edge_events=[];c.edge_search=None;c.edge_plan=copy.deepcopy(plan);c.edge_checked=True;c.edge_start=x[:3].copy()
        c.mesh_offset=plan['offset'];c.planned_rotation=plan['rotation'];c.approach_gap=plan.get('target_gap',.06)
        c.edge_age=0;c.edge_settled=0;c.set_joint_positions(q);return c
    for reason in ['unknown_support','pose_changed']:
        c=create(s.chosen);c.mode='EDGE_APPROACH';y=x.copy()
        if reason=='unknown_support':y[19:23]=Rotation.from_euler('y',45,degrees=True).as_quat()
        else:y[16]+=.02
        a,d=c.choose(y,np.ones(7,np.float32),np.zeros(7,np.float32))
        assert c.mode=='POSE_WAIT' and d['mode']!='DESCEND' and d.get('next_mode')!='DESCEND';checks.append(reason+' cancels new approach')
    bad=OldSearch(old,x,q)
    while not bad.advance(16):pass
    c=create(bad.chosen);c.mode='DESCEND';y=x.copy();y[:3]=bad.chosen['above'];y[3:7]=Rotation.from_matrix(bad.chosen['rotation']).as_quat();y[7:9]=[.032,-.032]
    a,d=c.choose(y,np.ones(7,np.float32),np.zeros(7,np.float32))
    assert c.mode=='POSE_WAIT' and d['mode']!='DESCEND' and any(e['event']=='executed_pose_can_guard' for e in c.edge_events)
    checks.append('old premature-finger-contact path rejected before another descent command')
    c=create(bad.chosen);c.mode='CLOSE';a,d=c.choose(y,np.ones(7,np.float32),np.zeros(7,np.float32))
    assert c.mode=='CLOSE' and a[6]>0;checks.append('intended closing is not blocked by open-approach guard')
    out={'passed':True,'checks':checks}
    with (RUN/'analysis/guards_a.json').open('x') as f:json.dump(out,f,indent=2)
    print(out)
