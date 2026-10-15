from pathlib import Path
import json,sys
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scipy.optimize import linprog
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery.recovery_controller import RecoveryController,Config
from recovery.path_search import EdgeSearch
from recovery.object_clearance import object_margin,enclosure,PARTS,CAN
from reproduction.improvement_v10_20261015_01.recovery.recovery_controller import RecoveryController as V10,Config as C10
from reproduction.improvement_v10_20261015_01.probe import snapshot

if __name__=='__main__':
    rng=np.random.default_rng(111015);positive=negative=0;invariance=[]
    for _ in range(45):
        x=np.zeros(23);x[16:19]=[.1,.1,.94];x[19:23]=Rotation.random(random_state=rng).as_quat()
        p=x[16:19]+rng.uniform(-.09,.09,3);q=p+rng.uniform(-.04,.04,3);r=Rotation.random(random_state=rng).as_matrix();gaps=[.057,.071]
        cert=object_margin(p,q,r,gaps,x,True);world=CAN@Rotation.from_quat(x[19:23]).as_matrix().T+x[16:19];ch=ConvexHull(world).equations
        for receipt,(name,vertices,_) in zip(cert,PARTS):
            vs=[]
            for gap in gaps:
                v=vertices.copy()
                if 'finger1' in name:v[:,1]+=(gap-.06)/2
                if 'finger2' in name:v[:,1]-=(gap-.06)/2
                vs.extend([v@r.T+p,v@r.T+q])
            h=ConvexHull(np.concatenate(vs)).equations
            test=linprog(np.zeros(3),A_ub=np.r_[h[:,:3],ch[:,:3]],b_ub=-np.r_[h[:,3],ch[:,3]],bounds=[(None,None)]*3,method='highs')
            if receipt['margin_m']>1e-5:
                assert test.status==2,(receipt,test.message);positive+=1
            else:negative+=1
        t=Rotation.random(random_state=rng).as_matrix();shift=rng.uniform(-1,1,3);y=x.copy();y[16:19]=t@x[16:19]+shift;y[19:23]=Rotation.from_matrix(t@Rotation.from_quat(x[19:23]).as_matrix()).as_quat()
        err=abs(object_margin(p,q,r,gaps,x)-object_margin(t@p+shift,t@q+shift,t@r,gaps,y));assert err<1e-10;invariance.append(err)
    old,x,q=snapshot();choices={}
    for name,axis,guard in [('axis',True,False),('guard',False,True),('v11',True,True)]:
        old.cfg=Config(axis_alignment=axis,can_guard=guard);s=EdgeSearch(old,x,q);slices=[]
        while not s.done:
            before=s.work;s.advance(16);slices.append(s.work-before)
        assert max(slices)<=16
        choices[name]={'chosen':s.chosen is not None,'height_m':None if s.chosen is None else s.chosen.get('height_m'),'target_gap_m':None if s.chosen is None else s.chosen.get('target_gap'),'work':s.work,'steps':len(slices),'receipts':s.receipts}
    assert not choices['guard']['chosen'] and choices['v11']['chosen'] and choices['v11']['height_m']==.020
    episodes=steps=0
    for f in (ROOT/'reproduction/improvement_v10_20261015_01/pilot_a').glob('v10_*/trace.jsonl'):
        job=json.loads(f.with_name('result.json').read_text())['job'];last=None
        for row in map(json.loads,f.open()):
            x=np.array(row['state_before'],np.float32)
            if row['demo']!=last:
                last=row['demo'];episodes+=1;prev=np.zeros(7,np.float32)
                a=V10([.1975,.4025,.8],.8,x,True,C10(**job['config']))
                b=RecoveryController([.1975,.4025,.8],.8,x,True,Config(**job['config'],axis_alignment=False,can_guard=False))
            for c in [a,b]:
                c.set_joint_positions(row['joint_positions'])
                if job.get('force_recovery_at')==row['step']:c.start_attempt('diagnostic_forced_start',x)
            prop=np.array(row['original_proposal'],np.float32);aa,da=a.choose(x,prop,prev);bb,db=b.choose(x,prop,prev)
            for d in [da,db]:d.pop('planning_ms',None)
            np.testing.assert_array_equal(aa,bb);assert da==db and a.events==b.events and a.edge_events==b.edge_events
            prev=np.array(row['executed_action'],np.float32);steps+=1
    result={'passed':True,'lp_certificates_verified':positive,'uncertified_pairs':negative,'transformation_max_error':max(invariance),'off_episodes':episodes,'off_steps':steps,'saved_state_searches':choices}
    with (RUN/'analysis/mechanisms_a.json').open('x') as f:json.dump(result,f,indent=2)
    print('PASS',positive,negative,episodes,steps,{k:(v['chosen'],v['height_m'],v['target_gap_m'],v['steps']) for k,v in choices.items()})
