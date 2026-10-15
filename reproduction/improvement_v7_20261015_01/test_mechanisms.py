"""Recorded-input v6 equivalence and pose/unknown transition tests."""
from pathlib import Path
import argparse,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6

def state():
    x=np.zeros(23,np.float32);x[:3]=[.1,-.25,1.05];x[3:7]=[1,0,0,0]
    x[16:19]=[.1,-.25,.86];x[19:23]=[0,0,0,1];x[7:9]=[.04,-.04]
    return x

def main():
    p=argparse.ArgumentParser();p.add_argument('--receipt',default='mechanisms_a.json');args=p.parse_args()
    steps=episodes=0
    for file in sorted((ROOT/'reproduction/improvement_v6_20261015_01/dev_a').glob('*/trace.jsonl')):
        last=None
        for line in file.open():
            r=json.loads(line);x=np.array(r['state_before'],np.float32)
            if r['demo']!=last:
                last=r['demo'];episodes+=1;previous=np.zeros(7,np.float32)
                a=V6([.1975,.4025,.8],.8,x)
                b=RecoveryController([.1975,.4025,.8],.8,x,config=Config(replan_on_change=False,unknown_guard=False))
            proposal=np.array(r['original_proposal'],np.float32)
            aa,da=a.choose(x,proposal,previous);bb,db=b.choose(x,proposal,previous)
            np.testing.assert_array_equal(aa,bb);assert da==db and a.events==b.events
            previous=np.array(r['executed_action'],np.float32);steps+=1
    checks=[];z=np.zeros(7,np.float32);x=state()
    c=RecoveryController([.1975,.4025,.8],.8,x);c.start_attempt('test',x)
    x[19:23]=Rotation.from_euler('x',90,degrees=True).as_quat();x[18]=.845
    a,d=c.choose(x,z,z);json.dumps(d,allow_nan=False);assert c.mode=='POSE_WAIT' and c.attempts==1
    for _ in range(10):
        a,d=c.choose(x,z,z);json.dumps(d,allow_nan=False)
    assert c.pose_replans==1 and c.grasp_kind=='sideways' and c.mode=='ALIGN' and c.attempts==1
    checks.append('changed_pose_invalidates_plan_and_replans_after_observed_settling_without_extra_attempt')
    x=state();x[16:19]=[.1,.01,.95]
    c=RecoveryController([.1975,.4025,.8],.8,x);c.start_attempt('test',x);c.enter('DESCEND','test',x)
    assert c.mode=='POSE_WAIT'
    for _ in range(60):a,d=c.choose(x,z,z)
    assert c.mode=='POSE_BLOCKED' and not any(e['to']=='DESCEND' for e in c.events) and c.clock==60
    checks.append('unknown_wait_is_bounded_and_never_defaults_to_descent')
    x=state();c=RecoveryController([.1975,.4025,.8],.8,x);c.start_attempt('test',x)
    x[19:23]=Rotation.from_euler('z',120,degrees=True).as_quat();assert not c.pose_changed(x)
    checks.append('cylinder_axial_spin_does_not_trigger_spurious_replan')
    c.pose_replans=c.cfg.max_pose_replans;x[16]+=.03;c.choose(x,z,z)
    for _ in range(10):c.choose(x,z,z)
    assert c.mode=='POSE_BLOCKED' and c.pose_replans==2
    checks.append('replan_limit_preserves_fixed_horizon')
    out={'passed':True,'disabled_exact_episodes':episodes,'disabled_exact_steps':steps,'checks':checks,
         'scope':'Recorded-input control equivalence and synthetic state transitions; physical tests separate.'}
    with (RUN/'analysis'/args.receipt).open('x',encoding='utf8') as f:json.dump(out,f,indent=2)
    print(json.dumps(out),flush=True)
if __name__=='__main__':main()
