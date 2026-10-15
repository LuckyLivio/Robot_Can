"""Replay saved actions in MuJoCo and require exact recorded state equality."""
from pathlib import Path
import argparse,json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
sys.path.insert(0,str(ROOT/'reproduction/extensions_20261012_01'));sys.path.insert(0,str(ROOT))
import h5py,numpy as np
from common import DATA,make_env,restore_demo,pack_obs
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();stage=RUN/a.stage
    jobs=json.loads((stage/'jobs.json').read_text());selected=[]
    if a.stage.startswith('pilot'):
        for v in ['v5','r1','r2','v6']:
            for suffix,demo in [('new_geometry','demo_6100002'),('known_pressure','demo_11000012'),('known_pressure','demo_11000013'),('full_noise','demo_133')]:
                selected.append((next(j for j in jobs if j['id']==v+'_'+suffix),demo))
    else:
        selected=[(j,j['demos'][0]) for j in jobs]
    env=make_env(False);results=[]
    try:
        for j,name in selected:
            with h5py.File(ROOT/j['dataset'] if j.get('dataset') else DATA) as f:obs=restore_demo(env,f['data'][name])
            n=0
            for line in (stage/j['id']/'trace.jsonl').open():
                r=json.loads(line)
                if r['demo']!=name:continue
                np.testing.assert_array_equal(pack_obs(obs),r['state_before'])
                obs,*_=env.step(np.array(r['executed_action'],np.float32))
                np.testing.assert_array_equal(pack_obs(obs),r['state_after'])
                assert bool(env._check_success())==r['success_after'];n+=1
            results.append({'job':j['id'],'demo':name,'steps':n,'max_state_error':0.})
    finally:env.close()
    result={'passed':True,'stage':a.stage,'episodes':len(results),'control_steps':sum(r['steps'] for r in results),'samples':results}
    with (RUN/'analysis'/f'{a.stage}_physics.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
