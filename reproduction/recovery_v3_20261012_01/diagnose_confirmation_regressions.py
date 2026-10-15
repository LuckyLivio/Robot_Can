"""Post-freeze diagnosis only: never changes the controller or test selection."""
import json,sys
import numpy as np,h5py
from scipy.spatial.transform import Rotation
from setup_study import ROOT,RUN,write
sys.path.insert(0,str(ROOT))
from common import make_env,restore_demo,pack_obs
from recovery_controller import RecoveryController,Config
from reproduction.recovery_v2_20261012_01.recovery_controller import RecoveryController as V2Controller,Config as V2Config
def main():
    regressions=json.loads((RUN/'diagnosis_confirmation.json').read_text())['regressions_vs_v2'];env=make_env(False);report=[]
    try:
        with h5py.File(RUN/'confirmation_starts.hdf5') as f:
            for case in regressions:
                pair=[]
                for v in ['v2','v3']:
                    path=RUN/'confirmation'/case['job'].replace('v3_',v+'_',1);result=json.loads((path/'result.json').read_text());job=result['job']
                    obs=restore_demo(env,f['data'][case['demo']]);cls,cfg=(RecoveryController,Config) if v=='v3' else (V2Controller,V2Config)
                    ctrl=cls([.1975,.4025,.8],.8,pack_obs(obs),config=cfg(**job['config']));prev=np.zeros(7,np.float32);samples=[]
                    for line in (path/'trace.jsonl').open():
                        r=json.loads(line)
                        if r['demo']!=case['demo']:continue
                        x=pack_obs(obs);a,d=ctrl.choose(x,np.array(r['original_proposal'],np.float32),prev);np.testing.assert_array_equal(a,r['submitted_action'])
                        if d['mode']=='ALIGN' and (ctrl.age%20==0 or d.get('next_mode')=='DESCEND'):
                            goal=np.r_[ctrl.grasp_target(x)[:2],max(ctrl.floor+ctrl.cfg.approach_clearance_m,x[18]+.14)]
                            q=env.sim.data.qpos[env.robots[0]._ref_joint_pos_indexes].copy();limits=env.sim.model.jnt_range[env.robots[0]._ref_joint_indexes]
                            samples.append({'step':r['step'],'age':ctrl.age,'attempt':ctrl.attempts,'eef':x[:3].tolist(),'goal':goal.tolist(),
                              'position_error_m':float(np.linalg.norm(x[:3]-goal)),
                              'rotation_error_rad':float(np.linalg.norm(Rotation.from_matrix(ctrl.goal_rotation@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec())),
                              'planned_euler_xyz':Rotation.from_matrix(ctrl.goal_rotation).as_euler('xyz').tolist(),'joint_margins_rad':np.minimum(q-limits[:,0],limits[:,1]-q).tolist()})
                        prev=np.array(r['executed_action'],np.float32);obs,*_=env.step(prev);np.testing.assert_array_equal(pack_obs(obs),r['state_after'])
                    pair.append({'version':v,'samples':samples})
                report.append({'case':case,'pair':pair})
    finally:env.close()
    write(RUN/'confirmation_regression_physics.json',{'purpose':'Post-hoc explanation, no parameter updates; these starts are now observed and cannot be fresh tests again.','cases':report})
    for r in report:print(json.dumps({'case':r['case'],'last_alignment_samples':[{**p,'samples':p['samples'][-2:]} for p in r['pair']]}))
if __name__=='__main__':main()
