import argparse,json,time
import h5py
import numpy as np
import torch
from common import ROOT,DATA,make_env,pack_obs,restore_demo,load_policy
from adaptive_model import ResponseWorldModel,ResidualAdapter,full_obs


def main(args):
    torch.set_num_threads(2)
    policy=load_policy(ROOT/'policy'/args.policy/args.policy_checkpoint)
    model=None
    linear_world=None
    if args.method=='linear_world':
        z=np.load(ROOT/'models'/args.model/'linear_model.npz');linear_world=z['coef']
    if args.method=='adaptive':
        ck=torch.load(ROOT/'models'/args.model/'model.pt',map_location='cpu',weights_only=True)
        model=ResponseWorldModel(ck['config']['dim'],ck['config']['width'],ck['config'].get('affine',False));model.load_state_dict(ck['state_dict']);model.eval()
        for parameter in model.parameters():parameter.requires_grad_(False)
    env=make_env(False);records=[]
    names=json.loads((ROOT/'data/splits.json').read_text())[args.split][:args.episodes]
    directory=ROOT/'evaluation'/args.run;directory.mkdir(parents=True,exist_ok=True)
    out=directory/f'{args.split}_bias{args.bias}.json'
    with h5py.File(DATA,'r') as f:
        for name in names:
            obs=restore_demo(env,f['data'][name])
            if hasattr(policy,'reset'):policy.reset()
            adapter=ResidualAdapter(model,args.rate,args.ridge) if args.method=='adaptive' else None
            rng=np.random.default_rng(60000+int(name.split('_')[1]))
            physical_bias=rng.choice([-1.,1.],3).astype(np.float32)*args.bias
            success=False;peak=0.;grasped=False;times=[];errors=[];start=time.perf_counter()
            previous=None;linear_bias=np.zeros(3,np.float32)
            for step in range(args.steps):
                tic=time.perf_counter();state=full_obs(obs)
                if adapter:adapter.observe(state)
                nominal=policy.best(torch.from_numpy(pack_obs(obs)[None]))[0,0].numpy()
                if adapter:
                    action=adapter.command(state,nominal)
                    estimated=adapter.bias.copy()
                elif args.method=='linear_world':
                    # Linearized world model predicts the next EEF response; use its action
                    # Jacobian to estimate the persistent action-channel offset.
                    if previous is not None:
                        p,c=previous; row=np.concatenate([p,c,[1]])
                        jac=linear_world[37:40,:3]
                        residual=state[:3]-row@linear_world[:,:3]
                        delta=np.linalg.solve(jac.T@jac+args.ridge*np.eye(3),jac.T@residual)
                        linear_bias=np.clip((1-args.rate)*linear_bias+args.rate*delta,-.4,.4)
                    action=nominal.copy();action[:3]-=linear_bias;action=np.clip(action,-1,1)
                    previous=(state.copy(),action.copy());estimated=linear_bias.copy()
                elif args.method=='linear':
                    if previous is not None:
                        p,c=previous
                        discrepancy=(state[:3]-p[:3])/.05-c[:3]
                        linear_bias=np.clip((1-args.rate)*linear_bias+args.rate*discrepancy,-.4,.4)
                    action=nominal.copy();action[:3]-=linear_bias
                    action=np.clip(action,-1,1);previous=(state.copy(),action.copy());estimated=linear_bias.copy()
                else:action=nominal.copy();estimated=np.zeros(3)
                times.append(time.perf_counter()-tic)
                injected=physical_bias if step>=args.onset else np.zeros(3)
                errors.append(float(np.linalg.norm(estimated-injected)))
                executed=action.copy();executed[:3]+=injected
                obs,*_=env.step(np.clip(executed,-1,1))
                stages=env.staged_rewards();peak=max(peak,float(max(stages)));grasped=grasped or stages[1]>.3
                if env._check_success():success=True;break
            row={'demo':name,'success':success,'steps':step+1,'peak_stage_reward':peak,'ever_grasped':bool(grasped),
                 'bias':physical_bias.tolist(),'mean_bias_error_after_onset':float(np.mean(errors[args.onset:])) if len(errors)>args.onset else None,
                 'last_estimate':estimated.tolist(),'mean_decision_ms':float(np.mean(times)*1000),'elapsed_s':time.perf_counter()-start}
            records.append(row)
            out.write_text(json.dumps({'args':vars(args),'input':'PRIVILEGED_STATE_DIAGNOSTIC','records':records,
                                      'success_rate':float(np.mean([r['success'] for r in records]))},indent=2))
            print(json.dumps(row),flush=True)
    env.close();print('success_rate',np.mean([r['success'] for r in records]),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--method',choices=['bc','adaptive','linear_world','linear'],default='adaptive')
    p.add_argument('--model',default='response_seed17_v2');p.add_argument('--run',default='adaptive_seed17_v2')
    p.add_argument('--policy',default='bc_chunk_dev_v4');p.add_argument('--policy-checkpoint',default='policy_15000.pt')
    p.add_argument('--split',choices=['dev','sealed_test'],default='dev');p.add_argument('--episodes',type=int,default=8)
    p.add_argument('--steps',type=int,default=400);p.add_argument('--bias',type=float,default=.2)
    p.add_argument('--onset',type=int,default=20);p.add_argument('--rate',type=float,default=.2);p.add_argument('--ridge',type=float,default=1e-5)
    main(p.parse_args())
