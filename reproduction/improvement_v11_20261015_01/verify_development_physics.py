from pathlib import Path
import json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT/'reproduction/extensions_20261012_01'));sys.path.insert(0,str(ROOT))
import h5py,numpy as np
from common import DATA,make_env,restore_demo,pack_obs
if __name__=='__main__':
    stage=RUN/'dev_a';jobs=json.loads((stage/'jobs.json').read_text());selected=[]
    for j in jobs:
        d=json.loads((stage/j['id']/'result.json').read_text());records=d['records']
        # Every executed policy/noise group: first listed start, every failure and every new edge activation.
        names={j['demos'][0]}|{r['demo'] for r in records if not r['success'] or r.get('edge_events')}
        for name in j['demos']:
            if name in names:selected.append((j,name))
    env=make_env(False);results=[]
    try:
        for j,name in selected:
            with h5py.File(ROOT/j['dataset'] if j.get('dataset') else DATA) as f:obs=restore_demo(env,f['data'][name])
            adr=env.sim.model.jnt_qposadr[[env.sim.model.joint_name2id('robot0_joint'+str(i)) for i in range(1,8)]];n=0
            for r in map(json.loads,(stage/j['id']/'trace.jsonl').open()):
                if r['demo']!=name:continue
                np.testing.assert_array_equal(pack_obs(obs),r['state_before']);np.testing.assert_array_equal(env.sim.data.qpos[adr],r['joint_positions'])
                obs,*_=env.step(np.array(r['executed_action'],np.float32));np.testing.assert_array_equal(pack_obs(obs),r['state_after']);np.testing.assert_array_equal(env.staged_rewards(),r['stages_after']);assert bool(env._check_success())==r['success_after'];n+=1
            assert n>0;results.append({'condition':j['id'],'demo':name,'steps':n});print(json.dumps(results[-1]),flush=True)
    finally:env.close()
    data={'passed':True,'episodes':len(results),'control_steps':sum(r['steps'] for r in results),'samples':results,'scope':'Every condition first start plus all failures and all new edge activations; saved action physics replay, not new outcome experiments.'}
    with (RUN/'analysis/development_physics.json').open('x') as f:json.dump(data,f,indent=2)
    print(json.dumps(data))
