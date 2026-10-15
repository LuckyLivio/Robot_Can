"""Replay existing development failures; privileged telemetry is diagnostic only."""
import sys,json
import numpy as np,h5py
from scipy.spatial.transform import Rotation
from setup_study import ROOT,RUN,write
sys.path.insert(0,str(ROOT))
from common import DATA,make_env,restore_demo,pack_obs
from reproduction.recovery_v2_20261012_01.recovery_controller import RecoveryController

def main():
    old=ROOT/'reproduction/recovery_v2_20261012_01/dev_a';env=make_env(False);reports=[]
    try:
        with h5py.File(DATA) as data:
            for jobid,name in [('bc_k2_noise005','demo_73'),('bc_k2_clean','demo_188')]:
                directory=old/jobid
                if not directory.exists():
                    directory=next(p for p in old.iterdir() if p.is_dir() and p.name.startswith('bc_k2_noise'))
                obs=restore_demo(env,data['data'][name]);controller=RecoveryController(env.target_bin_placements[env.object_to_id['can']],env.bin2_pos[2],pack_obs(obs));prev=np.zeros(7,np.float32);samples=[]
                for line in (directory/'trace.jsonl').open():
                    r=json.loads(line)
                    if r['demo']!=name:continue
                    x=pack_obs(obs);a,diag=controller.choose(x,np.array(r['original_proposal'],np.float32),prev)
                    np.testing.assert_array_equal(a,r['submitted_action'])
                    if diag['mode'] in ['ALIGN','DESCEND'] and (controller.age%10==0 or controller.age==69):
                        goal=controller.grasp_target(x)
                        if diag['mode']=='ALIGN':goal[2]=max(controller.floor+.20,x[18]+.14)
                        q=env.sim.data.qpos[env.robots[0]._ref_joint_pos_indexes].copy()
                        jointids=env.robots[0]._ref_joint_indexes
                        limits=env.sim.model.jnt_range[jointids]
                        contacts=[]
                        for c in env.sim.data.contact[:env.sim.data.ncon]:
                            names=[env.sim.model.body_id2name(int(env.sim.model.geom_bodyid[g])) for g in [c.geom1,c.geom2]]
                            if any('robot0' in str(b) or 'gripper' in str(b) for b in names):contacts.append(names)
                        samples.append({'step':r['step'],'phase':diag['mode'],'age':controller.age,'eef':x[:3].tolist(),'goal':goal.tolist(),'position_error':float(np.linalg.norm(x[:3]-goal)),
                            'rotation_error':float(np.linalg.norm(Rotation.from_matrix(controller.goal_rotation@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec())),
                            'planned_euler':Rotation.from_matrix(controller.goal_rotation).as_euler('xyz').tolist(),'q':q.tolist(),'joint_margin':np.minimum(q-limits[:,0],limits[:,1]-q).tolist(),'contacts':contacts,'action':a.tolist()})
                    prev=np.array(r['executed_action'],np.float32);obs,*_=env.step(prev);np.testing.assert_array_equal(pack_obs(obs),r['state_after'])
                reports.append({'job':directory.name,'demo':name,'events':controller.events,'samples':samples})
    finally:env.close()
    write(RUN/'alignment_diagnosis.json',reports)
    for r in reports:print(json.dumps({'demo':r['demo'],'samples':r['samples'][-8:]}))
if __name__=='__main__':main()
