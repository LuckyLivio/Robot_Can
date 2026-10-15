"""Freeze all seeds, losses, comparisons and evaluation jobs before running."""
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(RUN))
import numpy as np
import torch
from train_suite import construct,write_json,tensor_hash
from common import DATA

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

for file in ('train_suite.py','evaluate_suite.py','run_suite.py','register_suite.py'):
    ast.parse((RUN/file).read_text(encoding='utf-8'))
dataset='queuepair_20261012_01_real';seeds=[17,23,41];methods=['full','plain','direct','prediction_only']
splits=json.loads((ROOT/'data/splits.json').read_text());data_info={}
for split,groups,parents in [('train',160,20),('dev',64,8)]:
    with np.load(ROOT/'data'/f'branches_{split}_{dataset}.npz') as data:
        unique=sorted(set(data['parent'].tolist()))
        assert len(unique)==parents and set(unique).issubset(splits[split])
        assert data['x'].shape==(groups,23) and data['a'].shape==(groups,4,8,7)
        assert data['y'].shape==(groups,4,8,23) and data['labels'].shape==(groups,4,8,2)
        assert data['queue'].shape==(groups,2,7)
        for key in ('x','a','y','labels','queue'):assert np.isfinite(data[key]).all(),key
        assert np.max(np.abs(data['a']))<=1
        assert np.array_equal(data['a'][:,:,:2],np.repeat(data['queue'][:,None],4,axis=1))
        assert np.array_equal(data['y'][:,:,:2],np.repeat(data['y'][:,0:1,:2],4,axis=1))
        data_info[split]={'parents':unique,'groups':groups,'shape_a':list(data['a'].shape),'sha256':sha(ROOT/'data'/f'branches_{split}_{dataset}.npz')}
assert not set(data_info['train']['parents'])&set(data_info['dev']['parents'])
assert not set(splits['train'])&set(splits['dev'])
counts={};initial={}
for seed in seeds:
    initial[seed]={}
    for method in methods:
        torch.manual_seed(seed);model=construct(method,251 if method=='direct' else 128)
        counts[method]=sum(p.numel() for p in model.parameters())
        initial[seed][method]=tensor_hash(model.state_dict())
    assert initial[seed]['full']==initial[seed]['plain']==initial[seed]['prediction_only']
assert abs(counts['direct']/counts['full']-1)<.001

jobs=[];python=str(ROOT/'.venv/Scripts/python.exe')
def command(script,*args):return [python,'-X','utf8','-B','-u',str(RUN/script),*map(str,args)]
for seed in seeds:
    for method in methods:
        name=f'{RUN.name}_{method}_s{seed}'
        assert not (ROOT/'models'/name).exists()
        jobs.append({'id':f'train_{method}_s{seed}','phase':'train','method':method,'seed':seed,'model':name,
                     'command':command('train_suite.py','--run-dir',RUN,'--method',method,'--seed',seed),
                     'outputs':[f'models/{name}/model.pt',f'models/{name}/training_complete.json']})
    tag=f'{RUN.name}_head_s{seed}'
    jobs.append({'id':f'train_head_pair_s{seed}','phase':'train','method':'head_pair','seed':seed,
                 'command':command('train_suite.py','--run-dir',RUN,'--method','calibrate','--seed',seed),
                 'outputs':[f'reproduction/{tag}/training_complete.json',f'models/{tag}_control_s{seed}/model.pt',f'models/{tag}_calibrated_s{seed}/model.pt']})

settings=[]
for seed in seeds:
    for method in methods+['head_control','calibrated','no_risk_score','no_gate','horizon4']:
        if method in ('head_control','calibrated'):
            arm='control' if method=='head_control' else method
            model=f'{RUN.name}_head_s{seed}_{arm}_s{seed}'
        else:model=f'{RUN.name}_{method if method in methods else "full"}_s{seed}'
        settings.append({'method':method,'seed':seed,'model':model})
for k in range(3):settings.append({'method':f'bc_k{k}','seed':None,'model':f'{RUN.name}_full_s17'})
for setting in settings:
    method=setting['method'];seed=setting['seed']
    for noise in (0.,.05):
        noise_name='clean' if noise==0 else 'noise005'
        identity=f'{method}_s{seed}_{noise_name}' if seed is not None else f'{method}_{noise_name}'
        output_dir=RUN/'evaluations'/identity
        bc=method.startswith('bc_k');pred=method=='prediction_only'
        horizon=4 if method=='horizon4' else 8
        gate=0 if method=='no_gate' else .02
        risk=0 if method=='no_risk_score' else .5
        args=['--method','bc_shift' if bc else 'wm','--model',setting['model'],'--policy','bc_chunk_dev_v4',
              '--split','dev','--episodes',30,'--steps',400,'--delay',2,'--horizon',horizon,'--candidates',4,
              '--candidate-mode','shift','--fallback','shift','--fallback-index',2,'--gate-margin',gate,
              '--risk-weight',risk,'--noise',noise,'--output-dir',output_dir]
        if pred:args+=['--readout-weight',0]
        elif not bc:args+=['--score-only']
        if bc:args+=['--shift-index',int(method[-1])]
        tag=f'bc_shift_dev_d2_k{method[-1]}' if bc else f'wm_dev_d2_shift_fbshift_fbi2_gm{gate:g}'
        if noise:tag+=f'_noise{noise:g}'
        if not bc and not pred:tag+='_score'
        result=output_dir/f'delay_{tag}.json'
        jobs.append({'id':f'eval_{identity}','phase':'evaluate',**setting,'noise':noise,'horizon':horizon,'risk_weight':risk,'gate_margin':gate,
                     'command':command('evaluate_suite.py',*args),'outputs':[result.relative_to(ROOT).as_posix()]})
