"""Observation/asset-only support eligibility; no simulator or contact oracle."""
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from reproduction.improvement_v8_20261015_01.recovery.geometry import CAN, DATA, BOXES, separation, support as old_support

HULL = ConvexHull(CAN)

def clip(poly, normal, offset):
    out=[]
    if not len(poly):return np.empty((0,2))
    previous=poly[-1];pv=float(previous@normal+offset)
    for current in poly:
        cv=float(current@normal+offset)
        if (pv<=0)!=(cv<=0):out.append(previous+(current-previous)*(pv/(pv-cv)))
        if cv<=0:out.append(current)
        previous=current;pv=cv
    return np.asarray(out).reshape(-1,2)

def support(x,floor):
    old,reason=old_support(x,floor)
    if old is not None:return old,reason
    rotation=Rotation.from_quat(x[19:23]).as_matrix();axis=rotation[:,2]
    if abs(axis[2])>=.90:return None,reason
    world=CAN@rotation.T+x[16:19]
    if any(separation(world,c,h)<-.0015 for c,h in BOXES):return None,'support13_object_penetration'
    normals=HULL.equations[:,:3]@rotation.T
    offsets=HULL.equations[:,3]-normals@x[16:19]
    patches=[]
    # Intersect the can hull with a plane 1.5mm outside each box face, then
    # clip to the actual finite face. This detects long edges crossing a
    # narrow wall even when neither endpoint/mesh vertex lies on its top.
    for bi,b in enumerate(DATA['boxes']):
        c=np.array(b['center']);h=np.array(b['half'])
        if np.any(world.max(0)<c-h-.003) or np.any(world.min(0)>c+h+.003):continue
        for k,sgn in [(2,1),(0,-1),(0,1),(1,-1),(1,1)]:
            remaining=[i for i in range(3) if i!=k]
            plane=c[k]+sgn*(h[k]+.0015)
            lo=c[remaining]-h[remaining];hi=c[remaining]+h[remaining]
            poly=np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]])
            for n,d in zip(normals,offsets):
                poly=clip(poly,n[remaining],d+n[k]*plane)
                if not len(poly):break
            if len(poly)<3:continue
            area=abs(float(np.sum(poly[:,0]*np.roll(poly[:,1],-1)-poly[:,1]*np.roll(poly[:,0],-1))))/2
            if area<1e-7:continue
            p=np.zeros(3);p[k]=c[k]+sgn*h[k];p[remaining]=poly.mean(0)
            patches.append({'box':bi,'body':b['body'],'axis':k,'sign':sgn,'point':p.tolist(),'area_m2':area})
    upward=[p for p in patches if p['axis']==2]
    if not upward:return None,'support13_no_upward_patch'
    side=abs(axis[2])<.35
    lateral=[p for p in patches if p['axis']!=2]
    if not side and not lateral:return None,'support13_lean_without_side_patch'
    if side and max(p['point'][2] for p in upward)<floor+.05:return None,reason
    return {'kind':'side_perch' if side else 'leaning','height':max(p['point'][2] for p in upward),
            'axis':axis,'body':upward[0]['body'],'patches':patches},'support13_supported'
