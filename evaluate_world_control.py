"""Receding-horizon candidate selection; never simulate candidates during deployment."""
import argparse
import json
import time

import h5py
import numpy as np
import torch

from common import ROOT,DATA,make_env,pack_obs,restore_demo,load_policy
from collect_branches import candidates
from world_model import WorldModel,DirectScore,score


def main(args):
    torch.set_num_threads(2)
    policy=load_policy(ROOT/'policy'/args.policy/args.policy_checkpoint)
    checkpoint=torch.load(ROOT/'models'/args.model/'model.pt',map_location='cpu',weights_only=True)
    cfg=checkpoint['config']
    model=(DirectScore(cfg['dim'],cfg['horizon'],cfg['width']) if cfg['method']=='direct'
           else WorldModel(cfg['dim'],cfg['width'],cfg.get('future_only',False)))
    model.load_state_dict(checkpoint['state_dict']);model.eval()
    env=make_env(False)
    names=json.loads((ROOT/'data/splits.json').read_text())[args.split][:args.episodes]
    records=[]
    out=ROOT/'models'/args.model/f'control_{args.split}_noise{args.noise}_risk{args.risk_weight}.json'
    with h5py.File(DATA,'r') as file:
        for name in names:
            obs=restore_demo(env,file['data'][name])
            if hasattr(policy,'reset'):policy.reset()
            # Separate RNGs keep physical disturbance sequence identical across methods.
            seed=40000+int(name.split('_')[1])
            noise_rng=np.random.default_rng(seed)
            candidate_rng=np.random.default_rng(seed+100000)
            started=time.perf_counter();decision_times=[]
            success=False;peak=0.;ever_grasped=False;chosen_ids=[]
            for step in range(args.steps):
                x=pack_obs(obs)
                tic=time.perf_counter()
                with torch.no_grad():
                    base=policy.best(torch.from_numpy(x[None]))[0].numpy()
                    aa=candidates(base,candidate_rng,args.candidates)
                    # Same candidate generator is used for every learned scorer.
                    batch=torch.from_numpy(np.tile(x[None],(args.candidates,1)))
                    _,readouts=model(batch,torch.from_numpy(aa))
                    scores=score(readouts,args.risk_weight).numpy()
                    selected=int(scores.argmax());action=aa[selected,0].copy()
                decision_times.append(time.perf_counter()-tic);chosen_ids.append(selected)
                if args.noise:
                    action[:3]+=noise_rng.normal(0,args.noise,3)
                obs,_,_,_=env.step(np.clip(action,-1,1))
                stages=env.staged_rewards();peak=max(peak,float(max(stages)))
                ever_grasped=ever_grasped or stages[1]>.3
                if env._check_success():success=True;break
            row={'demo':name,'success':success,'steps':step+1,'peak_stage_reward':peak,'ever_grasped':bool(ever_grasped),
                 'elapsed_s':time.perf_counter()-started,'mean_decision_ms':float(np.mean(decision_times)*1000),
                 'fraction_base_selected':float(np.mean(np.array(chosen_ids)==0))}
            records.append(row)
            out.write_text(json.dumps({'args':vars(args),'model_config':cfg,'input':'PRIVILEGED_STATE_DIAGNOSTIC',
                                       'records':records,'success_rate':float(np.mean([r['success'] for r in records]))},indent=2),encoding='utf-8')
            print(json.dumps(row),flush=True)
    env.close()
    print('success_rate',np.mean([r['success'] for r in records]),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--model',required=True);p.add_argument('--policy',default='bc_chunk_dev_v1')
    p.add_argument('--policy-checkpoint',default='policy_5000.pt')
    p.add_argument('--split',choices=['dev','sealed_test'],default='dev')
    p.add_argument('--episodes',type=int,default=8);p.add_argument('--steps',type=int,default=400)
    p.add_argument('--noise',type=float,default=0.);p.add_argument('--candidates',type=int,default=6)
    p.add_argument('--risk-weight',type=float,default=.5)
    main(p.parse_args())
