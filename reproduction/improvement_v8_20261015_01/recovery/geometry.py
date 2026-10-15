"""Fixed collision-hull support and sampled hand-path checks, not arm safety."""
from pathlib import Path
import json
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from reproduction.recovery_v5_20261012_01.clearance import PARTS,CELLS
DATA=json.loads(Path(__file__).with_name('scene_geometry.json').read_text())
CAN=np.array(DATA['can_vertices']);BOXES=[(np.array(b['center']),np.array(b['half'])) for b in DATA['boxes']]

def axes_for(vertices):
    hull=ConvexHull(vertices);edges=np.unique(np.sort(np.concatenate([hull.simplices[:,[0,1]],hull.simplices[:,[1,2]],hull.simplices[:,[0,2]]]),axis=1),axis=0)
    directions=vertices[edges[:,1]]-vertices[edges[:,0]]
    axes=np.r_[np.eye(3),hull.equations[:,:3],np.cross(directions[:,None,:],np.eye(3)[None,:,:]).reshape(-1,3)]
    norm=np.linalg.norm(axes,axis=1);axes=axes[norm>1e-8]/norm[norm>1e-8,None]
    return np.unique(np.round(axes,7),axis=0)

def separation(vertices,center,half,axes=None):
    lo=vertices.min(0);hi=vertices.max(0)
    cheap=float(max(np.max(lo-center-half),np.max(center-half-hi)))
    if cheap>.002:return cheap
    if axes is None:axes=axes_for(vertices)
    projection=(vertices-center)@axes.T;radius=np.abs(axes)@half
    return float(np.max(np.maximum(projection.min(0)-radius,-radius-projection.max(0))))

def support(x,floor):
    rotation=Rotation.from_quat(x[19:23]).as_matrix();axis=rotation[:,2]
    if .35<abs(axis[2])<.90:return None,'tilted_unsettled_family'
    world=CAN@rotation.T+x[16:19];bottom=float(world[:,2].min());center=(world.min(0)+world.max(0))/2
    surfaces=[]
    for b in DATA['boxes']:
        c=np.array(b['center']);h=np.array(b['half']);top=c[2]+h[2]
        if abs(bottom-top)<.003 and np.all(abs(center[:2]-c[:2])<=h[:2]+.001):surfaces.append((b,top))
    if not surfaces:return None,'no_horizontal_support'
    # Allow only solver-scale penetration, not overlapping a wall footprint.
    for c,h in BOXES:
        if separation(world,c,h)<-.0015:return None,'object_intersects_fixed_geometry'
    chosen=min(surfaces,key=lambda s:abs(bottom-s[1]));b,top=chosen
    kind='floor' if top<floor+.05 else 'wall_top'
    if kind=='wall_top' and abs(axis[2])<.90:return None,'sideways_perch_unsupported'
    return {'kind':kind,'height':float(top),'axis':axis,'body':b['body']},'mesh_supported_'+kind

def hand_vertices(rotation,gap):
    out=[]
    for name,original,edges in PARTS:
        v=original.copy()
        if 'finger1' in name:v[:,1]+=(gap-.06)/2
        if 'finger2' in name:v[:,1]-=(gap-.06)/2
        out.append(v@rotation.T)
    return out

def path_margin(start,end,rotation,gap):
    # Convex sweep of each hand/finger part under fixed rotation along a segment.
    # Aperture extremes are checked; full arm and object interaction are excluded.
    worst=float('inf')
    for aperture in [0.,gap]:
        for part in hand_vertices(rotation,aperture):
            sweep=np.r_[part+start,part+end]
            for c,h in BOXES:
                worst=min(worst,separation(sweep,c,h))
                if worst<.001:return worst
    return worst

def plan(controller,x):
    domain,reason=support(x,controller.floor)
    if domain is None:return None,reason,0
    axis=domain['axis'];side=abs(axis[2])<.35;current=Rotation.from_quat(x[3:7]).as_matrix()
    down=np.diag([1.,-1.,-1.]);yaw0=np.arctan2(axis[1],axis[0]) if side else 0.
    gap=controller.cfg.side_gap_m if side else controller.cfg.corner_gap_m
    opts=[]
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
                        opts.append((cost,rot,offset))
    for _,rot,offset in sorted(opts,key=lambda s:s[0]):
        goal=x[16:19]+offset;above=np.r_[goal[:2],max(controller.floor+.20,x[18]+.14)]
        key=tuple(np.round(np.r_[rot.ravel(),offset,gap],4).tolist())
        if any(np.linalg.norm(x[16:19]-p['position'])<.008 and p['key']==key for p in controller.failed_plans):continue
        margin=path_margin(above,goal,rot,gap+controller.cfg.aperture_tolerance_m+controller.cfg.gap_uncertainty_m)
        if margin>=.001:return {'rotation':rot,'offset':offset,'gap':gap,'key':key,'margin':margin,'domain':domain,'kind':'sideways' if side else 'upright'},reason,len(opts)
    return None,'mesh_supported_no_hand_path',len(opts)
