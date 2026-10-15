from pathlib import Path
import argparse,hashlib,json,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from recovery.recovery_controller import RecoveryController,Config
from recovery.geometry import support,path_margin,CAN
from reproduction.improvement_v7_20261015_01.recovery.recovery_controller import RecoveryController as V7,Config as C7

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',default='mechanisms_c.json');args=parser.parse_args()
    checks=[];episodes=steps=0
    for p in (ROOT/'reproduction/improvement_v7_20261015_01/pilot_b').glob('v7_*/trace.jsonl'):
        result=json.loads(p.with_name('result.json').read_text());job=result['job'];last=None
        for line in p.open():
            r=json.loads(line);x=np.array(r['state_before'],np.float32)
            if r['demo']!=last:
                last=r['demo'];episodes+=1;prev=np.zeros(7,np.float32)
                a=V7([.1975,.4025,.8],.8,x,True,C7(**job['config']))
                b=RecoveryController([.1975,.4025,.8],.8,x,True,Config(**job['config'],geometry_support=False,retreat_replan=False))
            if job.get('force_recovery_at')==r['step']:
                a.start_attempt('diagnostic_forced_start',x);b.start_attempt('diagnostic_forced_start',x)
            proposal=np.array(r['original_proposal'],np.float32);aa,da=a.choose(x,proposal,prev);bb,db=b.choose(x,proposal,prev)
            np.testing.assert_array_equal(aa,bb);assert da==db and a.events==b.events
            prev=np.array(r['executed_action'],np.float32);steps+=1
    checks.append('flags_off_exact_frozen_v7')
    probes=[]
    for job,demo,step in [('v7_known_side_s41','demo_97',120),('v7_regression_6000005','demo_6000005',140)]:
        p=ROOT/'reproduction/improvement_v7_20261015_01/pilot_b'/job/'trace.jsonl'
        r=next(json.loads(l) for l in p.open() if json.loads(l)['demo']==demo and json.loads(l)['step']==step)
        x=np.array(r['state_before'],np.float32);domain,reason=support(x,.8)
        assert domain is not None,(job,reason)
        c=RecoveryController([.1975,.4025,.8],.8,x);tic=time.perf_counter();c.start_attempt('unit_diagnostic',x)
        probes.append({'job':job,'domain':domain['kind'],'reason':c.feasibility_reason,'plan_ok':c.plan_ok,'geometry':c.geometry_events,'plan_ms':1000*(time.perf_counter()-tic)})
        json.dumps(probes,allow_nan=False)
        if domain['kind']=='wall_top':
            c.enter('ALIGN','test_expanded_entry',x)
            assert c.mode=='POSE_WAIT' and c.retreat_stage=='vertical'
            checks.append('expanded_supported_plan_enters_bounded_relocation_before_alignment')
    checks.append('actual_hull_recognizes_side_floor_and_upright_wall_top')
    x[16:19]=[.7,.7,.86];assert support(x,.8)[0] is None
    x[16:19]=[.1,-.25,1.2];assert support(x,.8)[0] is None
    checks.append('airborne_and_outside_not_treated_as_supported')
    down=np.diag([1.,-1.,-1.]);assert path_margin(np.array([.3,.3,1.1]),np.array([.3,.3,.84]),down,.065)<.001
    assert path_margin(np.array([.1,-.25,1.2]),np.array([.2,-.25,1.2]),down,.065)>.001
    checks.append('hand_sweep_rejects_wall_and_accepts_high_free_segment')
    assert -.041<CAN[:,2].min()<-.039 and .039<CAN[:,2].max()<.041
    checks.append('collision_mesh_uses_actual_8cm_height')
    report={'passed':True,'off_episodes':episodes,'off_steps':steps,'checks':checks,'geometry_probes':probes}
    report['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (RUN/'recovery').iterdir() if p.is_file() and p.suffix in ['.py','.json']}
    with (RUN/'analysis'/args.receipt).open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
