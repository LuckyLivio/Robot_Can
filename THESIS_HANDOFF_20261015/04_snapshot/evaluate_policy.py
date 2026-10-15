import argparse
import json
import time

import h5py
import numpy as np
import torch

from common import ROOT,DATA,make_env,pack_obs,restore_demo,load_policy


def main(args):
    torch.set_num_threads(2)
    model=load_policy(ROOT/'policy'/args.policy/args.checkpoint)
    env=make_env(False)
    splits=json.loads((ROOT/'data/splits.json').read_text())
    names=splits[args.split][:args.episodes]
    records=[]
    out=ROOT/'policy'/args.policy/f'eval_{args.split}_{args.noise}_{args.checkpoint.replace(".pt", "")}.json'
    with h5py.File(DATA,'r') as file:
        for name in names:
            obs=restore_demo(env,file['data'][name])
            if hasattr(model,'reset'):model.reset()
            rng=np.random.default_rng(40000+int(name.split('_')[1]))
            start=time.perf_counter()
            success=False
            peak=0.
            grasped=False
            for step in range(args.steps):
                x=torch.from_numpy(pack_obs(obs)[None])
                a=model.best(x)[0,0].numpy()
                if args.noise:
                    a[:3]+=rng.normal(0,args.noise,3)
                a=np.clip(a,-1,1)
                obs,r,_,_=env.step(a)
                stages=env.staged_rewards()
                peak=max(peak,float(max(stages)))
                grasped=grasped or stages[1]>.3
                if env._check_success():
                    success=True
                    break
            row={'demo':name,'success':success,'steps':step+1,'peak_stage_reward':peak,
                 'ever_grasped':bool(grasped),'elapsed_s':time.perf_counter()-start}
            records.append(row)
            out.write_text(json.dumps({'input':'PRIVILEGED_STATE_DIAGNOSTIC','args':vars(args),
                                       'records':records,'success_rate':np.mean([r['success'] for r in records])},indent=2),encoding='utf-8')
            print(json.dumps(row),flush=True)
    env.close()
    print('success_rate',np.mean([r['success'] for r in records]),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--policy',default='bc_chunk_dev_v0')
    p.add_argument('--checkpoint',default='policy.pt')
    p.add_argument('--split',choices=['dev','sealed_test'],default='dev')
    p.add_argument('--episodes',type=int,default=8)
    p.add_argument('--steps',type=int,default=400)
    p.add_argument('--noise',type=float,default=0.)
    main(p.parse_args())