write_json(RUN/'jobs.json',jobs)
sources=[DATA,ROOT/'data/splits.json',ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt']
sources += [ROOT/'data'/f'branches_{split}_{dataset}.{ext}' for split in ('train','dev') for ext in ('npz','json')]
sources += [ROOT/name for name in ('world_model.py','common.py','collect_branches.py','evaluate_delay.py','calibrate_score_head.py')]
sources += [RUN/name for name in ('train_suite.py','evaluate_suite.py','run_suite.py','register_suite.py')]
protocol={'status':'frozen_before_training_and_closed_loop_results','seeds':seeds,'dataset':dataset,'data':data_info,
          'train_methods':methods,'parameters':counts,'initialization_hashes':initial,'training_updates':3000,'batch_groups':16,
          'optimizer':'Adam lr=0.0003, clip=10, float32, deterministic algorithms, highest matmul precision',
          'minibatches':'CPU torch.Generator(seed), 3000x16 indices; identical across all methods within a seed; independent of architecture RNG.',
          'model_initialization':'Full, Plain and prediction-only share initial tensors within seed. Direct matches total parameter count to within 0.1%.',
          'losses':{'full':'state MSE + progress BCE + 0.5 risk BCE + 0.2 rank',
                    'plain':'state MSE + progress BCE + 0.5 risk BCE',
                    'direct':'progress BCE + 0.5 risk BCE + 0.2 rank; no future-state output or state MSE',
                    'prediction_only':'state MSE only; unused random label head frozen and ignored at deployment',
                    'head_control':'additional 3000 head-only updates on selected Full; original label and ranking objective',
                    'calibrated':'same additional 3000 head-only updates and batches; add weight1 true-future-state label loss'},
          'selection':'Check every250 steps. Full/Plain/Direct: minimum dev branch score regret; prediction-only: minimum dev normalized state MSE. Earliest exact tie. Head arms retain existing predicted-score-regret selection. Never select from closed-loop successes.',
          'evaluation_settings':settings,'evaluation_workers':3,'closed_loop_split':'dev','demos':splits['dev'],'noise_std':[0.,.05],
          'delay':2,'horizon':8,'candidates':4,'fallback_index':2,'gate_margin':.02,'risk_weight':.5,'steps':400,
          'candidate_rollout':'Repeat constant candidate submission; commit one real command then replan each observation.',
          'paired_noise':'numpy default_rng(70000+demo_number); same per-step positional Gaussian draws within condition for every method.',
          'inference_ablations':{'no_risk_score':'Same Full checkpoint, risk_weight=0 only; training risk supervision remains. Isolates risk term at decision time.',
                                 'no_gate':'Same Full checkpoint, gate_margin=0; always choose score argmax.',
                                 'horizon4':'Same Full checkpoint, prediction horizon=4 rather than8; all candidates and other parameters unchanged.'},
          'prediction_only_caveat':'Use existing physical_cost on predicted future state, with known bin geometry and holding heuristic. Gate margin0.02 is in distance-cost units, not learned-score units; this is a label-free alternative controller, not a strict one-factor score-scale ablation. No random-head use.',
          'fairness_scope':'Matched data, per-seed batches, candidate set and common learned-score controller; Full/Plain share architecture; Direct has matched parameter count, not identical FLOPs. Head calibration has extra training; compare primarily with head_control, not only raw Full.',
          'primary_metric':'Per-seed success/30 in each condition, paired episode differences versus BC k2 and matched ablations. Average all three seeds, never choose best seed.',
          'uncertainty':'Paired bootstrap over parent episodes per seed; crossed seed and parent bootstrap for mean paired difference. Repeated seeds/conditions are not independent task samples; n=3 seed uncertainty is limited. Descriptive development intervals.',
          'no_tuning':'No hyperparameter or seed selection after outcomes; no sealed_test or new confirmation testing in this suite.',
          'input':'23D privileged simulator state including object state; not vision-only.',
          'job_count':len(jobs),'evaluation_jobs':sum(j['phase']=='evaluate' for j in jobs),'evaluation_episode_records':30*sum(j['phase']=='evaluate' for j in jobs),
          'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sources},'jobs_sha256':sha(RUN/'jobs.json'),
          'packages':{p:importlib.metadata.version(p) for p in ('torch','numpy','robosuite','mujoco','h5py')},
          'limitations':['Same fixed BC checkpoint, branch dataset and 30 repeatedly inspected dev parents; seeds vary WM initialization and minibatches only.',
                         'Branch training covers20 parents, development branch selection8 parents. No claim of using all140 training demonstrations for WM branches.',
                         'This completes multiseed development comparison, not untouched confirmation or a formal school graduation review.']}
write_json(RUN/'protocol.json',protocol)
write_json(RUN/'structural_validation.json',{'passed':True,'data_queue_prefix_identical':True,'train_dev_parents_disjoint':True,
             'matched_initialization':True,'parameters':counts,'model_seeds_distinct':len(set(initial[s]['full'] for s in seeds))==3})
print(json.dumps({'registered':RUN.name,'training_jobs':15,'evaluation_jobs':protocol['evaluation_jobs'],'episodes':protocol['evaluation_episode_records'],'parameters':counts}))
