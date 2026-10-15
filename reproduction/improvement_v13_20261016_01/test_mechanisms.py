from pathlib import Path
import argparse,ast,json,sys,time
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from reproduction.improvement_v13_20261016_01.recovery.support import support
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v12_20261015_01.recovery.recovery_controller import RecoveryController as V12,Config as C12
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='mechanisms_a');args=parser.parse_args()
    for p in list(RUN.glob('*.py'))+list((RUN/'recovery').glob('*.py')):ast.parse(p.read_text(encoding='utf8'))
    old=ROOT/'reproduction/improvement_v12_20261015_01';cases=[];saved=[]
    for job,demo in [('v12_bc_k2_clean','demo_12000011'),('v12_full_s23_clean','demo_12000036'),('v12_full_s23_noise005','demo_12000021')]:
        row=[r for r in map(json.loads,(old/'confirmation'/job/'trace.jsonl').open()) if r['demo']==demo][-1]
        x=np.array(row['state_before'],np.float32);d,reason=support(x,.8);assert d is not None and 'patches' in d
        saved.append((x,row));cases.append({'case':demo,'kind':d['kind'],'patches':d['patches']})
        for label,delta in [('airborne',.15),('penetrating',-.020)]:
            y=x.copy();y[18]+=delta;domain,r=support(y,.8);assert domain is None,(demo,label,r)
            cases.append({'case':demo+'_'+label,'reason':r})
    x,row=saved[0];c=RecoveryController([.1975,.4025,.8],.8,x);c.poses.extend([x[16:23].copy() for _ in range(4)])
    assert c.raw_settled(x)
    moved=x.copy();moved[16]+=.02;assert not c.raw_settled(moved)
    c.set_joint_positions(row['joint_positions']);c.clock=240;c.age=60;c.attempts=1
    V5.enter(c,'POSE_BLOCKED','synthetic_test',x);c.wait_since=100;c.try_escape(x);assert c.escape_count==0
    c.clock=160;c.try_escape(x);assert c.escape_count==1
    c.try_escape(x);assert c.escape_count==1
    command,info=c.choose(x,np.zeros(7,np.float32),np.zeros(7,np.float32))
    assert c.clock==161 and c.attempts==1 and info['mode']!='DESCEND'
    json.dumps(info,allow_nan=False)
    # Exact off-mode comparison on all old 38 diagnostic episodes, including
    # inherited forced-start conditions. This is input replay, not new physics.
    episodes=steps=0
    for job in json.loads((old/'pilot_a/jobs.json').read_text()):
        if job['version']!='v12':continue
        current=None
        for r in map(json.loads,(old/'pilot_a'/job['id']/'trace.jsonl').open()):
            x=np.array(r['state_before'],np.float32)
            if r['demo']!=current:
                current=r['demo'];episodes+=1;previous=np.zeros(7,np.float32)
                config=job['config'];a=V12([.1975,.4025,.8],.8,x,True,C12(**config))
                b=RecoveryController([.1975,.4025,.8],.8,x,True,Config(**config,stable_support=False,wait_escape=False))
            for c in [a,b]:
                c.set_joint_positions(r['joint_positions'])
                if job.get('force_recovery_at')==r['step']:c.start_attempt('diagnostic_forced_start',x)
            aa,ad=a.choose(x,np.array(r['original_proposal'],np.float32),previous)
            ba,bd=b.choose(x,np.array(r['original_proposal'],np.float32),previous)
            ad.pop('planning_ms',None);bd.pop('planning_ms',None)
            np.testing.assert_array_equal(aa,ba);assert ad==bd and a.events==b.events
            previous=np.array(r['executed_action'],np.float32);steps+=1
    result={'passed':True,'support_cases':cases,'off_replay_episodes':episodes,'off_replay_steps':steps,
            'temporal_stability_check':True,'escape_budget_and_count_check':True,'note':'Synthetic geometry and saved-input replay only; no new success-rate samples.'}
    with (RUN/'analysis'/f'{args.output}.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='support_cases'}))
