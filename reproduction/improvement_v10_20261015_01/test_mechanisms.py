from pathlib import Path
import json,sys,argparse
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery.recovery_controller import RecoveryController,Config
from recovery.path_search import EdgeSearch,sweep_margin
from reproduction.improvement_v9_20261015_01.recovery.recovery_controller import RecoveryController as V9,Config as C9
from reproduction.improvement_v8_20261015_01.recovery.geometry import path_margin
from probe import snapshot
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',default='mechanisms_b.json');args=parser.parse_args()
    rng=np.random.default_rng(101015);comparisons=[]
    for _ in range(80):
        p=rng.uniform([-.15,-.53,.85],[.34,.56,1.16]);q=p+rng.uniform(-.13,.13,3)
        r=Rotation.random(random_state=rng).as_matrix();gap=rng.uniform(.05,.085)
        a=sweep_margin(p,q,r,gap);b=path_margin(p,q,r,gap);assert (a>=.001)==(b>=.001),(a,b)
        comparisons.append([a,b])
    c,x,q=snapshot();choices={}
    for name,height,path in [('height',True,False),('path',False,True),('v10',True,True)]:
        c.cfg=Config(adaptive_height=height,edge_path=path);s=EdgeSearch(c,x,q);max_work=0
        while not s.done:
            old=s.work;s.advance(16);max_work=max(max_work,s.work-old)
        assert max_work<=16;choices[name]={'chosen':s.chosen is not None,'work':s.work,'receipts':s.receipts}
    assert not choices['height']['chosen']
    episodes=steps=0
    for f in (ROOT/'reproduction/improvement_v9_20261015_01/pilot_b').glob('v9_*/trace.jsonl'):
        job=json.loads(f.with_name('result.json').read_text())['job'];last=None
        for row in map(json.loads,f.open()):
            x=np.array(row['state_before'],np.float32)
            if row['demo']!=last:
                last=row['demo'];episodes+=1;prev=np.zeros(7,np.float32)
                a=V9([.1975,.4025,.8],.8,x,True,C9(**job['config']))
                b=RecoveryController([.1975,.4025,.8],.8,x,True,Config(**job['config'],adaptive_height=False,edge_path=False))
            for ctl in [a,b]:
                ctl.set_joint_positions(row['joint_positions'])
                if job.get('force_recovery_at')==row['step']:ctl.start_attempt('diagnostic_forced_start',x)
            prop=np.array(row['original_proposal'],np.float32);aa,da=a.choose(x,prop,prev);bb,db=b.choose(x,prop,prev)
            for d in [da,db]:d.pop('planning_ms',None)
            np.testing.assert_array_equal(aa,bb);assert da==db and a.events==b.events
            prev=np.array(row['executed_action'],np.float32);steps+=1
    result={'passed':True,'sweep_comparisons':comparisons,'off_episodes':episodes,'off_steps':steps,'saved_wall_top_search':choices}
    with (RUN/'analysis'/args.receipt).open('x') as f:json.dump(result,f,indent=2)
    print('PASS',episodes,steps,{k:(v['chosen'],v['work']) for k,v in choices.items()})
