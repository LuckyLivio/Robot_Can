"""Export a fixed arm chain; validate its FK against the restored task."""
from pathlib import Path
import json,sys
import h5py,numpy as np
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from common import DATA,make_env,restore_demo,pack_obs

def main():
    env=make_env(False)
    try:
        with h5py.File(DATA) as f:obs=restore_demo(env,f['data']['demo_97'])
        m=env.sim.model;d=env.sim.data
        names=['robot0_joint'+str(i) for i in range(1,8)]
        joints=[m.joint_name2id(n) for n in names]
        site=env.robots[0].eef_site_id['right'];b=int(m.site_bodyid[site]);chain=[]
        while b:
            js=[j for j in joints if m.jnt_bodyid[j]==b]
            assert len(js)<=1
            row={'body':m.body_id2name(b),'position':m.body_pos[b].tolist(),'quaternion_wxyz':m.body_quat[b].tolist()}
            if js:
                j=js[0];assert m.jnt_type[j]==3
                row.update(joint_index=joints.index(j),axis=m.jnt_axis[j].tolist(),anchor=m.jnt_pos[j].tolist())
            chain.append(row);b=int(m.body_parentid[b])
        data={'joint_names':names,'limits':m.jnt_range[joints].tolist(),'chain':list(reversed(chain)),
              'site_position':m.site_pos[site].tolist(),'site_quaternion_wxyz':m.site_quat[site].tolist(),
              'reference_q':d.qpos[[m.jnt_qposadr[j] for j in joints]].tolist(),
              'reference_position':d.site_xpos[site].tolist(),'reference_rotation':d.site_xmat[site].reshape(3,3).tolist(),
              'scope':'Fixed FK chain, no contact or future rollout. No full-arm collision certificate.'}
        from scipy.spatial.transform import Rotation
        observed=Rotation.from_quat(pack_obs(obs)[3:7]).as_matrix()
        data['site_to_observation_rotation']=(d.site_xmat[site].reshape(3,3).T@observed).tolist()
        data['reference_observation_rotation']=observed.tolist()
        data['orientation_note']='Original robot0_eef_quat is eef body orientation; position is grip_site. Fixed local rotation bridges them.'
        with (RUN/'recovery/arm_chain_observation.json').open('x') as f:json.dump(data,f,indent=2)
        print(json.dumps({'bodies':len(chain),'site':m.site_id2name(site),'joints':names}))
    finally:env.close()
if __name__=='__main__':main()
