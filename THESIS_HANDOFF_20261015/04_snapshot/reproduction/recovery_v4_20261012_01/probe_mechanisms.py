"""Post-hoc physics diagnostics on known pilot fixtures; never control inputs."""
import json,sys
from collections import Counter
import h5py,numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup_study import ROOT,RUN,write
sys.path.insert(0,str(ROOT))
from common import DATA,make_env,restore_demo,pack_obs
from recovery_controller import RecoveryController,Config
from reproduction.recovery_v2_20261012_01.recovery_controller import RecoveryController as V2,Config as V2Config

def main():
    env=make_env(False);results=[]
    cases=[('v2_known_alignment','demo_73'),('align_only_known_alignment','demo_73'),
           ('v2_new_geometry','demo_6100002'),('region_only_new_geometry','demo_6100002'),
           ('v2_new_geometry','demo_6100003'),('region_only_new_geometry','demo_6100003')]
    try:
        for name,demo in cases:
            folder=RUN/'pilot_b'/name;result=json.loads((folder/'result.json').read_text());j=result['job']
            with h5py.File(ROOT/j['dataset'] if j.get('dataset') else DATA) as f:obs=restore_demo(env,f['data'][demo])
            cls,config=(V2,V2Config) if j['version']=='v2' else (RecoveryController,Config)
            c=cls([.1975,.4025,.8],.8,pack_obs(obs),config=config(**j.get('config',{})))
            previous=np.zeros(7,np.float32);samples=[];contacts=Counter();descent_steps=0;controls=0
            for ln in (folder/'trace.jsonl').open():
                r=json.loads(ln)
                if r['demo']!=demo:continue
                x=pack_obs(obs);np.testing.assert_array_equal(x,r['state_before'])
                if j.get('force_recovery_at')==r['step']:c.start_attempt('diagnostic_forced_start',x)
                a,d=c.choose(x,np.array(r['original_proposal'],np.float32),previous)
                np.testing.assert_array_equal(a,r['submitted_action']);assert d==r['recovery']
                if d['mode']=='ALIGN':
                    goal=np.r_[c.grasp_target(x)[:2],max(1.,x[18]+.14)]
                    q=env.sim.data.qpos[env.robots[0]._ref_joint_pos_indexes];lim=env.sim.model.jnt_range[env.robots[0]._ref_joint_indexes]
                    samples.append({'step':r['step'],'position_error_m':float(np.linalg.norm(x[:3]-goal)),
                      'orientation_error_rad':float(np.linalg.norm(Rotation.from_matrix(c.goal_rotation@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec())),
                      'joint_margin_rad':np.minimum(q-lim[:,0],lim[:,1]-q).tolist()})
                previous=np.array(r['executed_action'],np.float32);obs,*_=env.step(previous)
                np.testing.assert_array_equal(pack_obs(obs),r['state_after']);assert bool(env._check_success())==r['success_after'];controls+=1
                if d['mode']=='DESCEND':
                    descent_steps+=1;pairs=set()
                    for contact in env.sim.data.contact[:env.sim.data.ncon]:
                        bodies=[env.sim.model.body_id2name(int(env.sim.model.geom_bodyid[g])) for g in [contact.geom1,contact.geom2]]
                        if any(str(b).startswith('bin') for b in bodies) and any('gripper' in str(b) for b in bodies):pairs.add(' / '.join(sorted(str(b) for b in bodies)))
                    contacts.update(pairs)
            record=next(x for x in result['records'] if x['demo']==demo)
            results.append({'job':name,'demo':demo,'success':record['success'],'steps':controls,'physics_replay_exact':True,
                'descent_steps':descent_steps,'wall_gripper_contact_boundaries':dict(contacts),'alignment_samples':samples,'events':record['events']})
    finally:env.close()
    write(RUN/'mechanism_physics.json',{'known_diagnostic_only':True,'measurement':'Contacts sampled only at 20Hz control boundaries, not every MuJoCo substep. Joint margins are post-hoc diagnostics, never controller inputs.','results':results})
    fig,ax=plt.subplots(1,2,figsize=(11,4))
    for r,color in zip(results[:2],['#778391','#20816b']):
        ss=r['alignment_samples'];t=[s['step'] for s in ss]
        ax[0].plot(t,[100*s['position_error_m'] for s in ss],label=r['job'],color=color)
        ax[1].plot(t,[np.degrees(s['orientation_error_rad']) for s in ss],label=r['job'],color=color)
    for a in ax:a.axvline(222,color='#b07841',ls='--',alpha=.7);a.set_xlabel('Control step');a.grid(alpha=.15)
    ax[0].set_ylabel('Position residual (cm)');ax[1].set_ylabel('Orientation residual (deg)');ax[0].legend()
    fig.suptitle('Known development case 73: switch at 222; aligned at 289; task still unfinished at 400')
    fig.tight_layout();fig.savefig(RUN/'alignment_mechanism.png',dpi=180);fig.savefig(RUN/'alignment_mechanism.svg');plt.close(fig)
    print(json.dumps([{k:v for k,v in r.items() if k not in ['alignment_samples','events']} for r in results],indent=2),flush=True)
if __name__=='__main__':main()
