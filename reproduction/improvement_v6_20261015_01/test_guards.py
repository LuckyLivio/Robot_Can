"""Transition edge cases and D=2 sign-actuator behavior, without simulation."""
from pathlib import Path
import argparse,json,sys
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from recovery.recovery_controller import RecoveryController,Config

def state():
    x=np.zeros(23,np.float32);x[:3]=[.1,-.25,1.05];x[3:7]=[1,0,0,0]
    x[16:19]=[.1,-.25,.86];x[19:23]=[0,0,0,1];x[7:9]=[.04,-.04]
    return x
def controller(x):return RecoveryController([.1975,.4025,.8],.8,x)

def main():
    p=argparse.ArgumentParser();p.add_argument('--receipt',default='guard_unit_checks.json');args=p.parse_args()
    x=state();z=np.zeros(7,np.float32);checks=[]
    with patch('recovery.recovery_controller.candidates',return_value=([],True)):
        c=controller(x);c.start_attempt('diagnostic_forced_start',x)
        for _ in range(12):a,d=c.choose(x,z,z)
        assert c.mode=='BLOCKED' and a[2]>=0 and not any(e['to']=='DESCEND' for e in c.events)
        assert c.attempts==1;checks.append('no_candidates_forced_start_retracts_then_blocks_without_descent')
        c=controller(x);c.clock=159;c.age=159
        a,d=c.choose(x,z,z)
        assert c.mode=='ABORT_RETRACT' and a[2]>=0
        checks.append('no_candidates_trigger_inside_base_choose_dispatches_safely')
        c=controller(x);c.mode='DESCEND';c.guard_scope=True;c.approach_gap=.056;c.plan_anchor=x[16:23].copy()
        a,d=c.choose(x,z,z)
        assert c.mode=='ABORT_RETRACT' and a[2]>=0
        checks.append('gap_violation_at_descent_safely_retracts')
    c=controller(x);c.mode='ALIGN';c.approach_gap=.056
    queue=[0.,0.];gap=.08;commands=[]
    for _ in range(30):
        c.clock+=1;x[7:9]=[gap/2,-gap/2];c.gaps.append(gap)
        a=c.pose_action(x,x[:3],-1);commands.append(float(a[6]))
        queue.append(float(a[6]));gap=float(np.clip(gap-.008*np.sign(queue.pop(0)),0.,.08))
    assert abs(gap-.056)<1e-6 and c.gap_ready(x)
    assert commands.count(1.)==3 and commands.count(-1.)==0
    checks.append('discrete_sign_gripper_with_D2_converges_without_repeated_pulses')
    result={'passed':True,'checks':checks,'gripper_model_note':'Idealized .008 m sign increment plus D2; real actuator is checked separately in pilot traces.'}
    with (RUN/'analysis'/args.receipt).open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
if __name__=='__main__':main()
