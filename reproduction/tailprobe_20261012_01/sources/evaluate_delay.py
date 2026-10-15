"""Delay-aware world-model control on PickPlaceCan."""
import argparse, hashlib, importlib.metadata, json, time
from collections import deque
from contextlib import ExitStack
from pathlib import Path
import h5py, numpy as np, torch
from common import ROOT, DATA, make_env, pack_obs, restore_demo, load_policy
from collect_branches import candidates
from world_model import WorldModel, DirectScore, score

def physical_cost(future, target, grasp_hint):
    eef=future[:,:,:3]; obj=future[:,:,16:19]
    target=torch.as_tensor(target,dtype=future.dtype,device=future.device)
    if grasp_hint:
        return ((obj-target)**2).sum(-1).sqrt().mean(-1)+.5*torch.relu(.86-obj[:,-1,2])
    return ((eef-obj)**2).sum(-1).sqrt().mean(-1)


def output_plan(args):
    split_names=json.loads((ROOT/'data/splits.json').read_text(encoding='utf-8'))[args.split]
    requested=getattr(args,'demos',None)
    output_dir=getattr(args,'output_dir',None)
    tracing=getattr(args,'trace',False)
    if args.episodes<1 or args.steps<1 or args.delay<0 or args.horizon<1:
        raise ValueError('episodes, steps and horizon must be positive; delay must be nonnegative.')
    if requested:
        if len(set(requested))!=len(requested) or any(n not in split_names for n in requested):
            raise ValueError('Every requested demo must be unique and belong to the selected split.')
        names=list(requested)
    else:
        names=split_names[:args.episodes]
    if (requested or tracing) and not output_dir:
        raise ValueError('--demos and --trace require an explicit --output-dir for diagnostic results.')
    tag=f'{args.method}_{args.split}_d{args.delay}'
    if args.method=='wm':
        tag+=f'_{args.candidate_mode}_fb{args.fallback}_fbi{args.fallback_index}_gm{args.gate_margin:g}'
    if args.method=='bc_shift' and args.shift_index is not None:
        tag+=f'_k{args.shift_index}'
    if args.noise:
        tag+=f'_noise{args.noise:g}'
    if args.score_only:
        tag+='_score'
    directory=Path(output_dir).resolve() if output_dir else ROOT/'models'/args.model
    out=directory/f'delay_{tag}.json'
    traces={name:directory/'traces'/f'{tag}__{name}.jsonl' for name in names} if tracing else {}
    for path in [out,*traces.values()]:
        if path.exists():
            raise FileExistsError(f'Refusing to overwrite existing result: {path}')
        for parent in path.parents:
            if parent.exists() and not parent.is_dir():
                raise NotADirectoryError(str(parent))
    return names,out,traces


def provenance(args,cfg):
    files=[DATA,ROOT/'data/splits.json',ROOT/'policy'/args.policy/args.policy_checkpoint,
           ROOT/'models'/args.model/'model.pt']
    files.extend(ROOT/name for name in ['evaluate_delay.py','common.py','world_model.py','collect_branches.py'])
    if cfg.get('dataset'):
        files.extend(ROOT/'data'/f'branches_{split}_{cfg["dataset"]}.npz' for split in ['train','dev'])
    return {'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in files if p.is_file()},
            'packages':{name:importlib.metadata.version(name)
                        for name in ['torch','numpy','robosuite','mujoco','h5py']},
            'trace_note':'Diagnostic logging adds runtime overhead. Predictions assume constant future candidate commands; actual control replans each step.'}


