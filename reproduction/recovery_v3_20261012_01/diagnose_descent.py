"""Explain residual DEV descent failures by exact physical replay."""
import sys,json
import numpy as np,h5py
from scipy.spatial.transform import Rotation
from setup_study import ROOT,RUN,write
sys.path.insert(0,str(ROOT))
from common import DATA,make_env,restore_demo,pack_obs
from recovery_controller import RecoveryController,Config
def main():
    reports=[];env=make_env(False)
    try:
        with h5py.File(DATA) as f:
            for jobid,name in [('full_s23_clean','demo_188'),('full_s17_clean','demo_97'),('full_s23_clean','demo_128')]:
                path=RUN/'dev_b'/jobid;job=json.loads((path/'result.json').read_text())['job'];obs=restore_demo(env,f['data'][name]);ctrl=RecoveryController([.1975,.4025,.8],.8,pack_obs(obs),config=Config(**job['config']));prev=np.zeros(7,np.float32);samples=[]
                for line in (path/'trace.jsonl').open():
                    r=json.loads(line)
                    if r['demo']!=name:continue
                    x=pack_obs(obs);a,d=ctrl.choose(x,np.array(r['original_proposal'],np.float32),prev);np.testing.assert_array_equal(a,r['submitted_action'])
                    if d['mode']=='DESCEND' and ctrl.age in [20,40,60,70]:
                        contacts=[]
                        for c in env.sim.data.contact[:env.sim.data.ncon]:
                            bodies=[str(env.sim.model.body_id2name(int(env.sim.model.geom_bodyid[g]))) for g in [c.geom1,c.geom2]]
                            if any('finger' in b or 'robot' in b or 'gripper' in b for b in bodies):contacts.append({'bodies':bodies,'geoms':[int(c.geom1),int(c.geom2)],'pos':c.pos.tolist(),'depth':float(c.dist)})
                        q=env.sim.data.qpos[env.robots[0]._ref_joint_pos_indexes].copy();limits=env.sim.model.jnt_range[env.robots[0]._ref_joint_indexes]
                        samples.append({'step':r['step'],'age':ctrl.age,'eef':x[:3].tolist(),'object':x[16:19].tolist(),'goal':ctrl.grasp_target(x).tolist(),'yaw':float(Rotation.from_matrix(ctrl.goal_rotation).as_euler('xyz')[2]),'kind':ctrl.grasp_kind,'gap':abs(float(x[7]-x[8])),'target_gap':ctrl.approach_gap,'offset':ctrl.grasp_offset.tolist(),'joint_margins':np.minimum(q-limits[:,0],limits[:,1]-q).tolist(),'contacts':contacts})
                    prev=np.array(r['executed_action'],np.float32);obs,*_=env.step(prev);np.testing.assert_array_equal(pack_obs(obs),r['state_after'])
                reports.append({'job':jobid,'demo':name,'samples':samples})
    finally:env.close()
    write(RUN/'descent_diagnosis_dev_b.json',reports)
    for r in reports:print(json.dumps({**r,'samples':r['samples'][-2:]}))
if __name__=='__main__':main()
