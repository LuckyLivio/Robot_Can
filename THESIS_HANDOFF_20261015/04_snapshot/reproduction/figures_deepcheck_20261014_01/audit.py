"""Offline checkpoint and plot audit. Does not train or run simulation."""
from pathlib import Path
import sys, json, hashlib, csv, importlib.util
import numpy as np
import torch
from torch.nn import functional as F

ROOT=Path(__file__).resolve().parents[2]; RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from world_model import WorldModel,score,target_score,grouped_rank_loss,rank_metrics
import make_figures as plots
torch.set_num_threads(4)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
def track(p):
    sources[p.relative_to(ROOT).as_posix()]=sha(p)
    return p
def load(p): return json.loads(track(p).read_text(encoding='utf-8-sig'))

def main():
    splits={}
    for split in ['train','dev']:
        path=track(ROOT/f'data/branches_{split}_queuepair_20261012_01_real.npz')
        with np.load(path) as data:
            splits[split]={k:torch.from_numpy(data[k]) for k in ['x','a','y','labels']}
            splits[split]['parents']=data['parent'].tolist()
    checkpoint_rows=[]; detail=[]; log_errors=[]
    for seed in [17,23,41]:
        folder=ROOT/f'models/multiseed_20261012_01_full_s{seed}'
        log=load(folder/'log.json')
        for record in log:
            step=record['step']; path=track(folder/f'checkpoints/step_{step:06d}.pt')
            ck=torch.load(path,map_location='cpu',weights_only=True)
            model=WorldModel(23,128,True);model.load_state_dict(ck['state_dict']);model.eval()
            for split,d in splits.items():
                g,k,h,_=d['a'].shape
                x=d['x'][:,None].expand(-1,k,-1).reshape(g*k,-1)
                y,labels=d['y'].flatten(0,1),d['labels'].flatten(0,1)
                with torch.no_grad():
                    future,logits=model(x,d['a'].flatten(0,1))
                    mse=((future-y)/model.scale).square()
                    pred=float(mse.mean());progress=float(F.binary_cross_entropy_with_logits(logits[:,:,0],labels[:,:,0]))
                    risk=float(F.binary_cross_entropy_with_logits(logits[:,:,1],labels[:,:,1]))
                    s=score(logits,.5); truth=target_score(labels,.5)
                    rank=float(grouped_rank_loss(s,truth,g,k))
                    metrics=rank_metrics(s.numpy(),truth.numpy(),g,k)
                    target=truth.numpy().reshape(g,k); choices=s.numpy().reshape(g,k).argmax(1)
                    regret=target.max(1)-target[np.arange(g),choices]
                    worst=int(regret.argmax())
                    row={'seed':seed,'step':step,'split':split,'groups':g,'parents':len(set(d['parents'])),
                         'prediction_mse':pred,'progress_bce':progress,'risk_bce':risk,'ranking_loss':rank,
                         'total_loss':pred+progress+.5*risk+.2*rank,**metrics,
                         'worst_group':worst,'worst_parent':d['parents'][worst],
                         'worst_regret':float(regret[worst]),'worst_contribution_to_mean':float(regret[worst]/g),
                         'object_error_mm':float(torch.linalg.vector_norm(future[:,:,16:19]-y[:,:,16:19],dim=-1).mean()*1000)}
                    checkpoint_rows.append(row)
                    if split=='dev':
                        log_errors.append({'seed':seed,'step':step,
                            'mse_abs_error':abs(pred-record['normalized_state_mse']),
                            'regret_abs_error':abs(metrics['mean_regret']-record['mean_regret'])})
                        detail.append({'seed':seed,'step':step,'choices':choices.tolist(),'regret':regret.tolist(),
                                       'mse_by_dimension':mse.mean((0,1)).tolist()})
        print(f'Checked 12 checkpoints for seed {seed}',flush=True)
    conf=plots.records(plots.CONF,60);dev=plots.records(plots.DEV,30)
    plots.check_summary(conf,plots.CONF);plots.check_summary(dev,plots.DEV)
    duplicates=[];steps=[];usage=[]
    for condition in ['clean','noise005']:
        for method in ['full','plain']:
            sets=[{n for n,r in conf[method,s,condition].items() if r['success']} for s in [17,23,41]]
            records=[conf[method,s,condition] for s in [17,23,41]]
            duplicates.append({'method':method,'condition':condition,'identical_success_sets':all(x==sets[0] for x in sets),
                               'identical_step_vectors':all([r[n]['steps'] for n in sorted(r)]==[records[0][n]['steps'] for n in sorted(r)] for r in records),
                               'success_counts':[len(x) for x in sets]})
        for seed in [17,23,41]:
            b,f=conf['bc_k2',None,condition],conf['full',seed,condition]
            delta=[r['steps']-b[n]['steps'] for n,r in f.items() if r['success'] and b[n]['success']]
            steps.append({'seed':seed,'condition':condition,'paired_n':len(delta),'full_faster':sum(x<0 for x in delta),
                          'equal_steps':sum(x==0 for x in delta),'full_slower':sum(x>0 for x in delta),
                          'median_difference':float(np.median(delta)),'mean_difference':float(np.mean(delta))})
            usage.append({'seed':seed,'condition':condition,'mean_fraction_override':float(np.mean([r['fraction_override'] for r in f.values()]))})
    lock=load(ROOT/plots.CONF/'lock.json')
    for rel,value in lock['input_sha256'].items():
        # Check the six frozen model weights without loading arbitrary files.
        if rel.startswith('models/') and rel.endswith('/model.pt'): assert sha(track(ROOT/rel))==value,rel
    sources.update(plots.SOURCES)
    maxm=max(r['mse_abs_error'] for r in log_errors);maxr=max(r['regret_abs_error'] for r in log_errors)
    assert maxm<1e-5 and maxr<1e-5,(maxm,maxr)
    result={'checkpoint_metrics':checkpoint_rows,'dev_group_details':detail,'log_recomputation_errors':log_errors,
            'max_mse_log_error':maxm,'max_regret_log_error':maxr,
            'duplicate_checks':duplicates,'paired_step_counts':steps,'controller_usage':usage,
            'sources_sha256':sources,'scope':'CPU offline reevaluation; no training, no new rollout; existing datasets and 36 checkpoints',
            'new_training_steps':0,'new_simulation_episodes':0}
    (RUN/'diagnostics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    with (RUN/'checkpoint_metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(checkpoint_rows[0]));w.writeheader();w.writerows(checkpoint_rows)
    print(json.dumps({'max_mse_error':maxm,'max_regret_error':maxr,'duplicates':duplicates,'steps':steps},ensure_ascii=False))

if __name__=='__main__':main()
