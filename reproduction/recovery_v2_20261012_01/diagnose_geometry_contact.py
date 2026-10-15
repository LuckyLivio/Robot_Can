"""Post-hoc contact diagnosis only. The controller never receives these contacts."""
import json,sys
from collections import Counter
import numpy as np,h5py
from setup_study import ROOT,RUN,write
sys.path.insert(0,str(ROOT))
from common import make_env,restore_demo,pack_obs

def main():
    directory=RUN/'geometry_confirmation/v2_geometry';result=json.loads((directory/'result.json').read_text())
    failures=[r['demo'] for r in result['records'] if not r['success']];env=make_env(False);diagnosis=[]
    try:
        with h5py.File(RUN/'geometry_starts.hdf5') as f:
            for name in failures:
                obs=restore_demo(env,f['data'][name]);counts=Counter();samples=[]
                for line in (directory/'trace.jsonl').open():
                    row=json.loads(line)
                    if row['demo']!=name:continue
                    obs,*_=env.step(np.array(row['executed_action'],np.float32));np.testing.assert_array_equal(pack_obs(obs),row['state_after'])
                    if row['recovery']['mode']!='DESCEND':continue
                    for contact in env.sim.data.contact[:env.sim.data.ncon]:
                        body_names=[env.sim.model.body_id2name(int(env.sim.model.geom_bodyid[g])) for g in [contact.geom1,contact.geom2]]
                        if 'bin2' in body_names and any('finger' in str(b) or 'hand' in str(b) or 'gripper' in str(b) for b in body_names):
                            key=' / '.join(str(b) for b in body_names);counts[key]+=1
                            if len(samples)<8:
                                samples.append({'step':row['step'],'bodies':body_names,'geom_ids':[int(contact.geom1),int(contact.geom2)],
                                    'contact_position':np.asarray(contact.pos).tolist(),'distance':float(contact.dist)})
                diagnosis.append({'demo':name,'contact_occurrences_at_control_boundaries':dict(counts),'samples':samples,
                                  'interpretation':'Post-hoc evidence of gripper-bin collision during the descending phase, not a control input.'})
    finally:env.close()
    write(RUN/'geometry_contact_diagnosis.json',diagnosis);print(json.dumps(diagnosis,indent=2))

if __name__=='__main__':main()
