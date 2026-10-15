import argparse
import json
import time

import numpy as np
import torch
from torch import nn

from common import ROOT
from world_model import WorldModel,DirectScore,score,target_score,grouped_rank_loss,rank_metrics


def data(path,device):
    with np.load(path) as f:
        arrays={k:torch.from_numpy(f[k]).to(device) for k in ['x','a','y','labels']}
    return arrays


def evaluate(model,dev,risk_weight):
    model.eval();n,k,h,_=dev['a'].shape
    preds=[];truth=[];errors=[]
    with torch.no_grad():
        for start in range(0,n,32):
            end=min(start+32,n);g=end-start
            x=dev['x'][start:end,None].expand(-1,k,-1).reshape(g*k,-1)
            a=dev['a'][start:end].flatten(0,1)
            yy,labels=model(x,a)
            preds.extend(score(labels,risk_weight).cpu().numpy().tolist())
            truth.extend(target_score(dev['labels'][start:end].flatten(0,1),risk_weight).cpu().numpy().tolist())
            if yy is not None:
                errors.append(((yy-dev['y'][start:end].flatten(0,1))/model.scale).square().mean().item())
    result=rank_metrics(preds,truth,n,k)
    result['normalized_state_mse']=float(np.mean(errors)) if errors else None
    return result


def main(args):
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    train=data(ROOT/'data'/f'branches_train_{args.dataset}.npz',device)
    dev=data(ROOT/'data'/f'branches_dev_{args.dataset}.npz',device)
    n,k,h,_=train['a'].shape;dim=train['x'].shape[-1]
    model=(DirectScore(dim,h,args.width) if args.method=='direct' else WorldModel(dim,args.width,args.future_only)).to(device)
    model.mean.copy_(train['x'].mean(0));model.scale.copy_(train['x'].std(0).clamp_min(.02))
    opt=torch.optim.Adam(model.parameters(),lr=args.lr)
    out=ROOT/'models'/args.run
    out.mkdir(parents=True,exist_ok=True)
    cfg=vars(args)|{'dim':dim,'horizon':h,'device':str(device),'input':'PRIVILEGED_STATE_DIAGNOSTIC',
                    'n_groups':n,'n_candidates':k,'parameters':sum(p.numel() for p in model.parameters())}
    (out/'config.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
    logs=[];best=float('inf');started=time.perf_counter()
    for step in range(1,args.updates+1):
        model.train()
        ids=torch.randint(n,(args.batch,),device=device)
        x=train['x'][ids,None].expand(-1,k,-1).reshape(args.batch*k,dim)
        a=train['a'][ids].flatten(0,1);y=train['y'][ids].flatten(0,1);labels=train['labels'][ids].flatten(0,1)
        predicted,readouts=model(x,a)
        pred_loss=((predicted-y)/model.scale).square().mean() if predicted is not None else readouts.sum()*0
        # All label-enabled methods receive identical supervision, including the direct scorer.
        progress_loss=nn.functional.binary_cross_entropy_with_logits(readouts[:,:,0],labels[:,:,0])
        risk_loss=nn.functional.binary_cross_entropy_with_logits(readouts[:,:,1],labels[:,:,1])
        ranking=grouped_rank_loss(score(readouts,args.risk_weight),target_score(labels,args.risk_weight),args.batch,k)
        label_weight=0. if args.method=='prediction_only' else 1.
        rank_weight=args.rank_weight if args.method in ['full','direct'] else 0.
        loss=pred_loss+label_weight*(progress_loss+.5*risk_loss)+rank_weight*ranking
        opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),10);opt.step()
        if step%250==0 or step==args.updates:
            metrics=evaluate(model,dev,args.risk_weight)
            row={'step':step,'loss':loss.item(),'prediction_loss':pred_loss.item(),'ranking_loss':ranking.item(),
                 'elapsed_s':time.perf_counter()-started}|metrics
            logs.append(row);print(json.dumps(row),flush=True)
            (out/'log.json').write_text(json.dumps(logs,indent=2),encoding='utf-8')
            criterion=metrics['mean_regret']
            if criterion<best:
                best=criterion
                torch.save({'state_dict':model.state_dict(),'config':cfg,'selected_step':step,'dev_metrics':metrics},out/'model.pt')
    print('saved',out,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--method',choices=['plain','full','direct','prediction_only'],default='plain')
    p.add_argument('--dataset',default='pilot_v0');p.add_argument('--run',default='plain_seed17_pilot_v0')
    p.add_argument('--seed',type=int,default=17);p.add_argument('--width',type=int,default=128)
    p.add_argument('--updates',type=int,default=3000);p.add_argument('--batch',type=int,default=16)
    p.add_argument('--lr',type=float,default=3e-4);p.add_argument('--rank-weight',type=float,default=.2)
    p.add_argument('--risk-weight',type=float,default=.5)
    p.add_argument('--future-only',action='store_true',help='Read task/risk only from recursively predicted states.')
    main(p.parse_args())
