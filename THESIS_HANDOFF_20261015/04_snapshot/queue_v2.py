"""Executed-action dynamics and queue-conditioned policy compensation.

The model learns physical transitions, not a second hidden command delay.
All counterfactual states in this module are predicted, never simulator queried.
"""
import argparse
import json
import time
from collections import deque
from pathlib import Path

import h5py
import numpy as np
import torch
from torch import nn

from common import ROOT, DATA, make_env, pack_obs, restore_demo, load_policy, read_episodes

V2 = ROOT / 'queue_v2'


class Dynamics(nn.Module):
    def __init__(self, width=128):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(30, width), nn.SiLU(), nn.Linear(width, width),
                                 nn.SiLU(), nn.Linear(width, 23))
        self.register_buffer('mean', torch.zeros(23))
        self.register_buffer('scale', torch.ones(23))

    def forward(self, x, actions):
        z = (x - self.mean) / self.scale
        outputs = []
        for t in range(actions.shape[1]):
            z = z + self.net(torch.cat([z, actions[:, t]], -1)) * .1
            outputs.append(z * self.scale + self.mean)
        return torch.stack(outputs, 1)


def build_data(split, horizon=6):
    xx, aa, yy = [], [], []
    for ep in read_episodes(split):
        n = len(ep['a']) - horizon + 1
        if n <= 0:
            continue
        ids = np.arange(0, n, 2)
        xx.append(ep['x'][ids])
        aa.append(np.stack([ep['a'][t:t+horizon] for t in ids]))
        yy.append(np.stack([ep['xn'][t:t+horizon] for t in ids]))
    # Old branch labels were produced from actual FIFO execution. Convert the
    # commanded sequence to its ACTUAL physical sequence before training.
    p = ROOT / 'data' / f'branches_{split}_delay2_shift_big100.npz'
    with np.load(p) as f:
        shape = f['a'].shape
        executed = np.zeros_like(f['a'])
        executed[:, :, 2:] = f['a'][:, :, :-2]
        xx.append(np.repeat(f['x'][:, None], shape[1], axis=1).reshape(-1, 23))
        aa.append(executed[:, :, :horizon].reshape(-1, horizon, 7))
        yy.append(f['y'][:, :, :horizon].reshape(-1, horizon, 23))
    return [np.concatenate(v).astype(np.float32) for v in (xx, aa, yy)]


def train(args):
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tr = [torch.from_numpy(v).to(device) for v in build_data('train', args.horizon)]
    dv = [torch.from_numpy(v).to(device) for v in build_data('dev', args.horizon)]
    model = Dynamics(args.width).to(device)
    model.mean.copy_(tr[0].mean(0))
    model.scale.copy_(tr[0].std(0).clamp_min(.02))
    weight = torch.ones(23, device=device)
    if args.task_weight:
        weight[:3] = 3
        weight[7:9] = 2
        weight[16:19] = 3
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    out = V2 / 'models' / args.run
    out.mkdir(parents=True, exist_ok=True)
    cfg = vars(args) | {'device': device, 'train_windows': len(tr[0]), 'dev_windows': len(dv[0]),
                        'action_semantics': 'ACTUALLY_EXECUTED', 'input': 'PRIVILEGED_STATE',
                        'parameters': sum(p.numel() for p in model.parameters())}
    (out/'config.json').write_text(json.dumps(cfg, indent=2), encoding='utf-8')
    best = float('inf'); logs = []; started = time.perf_counter()
    for step in range(1, args.updates+1):
        model.train()
        ids = torch.randint(len(tr[0]), (args.batch,), device=device)
        horizon = 1 if args.one_step else args.horizon
        pred = model(tr[0][ids], tr[1][ids, :horizon])
        loss = (((pred-tr[2][ids, :horizon])/model.scale).square()*weight).mean()
        opt.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 5); opt.step()
        if step % 250 == 0 or step == args.updates:
            model.eval(); errors = []; xyz = []
            with torch.no_grad():
                for j in range(0, len(dv[0]), 512):
                    p = model(dv[0][j:j+512], dv[1][j:j+512])
                    error = p - dv[2][j:j+512]
                    errors.append(((error/model.scale).square()*weight).mean().item())
                    xyz.append(error[:, :, :3].norm(dim=-1).mean().item())
            metric = float(np.mean(errors))
            row = {'step':step, 'loss':loss.item(), 'dev_loss':metric,
                   'eef_error_m':float(np.mean(xyz)), 'elapsed_s':time.perf_counter()-started}
            logs.append(row); print(json.dumps(row), flush=True)
            (out/'log.json').write_text(json.dumps(logs, indent=2), encoding='utf-8')
            if metric < best:
                best = metric
                torch.save({'state_dict': model.state_dict(), 'config': cfg, 'selected_step':step}, out/'model.pt')


def load_model(name):
    ck = torch.load(V2/'models'/name/'model.pt', map_location='cpu', weights_only=True)
    model = Dynamics(ck['config']['width']); model.load_state_dict(ck['state_dict']); model.eval()
    return model


