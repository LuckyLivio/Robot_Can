from probe import *
if __name__=='__main__':
    c,x,q=snapshot();base_goal=c.grasp_target(x);radial=base_goal[:2]-np.array([-.5,-.1]);radial/=np.linalg.norm(radial);rows=[]
    for degree in [30,35,40]:
        r=Rotation.from_rotvec(-np.deg2rad(degree)*np.r_[-radial[1],radial[0],0.]).as_matrix()@c.planned_rotation
        for shift in [0.,.006,.01]:
            goal=base_goal-np.r_[shift*radial,0.];above=goal-r[:,2]*.08
            a=solve(q,above,r);b=solve(np.array(a['q']),goal,r);ok=a['success'] and b['success']
            margin=general_path_margin(above,goal,r,.0655) if ok else None
            rows.append({'degree':degree,'shift_m':shift,'above':a,'grasp':b,'margin_m':margin,'feasible':bool(ok and margin>=.001)})
    with (RUN/'analysis/local_probe.json').open('x') as f:json.dump(rows,f,indent=2)
    for r in rows:print(r['degree'],r['shift_m'],r['feasible'],round(r['grasp']['position_error_m'],4),r['margin_m'])
