"""Fixed wall-top candidate families. No simulator or counterfactual rollouts."""
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v9_20261015_01.recovery.geometry import LOCAL,CENTERS,HALVES
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK

def sweep_margin(start,end,rotation,gap):
    """SAT for each hand part extruded along one straight fixed-rotation segment."""
    worst=float('inf');start=np.asarray(start);end=np.asarray(end);d=end-start
    for name,v,normals,edges in LOCAL:
        v=v@rotation.T;edges=edges@rotation.T
        axes=np.r_[np.eye(3),normals@rotation.T,np.cross(edges,d),np.cross(edges[:,None,:],np.eye(3)[None,:,:]).reshape(-1,3)]
        length=np.linalg.norm(axes,axis=1);axes=axes[length>1e-8]/length[length>1e-8,None]
        axes=np.unique(np.round(axes,7),axis=0)
        proj=v@axes.T;center=CENTERS@axes.T;radius=HALVES@abs(axes).T;y=rotation[:,1]@axes.T
        lo=proj.min(0)+np.minimum(start@axes.T,end@axes.T);hi=proj.max(0)+np.maximum(start@axes.T,end@axes.T)
        for aperture in [0.,gap]:
            shift=(aperture-.06)/2 if 'finger1' in name else (-(aperture-.06)/2 if 'finger2' in name else 0.)
            margin=np.max(np.maximum(lo[None,:]+shift*y-center-radius,center-radius-hi[None,:]-shift*y),axis=1)
            worst=min(worst,float(margin.min()))
            if worst<.001:return worst
    return worst

def turn_samples(start_rotation,end_rotation,gap):
    rv=Rotation.from_matrix(end_rotation@start_rotation.T).as_rotvec();angle=np.linalg.norm(rv)
    # Any point moves by at most radius * angular distance from a sample.
    radius=max(np.linalg.norm(v,axis=1).max() for _,v,_,_ in LOCAL)+abs(gap-.06)/2+.03
    n=max(1,int(np.ceil(angle/.08)));bound=2*radius*np.sin(angle/n/4)
    return [(Rotation.from_rotvec(rv*t/n).as_matrix()@start_rotation,float(bound)) for t in range(n+1)]

class EdgeSearch:
    def __init__(self,c,x,q):
        self.anchor=x[16:23].copy();self.start=x[:3].astype(float).copy();self.q=np.array(q).copy()
        self.current_rotation=Rotation.from_quat(x[3:7]).as_matrix()
        self.gap=min(.085,max(abs(float(x[7]-x[8])),c.approach_gap or .06)+c.cfg.aperture_tolerance_m+c.cfg.gap_uncertainty_m)
        goal=c.grasp_target(x);radial=goal[:2]-np.array([-.5,-.1]);radial/=np.linalg.norm(radial)
        distances=[.08,.04] if c.cfg.adaptive_height else [.128]
        self.options=[]
        for distance in distances:
            for flip in [False,True]:
                r=c.planned_rotation@np.diag([-1.,-1.,1.]) if flip else c.planned_rotation.copy()
                g=goal.copy()
                if c.cfg.edge_path:
                    r=Rotation.from_rotvec(-np.deg2rad(35)*np.r_[-radial[1],radial[0],0.]).as_matrix()@r
                    g-=np.r_[.006*radial,0.]
                above=g-r[:,2]*distance
                self.options.append({'rotation':r,'goal':g,'above':above,'offset':g-x[16:19],'distance_m':distance,'flip':flip})
        self.limit=c.cfg.ik_iterations_per_target;self.required_margin=c.cfg.joint_solution_margin_rad
        self.index=0;self.work=0;self.done=False;self.chosen=None;self.receipts=[];self.begin()
    def begin(self):
        o=self.options[self.index];self.targets=[self.start,o['above'],o['goal']];self.target=0
        self.ik=IK(self.q,self.targets[0],o['rotation'],self.limit);self.stage='ik';self.current=[];self.margins=[];self.turns=None;self.check_index=0
    def reject_or_accept(self,reason,accepted=False):
        o=self.options[self.index]
        self.receipts.append({'index':self.index,'distance_m':o['distance_m'],'flip':o['flip'],'reason':reason,'ik':self.current,'margins':self.margins,'accepted':accepted})
        if accepted:self.chosen=o;self.done=True
        else:
            self.index+=1
            if self.index==len(self.options):self.done=True
            else:self.begin()
    def advance(self,units=16):
        before=self.work
        if self.done:return True
        o=self.options[self.index]
        if self.stage=='ik':
            for _ in range(units):
                self.work+=1;self.ik.advance(1)
                if not self.ik.done:continue
                r=self.ik.receipt();self.current.append(r)
                if not r['success'] or r['limit_margin_rad']<self.required_margin:self.reject_or_accept('local_ik_not_validated');break
                self.target+=1
                if self.target==3:
                    self.stage='geometry';self.turns=turn_samples(self.current_rotation,o['rotation'],self.gap);break
                self.ik=IK(self.ik.q,self.targets[self.target],o['rotation'],self.limit)
        else:
            self.work+=1;i=self.check_index
            if i<len(self.turns):
                r,bound=self.turns[i];margin=sweep_margin(self.start,self.start,r,self.gap)-bound;kind='turn_with_arc_bound'
            else:
                j=i-len(self.turns);margin=sweep_margin(self.targets[j],self.targets[j+1],o['rotation'],self.gap);kind='straight_sweep'
            self.margins.append({'kind':kind,'margin_m':margin})
            if margin<.001:self.reject_or_accept('hand_path_not_validated')
            else:
                self.check_index+=1
                if self.check_index==len(self.turns)+2:self.reject_or_accept('validated_waypoints_and_hand_path',True)
        assert self.work-before<=units
        return self.done
