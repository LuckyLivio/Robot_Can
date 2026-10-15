"""Diagnose a small fixed set of wall-top inclined approaches on saved input."""
from probe import *
if __name__=='__main__':
    c,x,q=snapshot();goal=c.grasp_target(x);radial=goal[:2]-np.array([-.5,-.1]);radial/=np.linalg.norm(radial);rows=[]
    # Tilt hand toward/away from the fixed robot base; test paired yaw symmetry.
    for sign in [1,-1]:
        for degree in [10,20,30]:
            for flip in [0,1]:
                base=c.planned_rotation@np.diag([-1.,-1.,1.]) if flip else c.planned_rotation
                r=Rotation.from_rotvec(sign*np.deg2rad(degree)*np.r_[-radial[1],radial[0],0.]).as_matrix()@base
                for distance in [.04,.08,.12]:
                    above=goal-r[:,2]*distance;a=solve(q,above,r);b=solve(np.array(a['q']),goal,r)
                    ok=a['success'] and b['success'] and min(a['limit_margin_rad'],b['limit_margin_rad'])>=.04
                    margin=general_path_margin(above,goal,r,.0655) if ok else None
                    rows.append({'sign':sign,'degree':degree,'flip':flip,'distance_m':distance,'above':a,'grasp':b,'hand_margin_m':margin,'feasible':bool(ok and margin>=.001)})
    with (RUN/'analysis/inclined_probe.json').open('x') as f:json.dump(rows,f,indent=2)
    for r in rows:
        if r['feasible']:print({k:v for k,v in r.items() if k not in ['above','grasp']})
    print('feasible',sum(r['feasible'] for r in rows),'of',len(rows))
