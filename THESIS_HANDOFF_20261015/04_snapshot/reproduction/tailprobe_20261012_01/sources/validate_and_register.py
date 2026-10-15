"""Register the frozen experiment after checking planning semantics."""
import ast
from collections import deque
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from evaluate_candidate_rollout import imagine, load_frozen, write_json

RUN = Path(__file__).resolve().parent
torch.set_num_threads(2)
ast.parse((ROOT/'evaluate_candidate_rollout.py').read_text(encoding='utf-8'))
model, policy, cfg = load_frozen()
assert all(not p.requires_grad for p in list(model.parameters())+list(policy.parameters()))
assert not model.training and not policy.training
before = {k:v.clone() for k,v in model.state_dict().items()}
checks=[]
def close(name, actual, expected, tolerance=0.):
    actual=np.asarray(actual); expected=np.asarray(expected)
    assert actual.shape == expected.shape, (name,actual.shape,expected.shape)
    error=float(np.max(np.abs(actual-expected))) if actual.size else 0.
    checks.append({'name':name,'max_absolute_error':error,'tolerance':tolerance,'passed':error<=tolerance})
    assert error<=tolerance,(name,error,tolerance)

with torch.no_grad():
    for path in sorted((ROOT/'reproduction/candidate_truth_20261012_01/audit').glob('*.npz')):
        data=np.load(path); state=data['anchor']; commands=data['commands']
        for delay in (0,2):
            queue=data['queue'] if delay else np.empty((0,7),np.float32)
            for mode in ('repeat','bc_tail'):
                label=f'{path.stem}/d{delay}/{mode}'
                plan=imagine(model,policy,state,queue,commands,mode)
                future=plan['future'].numpy(); executed=plan['executed'].numpy(); submitted=plan['submitted'].numpy()
                independent=[]
                for k in range(4):
                    fifo=deque(q.copy() for q in queue); actions=[]
                    for command in submitted[k]:
                        fifo.append(command.copy()); actions.append(np.clip(fifo.popleft(),-1,1))
                    independent.append(actions)
                close(label+'/fifo',executed,independent)
                close(label+'/candidate_execution_at_D',executed[:,delay],commands)
                close(label+'/first_submission',submitted[:,0],commands)
                x=torch.from_numpy(np.repeat(state[None],4,0))
                reference,readouts=model(x,plan['executed'])
                close(label+'/original_forward_states',future,reference.numpy())
                close(label+'/original_forward_labels',plan['logits'].numpy(),readouts.numpy())
                if delay:
                    close(label+'/common_prefix_states',future[:,:delay],np.repeat(future[0:1,:delay],4,0))
                if mode=='bc_tail':
                    for t in range(1,8):
                        expected=policy.best(plan['future'][:,t-1])[:,2].numpy()
                        close(label+f'/bc_tail_t{t}',submitted[:,t],expected)
                    if delay:
                        close(label+'/common_prefix_BC',submitted[:,1:delay+1],np.repeat(submitted[0:1,1:delay+1],4,0))
                else:
                    close(label+'/repeat_commands',submitted,np.repeat(commands[:,None],8,1))
                reverse=imagine(model,policy,state,queue,commands[::-1].copy(),mode)
                # This is a branch-prediction check; fallback k=2 is not relabelled.
                for field in ('future','logits','executed','submitted','scores'):
                    close(label+'/permutation_'+field,plan[field].numpy(),reverse[field].numpy()[::-1],1e-6)
                identical=imagine(model,policy,state,queue,np.repeat(commands[2:3],4,0),mode)
                close(label+'/identical_candidates',identical['future'].numpy(),np.repeat(identical['future'][0:1].numpy(),4,0))
                assert identical['selected']==2
    for key,value in model.state_dict().items():
        assert torch.equal(value,before[key]),key
verification={'passed':all(c['passed'] for c in checks),'checks':checks,'count':len(checks),
              'model_and_BC_frozen':True,'model_state_unchanged':True,
              'note':'Planning function receives current state, FIFO, candidates and frozen models only; no simulator handle.'}
write_json(RUN/'planning_verification.json',verification)
sources=['evaluate_candidate_rollout.py','evaluate_delay.py','world_model.py','common.py','collect_branches.py',
         'data/splits.json','models/headcal_20261012_01_calibrated_s17/model.pt',
         'policy/bc_chunk_dev_v4/policy_15000.pt']
protocol={'registered_before_closed_loop_results':True,'model':'headcal_20261012_01_calibrated_s17',
          'primary_comparison':['repeat','bc_tail'],'split':'dev','parents':json.loads((ROOT/'data/splits.json').read_text())['dev'],
          'training':False,'hyperparameter_search':False,'steps':400,'delay':2,'horizon':8,'candidates':[0,1,2,3],
          'fallback_index':2,'gate_margin':0.02,'risk_weight':0.5,'noise':0.,'score_only':True,
          'repeat':'Repeat the current candidate submission through the imagined horizon, after the existing FIFO prefix.',
          'bc_tail':'Submit candidate once; every later imagined command is BC k=2 computed from that branch predicted state; retain WM recurrent hidden state.',
          'execution':'Both modes commit only one command and replan using WM at every new real observation.',
          'input':'Privileged 23D state; no image-only claim.',
          'primary_metric':'Paired episode success over all 30 dev parents; report gains and losses, also compare fixed BC k=2.',
          'secondary_metrics':['episode steps with failures capped at 400','override fraction','decision latency with trace overhead excluded'],
          'integration_check':'Repeat must reproduce prior calibrated 30-parent outcomes; four traced parents must match original evaluator.',
          'trace_parents':['demo_105','demo_124','demo_97','demo_179'],
          'stop_rule':'No development success improvement versus repeat: stop this frozen-rollout branch, preserve negative result; do not tune or open sealed_test.',
          'positive_rule':'A dev gain motivates a separately registered data-aligned training comparison; it does not establish formal superiority.',
          'limitations':['Single trained seed and repeatedly inspected development parents.',
                         'Frozen WM trained using repeated candidate commands; BC-tail changes action sequence distribution.',
                         'BC continuation in imagination is an approximation to future WM replanning.',
                         'No sealed or new confirmation evaluation in this probe.'],
          'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources}}
write_json(RUN/'protocol.json',protocol)
print(json.dumps({'passed_checks':len(checks),'model_frozen':True,'protocol_registered':True}))
