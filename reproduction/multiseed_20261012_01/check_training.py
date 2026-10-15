"""Verify matched runs, checkpoint selection, frozen dynamics and head exclusion."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
import numpy as np
import torch
from train_suite import write_json,construct
import evaluate_suite

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def load(model):return torch.load(ROOT/'models'/model/'model.pt',map_location='cpu',weights_only=True)
def module(checkpoint):
    cfg=checkpoint['config'];model=construct(cfg['method'],cfg['width'])
    model.load_state_dict(checkpoint['state_dict']);model.eval();return model

torch.set_num_threads(2)
protocol=read(RUN/'protocol.json');checks=[];selected=[]
for seed in protocol['seeds']:
    initial=[];batches=[];models={}
    for method in protocol['train_methods']:
        name=f'{RUN.name}_{method}_s{seed}';ck=load(name);models[method]=ck;cfg=ck['config']
        log=read(ROOT/'models'/name/'log.json')
        assert len(log)==12 and [x['step'] for x in log]==list(range(250,3001,250))
        assert ck['selected_step']==min(log,key=lambda x:x['selection_criterion'])['step']
        generator=torch.Generator(device='cpu').manual_seed(seed)
        expected=hashlib.sha256(torch.randint(160,(3000,16),generator=generator).numpy().tobytes()).hexdigest()
        assert cfg['minibatch_sha256']==expected
        batches.append(cfg['minibatch_sha256'])
        if method!='direct':initial.append(cfg['initial_state_sha256'])
        selected.append({'method':method,'seed':seed,'selected_step':ck['selected_step'],'parameters':cfg['parameters'],
                         'minibatch_sha256':cfg['minibatch_sha256'],'dev_metrics':ck['dev_metrics']})
        if method=='prediction_only':
            torch.manual_seed(seed);fresh=construct(method)
            for key,value in fresh.state_dict().items():
                if key.startswith('labels.'):assert torch.equal(value,ck['state_dict'][key]),key
    assert len(set(initial))==len(set(batches))==1
    full=module(models['full']);head_models={}
    for arm in ('control','calibrated'):
        name=f'{RUN.name}_head_s{seed}_{arm}_s{seed}';ck=load(name);cfg=ck['config']
        log=read(ROOT/'models'/name/'log.json')
        assert len(log)==12
        assert ck['selected_step']==min(log,key=lambda x:x['dev']['predicted']['rank']['mean_regret'])['step']
        assert cfg['calibration']['minibatch_sha256']==batches[0]
        for key,value in ck['state_dict'].items():
            if not key.startswith('labels.'):assert torch.equal(value,models['full']['state_dict'][key]),(seed,arm,key)
        head_models[arm]=module(ck)
        selected.append({'method':arm,'seed':seed,'selected_step':ck['selected_step'],'parameters':cfg['parameters'],
                         'minibatch_sha256':cfg['calibration']['minibatch_sha256'],'dev_metrics':ck['dev_metrics']})
    for split in ('train','dev'):
        with np.load(ROOT/'data'/f'branches_{split}_{protocol["dataset"]}.npz') as data:
            x=torch.from_numpy(np.repeat(data['x'],4,axis=0));actions=torch.from_numpy(data['a'].reshape(-1,8,7))
        with torch.no_grad():
            reference,_=full(x,actions)
            for arm,model in head_models.items():
                prediction,_=model(x,actions)
                assert torch.equal(prediction,reference),(seed,split,arm)
        checks.append({'seed':seed,'split':split,'groups':len(x)//4,'calibration_state_prediction_error':0.})

# Perturb only an unused prediction-only head. The actual robot trajectory must
# stay identical, including under fixed positional noise.
ck=load(f'{RUN.name}_prediction_only_s17')
perturbed=dict(ck);perturbed['state_dict']={key:value.clone() for key,value in ck['state_dict'].items()}
for key in perturbed['state_dict']:
    if key.startswith('labels.'):perturbed['state_dict'][key].fill_(37.)
folder=RUN/'validation/prediction_head_perturbed';folder.mkdir(parents=True,exist_ok=False)
with (folder/'model.pt').open('xb') as f:torch.save(perturbed,f)
def args(model,output):
    return argparse.Namespace(method='wm',model=model,policy='bc_chunk_dev_v4',policy_checkpoint='policy_15000.pt',
        split='dev',episodes=30,steps=400,delay=2,shift_index=None,fallback_index=2,candidates=4,horizon=8,noise=.05,
        risk_weight=.5,readout_weight=0.,gate_margin=.02,fallback='shift',score_only=False,candidate_mode='shift',
        demos=['demo_105'],output_dir=str(output),trace=True)
original=evaluate_suite.run(args(f'{RUN.name}_prediction_only_s17',RUN/'validation/prediction_original'))
changed=evaluate_suite.run(args(str(folder),RUN/'validation/prediction_perturbed'))
a,b=read(original),read(changed)
ra=[json.loads(line) for line in (original.parent/a['trace_files']['demo_105']).read_text().splitlines()]
rb=[json.loads(line) for line in (changed.parent/b['trace_files']['demo_105']).read_text().splitlines()]
assert len(ra)==len(rb)
for first,second in zip(ra,rb):
    assert first['learned_scores'] is None and first['predicted_risk'] is None and first['predicted_progress'] is None
    for key in first:
        if key!='decision_ms':assert first[key]==second[key],(first['step'],key)
write_json(RUN/'training_verification.json',{'passed':True,'matched_batch_hashes':True,'matched_world_model_initialization':True,
          'all_checkpoint_selection_verified':True,'calibration_freeze_checks':checks,
          'prediction_only_random_head_ignored':True,'prediction_head_perturbation_identical_steps':len(ra),'selected':selected})
print(json.dumps({'training_verification':'passed','model_checkpoints':len(selected),'ignored_head_steps':len(ra)}),flush=True)
