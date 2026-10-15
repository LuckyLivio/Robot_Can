from pathlib import Path
import json,sys,time
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from recovery.kinematics import IK,fk,DATA
from recovery.geometry import vertical_margin
from reproduction.improvement_v8_20261015_01.recovery.recovery_controller import RecoveryController,Config
def main():
    old=ROOT/'reproduction/improvement_v8_20261015_01'
    samples=json.loads((old/'analysis/alignment_diagnosis.json').read_text())['samples']
    trace={r['step']:r for r in map(json.loads,(old/'pilot_b/v8_regression_6000005/trace.jsonl').open())}
    results=[]
    for s in [samples[0],samples[len(samples)//2],samples[-1]]:
        r=trace[s['step']];x=np.array(r['state_after'],np.float32);q=np.array([j['q'] for j in s['joints']])
        p,R=fk(q);lag=float(np.linalg.norm(p-x[:3]));assert lag<.003,lag
        c=RecoveryController([.1975,.4025,.8],.8,x);c.plan_grasp(x);goal=c.grasp_target(x);above=np.r_[goal[:2],max(1.,x[18]+.14)]
        item={'step':s['step'],'current_q':q.tolist(),'fk_observation_position_lag_m':lag,'options':[]}
        for flip in [False,True]:
            rot=c.planned_rotation@(np.diag([-1.,-1.,1.]) if flip else np.eye(3));start=q.copy();receipts=[]
            tic=time.perf_counter()
            for target in [above,goal]:
                ik=IK(start,target,rot)
                while not ik.advance():pass
                receipts.append(ik.receipt());start=ik.q
            item['options'].append({'flip':flip,'targets':receipts,'ms':1000*(time.perf_counter()-tic),'hand_margin':vertical_margin(above,goal,rot,.0655)})
        results.append(item)
    with (RUN/'analysis/kinematic_probe.json').open('x') as f:json.dump(results,f,indent=2)
    print(json.dumps(results))
if __name__=='__main__':main()
