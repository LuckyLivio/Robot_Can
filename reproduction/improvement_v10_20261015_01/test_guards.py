from pathlib import Path
import copy,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery.recovery_controller import RecoveryController,Config
from recovery.path_search import EdgeSearch,turn_samples,sweep_margin
from probe import snapshot
if __name__=='__main__':
    old,x,q=snapshot();old.cfg=Config();s=EdgeSearch(old,x,q)
    while not s.advance(16):pass
    assert s.chosen is not None
    checks=[]
    for reason in ['unknown_support','pose_changed']:
        c=RecoveryController([.1975,.4025,.8],.8,x,True,Config())
        c.__dict__.update(copy.deepcopy(old.__dict__))
        c.edge_events=[];c.edge_search=None;c.edge_plan=copy.deepcopy(s.chosen);c.edge_checked=True;c.edge_start=x[:3].copy()
        c.mode='EDGE_APPROACH';c.edge_age=0;c.edge_settled=0;c.set_joint_positions(q)
        y=x.copy()
        if reason=='unknown_support':y[19:23]=Rotation.from_euler('y',45,degrees=True).as_quat()
        else:y[16]+=.02
        action,info=c.choose(y,np.ones(7,np.float32),np.zeros(7,np.float32))
        assert c.mode=='POSE_WAIT' and info['mode']!='DESCEND' and info.get('next_mode')!='DESCEND'
        checks.append(reason+' cancels edge approach before descent')
    # Dense reference along the accepted in-place turn independently checks the arc-bound result.
    initial=Rotation.from_quat(x[3:7]).as_matrix();end=s.chosen['rotation'];rv=Rotation.from_matrix(end@initial.T).as_rotvec()
    dense=[sweep_margin(x[:3],x[:3],Rotation.from_rotvec(rv*t).as_matrix()@initial,s.gap) for t in np.linspace(0,1,201)]
    assert min(dense)>=.001
    checks.append('201 dense orientations along accepted turn remain separated from fixed boxes')
    result={'passed':True,'checks':checks,'minimum_dense_turn_margin_m':min(dense),'scope':'Targeted new-mode guards and fixed-hand geometry; not a whole-arm certificate.'}
    with (RUN/'analysis/guards_b.json').open('x') as f:json.dump(result,f,indent=2)
    print(result)
