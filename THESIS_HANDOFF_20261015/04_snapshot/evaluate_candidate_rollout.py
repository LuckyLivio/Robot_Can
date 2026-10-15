"""Frozen-world-model dev probe: repeated command versus one command + BC tail.

BC-tail planning uses predicted states only. Actual execution still commits one
command and replans with the WM after every observation. The BC tail is an
explicit planning approximation, not a claim of exact future WM behavior.
"""
import argparse
from collections import deque
from contextlib import ExitStack
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

import h5py
import numpy as np
import torch

from common import ROOT, DATA, ChunkPolicy, load_policy, make_env, pack_obs, restore_demo
from world_model import WorldModel, score


def write_json(path, value):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)


def load_frozen(model_name='headcal_20261012_01_calibrated_s17'):
    checkpoint = torch.load(ROOT/'models'/model_name/'model.pt', map_location='cpu', weights_only=True)
    cfg = checkpoint['config']
    if cfg.get('method') != 'full' or not cfg.get('future_only'):
        raise ValueError('This probe requires the full future_only world model')
    model = WorldModel(cfg['dim'], cfg['width'], True)
    model.load_state_dict(checkpoint['state_dict']); model.eval(); model.requires_grad_(False)
    policy = load_policy(ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt')
    if type(policy) is not ChunkPolicy:
        raise ValueError('Only the original stateless chunk policy is supported')
    policy.requires_grad_(False)
    return model, policy, cfg


@torch.no_grad()
def imagine(model, policy, state, queue, commands, mode, horizon=8, tail_index=2):
    """Plan K branches without receiving an environment or future observations."""
    if mode not in ('repeat', 'bc_tail') or horizon < 1:
        raise ValueError('Invalid rollout mode or horizon')
    if not isinstance(model, WorldModel) or not model.future_only or type(policy) is not ChunkPolicy:
        raise ValueError('Unsupported model or stateful policy')
    if not 0 <= tail_index < policy.horizon:
        raise ValueError('BC tail index is outside the action chunk')
    x = torch.as_tensor(np.repeat(np.asarray(state, np.float32)[None], len(commands), axis=0))
    candidate = torch.as_tensor(np.asarray(commands, np.float32))
    pending = [torch.as_tensor(np.repeat(a[None],len(commands),axis=0))
               for a in np.asarray(queue,np.float32).reshape(-1,7)]
    if x.ndim != 2 or x.shape[1] != 23 or candidate.shape != (len(x),7):
        raise ValueError('Invalid candidate/state shape')
    if not all(torch.isfinite(value).all() for value in (x,candidate,*pending)):
        raise ValueError('Non-finite planning input')
    if any(torch.any(value.abs()>1) for value in (candidate,*pending)):
        raise ValueError('Probe expects the bounded BC commands and FIFO contents')
    if mode == 'repeat':
        submitted = candidate[:,None].expand(-1,horizon,-1).clone()
        prefix = torch.stack(pending,1) if pending else torch.empty((len(x),0,7))
        executed = torch.cat([prefix,submitted],1)[:,:horizon]
        future,logits = model(x,executed)
    else:
        z = (x-model.mean)/model.scale
        hidden = model.init(z)
        states,readouts,executions,submissions = [],[],[],[]
        for step in range(horizon):
            # At imagined step 0 only the current candidate differs. Later
            # commands come from BC k=2 at the corresponding predicted state.
            command = candidate if step == 0 else policy.best(states[-1])[:,tail_index]
            submissions.append(command)
            pending.append(command)
            action = pending.pop(0).clamp(-1,1)
            executions.append(action)
            # Preserve GRU memory through the whole horizon, exactly as forward().
            hidden = model.cell(torch.cat([z,action],-1),hidden)
            z = z+model.delta(hidden)*.1
            states.append(z*model.scale+model.mean)
            readouts.append(model.labels(z))
        future,logits = torch.stack(states,1),torch.stack(readouts,1)
        executed,submitted = torch.stack(executions,1),torch.stack(submissions,1)
    learned = score(logits,.5)
    costs = -learned
    raw = int(costs.argmin())
    selected = 2 if raw != 2 and float(costs[2]-costs[raw]) < .02 else raw
    return {'future':future,'logits':logits,'scores':learned,'costs':costs,
            'executed':executed,'submitted':submitted,'raw_selected':raw,'selected':selected,
            'raw_advantage':float(costs[2]-costs[raw]),
            'selected_advantage':float(costs[2]-costs[selected])}


def run(args):
    if args.steps != 400 or args.episodes < 1:
        raise ValueError('This frozen dev probe uses a 400-step budget')
    all_names = json.loads((ROOT/'data/splits.json').read_text())['dev']
    names = args.demos if args.demos else all_names[:args.episodes]
    if len(set(names)) != len(names) or any(n not in all_names for n in names):
        raise ValueError('Only unique dev parents are allowed')
    trace_names = set(args.trace_demos or [])
    if not trace_names.issubset(names):
        raise ValueError('Traced parents must belong to the evaluated dev set')
    directory = Path(args.output_dir).resolve()
    if directory.exists():
        raise FileExistsError(f'Refusing to overwrite an existing rollout probe: {directory}')
    torch.set_num_threads(2)
    model,policy,cfg = load_frozen(args.model)
    source_paths = [DATA,ROOT/'data/splits.json',ROOT/'models'/args.model/'model.pt',
                    ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt',ROOT/'evaluate_candidate_rollout.py',
                    ROOT/'world_model.py',ROOT/'common.py']
    provenance = {'sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
                  'packages':{p:importlib.metadata.version(p) for p in ('torch','numpy','mujoco','robosuite','h5py')}}
    directory.mkdir(parents=True,exist_ok=False)
    records = []
    with ExitStack() as resources:
        result_file = resources.enter_context((directory/'results.json').open('x',encoding='utf-8'))
        traces = {}
        for name in sorted(trace_names):
            trace_path = directory/'traces'/f'{name}.jsonl'
            trace_path.parent.mkdir(exist_ok=True)
            traces[name] = resources.enter_context(trace_path.open('x',encoding='utf-8'))
        configuration = {'split':'dev','method':'wm','model':args.model,'rollout_mode':args.mode,
                         'policy':'bc_chunk_dev_v4','policy_checkpoint':'policy_15000.pt',
                         'delay':2,'horizon':8,'candidates':4,'candidate_mode':'shift','fallback':'shift',
                         'fallback_index':2,'gate_margin':.02,'risk_weight':.5,'noise':0.,'score_only':True,'steps':400,
                         'tail_policy_index':2,'resolved_demos':names}
        def save(status):
            payload = {'status':status,'args':vars(args),'configuration':configuration,'records':records,
                       'success_rate':float(np.mean([r['success'] for r in records])) if records else None,
                       'input':'PRIVILEGED_STATE_DIAGNOSTIC','trace_schema_version':1,
                       'trace_files':{n:f'traces/{n}.jsonl' for n in traces},'provenance':provenance}
            result_file.seek(0); result_file.write(json.dumps(payload,indent=2,allow_nan=False))
            result_file.truncate(); result_file.flush()
        save('running')
        env = make_env(False); resources.callback(env.close)
        data = resources.enter_context(h5py.File(DATA,'r'))
        for name in names:
            obs = restore_demo(env,data['data'][name])
            queue = deque([np.zeros(7,np.float32) for _ in range(2)])
            selections,decision_times = [],[]
            success=False;peak=0.;grasped=False;started=time.perf_counter()
            for step in range(args.steps):
                state = pack_obs(obs)
                base = policy.best(torch.from_numpy(state[None]))[0].numpy()
                pending = np.asarray(queue,np.float32).reshape(-1,7).copy()
                if name in traces: stages_before = np.asarray(env.staged_rewards()).copy()
                tic=time.perf_counter()
                plan = imagine(model,policy,state,pending,base[:4],args.mode)
                selected=plan['selected'];command=base[selected].copy()
                decision_times.append(time.perf_counter()-tic); selections.append(selected)
                queue.append(command);action=np.clip(queue.popleft(),-1,1)
                obs,*_=env.step(action)
                stages=env.staged_rewards();peak=max(peak,float(max(stages)));grasped=grasped or stages[1]>.3
                success=bool(env._check_success())
                if name in traces:
                    probabilities=plan['logits'].sigmoid().numpy()
                    trace={'demo':name,'step':step+1,'state_before':state.tolist(),'state_after':pack_obs(obs).tolist(),
                           'queue_before':pending.tolist(),'base_chunk':base.tolist(),'candidate_actions':base[:4].tolist(),
                           'submitted_action':command.tolist(),'executed_action':action.tolist(),
                           'model_sequences':plan['executed'].numpy().tolist(),'imagined_submissions':plan['submitted'].numpy().tolist(),
                           'predicted_states':plan['future'].numpy().tolist(),'predicted_progress':probabilities[:,:,0].tolist(),
                           'predicted_risk':probabilities[:,:,1].tolist(),'learned_scores':plan['scores'].numpy().tolist(),
                           'selected':selected,'raw_selected':plan['raw_selected'],'fallback_index':2,
                           'raw_advantage':plan['raw_advantage'],'selected_advantage':plan['selected_advantage'],
                           'overrode_fallback':selected!=2,'stages_before':stages_before.tolist(),
                           'stages_after':np.asarray(stages).tolist(),'success_after':success,'decision_ms':decision_times[-1]*1000}
                    traces[name].write(json.dumps(trace,allow_nan=False)+'\n')
                if success:break
            row={'demo':name,'success':success,'steps':step+1,'peak_stage_reward':peak,'ever_grasped':bool(grasped),
                 'selection_counts':{str(k):selections.count(k) for k in sorted(set(selections))},
                 'fraction_fallback_selected':float(np.mean(np.asarray(selections)==2)),
                 'fraction_override':float(np.mean(np.asarray(selections)!=2)),
                 'mean_decision_ms':float(np.mean(decision_times)*1000),'elapsed_s':time.perf_counter()-started}
            if name in traces:traces[name].flush()
            records.append(row);save('running');print(json.dumps(row),flush=True)
        save('complete')
    print(json.dumps({'complete':args.mode,'success':sum(r['success'] for r in records),'episodes':len(records)}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['repeat','bc_tail'],required=True)
    parser.add_argument('--model',default='headcal_20261012_01_calibrated_s17')
    parser.add_argument('--episodes',type=int,default=30)
    parser.add_argument('--steps',type=int,default=400)
    parser.add_argument('--demos',nargs='+')
    parser.add_argument('--trace-demos',nargs='+')
    parser.add_argument('--output-dir',required=True)
    run(parser.parse_args())
