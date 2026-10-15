"""Conservative fixed-pose can/hand separation certificates, not contact simulation."""
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from reproduction.recovery_v5_20261012_01.clearance import PARTS
from reproduction.improvement_v8_20261015_01.recovery.geometry import CAN

CAN_NORMALS=ConvexHull(CAN).equations[:,:3]
HAND=[(name,v,ConvexHull(v).equations[:,:3]) for name,v,_ in PARTS]

def object_margin(start,end,rotation,gap,x,details=False):
    """Positive returned margin is a separating-plane certificate for the sweep.

    Use face normals of both shapes and hand-frame axes. Omitting cross-edge
    axes can reject a truly separated pair, but cannot certify an intersection.
    Vertices are the actual convex collision assets. No contact is permitted
    during open approach, including pads. Closing is handled after arrival.
    """
    can_rot=Rotation.from_quat(x[19:23]).as_matrix();can=CAN@can_rot.T+x[16:19]
    results=[]
    for name,original,normals in HAND:
        copies=[]
        for aperture in np.atleast_1d(gap):
            vertices=original.copy()
            if 'finger1' in name:vertices[:,1]+=(aperture-.06)/2
            if 'finger2' in name:vertices[:,1]-=(aperture-.06)/2
            copies.append(vertices)
        vertices=np.concatenate(copies)
        axes=np.r_[rotation.T,normals@rotation.T,CAN_NORMALS@can_rot.T]
        lengths=np.linalg.norm(axes,axis=1);axes=axes[lengths>1e-9]/lengths[lengths>1e-9,None]
        a=(vertices@rotation.T)@axes.T;lo=a.min(0)+np.minimum(start@axes.T,end@axes.T);hi=a.max(0)+np.maximum(start@axes.T,end@axes.T)
        b=can@axes.T
        margin=float(np.max(np.maximum(lo-b.max(0),b.min(0)-hi)))
        results.append({'part':name,'margin_m':margin})
    return results if details else min(p['margin_m'] for p in results)

def enclosure(goal,rotation,gap,x):
    can=(CAN@Rotation.from_quat(x[19:23]).as_matrix().T+x[16:19]-goal)@rotation
    # Inner pad faces sit 0.5 mm inside each ideal half-gap.
    clearance=float(gap/2-.0005-max(abs(can[:,1].min()),abs(can[:,1].max())))
    return {'closure_extent_m':float(np.ptp(can[:,1])),'closure_center_m':float((can[:,1].max()+can[:,1].min())/2),'inner_clearance_m':clearance}