def evaluate(args):
    torch.set_num_threads(2)
    torch.manual_seed(0)
    policy = load_policy(ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt')
    model = load_model(args.model) if args.method in ['wm', 'wm_corrected', 'wm_no_queue'] else None
    env = make_env(False)
    records=[]; traces=[]; out = V2/'results'/args.run
    out.mkdir(parents=True, exist_ok=True)
    names = json.loads((ROOT/'data/splits.json').read_text())['dev'][:args.episodes]
    with h5py.File(DATA,'r') as f:
        for i in range(args.episodes):
            seed = args.seed_start+i
            if args.initialization == 'demo_dev':
                obs = restore_demo(env, f['data'][names[i]])
                identity = names[i]
            else:
                np.random.seed(seed)
                # A fresh reset samples a fresh can placement; it does not
                # restore any demonstrated/test initial state.
                env.reset(); obs = env._get_observations(force_update=True)
                identity = f'fresh_{seed}'
            if hasattr(policy,'reset'): policy.reset()
            queue = deque([np.zeros(7,np.float32) for _ in range(args.delay)])
            rng = np.random.default_rng(seed+70000)
            success=False; peak=0; grasped=False; timings=[]; trace=[]; prev_pred=None
            residual=np.zeros(23,np.float32)
            xprev=None
            for step in range(args.steps):
                x = pack_obs(obs)
                base = policy.best(torch.from_numpy(x[None]))[0].numpy()
                tic=time.perf_counter(); predicted=x.copy()
                if args.method=='bc': action=base[0].copy()
                elif args.method=='shift': action=base[min(args.delay,7)].copy()
                elif args.method=='random_shift': action=base[rng.integers(0,8)].copy()
                elif args.method=='slow_bc': action=base[0].copy(); action[:6]*=.5
                elif args.method=='cv':
                    predicted=x if xprev is None else x+(x-xprev)*args.delay
                    action=policy.best(torch.from_numpy(predicted[None]))[0,0].numpy().copy()
                else:
                    if args.method=='wm_corrected' and prev_pred is not None:
                        residual=.8*residual+.2*(x-prev_pred)
                    prefix=np.asarray(list(queue),np.float32).reshape(-1,7)
                    if args.method=='wm_no_queue': prefix=np.zeros_like(prefix)
                    if len(prefix):
                        with torch.no_grad():
                            predicted=model(torch.from_numpy(x[None]),torch.from_numpy(prefix[None]))[0,-1].numpy()
                        if args.method=='wm_corrected':
                            predicted += np.clip(residual,-.015,.015)*args.delay
                    action=policy.best(torch.from_numpy(predicted[None]))[0,0].numpy().copy()
                timings.append(time.perf_counter()-tic)
                queue.append(action); executed=queue.popleft().copy()
                if args.noise: executed[:3] += rng.normal(0,args.noise,3)
                executed=np.clip(executed,-1,1)
                if model is not None:
                    with torch.no_grad():
                        prev_pred=model(torch.from_numpy(x[None]),torch.from_numpy(executed[None,None]))[0,0].numpy()
                trace.append({'step':step,'eef':x[:3].tolist(),'object':x[16:19].tolist(),
                              'future_eef':predicted[:3].tolist(),'action':action.tolist(),
                              'executed':executed.tolist(),'queue':np.asarray(queue).tolist()})
                xprev=x
                obs,_,_,_=env.step(executed)
                stages=env.staged_rewards(); peak=max(peak,float(max(stages))); grasped=grasped or stages[1]>.3
                if env._check_success(): success=True; break
            row={'identity':identity,'seed':seed,'success':success,'steps':step+1,
                 'peak_stage_reward':peak,'ever_grasped':bool(grasped),
                 'decision_ms':float(np.mean(timings)*1000)}
            records.append(row)
            if i < args.save_traces: traces.append({'record':row,'trace':trace})
            result={'args':vars(args),'input':'PRIVILEGED_STATE','records':records,
                    'success_rate':float(np.mean([r['success'] for r in records]))}
            (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(json.dumps(row),flush=True)
    (out/'traces.json').write_text(json.dumps(traces),encoding='utf-8')
    env.close(); print('success_rate',result['success_rate'],flush=True)


def cli():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
    t=sub.add_parser('train'); t.add_argument('--run',required=True); t.add_argument('--seed',type=int,default=17)
    t.add_argument('--updates',type=int,default=3000); t.add_argument('--batch',type=int,default=128)
    t.add_argument('--horizon',type=int,default=6); t.add_argument('--width',type=int,default=128)
    t.add_argument('--task-weight',action='store_true'); t.add_argument('--one-step',action='store_true')
    e=sub.add_parser('eval'); e.add_argument('--run',required=True); e.add_argument('--model',default='task_s17')
    e.add_argument('--method',choices=['bc','shift','random_shift','slow_bc','cv','wm','wm_corrected','wm_no_queue'],default='wm')
    e.add_argument('--delay',type=int,default=2); e.add_argument('--noise',type=float,default=0)
    e.add_argument('--episodes',type=int,default=12); e.add_argument('--steps',type=int,default=400)
    e.add_argument('--initialization',choices=['fresh','demo_dev'],default='demo_dev')
    e.add_argument('--seed-start',type=int,default=101000); e.add_argument('--save-traces',type=int,default=3)
    args=p.parse_args(); train(args) if args.command=='train' else evaluate(args)


if __name__=='__main__': cli()
