import argparse,json,time
import h5py
import numpy as np
import torch
from common import ROOT,DATA
from adaptive_model import FULL_KEYS,ResponseWorldModel


def episodes(split):
    names=json.loads((ROOT/'data/splits.json').read_text())[split]
    xs=[];ys=[];aa=[];roll_x=[];roll_a=[];roll_y=[]
    with h5py.File(DATA,'r') as f:
        for name in names:
            d=f['data'][name]
            x=np.concatenate([d['obs'][k][:] for k in FULL_KEYS],-1).astype(np.float32)
            y=np.concatenate([d['next_obs'][k][:] for k in FULL_KEYS],-1).astype(np.float32)
            a=d['actions'][:].astype(np.float32)
            xs.append(x);ys.append(y);aa.append(a)
            for t in range(0,len(a)-8,4):
                roll_x.append(x[t]);roll_a.append(a[t:t+8]);roll_y.append(y[t:t+8])
    return {'x':np.concatenate(xs),'a':np.concatenate(aa),'y':np.concatenate(ys),
            'roll_x':np.asarray(roll_x),'roll_a':np.asarray(roll_a),'roll_y':np.asarray(roll_y)}


def response_loss(pred,y,a):
    # Centered +/- pairs cancel shared prediction offset at the same initial state.
    ids=[0,1,2] # EEF response; object world position is indices 16:19, not relative pose 9:12.
    pp=pred[:,[2,4,6]][:,:,ids]-pred[:,[1,3,5]][:,:,ids]
    yy=y[:,[2,4,6]][:,:,ids]-y[:,[1,3,5]][:,:,ids]
    distances=(a[:,[2,4,6],:3]-a[:,[1,3,5],:3]).norm(dim=-1).clamp_min(.05)
    return (((pp-yy)/distances[:,:,None])/.02).square().mean()


def main(args):
    torch.set_num_threads(4);torch.manual_seed(args.seed)
    device='cuda' if torch.cuda.is_available() else 'cpu'
    raw=episodes('train');vraw=episodes('dev')
    with np.load(ROOT/'data'/f'response_train_{args.dataset}.npz') as f:
        paired={k:torch.from_numpy(f[k]).to(device) for k in ['x','a','y']}
    with np.load(ROOT/'data'/f'response_dev_{args.dataset}.npz') as f:
        vp={k:torch.from_numpy(f[k]).to(device) for k in ['x','a','y']}
    d={k:torch.from_numpy(v).to(device) for k,v in raw.items()}
    vd={k:torch.from_numpy(v).to(device) for k,v in vraw.items()}
    model=ResponseWorldModel(37,args.width,args.affine).to(device)
    model.mean.copy_(d['x'].mean(0));model.scale.copy_(d['x'].std(0).clamp_min(.02))
    optimizer=torch.optim.AdamW(model.parameters(),lr=args.lr,weight_decay=1e-5)
    out=ROOT/'models'/args.run;out.mkdir(parents=True,exist_ok=True)
    cfg=vars(args)|{'dim':37,'device':device,'input':'PRIVILEGED_STATE_DIAGNOSTIC',
                    'nominal_transitions':len(d['x']),'paired_groups':len(paired['x'])}
    (out/'config.json').write_text(json.dumps(cfg,indent=2))
    weights=torch.ones(37,device=device);weights[30:]=.1
    weights[:3]=args.eef_weight
    logs=[];best=float('inf');start=time.perf_counter()
    for step in range(1,args.updates+1):
        idx=torch.randint(len(d['x']),(128,),device=device)
        ids=torch.randint(len(paired['x']),(24,),device=device)
        x=paired['x'][ids,None].expand(-1,7,-1).flatten(0,1)
        a=paired['a'][ids].flatten(0,1)
        pred=model(x,a).reshape(24,7,37)
        ordinary=model(d['x'][idx],d['a'][idx])
        state=((ordinary-d['y'][idx])/model.scale).square().mul(weights).mean()
        state+=((pred-paired['y'][ids])/model.scale).square().mul(weights).mean()
        response=response_loss(pred,paired['y'][ids],paired['a'][ids])
        # Matched rollout supervision in both methods; response is the only ablation difference.
        rids=torch.randint(len(d['roll_x']),(24,),device=device)
        roll=model.rollout(d['roll_x'][rids],d['roll_a'][rids])
        multistep=((roll-d['roll_y'][rids])/model.scale).square().mul(weights).mean()
        loss=state+args.response_weight*response+.2*multistep
        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),10);optimizer.step()
        if step%250==0 or step==args.updates:
            with torch.no_grad():
                p=model(vd['x'][::3],vd['a'][::3])
                n=len(vp['x']);pv=model(vp['x'][:,None].expand(-1,7,-1).flatten(0,1),vp['a'].flatten(0,1)).reshape(n,7,37)
                ee=float((p[:,:3]-vd['y'][::3,:3]).square().mean().sqrt()*1000)
                obj=float((p[:,16:19]-vd['y'][::3,16:19]).square().mean().sqrt()*1000)
                sensitivity=float(response_loss(pv,vp['y'],vp['a']))
                rr=model.rollout(vd['roll_x'][::5],vd['roll_a'][::5])
                multi_mm=float((rr[:,:,:3]-vd['roll_y'][::5,:,:3]).square().mean().sqrt()*1000)
            row={'step':step,'loss':float(loss),'state_loss':float(state),'response_loss':float(response),
                 'dev_eef_rmse_mm':ee,'dev_object_rmse_mm':obj,'dev_response_mse':sensitivity,
                 'dev_rollout_eef_rmse_mm':multi_mm,'elapsed_s':time.perf_counter()-start}
            logs.append(row);(out/'log.json').write_text(json.dumps(logs,indent=2));print(json.dumps(row),flush=True)
            criterion=ee+10*sensitivity
            if criterion<best:
                best=criterion;torch.save({'state_dict':model.state_dict(),'config':cfg,'dev_metrics':row},out/'model.pt')
    print('saved',out,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',default='response_seed17_v2')
    p.add_argument('--dataset',default='v2');p.add_argument('--seed',type=int,default=17)
    p.add_argument('--width',type=int,default=256);p.add_argument('--updates',type=int,default=4000)
    p.add_argument('--lr',type=float,default=3e-4);p.add_argument('--response-weight',type=float,default=.5)
    p.add_argument('--affine',action='store_true');p.add_argument('--eef-weight',type=float,default=100.)
    main(p.parse_args())
