"""Count real bin-finger contacts during fixed corner-fixture descent."""
import json,sys,argparse
from collections import Counter
import numpy as np,h5py
from setup_study import ROOT,RUN,write
sys.path.insert(0,str(ROOT))
from common import make_env,restore_demo,pack_obs
def main(stage,receipt):
    env=make_env(False);report=[]
    try:
        with h5py.File(RUN/'pilot_starts.hdf5') as f:
            for version in ['v2','v3']:
                path=RUN/(stage if version=='v3' else 'pilot_a')/f'{version}_new_geometry'
                for name in ['demo_6100002','demo_6100003']:
                    obs=restore_demo(env,f['data'][name]);count=Counter();n=0
                    for line in (path/'trace.jsonl').open():
                        r=json.loads(line)
                        if r['demo']!=name:continue
                        obs,*_=env.step(np.array(r['executed_action'],np.float32));np.testing.assert_array_equal(pack_obs(obs),r['state_after'])
                        if r['recovery']['mode']!='DESCEND':continue
                        n+=1
                        for c in env.sim.data.contact[:env.sim.data.ncon]:
                            bodies=[str(env.sim.model.body_id2name(int(env.sim.model.geom_bodyid[g]))) for g in [c.geom1,c.geom2]]
                            if 'bin2' in bodies and any('finger' in b or 'gripper' in b for b in bodies):count[' / '.join(bodies)]+=1
                    report.append({'version':version,'demo':name,'descent_steps':n,'contacts_at_sampled_control_boundaries':dict(count)})
    finally:env.close()
    write(RUN/receipt,report);print(json.dumps(report))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',default='pilot_d');p.add_argument('--receipt',default='corner_contact_probe_d.json');a=p.parse_args();main(a.stage,a.receipt)
