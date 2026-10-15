"""Read-only physics replay for contacts/joint ranges in the observed regression."""
from pathlib import Path
from collections import Counter
import json,sys
import h5py,numpy as np
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from common import make_env,restore_demo,pack_obs

def main():
    folder=RUN/'pilot_b/v8_regression_6000005';result=json.loads((folder/'result.json').read_text());job=result['job']
    env=make_env(False);samples=[];pairs=Counter()
    try:
        with h5py.File(ROOT/job['dataset']) as f:obs=restore_demo(env,f['data'][job['demos'][0]])
        for line in (folder/'trace.jsonl').open():
            r=json.loads(line);np.testing.assert_array_equal(pack_obs(obs),r['state_before'])
            obs,*_=env.step(np.array(r['executed_action'],np.float32));np.testing.assert_array_equal(pack_obs(obs),r['state_after'])
            if r['recovery']['mode']!='ALIGN':continue
            m=env.sim.model;d=env.sim.data;contacts=[]
            for i in range(d.ncon):
                c=d.contact[i];names=[m.body_id2name(m.geom_bodyid[int(g)]) for g in [c.geom1,c.geom2]]
                if any(n and n.startswith('robot0_') for n in names) and any(n in ['bin1','bin2'] for n in names):
                    key=' / '.join(names);pairs[key]+=1;contacts.append({'bodies':names,'distance':float(c.dist)})
            joints=[]
            for name in m.joint_names:
                if not name.startswith('robot0_joint'):continue
                i=m.joint_name2id(name);q=float(d.qpos[m.jnt_qposadr[i]]);lo,hi=m.jnt_range[i]
                joints.append({'name':name,'q':q,'lower':float(lo),'upper':float(hi),'distance_to_limit':float(min(q-lo,hi-q))})
            samples.append({'step':r['step'],'eef':pack_obs(obs)[:3].tolist(),'bin_contacts':contacts,'joints':joints})
    finally:env.close()
    receipt={'passed_exact_replay':True,'alignment_steps':len(samples),'arm_bin_contact_counts':dict(pairs),
             'closest_joint_limit_rad':min(j['distance_to_limit'] for s in samples for j in s['joints']),
             'samples':samples,'scope':'Post-hoc diagnostics; no contacts/joints were supplied to the evaluated recovery controller. Contact occurrence alone is not a causal intervention.'}
    with (RUN/'analysis/alignment_diagnosis.json').open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps({k:v for k,v in receipt.items() if k!='samples'}),flush=True)
if __name__=='__main__':main()
