"""Same-state pose-control branches of a known DEV failure; not a test outcome."""
import sys,json,copy
from collections import deque
import numpy as np,h5py
from scipy.spatial.transform import Rotation
from setup_study import ROOT,RUN,write
sys.path.insert(0,str(ROOT))
from common import DATA,make_env,restore_demo,pack_obs
from reproduction.extensions_20261012_01.snapshot import Snapshot
from recovery_controller import RecoveryController
def main():
    old=ROOT/'reproduction/recovery_v2_20261012_01/dev_a/bc_k2_noise005/trace.jsonl'
    if not old.exists():old=next((ROOT/'reproduction/recovery_v2_20261012_01/dev_a').glob('bc_k2_noise*/trace.jsonl'))
    rows=[json.loads(l) for l in old.open() if json.loads(l)['demo']=='demo_73'];env=make_env(False)
    try:
        with h5py.File(DATA) as f:obs=restore_demo(env,f['data']['demo_73'])
        for r in rows:
            if r['step']==225:break
            obs,*_=env.step(np.array(r['executed_action'],np.float32))
        snap=Snapshot(env);x0=pack_obs(obs);results=[]
        for yaw in [np.pi,0.]:
            snap.restore();x=x0.copy();pending=deque(np.array(a,np.float32) for a in r['queue_before']);ctrl=RecoveryController([.1975,.4025,.8],.8,x)
            ctrl.goal_rotation=Rotation.from_euler('z',yaw).as_matrix()@np.diag([1.,-1.,-1.]);goal=np.r_[x[16:18],max(1.,x[18]+.14)];samples=[]
            for i in range(110):
                a=ctrl.pose_action(x,goal,-1);pending.append(a);obs,*_=env.step(pending.popleft());x=pack_obs(obs)
                samples.append({'step':i+1,'position_error':float(np.linalg.norm(x[:3]-goal)), 'angle_error':float(np.linalg.norm(Rotation.from_matrix(ctrl.goal_rotation@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec()))})
            q=env.sim.data.qpos[env.robots[0]._ref_joint_pos_indexes].copy();limits=env.sim.model.jnt_range[env.robots[0]._ref_joint_indexes]
            results.append({'yaw':yaw,'final':samples[-1],'first_aligned_step':next((s['step'] for s in samples if s['position_error']<.014 and s['angle_error']<.15),None),'joint_margin':np.minimum(q-limits[:,0],limits[:,1]-q).tolist(),'samples':samples})
        write(RUN/'alignment_branch_probe_d.json',{'dataset':'known development failure; diagnostic only','demo':'demo_73','initial_step':225,'D':2,'steps':110,'results':results})
        print(json.dumps([{k:v for k,v in x.items() if k!='samples'} for x in results]))
    finally:env.close()
if __name__=='__main__':main()
