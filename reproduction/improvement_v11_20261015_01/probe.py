from pathlib import Path
import json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from reproduction.improvement_v10_20261015_01.probe import snapshot
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK
from reproduction.improvement_v10_20261015_01.recovery.path_search import sweep_margin
from recovery.object_clearance import object_margin,enclosure
def solve(q,p,r):
    s=IK(q,p,r,48)
    while not s.advance(16):pass
    return s.receipt()
if __name__=='__main__':
    c,x,q=snapshot();radial=x[16:18]-np.array([-.5,-.1]);radial/=np.linalg.norm(radial);yaw=np.arctan2(radial[1],radial[0]);rows=[]
    for height in [.012,.020,.026]:
        for flip in [False,True]:
            down=Rotation.from_euler('z',yaw+(np.pi if flip else 0)).as_matrix()@np.diag([1.,-1.,-1.])
            r=Rotation.from_rotvec(-np.deg2rad(35)*np.r_[-radial[1],radial[0],0.]).as_matrix()@down
            g=x[16:19]+np.r_[-.006*radial,height];above=g-r[:,2]*.08
            solves=[];qq=q.copy()
            for p in [x[:3],above,g]:
                a=solve(qq,p,r);solves.append(a);qq=np.array(a['q'])
            row={'height_m':height,'flip':flip,'ik':solves,'enclosure':enclosure(g,r,.0545,x),'can_parts':object_margin(above,g,r,.0545,x,True),'box_margin_m':sweep_margin(above,g,r,.0655)};rows.append(row)
            print(height,flip,[(a['success'],round(a['position_error_m'],4),round(a['limit_margin_rad'],3)) for a in solves],round(row['enclosure']['inner_clearance_m'],4),[(p['part'].split('_')[-2],round(p['margin_m'],4)) for p in row['can_parts']])
    with (RUN/'analysis/local_geometry_probe.json').open('x') as f:json.dump(rows,f,indent=2)
