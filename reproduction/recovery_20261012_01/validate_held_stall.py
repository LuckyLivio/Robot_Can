"""Training-only physical test: hold still after lifting, then let the supervisor act."""
import json
import torch
import numpy as np
import evaluate_recovery as evaluator
from setup_study import RUN,write

original_loader=evaluator.load_policy
class StalledPolicy:
    def __init__(self,policy):self.policy=policy;self.triggered=False;self.calls=0;self.trigger_step=None
    def best(self,states):
        self.calls+=1;x=states[0].numpy()
        if not self.triggered and .90<x[18]<.96 and .025<abs(x[7]-x[8])<.067 and np.linalg.norm(x[:3]-x[16:19])<.04:
            self.triggered=True;self.trigger_step=self.calls
        if self.triggered:
            commands=torch.zeros((1,8,7));commands[:,:,6]=1.;return commands
        return self.policy.best(states)

def main():
    out=RUN/'extra_pilot';out.mkdir(exist_ok=False)
    wrappers=[]
    def loader(path):
        wrapper=StalledPolicy(original_loader(path));wrappers.append(wrapper);return wrapper
    evaluator.load_policy=loader
    job={'id':'held_stall','method':'bc_k2','seed':None,'noise':0.,'enabled':True,'demos':['demo_54'],
         'fault':'policy emits zero motion and closed gripper after the object is lifted; supervisor may override'}
    result=evaluator.run(job,out/'held_stall');row=result['records'][0]
    assert wrappers[0].triggered and row['success'] and any(e['reason']=='held_stall' for e in row['events'])
    evaluator.load_policy=original_loader
    full=evaluator.run({'id':'full_noisy_recovery','method':'full','seed':17,'noise':.05,'enabled':True,
                        'demos':['demo_54','demo_133']},out/'full_noisy_recovery')
    assert all(r['success'] for r in full['records'])
    write(out/'validation.json',{'passed':True,'held_stall_trigger_step':wrappers[0].trigger_step,
                                'held_stall_final_success':row['success'],'full_noisy_successes':2})

if __name__=='__main__':main()
