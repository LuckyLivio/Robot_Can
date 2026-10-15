"""Same initial simulator state, different action chunks; grouped by parent demo."""
import argparse
import json
import time

import h5py
import numpy as np

from common import ROOT,DATA,make_env,pack_obs,restore_demo,load_policy


def future_labels(env,initial_grasp):
    stages=np.asarray(env.staged_rewards())
    success=bool(env._check_success())
    progress=1. if success else float(stages.max())
    lost=bool(initial_grasp and stages[1]<.3 and not success)
    return np.array([progress,float(lost)],dtype=np.float32)


def candidates(base,rng,count):
    chunks=np.tile(base[None],(count,1,1))
    for k in range(1,count):
        # Candidate perturbations are part of the declared local action search.
        chunks[k,:,:3]+=rng.normal(0,.2,3)
        if k%3==0:
            chunks[k,:,6]*=-1
        elif k%3==1:
            chunks[k,:3,6]=-1
        chunks[k,:,3:6]+=rng.normal(0,.03,3)
    return np.clip(chunks,-1,1).astype(np.float32)


def main(args):
    env=make_env(False)
    policy=load_policy(ROOT/'policy'/args.policy/args.policy_checkpoint) if args.policy else None
    split=json.loads((ROOT/'data/splits.json').read_text())[args.split]
    rng=np.random.default_rng(args.seed)
    selected=split[:args.demos]
    all_x,all_a,all_y,all_labels,parents,points=[],[],[],[],[],[]
    out=ROOT/'data'/f'branches_{args.split}_{args.name}.npz'
    started=time.perf_counter()
    with h5py.File(DATA,'r') as file:
        for name in selected:
            d=file['data'][name]
            restore_demo(env,d,0,xml=True)
            n=len(d['actions'])
            indices=np.linspace(10,n-args.horizon-2,args.points,dtype=int)
            for t in indices:
                obs=restore_demo(env,d,int(t),xml=False)
                initial_x=pack_obs(obs)
                initial_grasp=bool(env.staged_rewards()[1]>.3)
                if policy is not None:
                    base=policy.best(__import__('torch').from_numpy(initial_x[None]))[0].numpy()
                else: base=d['actions'][t:t+args.horizon]
                aa=candidates(base,rng,args.candidates)
                ys=[];ll=[]
                for chunk in aa:
                    restore_demo(env,d,int(t),xml=False)
                    states=[];labels=[]
                    for action in chunk:
                        obs,*_=env.step(action)
                        states.append(pack_obs(obs))
                        labels.append(future_labels(env,initial_grasp))
                    ys.append(states);ll.append(labels)
                all_x.append(initial_x);all_a.append(aa);all_y.append(ys);all_labels.append(ll)
                parents.append(name);points.append(int(t))
            np.savez_compressed(out,x=np.asarray(all_x,np.float32),a=np.asarray(all_a,np.float32),
                                y=np.asarray(all_y,np.float32),labels=np.asarray(all_labels,np.float32),
                                parent=np.asarray(parents),point=np.asarray(points))
            print(json.dumps({'demo':name,'groups':len(all_x),'elapsed_s':time.perf_counter()-started}),flush=True)
    env.close()
    meta={'args':vars(args),'input':'PRIVILEGED_STATE_DIAGNOSTIC','groups':len(all_x),
          'transitions':len(all_x)*args.candidates*args.horizon,'elapsed_s':time.perf_counter()-started,
          'grouping':'All branches from a parent demo stay in its original split.'}
    out.with_suffix('.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--split',choices=['train','dev'],default='train')
    p.add_argument('--demos',type=int,default=20)
    p.add_argument('--points',type=int,default=8)
    p.add_argument('--horizon',type=int,default=8)
    p.add_argument('--candidates',type=int,default=6)
    p.add_argument('--seed',type=int,default=817)
    p.add_argument('--name',default='pilot_v0')
    p.add_argument('--policy',default=None);p.add_argument('--policy-checkpoint',default='policy_15000.pt')
    main(p.parse_args())
