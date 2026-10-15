"""Offline exact-baseline and geometry/aperture mechanism checks."""
from pathlib import Path
import sys,json,hashlib,argparse
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
import numpy as np
from recovery.recovery_controller import RecoveryController,Config
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5
from recovery.clearance_guard import vertical_margin

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',default='mechanisms.json');args=parser.parse_args()
    steps=episodes=0;gap_errors=[];source=[]
    for job in ['v5_bc_k2_clean','v5_bc_k2_noise005','v5_full_s17_clean','v5_full_s17_noise005']:
        p=ROOT/'reproduction/recovery_v5_20261012_01/dev_a'/job/'trace.jsonl'
        if not p.is_file():continue
        source.append(str(p.relative_to(ROOT)));last=None
        for line in p.open(encoding='utf8'):
            r=json.loads(line);x=np.array(r['state_before'],np.float32)
            if r['demo']!=last:
                last=r['demo'];episodes+=1;prev=np.zeros(7,np.float32)
                a=V5([.1975,.4025,.8],.8,x)
                b=RecoveryController([.1975,.4025,.8],.8,x,config=Config(aperture_guard=False,prevent_repeat=False))
            proposal=np.array(r['original_proposal'],np.float32)
            aa,da=a.choose(x,proposal,prev);bb,db=b.choose(x,proposal,prev)
            np.testing.assert_array_equal(aa,bb);assert da==db and a.events==b.events
            if a.approach_gap is not None and da['mode']=='DESCEND':gap_errors.append(abs(abs(float(x[7]-x[8]))-a.approach_gap))
            prev=np.array(r['executed_action'],np.float32);steps+=1
    assert steps>1000
    down=np.diag([1.,-1.,-1.]);cell=(-.09,.29,-.49,-.01)
    assert vertical_margin([.1,-.25,.855],down,cell,.8,.06)>0
    assert vertical_margin([.285,-.25,.855],down,cell,.8,.06)<0
    x=np.zeros(23,np.float32);x[2]=1.05;x[3:7]=[1,0,0,0];x[16:19]=[.1,-.25,.86];x[19:23]=[0,0,0,1];x[7]=.04;x[8]=-.04
    c=RecoveryController([.1975,.4025,.8],.8,x);c.approach_gap=.056;c.mode='ALIGN';c.clock=10
    cmd=c.pose_action(x,x[:3],-1);assert cmd[6]==1
    c.clock=11;assert c.pose_action(x,x[:3],-1)[6]==0,'Pulse must wait through D2'
    c.gaps.extend([.056]*4);x[7]=.028;x[8]=-.028;c.clock=16
    assert c.gap_ready(x);assert c.pose_action(x,x[:3],-1)[6]==0,'Reached gap must hold'
    # Full opening mismatch blocks transition rather than assuming command arrival.
    c.guard_scope=True;c.plan_ok=True;x[7]=.04;x[8]=-.04;c.gaps.clear();c.gaps.extend([.08]*4)
    c.enter('DESCEND','test',x);assert c.mode=='APERTURE'
    result={'passed':True,'disabled_exact_episodes':episodes,'disabled_exact_steps':steps,
        'baseline_narrow_descent_samples':len(gap_errors),'baseline_gap_abs_error_max_m':max(gap_errors) if gap_errors else None,
        'baseline_gap_abs_error_p95_m':float(np.quantile(gap_errors,.95)) if gap_errors else None,
        'pulse_wait_and_observed_gap_transition':True,'geometry_cases':2,'source_traces':source,
        'scope':'Recorded input replay and geometry checks only; physical pilot is separate.'}
    p=RUN/'analysis'/args.receipt
    with p.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
