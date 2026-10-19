import json
from collections import deque,Counter
import numpy as np
def audit(directory):
    result=json.loads((directory/'result.json').read_text());assert result['status']=='complete';job=result['job']
    rows={r['demo']:r for r in result['records']};seen=[];current=None;count=0;replays=[]
    cls,cfg=controller_class(job['version'])
    def finish(name,steps,last,controller,interventions,stable,modes):
        s=rows[name];assert s['steps']==steps and s['success']==last['success_after']
        assert s['success'] or steps==400
        assert s['attempts']==controller.attempts and s['events']==controller.events
        assert s['verified_regrasps']==controller.verified_regrasps and s['failed_attempts']==controller.failed_attempts
        assert s['intervention_steps']==interventions and s['stable_hold_steps']==stable and s['phases']==dict(modes)
        if s['success']:assert not earlier_success
    for line in (directory/'trace.jsonl').open():
        row=json.loads(line);name=row['demo'];x=np.asarray(row['state_before'],np.float32)
        if name!=current:
            if current is not None:finish(current,steps,last,controller,interventions,stable,modes)
            assert name not in seen;seen.append(name);current=name
            controller=cls([.1975,.4025,.8],.8,x,job['enabled'],cfg(**job.get('config',{})))
            pending=deque([np.zeros(7,np.float32) for _ in range(2)],maxlen=3)
            rng=np.random.default_rng(70000+int(name.split('_')[1]));previous=np.zeros(7,np.float32);before=x.copy()
            steps=0;interventions=0;stable=0;modes=Counter();earlier_success=False
            fault_left=0;fault_step=None
        else:earlier_success=earlier_success or last['success_after']
        steps+=1;count+=1;assert row['step']==steps<=400
        np.testing.assert_array_equal(before,x);np.testing.assert_array_equal(row['queue_before'],list(pending))
        if hasattr(controller,'set_joint_positions'):controller.set_joint_positions(row['joint_positions'])
        if job.get('force_recovery_at')==steps:controller.start_attempt('diagnostic_forced_start',x)
        command,diag=controller.choose(x,np.asarray(row['original_proposal'],np.float32),previous)
        saved=dict(row['recovery']);saved.pop('planning_ms',None);comparison=dict(diag);comparison.pop('planning_ms',None)
        assert comparison==saved,(job['id'],name,steps,'controller replay')
        if job.get('fault')=='open_after_verified_lift' and fault_step is None and diag['stable_hold'] and .89<x[18]<.96 and np.linalg.norm(x[16:18]-controller.target[:2])>.30:
            fault_step=steps;fault_left=12
        assert row['fault_injected']==(fault_left>0)
        if fault_left>0:command[6]=-1.;fault_left-=1
        np.testing.assert_allclose(command,row['submitted_action'],rtol=0,atol=1e-7)
        assert abs(command).max()<=1 and np.isfinite(command).all() and controller.attempts<=2
        if not job.get('fault_policy'):
            np.testing.assert_array_equal(row['original_proposal'],row['base_chunk'][row['original_selected']])
        if job['method']=='full':
            scores=np.array(row['original_scores']);raw=int(scores.argmax());chosen=2 if raw!=2 and scores[raw]-scores[2]<.02 else raw
            assert chosen==row['original_selected']
        else:assert row['original_selected']==2
        pending.append(np.asarray(row['submitted_action'],np.float32));action=pending.popleft()
        np.testing.assert_array_equal(action,row['executed_action_before_noise'])
        if job['noise']:action[:3]+=rng.normal(0,job['noise'],3)
        previous=np.clip(action,-1,1);np.testing.assert_array_equal(previous,row['executed_action'])
        before=np.asarray(row['state_after'],np.float32);assert np.isfinite(before).all()
        interventions+=diag['intervened'];stable+=diag['stable_hold'];modes[diag['mode']]+=1;last=row
    finish(current,steps,last,controller,interventions,stable,modes)
    assert seen==job['demos'] and len(seen)==len(rows)
    return {'job':job['id'],'episodes':len(rows),'controls':count}
