"""Conservative world-model MPC: override BC only when predicted future is clearly better."""
import argparse,json,time
import h5py,numpy as np,torch
from common import ROOT,DATA,make_env,pack_obs,restore_demo,load_policy
from collect_branches import candidates
from world_model import WorldModel,score

def main(args):
    torch.set_num_threads(2)
    policy=load_policy(ROOT/'policy'/args.policy/args.policy_checkpoint)
    ck=torch.load(ROOT/'models'/args.model/'model.pt',map_location='cpu',weights_only=True);cfg=ck['config']
    model=WorldModel(cfg['dim'],cfg['width'],cfg.get('future_only',False));model.load_state_dict(ck['state_dict']);model.eval()
    env=make_env(False);names=json.loads((ROOT/'data/splits.json').read_text())[args.split][:args.episodes]
    records=[];out=ROOT/'models'/args.model/f'gated_{args.split}_margin{args.margin}.json'
    with h5py.File(DATA,'r') as f:
      for name in names:
        obs=restore_demo(env,f['data'][name]);rng=np.random.default_rng(40000+int(name.split('_')[1]));crng=np.random.default_rng(100000+int(name.split('_')[1]))
        success=False;peak=0.;grasped=False;chosen=[];times=[];start=time.perf_counter()
        for step in range(args.steps):
          x=pack_obs(obs);tic=time.perf_counter()
          with torch.no_grad():
            base=policy.best(torch.from_numpy(x[None]))[0,0].numpy();aa=candidates(base,crng,args.candidates)
            xb=torch.from_numpy(np.repeat(x[None],args.candidates,axis=0));ab=torch.from_numpy(aa)
            future,_=model(xb,ab);predscore=score(_,args.risk_weight)
            chosen_score=float(predscore[0]);sel=0
            for k in range(1,args.candidates):
              if float(predscore[k])>chosen_score+args.margin:chosen_score=float(predscore[k]);sel=k
            action=aa[sel,0].copy()
          times.append(time.perf_counter()-tic);chosen.append(sel)
          if args.noise: action[:3]+=rng.normal(0,args.noise,3)
          obs,*_=env.step(np.clip(action,-1,1));st=env.staged_rewards();peak=max(peak,float(max(st)));grasped=grasped or st[1]>.3
          if env._check_success():success=True;break
        row={'demo':name,'success':success,'steps':step+1,'peak_stage_reward':peak,'ever_grasped':bool(grasped),
             'fraction_base_selected':float(np.mean(np.asarray(chosen)==0)),'mean_decision_ms':float(np.mean(times)*1000),'elapsed_s':time.perf_counter()-start}
        records.append(row);out.write_text(json.dumps({'args':vars(args),'input':'PRIVILEGED_STATE_DIAGNOSTIC','records':records,'success_rate':float(np.mean([z['success'] for z in records]))},indent=2));print(json.dumps(row),flush=True)
    env.close();print('success_rate',np.mean([z['success'] for z in records]),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--model',default='full_future_seed17_pilot_v1');p.add_argument('--policy',default='bc_chunk_dev_v4');p.add_argument('--policy-checkpoint',default='policy_15000.pt');p.add_argument('--split',choices=['dev','sealed_test'],default='dev');p.add_argument('--episodes',type=int,default=8);p.add_argument('--steps',type=int,default=400);p.add_argument('--candidates',type=int,default=6);p.add_argument('--margin',type=float,default=.2);p.add_argument('--risk-weight',type=float,default=.5);p.add_argument('--noise',type=float,default=0);main(p.parse_args())
