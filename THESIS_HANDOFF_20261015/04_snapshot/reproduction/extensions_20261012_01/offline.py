"""No fitting: compare frozen forecasts and score heads on the same dev branches."""
import json, sys
from pathlib import Path
import numpy as np, torch
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
sys.path.insert(0,str(ROOT))
from world_model import WorldModel,score,target_score
from evaluate import select


def ranking(pred,truth):
    raw=np.argmax(pred,axis=1)
    chosen=np.asarray([select(s,[0,1,2,3])[1] for s in pred])
    maximum=truth.max(1)
    pd=pred[:,:,None]-pred[:,None,:];td=truth[:,:,None]-truth[:,None,:]
    mask=(np.abs(td)>.025)&np.triu(np.ones((4,4),bool),1)[None]
    tie=np.abs(pd[mask])<=1e-7
    correct=(pd[mask]*td[mask]>0)&~tie
    return {'raw_regret':float(np.mean(maximum-truth[np.arange(len(truth)),raw])),
            'gated_regret':float(np.mean(maximum-truth[np.arange(len(truth)),chosen])),
            'gated_optimal_within_025':float(np.mean(maximum-truth[np.arange(len(truth)),chosen]<=.025)),
            'nontrivial_pairs':int(mask.sum()),'pair_tie_rate':float(tie.mean()),
            'pair_accuracy_ties_half':float(np.mean(correct.astype(float)+.5*tie)),
            'override_fraction':float(np.mean(chosen!=2)),
            'oracle_gate_agreement':float(np.mean(chosen==np.asarray([select(s,[0,1,2,3])[1] for s in truth])))}


@torch.no_grad()
def main():
    torch.set_num_threads(2)
    data=np.load(ROOT/'data/branches_dev_queuepair_20261012_01_real.npz',allow_pickle=False)
    x=torch.from_numpy(np.repeat(data['x'][:,None],4,1).reshape(-1,23))
    actions=torch.from_numpy(data['a'].reshape(-1,8,7))
    y=torch.from_numpy(data['y'].reshape(-1,8,23))
    labels=torch.from_numpy(data['labels'].reshape(-1,8,2))
    truth=target_score(labels,.5).numpy().reshape(-1,4)
    rows=[]; arrays={'truth_scores':truth,'parent':data['parent']}
    for method in ['full','plain']:
      for seed in [17,23,41]:
        ck=torch.load(ROOT/f'models/multiseed_20261012_01_{method}_s{seed}/model.pt',map_location='cpu',weights_only=True)
        cfg=ck['config'];model=WorldModel(cfg['dim'],cfg['width'],cfg['future_only'])
        model.load_state_dict(ck['state_dict']);model.eval()
        future,logits=model(x,actions)
        true_head=score(model.labels((y-model.mean)/model.scale),.5).numpy().reshape(-1,4)
        modes=[(method,future,logits)]
        if method=='full':
            persistent=x[:,None].repeat(1,8,1)
            modes.append(('persistence',persistent,model.labels((persistent-model.mean)/model.scale)))
        for label,predicted,readout in modes:
            normalized=((predicted-y)/model.scale).square()
            predicted_score=score(readout,.5).numpy().reshape(-1,4)
            row={'method':label,'seed':seed,'groups':64,'parents':len(set(data['parent'])),
                 'normalized_state_mse':float(normalized.mean()),
                 'eef_position_rmse_m':float((predicted[:,:,:3]-y[:,:,:3]).square().sum(-1).mean().sqrt()),
                 'object_position_rmse_m':float((predicted[:,:,16:19]-y[:,:,16:19]).square().sum(-1).mean().sqrt()),
                 'normalized_mse_per_horizon':normalized.mean((0,2)).tolist(),
                 'forecast_score':ranking(predicted_score,truth),
                 'same_head_on_true_states':ranking(true_head,truth)}
            rows.append(row)
            arrays[f'{label}_s{seed}_scores']=predicted_score
            if label!='persistence': arrays[f'{label}_s{seed}_true_state_head_scores']=true_head
    report={'split':'dev','groups':64,'independent_parents':8,
            'caution':'These branch parents and targets were already used for checkpoint selection; this is mechanism diagnosis, not independent generalization.',
            'oracle':ranking(truth,truth),'rows':rows,
            'persistence_definition':'Hold all 23 state entries at x_t; no action dependence; same Full score head',
            'pair_metric':'Pairs with absolute true score gap > .025. Ties within 1e-7 receive half accuracy and are explicitly reported, not mistaken for correctly ranked pairs.'}
    with (RUN/'offline_metrics.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2,allow_nan=False)
    with (RUN/'offline_scores.npz').open('xb') as f:np.savez_compressed(f,**arrays)
    print(json.dumps({'complete':True,'arms':len(rows),'groups':64,'parents':8}))


if __name__=='__main__':main()
