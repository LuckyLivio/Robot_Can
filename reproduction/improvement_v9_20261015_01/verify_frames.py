"""Independent FK cross-check against MuJoCo site position and observed eef body."""
from pathlib import Path
import json,sys
import h5py,numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from common import DATA,make_env,restore_demo
from recovery.kinematics import fk,LIMITS
def main():
    env=make_env(False);rng=np.random.default_rng(91016);checks=[]
    try:
        for demo in ['demo_97','demo_133','demo_188']:
            with h5py.File(DATA) as f:restore_demo(env,f['data'][demo])
            m=env.sim.model;d=env.sim.data;robot=env.robots[0]
            site=robot.eef_site_id['right'];body=m.body_name2id(robot.robot_model.eef_name['right'])
            adr=m.jnt_qposadr[[m.joint_name2id('robot0_joint'+str(i)) for i in range(1,8)]]
            for i in range(20):
                q=LIMITS[:,0]+.1+rng.random(7)*(LIMITS[:,1]-LIMITS[:,0]-.2)
                d.qpos[adr]=q;env.sim.forward();p,R=fk(q)
                position=float(np.linalg.norm(p-d.site_xpos[site]));angle=float(np.linalg.norm(Rotation.from_matrix(R@d.body_xmat[body].reshape(3,3).T).as_rotvec()))
                assert position<1e-10 and angle<1e-6,(position,angle)
                checks.append({'demo':demo,'pose':i,'position_error_m':position,'body_angle_error_rad':angle})
    finally:env.close()
    receipt={'passed':True,'static_fk_cases':len(checks),'max_position_error_m':max(c['position_error_m'] for c in checks),
             'max_body_angle_error_rad':max(c['body_angle_error_rad'] for c in checks),'samples':checks,
             'scope':'60 static forward-kinematics checks across three restored models. Site translation and eef-body rotation intentionally match pack_obs conventions. No task rollouts or new evaluation starts.'}
    with (RUN/'analysis/frame_validation.json').open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps({k:v for k,v in receipt.items() if k!='samples'}))
if __name__=='__main__':main()
