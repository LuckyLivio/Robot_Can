"""Post-hoc solver initialization audit; never used to select evaluated actions."""
from pathlib import Path
import argparse,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from recovery.kinematics import IK,fk,LIMITS
from reproduction.improvement_v8_20261015_01.recovery.recovery_controller import RecoveryController,Config
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',default='regression_diagnosis_corrected_frame.json');args=parser.parse_args()
    folder=RUN/'pilot_a/v8_regression_6000049';job=json.loads((folder/'result.json').read_text())['job']
    rows=list(map(json.loads,(folder/'trace.jsonl').open()));x=np.array(rows[0]['state_before'],np.float32)
    c=RecoveryController([.1975,.4025,.8],.8,x,True,Config(**job['config']));prev=np.zeros(7,np.float32)
    for r in rows:
        x=np.array(r['state_before'],np.float32);c.choose(x,np.array(r['original_proposal'],np.float32),prev)
        prev=np.array(r['executed_action'],np.float32)
        if r['step']==117:break
    rot=c.planned_rotation.copy();goal=c.grasp_target(x);above=np.r_[goal[:2],max(1.,x[18]+.14)]
    out=[]
    for step in [117,172,193]:
        r=rows[step-1];q=np.array(r['joint_positions']);p,R=fk(q);entry={'initial_q_from_baseline_step':step,
              'measured_limit_margin_rad':float(np.min(np.minimum(q-LIMITS[:,0],LIMITS[:,1]-q))),
              'fk_position':p.tolist(),'orientation_error_to_planned_rad':float(np.linalg.norm(Rotation.from_matrix(rot@R.T).as_rotvec())),
              'solves':[]}
        for label,target in [('above',above),('grasp',goal)]:
            ik=IK(q,target,rot)
            while not ik.advance():pass
            entry['solves'].append({'target':label,**ik.receipt()})
        out.append(entry)
    receipt={'case':'BC noise demo_6000049','baseline_success':True,'v9_success':False,'samples':out,
             'scope':'Post-hoc diagnostic using saved successful baseline states. Future baseline states were NOT available to the evaluated controller. Finite local IK failure is not a proof of infeasibility.'}
    receipt['orientation_frame']='robot0_eef_quat body orientation; corrected site-to-body transform'
    with (RUN/'analysis'/args.receipt).open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt))
if __name__=='__main__':main()
