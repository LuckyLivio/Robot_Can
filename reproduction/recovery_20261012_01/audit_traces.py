"""Replay observation-only decisions and enforce the original D2/noise semantics."""
import json
from collections import deque,Counter
import numpy as np
from recovery_controller import RecoveryController,Config


def audit(directory):
    result=json.loads((directory/'result.json').read_text());assert result['status']=='complete'
    job=result['job'];rows={r['demo']:r for r in result['records']}
    seen=[];last=None;counts={};controls=0
    for line in (directory/'trace.jsonl').open():
        r=json.loads(line);name=r['demo'];x=np.asarray(r['state_before'],np.float32)
        if name!=last:
            if last is not None:finish()
            assert name not in seen;seen.append(name);last=name
            controller=RecoveryController([.1975,.4025,.8],.8,x,job.get('enabled',True),Config(**job.get('config',{})))
            queue=deque([np.zeros(7,np.float32) for _ in range(2)],maxlen=3)
            rng=np.random.default_rng(70000+int(name.split('_')[1]));previous=np.zeros(7,np.float32)
            step=0;before=x.copy();interventions=0;stable=0;modes=Counter();faults=0
        step+=1;controls+=1;assert r['step']==step and step<=400
        np.testing.assert_array_equal(before,x)
        np.testing.assert_array_equal(r['queue_before'],list(queue))
        proposal=np.asarray(r['original_proposal'],np.float32)
        command,diagnostic=controller.choose(x,proposal,previous)
        assert diagnostic==r['recovery'],(name,step,'decision replay')
        if r['fault_injected']:command[6]=-1;faults+=1
        np.testing.assert_allclose(command,r['submitted_action'],rtol=0,atol=1e-7)
        assert np.isfinite(command).all() and abs(command).max()<=1
        queue.append(np.asarray(r['submitted_action'],np.float32));applied=queue.popleft()
        np.testing.assert_array_equal(applied,r['executed_action_before_noise'])
        if job['noise']:applied[:3]+=rng.normal(0,job['noise'],3)
        previous=np.clip(applied,-1,1);np.testing.assert_array_equal(previous,r['executed_action'])
        before=np.asarray(r['state_after'],np.float32);assert np.isfinite(before).all()
        interventions+=diagnostic['intervened'];stable+=diagnostic['stable_hold'];modes[diagnostic['mode']]+=1
        assert controller.attempts<=2
        if r['success_after']:assert step==rows[name]['steps']
        def finish():
            summary=rows[last]
            assert summary['steps']==step
            assert summary['success']==r['success_after'] if r['demo']==last else summary['steps']<400 or not summary['success']
            assert summary['intervention_steps']==interventions and summary['stable_hold_steps']==stable
            assert summary['phases']==dict(modes) and summary['attempts']==controller.attempts
            assert summary['events']==controller.events
            assert summary['verified_regrasps']==controller.verified_regrasps
            assert summary['failed_attempts']==controller.failed_attempts
            if not summary['success']:assert step==400
            if job.get('fault')=='open_after_verified_lift':assert faults==12
            counts[last]={'steps':step,'fault_commands':faults}
    if last is not None:finish()
    assert seen==job['demos'] and len(rows)==len(seen)
    return {'job':job['id'],'episodes':len(rows),'controls':controls,'checks':'observation-only replay, FIFO, noise, finite actions, bounded retries, complete traces','counts':counts}
