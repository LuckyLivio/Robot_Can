from pathlib import Path
import json, sys
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v11_20261015_01.recovery.recovery_controller import RecoveryController as V11,Config as C11

def state(z=.90):
    x=np.zeros(23,np.float32);x[3]=1.;x[22]=1.
    x[:3]=[.1,-.1,z+.015];x[16:19]=[.1,-.1,z];x[7:9]=[.025,-.025]
    return x

def synthetic(kind):
    x=state();c=RecoveryController([.1975,.4025,.8],.8,x,True,Config())
    c.attempts=1;c.begin_wait('mechanism_test',x);c._previous_action=np.zeros(7,np.float32)
    moves=[]
    for i in range(12):
        x=state(.90+i*.006)
        if kind=='near_unheld':x[18]=.90
        if kind=='support_motion':x[2]=.915
        if kind=='stationary':x=state()
        if kind=='collision':x[16]+=.012*(i%2)
        if kind=='off_center':x[16]+=.04
        if kind=='open_gap':x[7:9]=[.04,-.04]
        if kind=='opening':c._previous_action[6]=-1
        a,d=c.wait_action(x);moves.append(d['mode'])
        assert c.clock==i+1 and c.attempts==1
        if c.mode=='LIFT':break
    return c,x,moves

if __name__=='__main__':
    cases={}
    for name in ['held','near_unheld','support_motion','stationary','collision','off_center','open_gap','opening']:
        c,x,modes=synthetic(name);yes=c.mode=='LIFT';assert yes==(name=='held'),(name,modes)
        cases[name]={'transfer_to_lift':yes,'calls':len(modes)}
    c,x,_=synthetic('held');x[16]+=.15
    from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5
    for _ in range(c.cfg.stable_frames):
        c.set_joint_positions([0,-.4,0,-2.,0,1.6,.8])
        _,d=c.choose(x,np.zeros(7,np.float32),np.zeros(7,np.float32))
    assert any(e['reason']=='observed_grasp_loss' for e in c.events)
    cases['true_loss']={'loss_detected':True,'attempts':c.attempts}
    # All v11 diagnostic inputs plus the known development regression, with the
    # new feature disabled. Compare actual commands, diagnostics and events.
    inputs=list((ROOT/'reproduction/improvement_v11_20261015_01/pilot_a').glob('v11_*/trace.jsonl'))
    inputs.append(ROOT/'reproduction/improvement_v11_20261015_01/dev_a/v11_full_s41_noise005/trace.jsonl')
    episodes=steps=0
    for p in inputs:
        j=json.loads(p.with_name('result.json').read_text())['job'];last=None
        for row in map(json.loads,p.open()):
            if 'dev_a' in p.parts and row['demo']!='demo_87':continue
            x=np.array(row['state_before'],np.float32)
            if row['demo']!=last:
                last=row['demo'];episodes+=1;prev=np.zeros(7,np.float32)
                a=V11([.1975,.4025,.8],.8,x,True,C11(**j['config']))
                b=RecoveryController([.1975,.4025,.8],.8,x,True,Config(**j['config'],wait_hold_history=False))
            for c in [a,b]:
                c.set_joint_positions(row['joint_positions'])
                if j.get('force_recovery_at')==row['step']:c.start_attempt('diagnostic_forced_start',x)
            proposal=np.array(row['original_proposal'],np.float32);aa,da=a.choose(x,proposal,prev);bb,db=b.choose(x,proposal,prev)
            for d in [da,db]:d.pop('planning_ms',None)
            np.testing.assert_array_equal(aa,bb);assert da==db and a.events==b.events
            assert a.clock==b.clock and a.attempts==b.attempts
            prev=np.array(row['executed_action'],np.float32);steps+=1
    # A diagnostic reproduction on saved old observations, not a new rollout.
    p=inputs[-1];j=json.loads(p.with_name('result.json').read_text())['job'];c=None;transition=None
    for row in map(json.loads,p.open()):
        if row['demo']!='demo_87':continue
        x=np.array(row['state_before'],np.float32)
        if c is None:c=RecoveryController([.1975,.4025,.8],.8,x,True,Config(**j['config']));prev=np.zeros(7,np.float32)
        c.set_joint_positions(row['joint_positions']);c.choose(x,np.array(row['original_proposal'],np.float32),prev)
        if c.wait_hold_events and c.mode=='LIFT':transition=row['step'];break
        prev=np.array(row['executed_action'],np.float32)
    assert transition is not None
    result={'passed':True,'synthetic_cases':cases,'off_episodes':episodes,'off_steps':steps,
            'saved_input_demo87_transition_step':transition,'note':'Synthetic mechanism checks and saved-input replay, not new success evaluations.'}
    with (RUN/'analysis/mechanisms_a.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
