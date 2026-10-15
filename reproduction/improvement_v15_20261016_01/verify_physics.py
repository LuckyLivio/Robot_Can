"""Physical replay of saved commands; does not add evaluation samples."""
from pathlib import Path
import argparse,json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
import h5py,numpy as np
from common import DATA,make_env,restore_demo,pack_obs
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();stage=RUN/a.stage
    jobs=json.loads((stage/'jobs.json').read_text());selected=[]
    for j in jobs:
        rows=json.loads((stage/j['id']/'result.json').read_text())['records']
        names={rows[0]['demo']}
        names.update(r['demo'] for r in rows if not r['success'] or r.get('wait_hold_events') or r.get('support13_events') or r.get('escape_events') or r.get('tracking14_events') or r.get('clearance14_events') or r.get('carry15_events') or r.get('edge15_events') or r.get('budget15_events'))
        selected.extend((j,n) for n in j['demos'] if n in names)
    env=make_env(False);results=[]
    try:
        for j,name in selected:
            with h5py.File(ROOT/j['dataset'] if j.get('dataset') else DATA) as f:obs=restore_demo(env,f['data'][name])
            n=0
            for row in map(json.loads,(stage/j['id']/'trace.jsonl').open()):
                if row['demo']!=name:continue
                np.testing.assert_array_equal(pack_obs(obs),row['state_before'])
                obs,*_=env.step(np.array(row['executed_action'],np.float32))
                np.testing.assert_array_equal(pack_obs(obs),row['state_after'])
                np.testing.assert_array_equal(np.asarray(env.staged_rewards()),row['stages_after'])
                assert bool(env._check_success())==row['success_after'];n+=1
            assert n>0;results.append({'job':j['id'],'demo':name,'steps':n});print(j['id'],name,n,flush=True)
    finally:env.close()
    out={'passed':True,'stage':a.stage,'episodes':len(results),'steps':sum(r['steps'] for r in results),
         'selection':'First episode per job, all failures and all wait-hold, support13, escape, tracking14, clearance14, carry15, edge15 and budget15 event episodes',
         'note':'Physical replay of existing trajectories, not new statistical samples.','samples':results}
    with (RUN/'analysis'/f'{a.stage}_physics.json').open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps({k:v for k,v in out.items() if k!='samples'}))
