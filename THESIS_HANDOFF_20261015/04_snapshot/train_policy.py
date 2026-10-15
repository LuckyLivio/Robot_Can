import argparse
import json
import time

import numpy as np
import torch

from common import ROOT,ChunkPolicy,RecurrentChunkPolicy,policy_windows,read_episodes


def recurrent_windows(episodes,horizon,history):
    xx=[];aa=[]
    for ep in episodes:
        for t in range(len(ep['a'])-horizon+1):
            ids=np.maximum(np.arange(t-history+1,t+1),0)
            xx.append(ep['x'][ids]);aa.append(ep['a'][t:t+horizon])
    return np.asarray(xx),np.asarray(aa)


def main(args):
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    train=read_episodes('train')
    dev=read_episodes('dev')
    if args.architecture=='recurrent':
        x,a=recurrent_windows(train,args.horizon,args.history)
        vx,va=recurrent_windows(dev,args.horizon,args.history)
    else:
        x,a=policy_windows(train,args.horizon)
        vx,va=policy_windows(dev,args.horizon)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    x,a,vx,va=[torch.from_numpy(v).to(device) for v in [x,a,vx,va]]
    model=(RecurrentChunkPolicy(x.shape[-1],args.horizon,5,args.width,args.history)
           if args.architecture=='recurrent' else ChunkPolicy(x.shape[-1],args.horizon,5,args.width)).to(device)
    flattened=x.reshape(-1,x.shape[-1])
    model.mean.copy_(flattened.mean(0))
    model.scale.copy_(flattened.std(0).clamp_min(.02))
    opt=torch.optim.Adam(model.parameters(),lr=args.lr)
    cfg=vars(args)|{'dim':x.shape[-1],'mixtures':5,'device':str(device),'input':'PRIVILEGED_STATE_DIAGNOSTIC','n_train_windows':len(x)}
    out=ROOT/'policy'/args.name
    out.mkdir(parents=True,exist_ok=True)
    (out/'config.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
    records=[]
    best=float('inf')
    start=time.perf_counter()
    for step in range(1,args.updates+1):
        model.train()
        ids=torch.randint(len(x),(args.batch,),device=device)
        loss=model.loss(x[ids],a[ids])
        opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),10.);opt.step()
        if step%250==0 or step==args.updates:
            model.eval()
            with torch.no_grad():
                ids=torch.arange(0,len(vx),max(1,len(vx)//2048),device=device)
                val=model.loss(vx[ids],va[ids]).item()
                mse=(model.best(vx[ids])[:,0]-va[ids,0]).square().mean().item()
            row={'update':step,'loss':loss.item(),'dev_nll':val,'dev_action_mse':mse,'elapsed_s':time.perf_counter()-start}
            records.append(row)
            (out/'log.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
            print(json.dumps(row),flush=True)
            if val<best:
                best=val
                torch.save({'state_dict':model.state_dict(),'config':cfg,'selected_update':step},out/'policy.pt')
            if step in [500,750,1500,3000,args.updates]:
                torch.save({'state_dict':model.state_dict(),'config':cfg,'selected_update':step},out/f'policy_{step}.pt')
    print('saved',out,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--seed',type=int,default=17)
    p.add_argument('--horizon',type=int,default=8)
    p.add_argument('--width',type=int,default=256)
    p.add_argument('--updates',type=int,default=5000)
    p.add_argument('--batch',type=int,default=256)
    p.add_argument('--lr',type=float,default=3e-4)
    p.add_argument('--name',default='bc_chunk_dev_v0')
    p.add_argument('--architecture',choices=['mlp','recurrent'],default='mlp')
    p.add_argument('--history',type=int,default=10)
    main(p.parse_args())
