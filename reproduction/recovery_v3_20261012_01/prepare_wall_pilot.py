"""Additional training-initialized sideways wall fixtures after dev diagnostics."""
import json,sys
import numpy as np,h5py
from scipy.spatial.transform import Rotation
from setup_study import ROOT,RUN,write
sys.path.insert(0,str(ROOT))
from common import DATA,make_env,restore_demo,pack_obs
def main():
    specs=[('demo_6200000',[.02,.38,.89],90,0),('demo_6200001',[.185,.115,.89],90,0),('demo_6200002',[.145,.14,.89],90,90)]
    env=make_env(False);description=[]
    try:
        with h5py.File(DATA) as source,h5py.File(RUN/'wall_pilot_starts.hdf5','x') as target:
            group=target.create_group('data');group.attrs['env_args']=source['data'].attrs['env_args']
            for name,pos,pitch,yaw in specs:
                restore_demo(env,source['data']['demo_54']);joint=next(o for o in env.objects if o.name.lower()=='can').joints[0]
                quat=(Rotation.from_euler('z',yaw,degrees=True)*Rotation.from_euler('y',pitch,degrees=True)).as_quat()
                env.sim.data.set_joint_qpos(joint,np.r_[pos,quat[3],quat[:3]]);env.sim.data.set_joint_qvel(joint,np.zeros(6));env.sim.forward()
                for _ in range(40):obs,*_=env.step(np.array([0,0,0,0,0,0,-1],np.float32))
                state=env.sim.get_state().flatten().copy();state[0]=0.;d=group.create_group(name);d.attrs['model_file']=env.sim.model.get_xml();d.create_dataset('states',data=state[None]);description.append({'demo':name,'observation':pack_obs(obs).tolist()})
    finally:env.close()
    jobs=json.loads((RUN/'pilot_jobs_c.json').read_text())
    for version in ['v2','v3']:
        jobs.append({'id':version+'_side_wall','version':version,'method':'bc_k2','seed':None,'noise':0.,'enabled':True,'steps':400,
            'dataset':(RUN/'wall_pilot_starts.hdf5').relative_to(ROOT).as_posix(),'demos':[s[0] for s in specs],'fault_policy':'stationary_open','force_recovery_at':80})
    write(RUN/'pilot_jobs_e.json',jobs);write(RUN/'wall_pilot_description.json',description)
if __name__=='__main__':main()
