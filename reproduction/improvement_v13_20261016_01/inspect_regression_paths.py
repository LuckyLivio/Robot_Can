"""Read-only internal-state replay of two confirmation failures versus v6."""
from pathlib import Path
import json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from variants import controller_class
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin

if __name__=='__main__':
    out=[]
    for condition,demo,selected in [('bc_k2_noise005','demo_13000021',[206,270,277,344,400]),
                                    ('full_s41_noise005','demo_13000022',[230,231,364,371,372,400])]:
        p=RUN/'confirmation'/('v13_'+condition);job=json.loads((p/'result.json').read_text())['job'];c=None
        for row in map(json.loads,(p/'trace.jsonl').open()):
            if row['demo']!=demo:continue
            x=np.array(row['state_before'],np.float32);q=np.array(row['joint_positions'])
            if c is None:
                cls,cfg=controller_class('v13');c=cls([.1975,.4025,.8],.8,x,True,cfg(**job['config']))
            c.set_joint_positions(q);phase=c.mode;plan=c.edge_plan;goal=None
            if plan is not None and phase in ['EDGE_ROTATE','EDGE_APPROACH']:
                goal=c.edge_start if phase=='EDGE_ROTATE' else plan['above']
            features={'condition':condition,'demo':demo,'step':row['step'],'mode_before':phase,
                      'measured_joint_margin_rad':float(np.min(np.minimum(q-LIMITS[:,0],LIMITS[:,1]-q)))}
            if goal is not None:
                angle=np.linalg.norm(Rotation.from_matrix(plan['rotation']@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec())
                features.update(position_error_m=float(np.linalg.norm(x[:3]-goal)),angle_error_rad=float(angle),
                                position_threshold_m=.009,angle_threshold_rad=.08,goal=np.asarray(goal).tolist())
            if plan is not None and phase=='DESCEND':
                gap=abs(float(x[7]-x[8]));rot=Rotation.from_quat(x[3:7]).as_matrix()
                features['current_can_margin_m']=object_margin(x[:3],c.grasp_target(x),rot,[gap-.001,gap+.001],x)
            action,info=c.choose(x,np.array(row['original_proposal'],np.float32),np.array(row['queue_before'][0],np.float32) if row['step']==1 else previous)
            np.testing.assert_allclose(action,row['submitted_action'],rtol=0,atol=1e-7)
            previous=np.array(row['executed_action'],np.float32)
            if row['step'] in selected:features['mode_after']=c.mode;out.append(features)
    result={'passed':True,'diagnostic_saved_input_replay_only':True,'samples':out,
            'note':'No new physical episodes or parameter changes. Margins describe observed execution, not a full-arm safety certificate.'}
    with (RUN/'analysis/confirmation_path_diagnosis.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
