"""Fixed Panda FK/Jacobian and iteration-bounded damped IK. No simulator calls."""
from pathlib import Path
import json
import numpy as np
from scipy.spatial.transform import Rotation
DATA=json.loads(Path(__file__).with_name('arm_chain.json').read_text())
LIMITS=np.array(DATA['limits'])
CHAIN=[(np.array(b['position']),Rotation.from_quat(np.roll(b['quaternion_wxyz'],-1)).as_matrix(),
        b.get('joint_index'),np.array(b.get('axis',[0,0,1])),np.array(b.get('anchor',[0,0,0]))) for b in DATA['chain']]
SITE_P=np.array(DATA['site_position']);SITE_R=Rotation.from_quat(np.roll(DATA['site_quaternion_wxyz'],-1)).as_matrix()

def fk(q,jacobian=False):
    p=np.zeros(3);R=np.eye(3);origins=[];axes=[]
    for offset,rot,i,axis,anchor in CHAIN:
        p=p+R@offset;R=R@rot
        if i is not None:
            origins.append(p+R@anchor);axes.append(R@axis)
            change=Rotation.from_rotvec(axis*q[i]).as_matrix()
            p=p+R@(anchor-change@anchor);R=R@change
    p=p+R@SITE_P;R=R@SITE_R
    if not jacobian:return p,R
    axes=np.asarray(axes);J=np.r_[np.cross(axes,p-np.asarray(origins)).T,axes.T]
    return p,R,J

class IK:
    def __init__(self,q,target,rotation,max_iterations=48):
        self.q=np.array(q,float).copy();self.target=np.array(target);self.rotation=np.array(rotation)
        self.iterations=0;self.max_iterations=max_iterations;self.done=False;self.success=False
        self.position_error=None;self.angle_error=None
    def advance(self,n=4):
        for _ in range(n):
            if self.done:break
            p,R,J=fk(self.q,True);dp=self.target-p;dr=Rotation.from_matrix(self.rotation@R.T).as_rotvec()
            self.position_error=float(np.linalg.norm(dp));self.angle_error=float(np.linalg.norm(dr))
            if self.position_error<.004 and self.angle_error<.04:self.done=True;self.success=True;break
            scale=np.array([1,1,1,.25,.25,.25]);A=scale[:,None]*J;e=scale*np.r_[dp,dr]
            dq=A.T@np.linalg.solve(A@A.T+.0004*np.eye(6),e)
            # Restrict each iteration and keep a fixed 0.02 rad numerical margin.
            dq*=min(1.,.15/max(np.max(np.abs(dq)),1e-12))
            self.q=np.clip(self.q+dq,LIMITS[:,0]+.02,LIMITS[:,1]-.02)
            self.iterations+=1
            if self.iterations>=self.max_iterations:self.done=True
        return self.done
    def receipt(self):
        p,R=fk(self.q)
        return {'success':self.success,'iterations':self.iterations,'q':self.q.tolist(),
                'position_error_m':float(np.linalg.norm(self.target-p)),
                'angle_error_rad':float(np.linalg.norm(Rotation.from_matrix(self.rotation@R.T).as_rotvec())),
                'limit_margin_rad':float(np.min(np.minimum(self.q-LIMITS[:,0],LIMITS[:,1]-self.q)))}
