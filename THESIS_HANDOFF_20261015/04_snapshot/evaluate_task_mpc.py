"""State-diagnostic task MPC using a learned action-conditioned world model.

The model predicts future robot/object states; the controller never simulates candidate
actions in the environment. A geometric PD policy is a matched non-WM baseline.
"""
import argparse,json,time
import h5py,numpy as np,torch
from common import ROOT,DATA,make_env,pack_obs,restore_demo,load_policy
from world_model import WorldModel

def action_candidates(base,x,env,count=8):
    eef=x[:3];obj=x[16:19];target=env.target_bin_placements[env.object_to_id['can']]
    # infer grasp/transport from object height and eef-object distance
    grasped=(obj[2]>.88 and np.linalg.norm(obj-eef)<.09)
    goal=target if grasped else obj
    delta=goal-eef
    pd=np.clip(delta/.05,-1,1)
    actions=[base.copy()]
    # nominal target-directed candidates plus small lateral alternatives
    for scale in [.7,1.,1.3]:
        a=base.copy();a[:,:3]=np.clip(pd*scale,-1,1);a[:,6]=base[:,6]
        actions.append(a)
    for axis in [0,1,2]:
        a=actions[2].copy();a[:,axis]=np.clip(a[:,axis]+.25,-1,1);actions.append(a)
    return np.asarray(actions[:count],np.float32),grasped

def main(args):
    torch.set_num_threads(2)
    policy=load_policy(ROOT/'policy'/args.policy/args.policy_checkpoint)
    ck=torch.load(ROOT/'models'/args.model/'model.pt',map_location='cpu',weights_only=True);cfg=ck['config'];model=WorldModel(cfg['dim'],cfg['width'],cfg.get('future_only',False));model.load_state_dict(ck['state_dict']);model.eval()
    env=make_env(False);names=json.loads((ROOT/'data/splits.json').read_text())[args.split][:args.episodes];records=[];out=ROOT/'models'/args.model/f'taskmpc_{args.mode}_{args.split}.json'
    with h5py.File(DATA,'r') as f:
      for name in names:
        obs=restore_demo(env,f['data'][name]);
        if hasattr(policy,'reset'):policy.reset()
        success=False;peak=0.;grasped=False;times=[];chosen=[];start=time.perf_counter()
        for step in range(args.steps):
          x=pack_obs(obs);base=policy.best(torch.from_numpy(x[None]))[0].numpy();tic=time.perf_counter()
          aa,infer_grasp=action_candidates(base,x,env,args.candidates)
          if args.mode=='pd': action=aa[1,0]
          else:
            with torch.no_grad():
              xb=torch.from_numpy(np.repeat(x[None],len(aa),0));ab=torch.from_numpy(aa);future,_=model(xb,ab)
              obj=future[:,:,16:19];eef=future[:,:,:3];target=torch.from_numpy(env.target_bin_placements[env.object_to_id['can']].astype(np.float32))
              # Cost switches automatically once predicted object is lifted.
              lift=(obj[:,:,2]>.90).float();dist_obj=((eef-obj).square().sum(-1)+1e-6).sqrt();dist_bin=((obj-target).square().sum(-1)+1e-6).sqrt()
              cost=((1-lift)*dist_obj+lift*dist_bin).mean(1)+.05*torch.relu(.9-obj[:,-1,2])
              selected=int(cost.argmin());action=aa[selected,0] if aa.ndim==3 else aa[selected]
              chosen.append(selected)
          times.append(time.perf_counter()-tic);obs,*_=env.step(np.clip(action,-1,1));st=env.staged_rewards();peak=max(peak,float(max(st)));grasped=grasped or st[1]>.3
          if env._check_success():success=True;break
        row={'demo':name,'success':success,'steps':step+1,'peak_stage_reward':peak,'ever_grasped':grasped,'mean_decision_ms':float(np.mean(times)*1000),'fraction_base':float(np.mean(np.asarray(chosen)==0)) if chosen else None,'elapsed_s':time.perf_counter()-start};records.append(row);out.write_text(json.dumps({'args':vars(args),'input':'PRIVILEGED_STATE_DIAGNOSTIC','records':records,'success_rate':float(np.mean([r['success'] for r in records]))},indent=2));print(json.dumps(row),flush=True)
    env.close();print('success_rate',np.mean([r['success'] for r in records]),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['pd','wm'],default='wm');p.add_argument('--model',default='full_future_seed17_pilot_v1');p.add_argument('--policy',default='bc_chunk_dev_v4');p.add_argument('--policy-checkpoint',default='policy_15000.pt');p.add_argument('--split',choices=['dev','sealed_test'],default='dev');p.add_argument('--episodes',type=int,default=8);p.add_argument('--steps',type=int,default=400);p.add_argument('--candidates',type=int,default=8);main(p.parse_args())
