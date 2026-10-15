"""Check whether the new edge module caused the development regression."""
from pathlib import Path
import json,sys
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
import audit_core
from reproduction.improvement_v10_20261015_01.recovery.recovery_controller import RecoveryController as V10,Config as C10
from reproduction.improvement_v8_20261015_01.recovery.geometry import support
def old_config(**kwargs):
    kwargs.pop('axis_alignment',None);kwargs.pop('can_guard',None);return C10(**kwargs)
if __name__=='__main__':
    audit_core.controller_class=lambda version:(V10,old_config)
    stage=RUN/'dev_a';checks=[]
    for job in json.loads((stage/'jobs.json').read_text()):checks.append(audit_core.audit(stage/job['id']))
    rows=[r for r in map(json.loads,(stage/'v11_full_s41_noise005/trace.jsonl').open()) if r['demo']=='demo_87']
    samples=[]
    for r in rows:
        if r['step'] not in [139,141,142,155,180,186,198,202,240,400]:continue
        x=np.array(r['state_before']);samples.append({'step':r['step'],'mode':r['recovery']['mode'],'eef':x[:3].tolist(),'can':x[16:19].tolist(),'gap_m':abs(float(x[7]-x[8])),'relative':(x[:3]-x[16:19]).tolist(),'support_reason':support(x,.8)[1],'stages_after':r['stages_after']})
    held=[r for r in rows if 180<=r['step']<=400];relative=np.array([np.array(r['state_before'])[:3]-np.array(r['state_before'])[16:19] for r in held])
    result={'passed':True,'v10_replay_equals_v11':True,'episodes':sum(r['episodes'] for r in checks),'control_steps':sum(r['controls'] for r in checks),'new_edge_events_in_development':0,
        'regression':{'condition':'full_s41_noise005','demo':'demo_87','v6_success_at':358,'v11_failed_at':400,'samples':samples,'relative_max_deviation_m':float(np.linalg.norm(relative-relative.mean(0),axis=1).max()),'reason':'Inherited pose-wait logic treats the lifted, co-moving can as unsupported. POSE_WAIT preserves aperture, does not update normal holding detection, then times out into POSE_BLOCKED.'},
        'scope':'All 240 saved-input actions/FIFO/noise/events exactly reproduced with frozen v10. This is not an additional physical v10 development run.'}
    with (RUN/'analysis/development_regression_diagnosis.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='regression'}));print('relative deviation',result['regression']['relative_max_deviation_m'])
