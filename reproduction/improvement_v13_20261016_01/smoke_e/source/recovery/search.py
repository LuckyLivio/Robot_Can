"""Bounded local candidates with inherited hand/can/IK path certificates."""
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v9_20261015_01.recovery.geometry import vertical_margin
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import enclosure,object_margin
from reproduction.improvement_v11_20261015_01.recovery.path_search import EdgeSearch

def options(c,x,domain):
    axis=domain['axis'].copy()
    if axis[2]<0:axis=-axis
    horizontal=axis.copy();horizontal[2]=0;horizontal/=np.linalg.norm(horizontal)
    current=Rotation.from_quat(x[3:7]).as_matrix();out=[]
    for slope in [0.,1.,.5]:
        ax=horizontal*(1-slope)+axis*slope;ax/=np.linalg.norm(ax)
        y=np.cross([0.,0.,-1.],ax);y/=np.linalg.norm(y);z=np.cross(ax,y)
        nominal=np.column_stack([ax,y,z])
        for flip in [False,True]:
            r=nominal@np.diag([-1.,-1.,1.]) if flip else nominal
            for height in [.008,.016,.024]:
                for shift in [0.,-.015,.015]:
                    offset=(-.01+shift)*domain['axis']+np.array([0.,0.,height]);goal=x[16:19]+offset
                    enc=enclosure(goal,r,.06,x)
                    need=enc['closure_extent_m']+2*abs(enc['closure_center_m'])+.007+c.cfg.aperture_tolerance_m+c.cfg.gap_uncertainty_m
                    gap=max(.060,float(np.ceil(need/.002)*.002))
                    if gap>.072:continue
                    cost=.01*np.linalg.norm(Rotation.from_matrix(r@current.T).as_rotvec())+height+abs(shift)+.003*slope
                    key=tuple(np.round(np.r_[r.ravel(),offset,gap],4))
                    out.append((cost,{'rotation':r,'offset':offset,'gap':gap,'key':key,'domain':domain,'kind':'sideways'}))
    return [o for _,o in sorted(out,key=lambda t:t[0])]

class Search:
    def __init__(self,c,x,domain):
        self.x=np.array(x).copy();self.floor=c.floor;self.domain=domain;self.reason='support13_pending'
        self.opts=options(c,x,domain);self.index=0;self.checked=0;self.done=False;self.chosen=None
        self.failed=list(c.failed_plans);self.extra=c.cfg.aperture_tolerance_m+c.cfg.gap_uncertainty_m
    def advance(self,count):
        for _ in range(count):
            if self.done:break
            if self.index==len(self.opts):self.done=True;self.reason='support13_no_clear_hand_candidate';break
            o=self.opts[self.index];self.index+=1
            if any(np.linalg.norm(self.x[16:19]-f['position'])<.008 and o['key']==f['key'] for f in self.failed):continue
            goal=self.x[16:19]+o['offset'];above=np.r_[goal[:2],max(self.floor+.24,self.x[18]+.14)]
            self.checked+=1
            margin=vertical_margin(above,goal,o['rotation'],o['gap']+self.extra)
            if margin<.001:continue
            can=object_margin(above,goal,o['rotation'],[o['gap']-self.extra,o['gap']+self.extra],self.x)
            if can<.003:continue
            self.chosen={**o,'margin':margin};self.reason='support13_mesh_candidate';self.done=True
        return self.done

class PathSearch(EdgeSearch):
    def __init__(self,c,x,q):
        super().__init__(c,x,q)
        goal=c.grasp_target(x);self.options=[]
        for distance in [.06,.10]:
            for flip in [False,True]:
                r=c.planned_rotation@np.diag([-1.,-1.,1.]) if flip else c.planned_rotation.copy()
                self.options.append({'rotation':r,'goal':goal.copy(),'above':goal-r[:,2]*distance,
                                     'offset':goal-x[16:19],'distance_m':distance,'flip':flip})
        self.index=0;self.begin()
