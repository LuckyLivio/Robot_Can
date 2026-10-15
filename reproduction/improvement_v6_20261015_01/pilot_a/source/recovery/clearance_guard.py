"""Fixed hand/finger geometry checks only; no simulator or reward input."""
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.recovery_v5_20261012_01.clearance import clearance_margin,side_cell


def vertical_margin(goal,rotation,cell,floor,gap,step=.005):
    """Sample vertical approach / short trial lift, including both gap extremes.

    Arm, object contacts and continuous swept-volume safety are not represented.
    """
    goal=np.asarray(goal,float)
    heights=np.linspace(goal[2],max(floor+.20,goal[2]+.14),
                        int(np.ceil(max(floor+.20-goal[2],.14)/step))+1)
    worst=float('inf')
    for z in heights:
        p=goal.copy();p[2]=z
        for aperture in [0.,gap]:
            worst=min(worst,float(clearance_margin(p,rotation,cell,floor,aperture)))
    return worst


def key(rotation,offset,side_offset,gap):
    return tuple(np.round(np.r_[np.asarray(rotation).ravel(),offset,side_offset,gap],4).tolist())


def candidates(c,x):
    """v5 candidate family, with original selected candidate first."""
    cell=side_cell(x[16:19],c.grasp_axis,c.floor) if c.grasp_kind=='sideways' else c.resting_cell(x)
    narrow=c.approach_gap is not None or bool(c.side_plan and c.side_plan.get('eligible'))
    if c.grasp_kind=='upright' and cell is not None:
        a,b,d,e=cell
        narrow=narrow or max(min(x[16]-a,b-x[16]),min(x[17]-d,e-x[17]))<c.cfg.corner_distance_m
    if cell is None or not narrow:return [],False
    gap=c.approach_gap or (c.cfg.side_gap_m if c.grasp_kind=='sideways' else c.cfg.corner_gap_m)
    opts=[{'rotation':c.planned_rotation.copy(),'grasp_offset':c.grasp_offset.copy(),
           'side_offset':c.side_offset.copy(),'gap':gap,'cell':cell,'cost':-1.}]
    current=Rotation.from_quat(x[3:7]).as_matrix();down=np.diag([1.,-1.,-1.])
    if c.grasp_kind=='sideways':
        yaw=float(np.arctan2(c.grasp_axis[1],c.grasp_axis[0]))
        rots=[Rotation.from_rotvec([0,0,yaw+k*np.pi]).as_matrix()@down for k in [0,1]]
        nominal=min(rots,key=lambda r:np.linalg.norm(Rotation.from_matrix(r@current.T).as_rotvec()))
        for h in [c.cfg.sideways_grasp_z_m,.014,.020]:
            for shift in [0.,-.015,.015]:
                offset=shift*c.grasp_axis+np.array([0.,0.,h-c.cfg.sideways_grasp_z_m])
                for away in [np.array([1.,0.]),np.array([-1.,0.]),np.array([0.,1.]),np.array([0.,-1.])]:
                    for degree in [0.,10.,20.,30.,35.]:
                        r=Rotation.from_rotvec(np.deg2rad(degree)*np.r_[-away[1],away[0],0.]).as_matrix()@nominal
                        opts.append({'rotation':r,'grasp_offset':np.zeros(2),'side_offset':offset,
                                     'gap':c.cfg.side_gap_m,'cell':cell,
                                     'cost':.03*degree/35+2*(h-c.cfg.sideways_grasp_z_m)+.5*abs(shift)})
    else:
        a,b,d,e=cell;away=np.array([1. if x[16]<(a+b)/2 else -1.,1. if x[17]<(d+e)/2 else -1.])
        offset=c.cfg.corner_offset_m*away
        for yaw in np.arange(-np.pi/4,3*np.pi/4+1e-6,np.pi/12):
            closure=np.array([-np.sin(yaw),np.cos(yaw)])
            if .025+abs(float(offset@closure))>c.cfg.corner_gap_m/2-.001:continue
            rots=[Rotation.from_rotvec([0,0,yaw+k*np.pi]).as_matrix()@down for k in [0,1]]
            r=min(rots,key=lambda v:np.linalg.norm(Rotation.from_matrix(v@current.T).as_rotvec()))
            opts.append({'rotation':r,'grasp_offset':offset.copy(),'side_offset':np.zeros(3),
                         'gap':c.cfg.corner_gap_m,'cell':cell,'cost':abs(float(yaw))*.001})
    result=[];seen=set()
    for v in sorted(opts,key=lambda v:v['cost']):
        k=key(v['rotation'],v['grasp_offset'],v['side_offset'],v['gap'])
        if k in seen:continue
        seen.add(k);v['key']=k;result.append(v)
    return result,True


def goal_for(c,x,opt):
    p=x[16:19].astype(float).copy()
    if c.grasp_kind=='sideways':
        p-=.01*c.grasp_axis;p[2]+=c.cfg.sideways_grasp_z_m;p[2]=max(p[2],c.floor+.035)
    else:p[2]+=c.cfg.grasp_offset_z_m
    p[:2]+=opt['grasp_offset'];p+=opt['side_offset']
    return p
