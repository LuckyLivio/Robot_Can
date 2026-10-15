"""Serial recorded-input microbenchmark; not physical-policy inference timing."""
import json,sys,time,hashlib
from pathlib import Path
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from verify_run import load
from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v9_20261015_01.recovery.geometry import projected_parts
old=load(RUN/'pilot_a/source/recovery/recovery_controller.py');results=[]
for case in ['regression_6000049','regression_6000005']:
    p=RUN/'pilot_a'/('v10_'+case);job=json.loads((p/'result.json').read_text())['job'];rows=[json.loads(l) for l in (p/'trace.jsonl').open()]
    for repeat in range(3):
        for name,cls,cfg in ([('archived',old.RecoveryController,old.Config),('current',RecoveryController,Config)] if repeat%2==0 else [('current',RecoveryController,Config),('archived',old.RecoveryController,old.Config)]):
            projected_parts.cache_clear();c=cls([.1975,.4025,.8],.8,np.array(rows[0]['state_before'],np.float32),True,cfg(**job['config']));dur=[];prev=np.zeros(7,np.float32)
            for row in rows:
                c.set_joint_positions(row['joint_positions']);x=np.array(row['state_before'],np.float32);proposal=np.array(row['original_proposal'],np.float32)
                tic=time.perf_counter();a,d=c.choose(x,proposal,prev);dur.append(1000*(time.perf_counter()-tic))
                np.testing.assert_allclose(a,row['submitted_action'],rtol=0,atol=1e-7);prev=np.array(row['executed_action'],np.float32)
            results.append({'case':case,'repeat':repeat,'version':name,'steps':len(rows),'total_ms':sum(dur),'p99_ms':float(np.percentile(dur,99)),'max_ms':max(dur),'over_50ms':sum(t>50 for t in dur)})
report={'passed':True,'same_controls':True,'measure':'serial supervisor choose() on recorded inputs only; excludes BC/WM/physics/render/logging; three order-alternated repetitions','rows':results,
        'source_sha256':{p.relative_to(RUN).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (RUN/'recovery').glob('*.py')}}
with (RUN/'analysis/guard_timing_microbenchmark.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
