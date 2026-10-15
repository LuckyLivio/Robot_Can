"""Predetermined training-only diagnostic states; no policy/outcome selection."""
import json,sys
import numpy as np,h5py
from scipy.spatial.transform import Rotation
from setup_study import ROOT,RUN,write
sys.path.insert(0,str(ROOT))
from common import DATA,make_env,restore_demo,pack_obs

def main():
    names=json.loads((ROOT/'data/splits.json').read_text())['train'][:8];jobs=[]
    for version in ['v1','v2']:
        jobs.append({'id':f'{version}_train','method':'bc_k2','seed':None,'noise':0.,'enabled':True,'version':version,'demos':names})
        jobs.append({'id':f'{version}_loss','method':'bc_k2','seed':None,'noise':0.,'enabled':True,'version':version,'demos':names[:2],'fault':'open_after_verified_lift'})
    jobs.append({'id':'v2_held_stall','method':'bc_k2','seed':None,'noise':0.,'enabled':True,'version':'v2','demos':names[:1],'fault_policy':'stationary_after_lift'})
    specs=[('demo_4000000',[.06,-.20,.89],90,0,'sideways_source_x'),
           ('demo_4000001',[.06,-.20,.89],90,90,'sideways_source_y'),
           ('demo_4000002',[.18,.085,.88],0,0,'upright_destination_front_wall'),
           ('demo_4000003',[.055,.40,.88],0,0,'upright_destination_divider')]
    env=make_env(False);descriptions=[]
    try:
        with h5py.File(DATA) as source,h5py.File(RUN/'pilot_starts_fixed.hdf5','x') as target:
            group=target.create_group('data');group.attrs['env_args']=source['data'].attrs['env_args']
            for name,position,pitch,yaw,label in specs:
                restore_demo(env,source['data'][names[0]])
                obj=next(o for o in env.objects if o.name.lower()=='can');joint=obj.joints[0]
                quat=(Rotation.from_euler('z',yaw,degrees=True)*Rotation.from_euler('y',pitch,degrees=True)).as_quat()
                # Explicit stress INITIALIZATION only; no teleporting during a rollout.
                env.sim.data.set_joint_qpos(joint,np.r_[position,quat[3],quat[:3]])
                env.sim.data.set_joint_qvel(joint,np.zeros(6));env.sim.forward()
                for _ in range(40):obs,*_=env.step(np.array([0,0,0,0,0,0,-1],np.float32))
                state=env.sim.get_state().flatten().copy();state[0]=0.
                d=group.create_group(name);d.attrs['model_file']=env.sim.model.get_xml();d.create_dataset('states',data=state[None]);d.attrs['diagnostic']=label
                descriptions.append({'name':name,'label':label,'position':pack_obs(obs)[16:19].tolist(),'quaternion':pack_obs(obs)[19:23].tolist()})
    finally:env.close()
    for version in ['v1','v2']:
        jobs.append({'id':f'{version}_geometry','method':'bc_k2','seed':None,'noise':0.,'enabled':True,'version':version,
                     'dataset':(RUN/'pilot_starts_fixed.hdf5').relative_to(ROOT).as_posix(),'demos':[s[0] for s in specs],'fault_policy':'stationary_open'})
    write(RUN/'pilot_jobs_fixed.json',jobs);write(RUN/'pilot_state_description_fixed.json',descriptions);print(json.dumps(descriptions),flush=True)

if __name__=='__main__':main()
