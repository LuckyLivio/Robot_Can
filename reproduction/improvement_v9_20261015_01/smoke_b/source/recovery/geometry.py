"""Cached vertical hand sweeps and resumable v8 candidate enumeration."""
from functools import lru_cache
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from reproduction.improvement_v8_20261015_01.recovery.geometry import support,BOXES,hand_vertices,path_margin as general_path_margin
from reproduction.recovery_v5_20261012_01.clearance import PARTS

CENTERS=np.array([c for c,h in BOXES]);HALVES=np.array([h for c,h in BOXES])
LOCAL=[]
for name,v,e in PARTS:
    hull=ConvexHull(v);LOCAL.append((name,v,hull.equations[:,:3],v[e[:,1]]-v[e[:,0]]))

@lru_cache(maxsize=128)
def projected_parts(rotation_tuple):
    R=np.array(rotation_tuple).reshape(3,3);result=[];vertical=np.array([0.,0.,1.])
    for name,v,normals,edges in LOCAL:
        v=v@R.T;edges=edges@R.T
        # Face normals of the convex extrusion and edge x AABB-edge axes.
        axes=np.r_[np.eye(3),normals@R.T,np.cross(edges,vertical),
                   np.cross(edges[:,None,:],np.eye(3)[None,:,:]).reshape(-1,3)]
        lengths=np.linalg.norm(axes,axis=1);axes=axes[lengths>1e-8]/lengths[lengths>1e-8,None]
        axes=np.unique(np.round(axes,7),axis=0)
        projections=v@axes.T
        result.append((name,axes,projections.min(0),projections.max(0),CENTERS@axes.T,HALVES@abs(axes).T,R[:,1]@axes.T))
    return result

def vertical_margin(above,goal,rotation,gap):
    assert np.linalg.norm(np.asarray(above)[:2]-np.asarray(goal)[:2])<1e-10
    worst=float('inf')
    for name,axes,lo,hi,centers,radius,yproj in projected_parts(tuple(np.asarray(rotation).ravel())):
        s=np.asarray(above)@axes.T;t=np.asarray(goal)@axes.T
        for aperture in [0.,gap]:
            shift=(aperture-.06)/2 if 'finger1' in name else (-(aperture-.06)/2 if 'finger2' in name else 0.)
            a=lo+np.minimum(s,t)+shift*yproj;b=hi+np.maximum(s,t)+shift*yproj
            margin=np.max(np.maximum(a[None,:]-centers-radius,centers-radius-b[None,:]),axis=1)
            worst=min(worst,float(margin.min()))
            if worst<.001:return worst
    return worst

def options(controller,x,domain):
    axis=domain['axis'];side=abs(axis[2])<.35;current=Rotation.from_quat(x[3:7]).as_matrix()
    down=np.diag([1.,-1.,-1.]);yaw0=np.arctan2(axis[1],axis[0]) if side else 0.
    gap=controller.cfg.side_gap_m if side else controller.cfg.corner_gap_m;opts=[]
    for yaw_delta in ([0.] if side else [0.,np.pi/2,np.pi/4,-np.pi/4]):
        for flip in [0.,np.pi]:
            nominal=Rotation.from_rotvec([0,0,yaw0+yaw_delta+flip]).as_matrix()@down
            tilts=[(0.,np.array([1.,0.]))]
            if side:tilts += [(d,np.array(v)) for d in [10.,20.,30.,35.] for v in [(1,0),(-1,0),(0,1),(0,-1)]]
            for degree,away in tilts:
                rot=Rotation.from_rotvec(np.deg2rad(degree)*np.r_[-away[1],away[0],0.]).as_matrix()@nominal
                for height in ([.008,.014,.020] if side else [.012]):
                    for shift in [0.,-.01,.01]:
                        offset=np.array([0.,0.,height])+shift*(axis if side else rot[:,0])
                        cost=float(np.linalg.norm(Rotation.from_matrix(rot@current.T).as_rotvec()))*.01+abs(shift)+(height-.008)+.03*degree/35
                        key=tuple(np.round(np.r_[rot.ravel(),offset,gap],4).tolist())
                        opts.append((cost,{'rotation':rot,'offset':offset,'gap':gap,'key':key,'domain':domain,'kind':'sideways' if side else 'upright'}))
    return [v for _,v in sorted(opts,key=lambda s:s[0])]

class Search:
    def __init__(self,controller,x):
        self.x=np.array(x).copy();self.floor=controller.floor
        self.domain,self.reason=support(x,self.floor);self.done=self.domain is None;self.chosen=None;self.checked=0
        self.opts=[] if self.done else options(controller,x,self.domain)
        self.index=0;self.failed=list(controller.failed_plans)
        self.extra=controller.cfg.aperture_tolerance_m+controller.cfg.gap_uncertainty_m
    def advance(self,count=8):
        for _ in range(count):
            if self.done:break
            if self.index>=len(self.opts):self.done=True;self.reason='mesh_supported_no_hand_path';break
            opt=self.opts[self.index];self.index+=1
            if any(np.linalg.norm(self.x[16:19]-p['position'])<.008 and p['key']==opt['key'] for p in self.failed):continue
            goal=self.x[16:19]+opt['offset'];above=np.r_[goal[:2],max(self.floor+.20,self.x[18]+.14)]
            margin=vertical_margin(above,goal,opt['rotation'],opt['gap']+self.extra);self.checked+=1
            if margin>=.001:self.chosen={**opt,'margin':margin};self.done=True
        return self.done
