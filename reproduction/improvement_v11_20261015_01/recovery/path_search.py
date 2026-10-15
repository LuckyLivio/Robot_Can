"""Fixed wall-top candidate families. No simulator or counterfactual rollouts."""
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v9_20261015_01.recovery.geometry import LOCAL,CENTERS,HALVES
from reproduction.improvement_v9_20261015_01.recovery.kinematics import IK
from .object_clearance import object_margin,enclosure

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
        self.can_guard=c.cfg.can_guard;self.axis_alignment=c.cfg.axis_alignment;self.x=np.array(x).copy()
        self.extra=c.cfg.aperture_tolerance_m+c.cfg.gap_uncertainty_m
        self.nominal_gap=c.approach_gap or .06;self.observed_gap=abs(float(x[7]-x[8]))
        self.object_margin_required=.003;self.maximum_gap=.072
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
        if self.axis_alignment:
            self.options=[];yaw=np.arctan2(radial[1],radial[0])
            for height in [.012,.020,.026]:
                for distance in distances:
                    for flip in [False,True]:
                        down=Rotation.from_euler('z',yaw+(np.pi if flip else 0)).as_matrix()@np.diag([1.,-1.,-1.])
                        r=Rotation.from_rotvec(-np.deg2rad(35)*np.r_[-radial[1],radial[0],0.]).as_matrix()@down
                        g=x[16:19].astype(float)+np.r_[-.006*radial,height];above=g-r[:,2]*distance
                        self.options.append({'rotation':r,'goal':g,'above':above,'offset':g-x[16:19],'distance_m':distance,'flip':flip,'height_m':height})
        self.limit=c.cfg.ik_iterations_per_target;self.required_margin=c.cfg.joint_solution_margin_rad
        self.index=0;self.work=0;self.done=False;self.chosen=None;self.receipts=[];self.begin()
    def begin(self):
        o=self.options[self.index];self.targets=[self.start,o['above'],o['goal']];self.target=0
        self.ik=IK(self.q,self.targets[0],o['rotation'],self.limit);self.stage='prefilter' if self.can_guard else 'ik';self.current=[];self.margins=[];self.turns=None;self.check_index=0
        self.object_index=0
    def reject_or_accept(self,reason,accepted=False):
        o=self.options[self.index]
        if accepted and self.can_guard and self.stage!='object':
            self.stage='object';self.object_index=0;return
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
        if self.stage=='prefilter':
            self.work+=1;e=enclosure(o['goal'],o['rotation'],self.nominal_gap,self.x)
            maximum=e['closure_extent_m']/2+abs(e['closure_center_m'])
            need=2*(maximum+.0005+self.object_margin_required)+self.extra
            target=max(self.nominal_gap,float(np.ceil(need/.002)*.002))
            if target>self.maximum_gap:
                self.margins.append({'kind':'required_aperture','target_gap_m':target,'maximum_gap_m':self.maximum_gap})
                self.reject_or_accept('can_does_not_fit_bounded_aperture');return self.done
            o['target_gap']=target;self.gap=min(.085,max(self.observed_gap,target)+self.extra)
            self.object_gap=[target-self.extra,target+self.extra]
            margin=object_margin(o['goal'],o['goal'],o['rotation'],self.object_gap,self.x)
            self.margins.append({'kind':'terminal_open_hand_can','margin_m':margin,'target_gap_m':target})
            if margin<self.object_margin_required:self.reject_or_accept('terminal_can_clearance_not_validated')
            else:self.stage='ik'
            return self.done
        if self.stage=='object':
            nturn=len(self.turns);count=min(4,nturn-self.object_index) if self.object_index<nturn else 1
            for _ in range(count):
                self.work+=1;i=self.object_index
                if i<nturn:
                    rot,bound=self.turns[i];gaps=[min(self.observed_gap,self.object_gap[0])-.001,max(self.observed_gap,self.object_gap[1])+.001]
                    margin=object_margin(self.start,self.start,rot,gaps,self.x)-bound;kind='turn_can_arc_bound'
                else:
                    j=i-nturn;gaps=self.object_gap
                    margin=object_margin(self.targets[j],self.targets[j+1],o['rotation'],gaps,self.x);kind='open_hand_can_sweep'
                self.margins.append({'kind':kind,'margin_m':margin})
                if margin<self.object_margin_required:self.reject_or_accept('can_approach_not_validated');break
                self.object_index+=1
                if self.object_index==nturn+2:self.reject_or_accept('validated_waypoints_boxes_and_can',True);break
            assert self.work-before<=units;return self.done
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
            count=min(4,len(self.turns)-self.check_index) if self.check_index<len(self.turns) else 1
            for _ in range(count):
                self.work+=1;i=self.check_index
                if i<len(self.turns):
                    r,bound=self.turns[i];margin=sweep_margin(self.start,self.start,r,self.gap)-bound;kind='turn_with_arc_bound'
                else:
                    j=i-len(self.turns);margin=sweep_margin(self.targets[j],self.targets[j+1],o['rotation'],self.gap);kind='straight_sweep'
                self.margins.append({'kind':kind,'margin_m':margin})
                if margin<.001:self.reject_or_accept('hand_path_not_validated');break
                self.check_index+=1
                if self.check_index==len(self.turns)+2:self.reject_or_accept('validated_waypoints_and_hand_path',True);break
        assert self.work-before<=units
        return self.done