def run(args):
    names,out,trace_paths=output_plan(args)
    torch.set_num_threads(2)
    policy=load_policy(ROOT/'policy'/args.policy/args.policy_checkpoint)
    ck=torch.load(ROOT/'models'/args.model/'model.pt',map_location='cpu',weights_only=True)
    cfg=ck['config']
    # Keep the direct-score ablation on the same deployment path.  It has no
    # predicted state, so it is evaluated with learned score only; the full
    # method additionally exposes a predicted future state to the planner.
    if cfg.get('method') == 'direct':
        model=DirectScore(cfg['dim'],cfg.get('horizon',args.horizon),cfg['width'])
    else:
        model=WorldModel(cfg['dim'],cfg['width'],cfg.get('future_only',False))
    model.load_state_dict(ck['state_dict']); model.eval()
    run_provenance=provenance(args,cfg)
    out.parent.mkdir(parents=True,exist_ok=True)
    records=[]
    with ExitStack() as resources:
      result_file=resources.enter_context(out.open('x',encoding='utf-8'))
      trace_files={}
      for name,path in trace_paths.items():
          path.parent.mkdir(parents=True,exist_ok=True)
          trace_files[name]=resources.enter_context(path.open('x',encoding='utf-8'))
      def save_result(status):
          payload={'args':vars(args),'input':'PRIVILEGED_STATE_DIAGNOSTIC',
                   'status':status,'resolved_demos':names,'records':records,
                   'success_rate':float(np.mean([r['success'] for r in records])) if records else None,
                   'trace_schema_version':1,'trace_files':{n:p.relative_to(out.parent).as_posix() for n,p in trace_paths.items()},
                   'provenance':run_provenance}
          result_file.seek(0); result_file.write(json.dumps(payload,indent=2,allow_nan=False))
          result_file.truncate(); result_file.flush()
      save_result('running')
      env=make_env(False); resources.callback(env.close)
      target=env.target_bin_placements[env.object_to_id['can']].astype(np.float32)
      f=resources.enter_context(h5py.File(DATA,'r'))
      for name in names:
        obs=restore_demo(env,f['data'][name]);
        if hasattr(policy,'reset'):policy.reset()
        queue=deque([np.zeros(7,np.float32) for _ in range(args.delay)],maxlen=args.delay+1)
        rng=np.random.default_rng(70000+int(name.split('_')[1])); crng=np.random.default_rng(170000+int(name.split('_')[1]))
        success=False; peak=0.; grasped=False; selected_ids=[]; fallback_ids=[]; decision=[]; started=time.perf_counter()
        for step in range(args.steps):
          x=pack_obs(obs); base=policy.best(torch.from_numpy(x[None]))[0].numpy()
          tracing=name in trace_files
          if tracing:
              queue_before=np.asarray(list(queue),np.float32).reshape(-1,7).copy()
              stages_before=np.asarray(env.staged_rewards()).copy()
          tic=time.perf_counter()
          if args.method=='bc':
            new_action=base[0].copy(); selected=0
          elif args.method=='bc_shift':
            shift=min(args.shift_index if args.shift_index is not None else args.delay,base.shape[0]-1);new_action=base[shift].copy();selected=shift
          else:
            if args.candidate_mode=='shift':
                nshift=min(args.candidates,base.shape[0]); aa=np.asarray([np.repeat(base[k:k+1],base.shape[0],axis=0) for k in range(nshift)],np.float32)
            else:
                aa=candidates(base,crng,args.candidates)
            seqs=[]
            for candidate in aa:
              prefix=np.asarray(list(queue),np.float32).reshape(-1,7)
              # Only the first command is committed before the next observation.
              # Repeat it in imagination so the model/planner interface matches
              # the receding-horizon execution semantics.
              repeated=np.repeat(candidate[0:1],args.horizon,axis=0)
              seq=np.concatenate([prefix,repeated],axis=0)[:args.horizon]
              if len(seq)<args.horizon: seq=np.concatenate([seq,np.repeat(candidate[0:1],args.horizon-len(seq),axis=0)],axis=0)
              seqs.append(seq)
            xb=torch.from_numpy(np.repeat(x[None],len(seqs),axis=0)); ab=torch.from_numpy(np.asarray(seqs,np.float32))
            with torch.no_grad():
              future,readouts=model(xb,ab)
              holding=bool(x[18]>.88 and np.linalg.norm(x[:3]-x[16:19])<.10)
              # Candidate effect starts after the FIFO queue has drained.
              if future is None and not args.score_only:
                  raise ValueError('DirectScore ablation requires --score-only because it has no predicted physical state')
              cost=physical_cost(future[:,min(args.delay,args.horizon-1):],target,holding) if future is not None else torch.zeros(len(seqs))
              if readouts is not None:
                  learned=score(readouts,args.risk_weight)
                  if args.score_only: cost=-learned
                  else: cost=cost-args.readout_weight*learned
              selected=int(cost.argmin())
              fallback_idx=0 if args.fallback=='base' else min(args.fallback_index if args.fallback_index is not None else args.delay,args.candidates-1)
              if not 0<=fallback_idx<len(seqs):
                  raise ValueError('Fallback index is outside the actual candidate set.')
              raw_selected=selected
              # The learned model may override the known delay-compensating
              # action only when its predicted score improves by a margin.
              if selected != fallback_idx and float(cost[fallback_idx] - cost[selected]) < args.gate_margin:
                  selected=fallback_idx
            new_action=aa[selected,0].copy()
            fallback_ids.append(fallback_idx)
          if tracing: submitted_action=new_action.copy()
          selected_ids.append(selected); decision.append(time.perf_counter()-tic); queue.append(new_action); executed=queue.popleft()
          if tracing: executed_before_noise=executed.copy()
          if args.noise: executed[:3]+=rng.normal(0,args.noise,3)
          applied=np.clip(executed,-1,1)
          obs,_,_,_=env.step(applied); stages=env.staged_rewards(); peak=max(peak,float(max(stages))); grasped=grasped or stages[1]>.3
          success=bool(env._check_success())
          if tracing:
              trace={'demo':name,'step':step+1,'state_before':x.tolist(),'state_after':pack_obs(obs).tolist(),
                     'queue_before':queue_before.tolist(),'base_chunk':base.tolist(),
                     'submitted_action':submitted_action.tolist(),'executed_action_before_noise':executed_before_noise.tolist(),
                     'executed_action':applied.tolist(),'stages_before':stages_before.tolist(),
                     'stages_after':np.asarray(stages).tolist(),'success_after':success,
                     'target_position':target.tolist(),'selected':selected,'decision_ms':decision[-1]*1000}
              if args.method=='wm':
                  probabilities=readouts.sigmoid().numpy()
                  trace.update(candidate_actions=aa[:,0].tolist(),model_sequences=np.asarray(seqs).tolist(),
                               predicted_states=future.numpy().tolist() if future is not None else None,
                               predicted_progress=probabilities[:,:,0].tolist(),predicted_risk=probabilities[:,:,1].tolist(),
                               learned_scores=learned.numpy().tolist(),costs=cost.numpy().tolist(),
                               raw_selected=raw_selected,fallback_index=fallback_idx,
                               raw_advantage=float(cost[fallback_idx]-cost[raw_selected]),
                               selected_advantage=float(cost[fallback_idx]-cost[selected]),
                               overrode_fallback=selected!=fallback_idx,gate_blocked=raw_selected!=selected)
              trace_files[name].write(json.dumps(trace,allow_nan=False)+'\n')
          if success: break
        row={'demo':name,'success':success,'steps':step+1,'peak_stage_reward':peak,'ever_grasped':bool(grasped),'delay':args.delay,'fraction_base_selected':float(np.mean(np.asarray(selected_ids)==0)),'mean_decision_ms':float(np.mean(decision)*1000),'elapsed_s':time.perf_counter()-started}
        row['selection_counts']={str(k):selected_ids.count(k) for k in sorted(set(selected_ids))}
        if fallback_ids:
            fraction=float(np.mean(np.asarray(selected_ids)==np.asarray(fallback_ids)))
            row.update(fraction_fallback_selected=fraction,fraction_override=1-fraction)
        if tracing: trace_files[name].flush()
        records.append(row); save_result('running'); print(json.dumps(row),flush=True)
      save_result('complete')
    print('success_rate',np.mean([r['success'] for r in records]),flush=True)
    return out

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--method',choices=['bc','bc_shift','wm'],default='wm');p.add_argument('--model',default='full_future_bc_v4');p.add_argument('--policy',default='bc_chunk_dev_v4');p.add_argument('--policy-checkpoint',default='policy_15000.pt');p.add_argument('--split',choices=['dev','sealed_test'],default='dev');p.add_argument('--episodes',type=int,default=8);p.add_argument('--steps',type=int,default=400);p.add_argument('--delay',type=int,default=2);p.add_argument('--shift-index',type=int,default=None);p.add_argument('--fallback-index',type=int,default=None);p.add_argument('--candidates',type=int,default=6);p.add_argument('--horizon',type=int,default=8);p.add_argument('--noise',type=float,default=0.);p.add_argument('--risk-weight',type=float,default=.5);p.add_argument('--readout-weight',type=float,default=.02);p.add_argument('--gate-margin',type=float,default=.0);p.add_argument('--fallback',choices=['base','shift'],default='base');p.add_argument('--score-only',action='store_true');p.add_argument('--candidate-mode',choices=['random','shift'],default='random')
 p.add_argument('--demos',nargs='+',help='Specific demos in --split; overrides --episodes and requires --output-dir.')
 p.add_argument('--output-dir',help='Separate output directory. Existing result and trace files are never overwritten.')
 p.add_argument('--trace',action='store_true',help='Save per-step decision JSONL; requires --output-dir.')
 run(p.parse_args())
