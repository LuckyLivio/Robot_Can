"""Matched-data multiseed training. New outputs only; never edits old models."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from torch import nn
from world_model import WorldModel,DirectScore,score,target_score,grouped_rank_loss,rank_metrics

def write_json(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False)

def configure(seed):
    torch.set_num_threads(4);torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.set_float32_matmul_precision('highest')

def construct(method,width=128):
    return DirectScore(23,8,width) if method=='direct' else WorldModel(23,width,True)

def load_data(dataset,device):
    splits=json.loads((ROOT/'data/splits.json').read_text())
    result={};parents={}
    for split in ('train','dev'):
        with np.load(ROOT/'data'/f'branches_{split}_{dataset}.npz') as data:
            parents[split]=sorted(set(data['parent'].tolist()))
            assert set(parents[split]).issubset(splits[split])
            result[split]={k:torch.from_numpy(data[k]).to(device) for k in ('x','a','y','labels')}
        for value in result[split].values():assert torch.isfinite(value).all()
        assert result[split]['a'].shape[1:]==(4,8,7)
    assert not (set(parents['train'])&set(parents['dev']))
    return result,parents

@torch.no_grad()
def evaluate(model,data):
    model.eval();n,k,h,_=data['a'].shape
    predictions=[];truth=[];square_sum=0.;count=0
    for start in range(0,n,32):
        end=min(n,start+32);g=end-start
        x=data['x'][start:end,None].expand(-1,k,-1).reshape(g*k,-1)
        future,logits=model(x,data['a'][start:end].flatten(0,1))
        predictions.extend(score(logits,.5).cpu().tolist())
        truth.extend(target_score(data['labels'][start:end].flatten(0,1),.5).cpu().tolist())
        if future is not None:
            error=((future-data['y'][start:end].flatten(0,1))/model.scale).square()
            square_sum+=float(error.sum());count+=error.numel()
    result=rank_metrics(predictions,truth,n,k)
    result['normalized_state_mse']=square_sum/count if count else None
    return result

def tensor_hash(state):
    digest=hashlib.sha256()
    for key,value in sorted(state.items()):
        digest.update(key.encode());digest.update(value.detach().cpu().numpy().tobytes())
    return digest.hexdigest()

def main(args):
    run=Path(args.run_dir).resolve();protocol=json.loads((run/'protocol.json').read_text())
    assert args.seed in protocol['seeds']
    configure(args.seed)
    if args.method=='calibrate':
        from calibrate_score_head import main as calibrate
        calibrate(argparse.Namespace(tag=f'{run.name}_head_s{args.seed}',
                  base_model=f'{run.name}_full_s{args.seed}',dataset=protocol['dataset'],seed=args.seed,
                  updates=3000,batch=16,lr=.0003,real_weight=1.,eval_every=250))
        return
    assert args.method in protocol['train_methods']
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    data,parents=load_data(protocol['dataset'],device)
    train,dev=data['train'],data['dev'];n,k,h,_=train['a'].shape
    width=251 if args.method=='direct' else 128
    model=construct(args.method,width).to(device)
    model.mean.copy_(train['x'].mean(0));model.scale.copy_(train['x'].std(0).clamp_min(.02))
    initial_hash=tensor_hash(model.state_dict())
    if args.method=='prediction_only':
        model.labels.requires_grad_(False)
        head_before={k:v.clone() for k,v in model.labels.state_dict().items()}
    batch_generator=torch.Generator(device='cpu').manual_seed(args.seed)
    batches_cpu=torch.randint(n,(3000,16),generator=batch_generator)
    batches=batches_cpu.to(device)
    out=ROOT/'models'/f'{run.name}_{args.method}_s{args.seed}'
    (out/'checkpoints').mkdir(parents=True,exist_ok=False)
    parameters=list(p for p in model.parameters() if p.requires_grad)
    optimizer=torch.optim.Adam(parameters,lr=.0003)
    cfg={'method':args.method,'dataset':protocol['dataset'],'run':out.name,'seed':args.seed,'width':width,
         'updates':3000,'batch':16,'lr':.0003,'rank_weight':.2 if args.method in ('full','direct') else 0.,
         'risk_weight':.5,'future_only':args.method!='direct','dim':23,'horizon':8,'device':str(device),
         'input':'PRIVILEGED_STATE_DIAGNOSTIC','n_groups':n,'n_candidates':k,
         'parameters':sum(p.numel() for p in model.parameters()),'trainable_parameters':sum(p.numel() for p in parameters),
         'initial_state_sha256':initial_hash,'minibatch_sha256':hashlib.sha256(batches_cpu.numpy().tobytes()).hexdigest(),
         'selection':'minimum normalized dev state MSE; earliest tie' if args.method=='prediction_only' else 'minimum dev score mean_regret; earliest tie',
         'deterministic_algorithms':True,'matmul_precision':'highest','parents':parents,
         'protocol_sha256':hashlib.sha256((run/'protocol.json').read_bytes()).hexdigest()}
    write_json(out/'config.json',cfg)
    best=float('inf');chosen=None;logs=[];start=time.perf_counter()
    for step,ids in enumerate(batches,1):
        model.train()
        x=train['x'][ids,None].expand(-1,k,-1).reshape(16*k,23)
        actions=train['a'][ids].flatten(0,1);y=train['y'][ids].flatten(0,1);labels=train['labels'][ids].flatten(0,1)
        future,logits=model(x,actions)
        zero=logits.sum()*0
        pred_loss=((future-y)/model.scale).square().mean() if future is not None else zero
        if args.method=='prediction_only':
            progress_loss,risk_loss,ranking=zero,zero,zero
            loss=pred_loss
        else:
            progress_loss=nn.functional.binary_cross_entropy_with_logits(logits[:,:,0],labels[:,:,0])
            risk_loss=nn.functional.binary_cross_entropy_with_logits(logits[:,:,1],labels[:,:,1])
            ranking=grouped_rank_loss(score(logits,.5),target_score(labels,.5),16,k)
            loss=pred_loss+progress_loss+.5*risk_loss+cfg['rank_weight']*ranking
        assert torch.isfinite(loss)
        optimizer.zero_grad(set_to_none=True);loss.backward();nn.utils.clip_grad_norm_(parameters,10);optimizer.step()
        if step%250==0:
            metrics=evaluate(model,dev)
            criterion=metrics['normalized_state_mse'] if args.method=='prediction_only' else metrics['mean_regret']
            if args.method=='prediction_only':
                for name,value in model.labels.state_dict().items():assert torch.equal(value,head_before[name])
            state={key:value.detach().cpu().clone() for key,value in model.state_dict().items()}
            ck={'config':cfg,'state_dict':state,'selected_step':step,'dev_metrics':metrics}
            with (out/'checkpoints'/f'step_{step:06d}.pt').open('xb') as f:torch.save(ck,f)
            if criterion<best:best,chosen=criterion,ck
            row={'step':step,'loss':float(loss.detach()),'prediction_loss':float(pred_loss.detach()),
                 'progress_loss':float(progress_loss.detach()),'risk_loss':float(risk_loss.detach()),
                 'ranking_loss':float(ranking.detach()),'selection_criterion':criterion,'elapsed_s':time.perf_counter()-start,**metrics}
            logs.append(row);print(json.dumps({'model':out.name,**row}),flush=True)
    with (out/'model.pt').open('xb') as f:torch.save(chosen,f)
    write_json(out/'log.json',logs)
    write_json(out/'training_complete.json',{'status':'complete','model':out.name,'selected_step':chosen['selected_step'],
               'minibatch_sha256':cfg['minibatch_sha256'],'initial_state_sha256':initial_hash,
               'sha256':hashlib.sha256((out/'model.pt').read_bytes()).hexdigest(),'elapsed_s':time.perf_counter()-start})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--method',choices=['full','plain','direct','prediction_only','calibrate'],required=True)
    main(parser.parse_args())
