"""Replay frozen v11 on recorded v12 observations; no counterfactual outcomes."""
from pathlib import Path
from dataclasses import fields
import json,sys
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from reproduction.improvement_v11_20261015_01.recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v8_20261015_01.recovery.geometry import support,CAN
from scipy.spatial.transform import Rotation
if __name__=='__main__':
    summary=json.loads((RUN/'analysis/confirmation.json').read_text());reg={tuple(k) for k in summary['regressions']}
    results=[];count=0
    for j in json.loads((RUN/'confirmation/jobs.json').read_text()):
        if j['version']!='v12':continue
        cfg=Config(**{k:v for k,v in j['config'].items() if k in {f.name for f in fields(Config)}})
        previous=None;current=None;record=None
        for r in map(json.loads,(RUN/'confirmation'/j['id']/'trace.jsonl').open()):
            x=np.array(r['state_before'],np.float32)
            if r['demo']!=current:
                if record:results.append(record)
                current=r['demo'];c=RecoveryController([.1975,.4025,.8],.8,x,True,cfg);previous=np.zeros(7,np.float32)
                record={'condition':j['id'].split('_',1)[1],'demo':current,'steps':0,'first_command_difference':None,'v12_success':False}
            c.set_joint_positions(r['joint_positions']);action,_=c.choose(x,np.array(r['original_proposal'],np.float32),previous)
            if not np.array_equal(action,np.array(r['submitted_action'],np.float32)) and record['first_command_difference'] is None:
                record['first_command_difference']=r['step']
            record['steps']+=1;record['v12_success']=r['success_after'];count+=1;previous=np.array(r['executed_action'],np.float32)
            if r['step']==400 and not r['success_after']:
                end=np.array(r['state_after']);rot=Rotation.from_quat(end[19:23]).as_matrix();_,reason=support(end,.8)
                record['terminal_geometry']={'mesh_support_reason':reason,'reported_feasibility':r['recovery'].get('feasibility_reason'),
                    'axis_abs_z':abs(float(rot[2,2])),'can_bottom_z_m':float((CAN@rot.T+end[16:19])[:,2].min()),
                    'object_position':end[16:19].tolist(),'mode':r['recovery']['mode']}
        if record:results.append(record)
    same=sum(r['first_command_difference'] is None for r in results)
    out={'passed':True,'episodes':len(results),'control_steps':count,'v11_commands_identical_entire_trajectory':same,
         'changed':[r for r in results if r['first_command_difference'] is not None],
         'regression_attribution':[r for r in results if (r['condition'],r['demo']) in reg],
         'scope':'Recorded-input v11 decision replay, not physical v11 closed-loop evaluation. An entirely identical command trajectory supports inheritance attribution; after first divergence no counterfactual v11 success is inferred.'}
    with (RUN/'analysis/confirmation_attribution.json').open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps({k:v for k,v in out.items() if k!='scope'},indent=2))
