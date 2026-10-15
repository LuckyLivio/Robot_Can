"""Training initialization fixtures, fixed before v3 outcomes are observed."""
import json,sys
import numpy as np,h5py
from scipy.spatial.transform import Rotation
from setup_study import ROOT,RUN,write
sys.path.insert(0,str(ROOT))
from common import DATA,make_env,restore_demo,pack_obs
def main():
    names=json.loads((ROOT/'data/splits.json').read_text())['train'][:8];jobs=[]
    specs=[('demo_6100000',[.22,-.38,.88],0,0,'far_source'),('demo_6100001',[.24,-.43,.88],0,0,'far_source_corner'),
           ('demo_6100002',[.151,.077,.88],0,0,'destination_corner'),('demo_6100003',[.153,.085,.88],0,0,'destination_corner_wider')]
    env=make_env(False);descriptions=[]
    try:
        with h5py.File(DATA) as source,h5py.File(RUN/'pilot_starts.hdf5','x') as target:
            group=target.create_group('data');group.attrs['env_args']=source['data'].attrs['env_args']
            for name,pos,pitch,yaw,label in specs:
                restore_demo(env,source['data'][names[0]])
                obj=next(o for o in env.objects if o.name.lower()=='can');joint=obj.joints[0]
                quat=(Rotation.from_euler('z',yaw,degrees=True)*Rotation.from_euler('y',pitch,degrees=True)).as_quat()
                env.sim.data.set_joint_qpos(joint,np.r_[pos,quat[3],quat[:3]]);env.sim.data.set_joint_qvel(joint,np.zeros(6));env.sim.forward()
                for _ in range(40):obs,*_=env.step(np.array([0,0,0,0,0,0,-1],np.float32))
                state=env.sim.get_state().flatten().copy();state[0]=0.
                d=group.create_group(name);d.attrs['model_file']=env.sim.model.get_xml();d.create_dataset('states',data=state[None]);d.attrs['diagnostic']=label
                descriptions.append({'name':name,'label':label,'observation':pack_obs(obs).tolist()})
    finally:env.close()
    for version in ['v2','v3']:
        base={'method':'bc_k2','seed':None,'noise':0.,'enabled':True,'version':version}
        jobs.extend([{**base,'id':version+'_train','demos':names},
                     {**base,'id':version+'_loss','demos':names[:2],'fault':'open_after_verified_lift'},
                     {**base,'id':version+'_held_stall','demos':names[:1],'fault_policy':'stationary_after_lift'},
                     {**base,'id':version+'_old_geometry','dataset':'reproduction/recovery_v2_20261012_01/pilot_starts_fixed.hdf5','demos':[f'demo_{4000000+i}' for i in range(4)],'fault_policy':'stationary_open','force_recovery_at':80},
                     {**base,'id':version+'_new_geometry','dataset':(RUN/'pilot_starts.hdf5').relative_to(ROOT).as_posix(),'demos':[s[0] for s in specs],'fault_policy':'stationary_open','force_recovery_at':80},
                     {**base,'id':version+'_full_noise','method':'full','seed':17,'noise':.05,'demos':names[:2]}])
    write(RUN/'pilot_jobs.json',jobs);write(RUN/'pilot_state_description.json',descriptions)
    print(json.dumps({'episodes':sum(len(j['demos']) for j in jobs),'fixtures':descriptions}))
if __name__=='__main__':main()
