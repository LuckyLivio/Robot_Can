"""Collect counterfactual branches under the declared FIFO action delay."""
import argparse,json,time
from collections import deque
import h5py,numpy as np,torch
from common import ROOT,DATA,make_env,pack_obs,restore_demo,load_policy
from collect_branches import candidates,future_labels

def main(args):
 out=ROOT/'data'/f'branches_{args.split}_{args.name}.npz'
 if out.exists() or out.with_suffix('.json').exists():
  raise FileExistsError(f'Refusing to overwrite branch data: {out}. Use a new --name.')
 env=make_env(False); policy=load_policy(ROOT/'policy'/args.policy/args.policy_checkpoint)
 split=json.loads((ROOT/'data/splits.json').read_text(encoding='utf-8'))[args.split]; selected=split[:args.demos]
 rng=np.random.default_rng(args.seed); xs=[];aa=[];ys=[];ll=[];parents=[];points=[];start=time.perf_counter()
 with h5py.File(DATA,'r') as f:
  for name in selected:
   d=f['data'][name];restore_demo(env,d,0,xml=True)
   n=len(d['actions']); indices=np.linspace(10,n-args.horizon-2,args.points,dtype=int)
   for t in indices:
    obs=restore_demo(env,d,int(t),xml=False);x=pack_obs(obs);base=policy.best(torch.from_numpy(x[None]))[0].numpy()
    if args.candidate_mode=='shift':
     candidates_now=np.asarray([np.repeat(base[k:k+1],base.shape[0],axis=0) for k in range(min(args.candidates,base.shape[0]))],np.float32)
    else: candidates_now=candidates(base,rng,args.candidates)
    initial_grasp=bool(env.staged_rewards()[1]>.3)
    group_a=[];group_y=[];group_l=[]
    for candidate in candidates_now:
     restore_demo(env,d,int(t),xml=False);q=deque([np.zeros(7,np.float32) for _ in range(args.delay)],maxlen=args.delay+1);executed_actions=[];states=[];labels=[]
     for action in candidate:
      q.append(action);executed=q.popleft();executed_actions.append(executed.copy());obs,*_=env.step(executed);states.append(pack_obs(obs));labels.append(future_labels(env,initial_grasp))
     group_a.append(executed_actions);group_y.append(states);group_l.append(labels)
    # Model inputs describe executed actions, matching the FIFO-prefixed evaluator.
    xs.append(x);aa.append(group_a);ys.append(group_y);ll.append(group_l);parents.append(name);points.append(int(t))
   np.savez_compressed(out,x=np.asarray(xs,np.float32),a=np.asarray(aa,np.float32),y=np.asarray(ys,np.float32),labels=np.asarray(ll,np.float32),parent=np.asarray(parents),point=np.asarray(points));print(json.dumps({'demo':name,'groups':len(xs),'elapsed_s':time.perf_counter()-start}),flush=True)
 env.close();out.with_suffix('.json').write_text(json.dumps({'args':vars(args),'input':'PRIVILEGED_STATE_DIAGNOSTIC','action_semantics':'executed_after_fifo','groups':len(xs),'elapsed_s':time.perf_counter()-start},indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--split',choices=['train','dev'],default='train');p.add_argument('--demos',type=int,default=20);p.add_argument('--points',type=int,default=8);p.add_argument('--horizon',type=int,default=8);p.add_argument('--candidates',type=int,default=6);p.add_argument('--delay',type=int,default=2);p.add_argument('--seed',type=int,default=2718);p.add_argument('--name',default='delay2_v0');p.add_argument('--policy',default='bc_chunk_dev_v4');p.add_argument('--policy-checkpoint',default='policy_15000.pt');p.add_argument('--candidate-mode',choices=['random','shift'],default='random');main(p.parse_args())
