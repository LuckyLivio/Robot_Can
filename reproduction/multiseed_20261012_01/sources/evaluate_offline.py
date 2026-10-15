"""Secondary physical/score metrics on the fixed 64 development branch groups."""
import csv
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
import numpy as np
import torch
from train_suite import construct,write_json
from world_model import score,target_score,rank_metrics

torch.set_num_threads(2)
protocol=json.loads((RUN/'protocol.json').read_text())
with np.load(ROOT/'data'/f'branches_dev_{protocol["dataset"]}.npz') as data:
    x=torch.from_numpy(np.repeat(data['x'],4,axis=0))
    a=torch.from_numpy(data['a'].reshape(-1,8,7));y=torch.from_numpy(data['y'].reshape(-1,8,23))
    labels=torch.from_numpy(data['labels'].reshape(-1,8,2))
truth=target_score(labels,.5);rows=[];horizon_rows=[]
for seed in protocol['seeds']:
    reference=None
    for method in ('full','plain','direct','prediction_only','control','calibrated'):
        name=f'{RUN.name}_head_s{seed}_{method}_s{seed}' if method in ('control','calibrated') else f'{RUN.name}_{method}_s{seed}'
        ck=torch.load(ROOT/'models'/name/'model.pt',map_location='cpu',weights_only=True);cfg=ck['config']
        model=construct(cfg['method'],cfg['width']);model.load_state_dict(ck['state_dict']);model.eval()
        with torch.no_grad():future,logits=model(x,a)
        row={'method':method,'seed':seed,'groups':64,'parents':8,'normalized_state_mse':None,
             'eef_mean_error_mm':None,'object_mean_error_mm':None,'score_mae':None,'risk_brier':None,
             'mean_regret':None,'wrong_pair_rate':None,'real_state_head_score_mae':None,'real_state_head_risk_brier':None}
        if future is not None:
            if method=='full':reference=future.clone()
            if method in ('control','calibrated'):assert torch.equal(future,reference)
            eef=torch.linalg.vector_norm(future[:,:,:3]-y[:,:,:3],dim=-1)*1000
            obj=torch.linalg.vector_norm(future[:,:,16:19]-y[:,:,16:19],dim=-1)*1000
            row.update(normalized_state_mse=float(((future-y)/model.scale).square().mean()),
                       eef_mean_error_mm=float(eef.mean()),object_mean_error_mm=float(obj.mean()))
            for h in range(8):horizon_rows.append({'method':method,'seed':seed,'horizon':h+1,'eef_error_mm':float(eef[:,h].mean()),'object_error_mm':float(obj[:,h].mean())})
        if method!='prediction_only':
            with torch.no_grad():
                scores=score(logits,.5);rank=rank_metrics(scores.numpy(),truth.numpy(),64,4)
                row.update(score_mae=float((scores-truth).abs().mean()),risk_brier=float((logits[:,:,1].sigmoid()-labels[:,:,1]).square().mean()),
                           mean_regret=rank['mean_regret'],wrong_pair_rate=rank['wrong_pair_rate'])
                if future is not None:
                    real_logits=model.labels((y-model.mean)/model.scale)
                    row.update(real_state_head_score_mae=float((score(real_logits,.5)-truth).abs().mean()),
                               real_state_head_risk_brier=float((real_logits[:,:,1].sigmoid()-labels[:,:,1]).square().mean()))
        rows.append(row)
directory=RUN/'offline';directory.mkdir(exist_ok=False)
for name,values in [('metrics.csv',rows),('prediction_horizons.csv',horizon_rows)]:
    with (directory/name).open('x',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
write_json(directory/'metrics.json',{'records':rows,'horizons':horizon_rows,
           'note':'All selected checkpoints, fixed 64 development groups from8 parents. CPU readout for descriptive physical/score diagnostics only; not used to select checkpoints. Head continuation/calibration dynamics exactly equal the corresponding Full.'})
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
for method,label,color in [('full','Full','#3366a3'),('plain','No rank','#d28535'),('prediction_only','Prediction only','#279879')]:
    for ax,field,title in zip(axes,('eef_error_mm','object_error_mm'),('End-effector position','Object position')):
        values=np.asarray([[next(r[field] for r in horizon_rows if r['method']==method and r['seed']==seed and r['horizon']==h) for h in range(1,9)] for seed in protocol['seeds']])
        mean=values.mean(0);sd=values.std(0,ddof=1)
        ax.plot(range(1,9),mean,marker='o',color=color,label=label)
        ax.fill_between(range(1,9),mean-sd,mean+sd,color=color,alpha=.15)
        ax.set(xlabel='Prediction step',ylabel='Mean position error (mm)',title=title,xticks=range(1,9));ax.grid(alpha=.2)
axes[0].legend()
fig.suptitle('Fixed development branches | mean +/- sample SD across3 seeds\nHead-only variants share Full dynamics; Direct has no state predictions',fontsize=12)
fig.savefig(directory/'physical_prediction.png',dpi=180);fig.savefig(directory/'physical_prediction.pdf');plt.close(fig)
print(json.dumps({'offline_complete':True,'models':len(rows),'records':rows}),flush=True)
