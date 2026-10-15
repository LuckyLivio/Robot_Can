"""Distill world-model-selected counterfactual actions into a low-data policy."""
import argparse,json,time
import numpy as np,torch
from common import ROOT,ChunkPolicy,policy_windows,read_episodes
from world_model import WorldModel,score

def main(args):
 torch.set_num_threads(4);torch.manual_seed(args.seed);np.random.seed(args.seed);device='cuda' if torch.cuda.is_available() else 'cpu'
 train=read_episodes('train');dev=read_episodes('dev');train=train[:args.demo_limit]
 x,a=policy_windows(train,args.horizon);vx,va=policy_windows(dev,args.horizon)
 with np.load(ROOT/'data'/f'branches_train_{args.dataset}.npz') as f:
  bx=torch.from_numpy(f['x']).to(device);ba=torch.from_numpy(f['a']).to(device)
 ck=torch.load(ROOT/'models'/args.model/'model.pt',map_location='cpu',weights_only=True);cfg=ck['config'];wm=WorldModel(cfg['dim'],cfg['width'],cfg.get('future_only',False)).to(device);wm.load_state_dict(ck['state_dict']);wm.eval()
 with torch.no_grad():
  tiled=bx[:,None].expand(-1,ba.shape[1],-1).flatten(0,1);_,heads=wm(tiled,ba.flatten(0,1));chosen=score(heads,args.risk_weight).reshape(len(bx),ba.shape[1]).argmax(-1).cpu().numpy()
 aug_a=np.asarray([ba[i,k].cpu().numpy() for i,k in enumerate(chosen)],np.float32);aug_x=bx.cpu().numpy()
 if args.augment:
  x=np.concatenate([x,aug_x],0);a=np.concatenate([a,aug_a],0)
 x,a,vx,va=[torch.from_numpy(v).to(device) for v in [x,a,vx,va]]
 model=ChunkPolicy(x.shape[-1],args.horizon,5,args.width).to(device);model.mean.copy_(x.mean(0));model.scale.copy_(x.std(0).clamp_min(.02));opt=torch.optim.Adam(model.parameters(),lr=args.lr)
 out=ROOT/'policy'/args.name;out.mkdir(parents=True,exist_ok=True);conf=vars(args)|{'dim':x.shape[-1],'mixtures':5,'device':device,'n_windows':len(x),'selected_candidate_hist':np.bincount(chosen,minlength=ba.shape[1]).tolist()};(out/'config.json').write_text(json.dumps(conf,indent=2));logs=[];best=1e9;start=time.perf_counter()
 for step in range(1,args.updates+1):
  ids=torch.randint(len(x),(args.batch,),device=device);loss=model.loss(x[ids],a[ids]);opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),10);opt.step()
  if step%250==0 or step==args.updates:
   with torch.no_grad():idsv=torch.arange(0,len(vx),max(1,len(vx)//2048),device=device);val=model.loss(vx[idsv],va[idsv]).item();mse=(model.best(vx[idsv])[:,0]-va[idsv,0]).square().mean().item()
   row={'update':step,'loss':loss.item(),'dev_nll':val,'dev_action_mse':mse,'elapsed_s':time.perf_counter()-start};logs.append(row);(out/'log.json').write_text(json.dumps(logs,indent=2));print(json.dumps(row),flush=True)
   if val<best:best=val;torch.save({'state_dict':model.state_dict(),'config':conf,'selected_update':step},out/'policy.pt')
   if step in [500,1000,2000,args.updates]:torch.save({'state_dict':model.state_dict(),'config':conf,'selected_update':step},out/f'policy_{step}.pt')
 print('saved',out,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--name',default='wm_aug_low20');p.add_argument('--model',default='full_future_bc_v4');p.add_argument('--dataset',default='bc_v4_pilot');p.add_argument('--demo-limit',type=int,default=20);p.add_argument('--augment',action='store_true');p.add_argument('--horizon',type=int,default=8);p.add_argument('--width',type=int,default=256);p.add_argument('--updates',type=int,default=5000);p.add_argument('--batch',type=int,default=256);p.add_argument('--lr',type=float,default=3e-4);p.add_argument('--risk-weight',type=float,default=.5);p.add_argument('--seed',type=int,default=17);main(p.parse_args())
