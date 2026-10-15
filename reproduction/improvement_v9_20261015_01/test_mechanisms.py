"""Meaningful numerical, bounded-work, safety, and disabled-path tests."""
from pathlib import Path
import argparse,json,sys,time
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from recovery.kinematics import DATA,fk,IK,LIMITS
from recovery.geometry import vertical_margin,general_path_margin,Search
from recovery.recovery_controller import RecoveryController,Config,PoseSearch
from reproduction.improvement_v8_20261015_01.recovery.recovery_controller import RecoveryController as V8,Config as C8

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',default='mechanisms_b.json');args=parser.parse_args()
    checks=[];rng=np.random.default_rng(91015);jac_errors=[]
    q=np.array(DATA['reference_q']);p,R=fk(q)
    np.testing.assert_allclose(p,DATA['reference_position'],atol=1e-12);np.testing.assert_allclose(R,DATA['reference_rotation'],atol=1e-12)
    for _ in range(12):
        q=LIMITS[:,0]+.2+rng.random(7)*(LIMITS[:,1]-LIMITS[:,0]-.4);p,R,J=fk(q,True);numeric=[]
        for i in range(7):
            qq=q.copy();qq[i]+=1e-6;pp,RR=fk(qq);numeric.append(np.r_[(pp-p)/1e-6,Rotation.from_matrix(RR@R.T).as_rotvec()/1e-6])
        err=float(np.max(abs(np.asarray(numeric).T-J)));jac_errors.append(err);assert err<2e-6
        ik=IK(q+np.ones(7)*.01,p,R)
        while not ik.advance(4):pass
        assert ik.success,ik.receipt()
    checks.append('FK reference matches simulator; Jacobian finite differences and nearby reachable IK pass')
    ik=IK(np.array(DATA['reference_q']),[4,4,4],np.eye(3))
    while not ik.advance(4):pass
    assert not ik.success and ik.iterations==48;checks.append('unreachable target rejected within iteration cap')
    q=np.array(DATA['reference_q']);q[-1]=2.4;p,R=fk(q);synthetic=np.zeros(23);synthetic[18]=p[2]-.14
    stub=SimpleNamespace(grasp_target=lambda x:p,floor=p[2]-.20,cfg=Config(),planned_rotation=R@np.diag([-1.,-1.,1.]),approach_gap=.06)
    search=PoseSearch(stub,synthetic,q)
    while not search.advance(16):pass
    assert search.chosen==1 and not search.receipts[0]['feasible'] and search.receipts[1]['feasible']
    checks.append('synthetic reachable equivalent pose selected when first branch fails near joint7 limit')
    comparisons=[]
    for _ in range(100):
        goal=np.r_[rng.uniform(-.12,.32),rng.uniform(-.5,.54),rng.uniform(.83,.98)];above=goal.copy();above[2]=1.15
        rot=Rotation.from_euler('xyz',[np.pi+rng.uniform(-.5,.5),rng.uniform(-.5,.5),rng.uniform(-np.pi,np.pi)]).as_matrix();gap=rng.uniform(.055,.085)
        a=general_path_margin(above,goal,rot,gap);b=vertical_margin(above,goal,rot,gap)
        assert (a>=.001)==(b>=.001),(a,b);comparisons.append([a,b])
    checks.append('100 fixed random vertical sweeps agree with frozen v8 feasibility')
    episodes=steps=0
    for path in (ROOT/'reproduction/improvement_v8_20261015_01/pilot_b').glob('v8_*/trace.jsonl'):
        job=json.loads(path.with_name('result.json').read_text())['job'];last=None
        for row in map(json.loads,path.open()):
            x=np.array(row['state_before'],np.float32)
            if row['demo']!=last:
                last=row['demo'];episodes+=1;prev=np.zeros(7,np.float32)
                a=V8([.1975,.4025,.8],.8,x,True,C8(**job['config']))
                b=RecoveryController([.1975,.4025,.8],.8,x,True,Config(**job['config'],joint_selection=False,bounded_planning=False))
            if job.get('force_recovery_at')==row['step']:a.start_attempt('diagnostic_forced_start',x);b.start_attempt('diagnostic_forced_start',x)
            prop=np.array(row['original_proposal'],np.float32);aa,da=a.choose(x,prop,prev);bb,db=b.choose(x,prop,prev)
            np.testing.assert_array_equal(aa,bb);assert da==db and a.events==b.events
            prev=np.array(row['executed_action'],np.float32);steps+=1
    checks.append('both flags off exactly reproduce frozen v8 commands and diagnostics')
    probe_path=ROOT/'reproduction/improvement_v8_20261015_01/pilot_b/v8_known_side_s41/trace.jsonl'
    row=next(r for r in map(json.loads,probe_path.open()) if r['step']==120)
    x=np.array(row['state_before'],np.float32);c=RecoveryController([.1975,.4025,.8],.8,x);c.plan_grasp(x)
    search=Search(c,x);slices=[]
    while not search.done:
        old=search.index;tic=time.perf_counter();search.advance(8);slices.append((search.index-old,1000*(time.perf_counter()-tic)))
    assert all(n<=8 for n,ms in slices);assert search.chosen is None
    checks.append('306-candidate no-feasible search respects per-step eight-candidate cap')
    # While pending, only zero hold commands, never a new descent command.
    c.start_attempt('unit',x);c.set_joint_positions(np.array(DATA['reference_q']))
    for _ in range(4):
        action,info=c.choose(x,np.ones(7,np.float32),np.zeros(7,np.float32));assert info['mode']=='PLAN_WAIT';np.testing.assert_array_equal(action,np.zeros(7))
    checks.append('pending feasibility holds without issuing descent')
    unknown_path=ROOT/'reproduction/improvement_v8_20261015_01/pilot_b/v8_known_side_s17/trace.jsonl'
    row=next(r for r in map(json.loads,unknown_path.open()) if r['step']==97)
    x=np.array(row['state_before'],np.float32);c=RecoveryController([.1975,.4025,.8],.8,x);c.start_attempt('unit',x)
    assert c.mesh_search is None and c.mode=='RETRACT' and c.feasibility_status=='unknown'
    checks.append('unsettled unknown support remains unknown and does not prematurely block')
    report={'passed':True,'checks':checks,'jacobian_max_error':max(jac_errors),'off_episodes':episodes,'off_steps':steps,
            'geometry_comparisons':comparisons,'bounded_search_slices':slices,'note':'Timing is measured on this machine, not a hard real-time certificate.'}
    with (RUN/'analysis'/args.receipt).open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k not in ['geometry_comparisons','bounded_search_slices']}));print('slice max ms',max(ms for n,ms in slices))
if __name__=='__main__':main()
