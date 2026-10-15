"""Recorded-state failure audit, without further experiments or tuning."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController
from reproduction.recovery_v5_20261012_01.clearance import side_cell
def main():
    report=json.loads((RUN/'analysis/dev_comparison.json').read_text());out=[]
    for f in report['failures']:
        trace=[json.loads(l) for l in (RUN/'dev_a'/f['job']/'trace.jsonl').open() if '"demo": "'+f['demo']+'"' in l]
        c=RecoveryController([.1975,.4025,.8],.8,np.array(trace[0]['state_before'],np.float32))
        events=[]
        for e in f['events']:
            row=trace[max(0,e['step']-1)];x=np.array(row['state_before'],np.float32)
            axis=Rotation.from_quat(x[19:23]).as_matrix()[:,2]
            c.plan_grasp(x)
            events.append({'step':e['step'],'to':e['to'],'reason':e['reason'],'object_position':x[16:19].tolist(),
                           'axis_z':float(axis[2]),'side_cell':side_cell(x[16:19],axis,.8),
                           'upright_cell':c.resting_cell(x),'eef_position':x[:3].tolist(),
                           'grasp_target_error_m':float(np.linalg.norm(c.grasp_target(x)-x[:3])),
                           'observed_gap_m':abs(float(x[7]-x[8]))})
        last=trace[-1]
        oldpath=ROOT/'reproduction/recovery_v5_20261012_01/dev_a'/('v5'+f['job'][2:])/'trace.jsonl'
        old=[json.loads(l) for l in oldpath.open() if '"demo": "'+f['demo']+'"' in l]
        first_change=next((r['step'] for r,b in zip(trace,old) if r['submitted_action']!=b['submitted_action']),None)
        out.append({'job':f['job'],'demo':f['demo'],'first_command_change_from_v5':first_change,
                    'final_object_position':last['state_after'][16:19],'events':events,
                    'v5_descent_steps':sum(r['recovery']['mode']=='DESCEND' for r in old),
                    'v6_descent_steps':sum(r['recovery']['mode']=='DESCEND' for r in trace)})
    with (RUN/'analysis/failure_audit.json').open('x',encoding='utf8') as f:json.dump(out,f,indent=2)
    for r in out:print(json.dumps(r),flush=True)
if __name__=='__main__':main()
