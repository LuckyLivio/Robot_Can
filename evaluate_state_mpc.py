"""World-model MPC whose objective is computed from recursively predicted physical states."""
import argparse,json,time
import h5py,numpy as np,torch
from common import ROOT,DATA,make_env,pack_obs,restore_demo,load_policy
from collect_branches import candidates
from world_model import WorldModel

def main(args):
 torch.set_num_threads(2);policy=load_policy(ROOT/'policy'/args.policy/args.policy_checkpoint)
 ck=torch.load(ROOT/'models'/args.model/'model.pt',map_location='cpu',weights_only=True);cfg=ck['config'];model=WorldModel(cfg['dim'],cfg['width'],cfg.get('future_only',False));model.load_state_dict(ck['state_dict']);model.eval();env=make_env(False)
 names=json.loads((ROOT/'data/splits.json').read_text())[args.split][:args.episodes];records=[];out=ROOT/'models'/args.model/f'state_mpc_{args.split}_margin{args.margin}.json'
 with h5py.File(DATA,'r') as f:
  for name in names:
   obs=restore_demo(env,f['data'][name]);
   if hasattr(policy,'reset'):policy.reset()
   rng=np.random.default_rng(100000+int(name.split('_')[1]));success=False;peak=0.;grasped=False;times=[];ids=[];start=time.perf_counter()
   target=env.target_bin_placements[env.object_to_id['can']].astype(np.float32)
   for step in range(args.steps):
    x=pack_obs(obs);base=policy.best(torch.from_numpy(x[None]))[0].numpy();aa=candidates(base,rng,args.candidates);tic=time.perf_counter()
    with torch.no_grad():
     future,_=model(torch.from_numpy(np.repeat(x[None],len(aa),0)),torch.from_numpy(aa));eef=future[:,:,:3];obj=future[:,:,16:19];t=torch.from_numpy(target)
     current_dist=np.linalg.norm(x[:3]-x[16:19]);currently_holding=(x[16:19][2]>.88 and current_dist<.1)
     if currently_holding:cost=((obj-t)**2).sum(-1).sqrt().mean(1)+.5*torch.relu(.86-obj[:,-1,2])
     else:cost=((eef-obj)**2).sum(-1).sqrt().mean(1)
     best=float(cost[0]);sel=0
     for k in range(1,len(aa)):
      if float(cost[k])<best-args.margin:best=float(cost[k]);sel=k
     action=aa[sel,0].copy();ids.append(sel)
    times.append(time.perf_counter()-tic);obs,*_=env.step(np.clip(action,-1,1));st=env.staged_rewards();peak=max(peak,float(max(st)));grasped=grasped or st[1]>.3
    if env._check_success():success=True;break
   row={'demo':name,'success':success,'steps':step+1,'peak_stage_reward':peak,'ever_grasped':grasped,'fraction_base':float(np.mean(np.asarray(ids)==0)),'mean_decision_ms':float(np.mean(times)*1000),'elapsed_s':time.perf_counter()-start};records.append(row);out.write_text(json.dumps({'args':vars(args),'input':'PRIVILEGED_STATE_DIAGNOSTIC','records':records,'success_rate':float(np.mean([z['success'] for z in records]))},indent=2));print(json.dumps(row),flush=True)
 env.close();print('success_rate',np.mean([z['success'] for z in records]),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--model',default='full_future_bc_v4');p.add_argument('--policy',default='bc_chunk_dev_v4');p.add_argument('--policy-checkpoint',default='policy_15000.pt');p.add_argument('--split',choices=['dev','sealed_test'],default='dev');p.add_argument('--episodes',type=int,default=8);p.add_argument('--steps',type=int,default=400);p.add_argument('--candidates',type=int,default=6);p.add_argument('--margin',type=float,default=.005);main(p.parse_args())
