"""Behavioral contracts: exact v2 fallback, geometry eligibility, and progress trigger."""
import json,sys
from collections import deque
import numpy as np
from scipy.spatial.transform import Rotation
from setup_study import ROOT,RUN,write,digest
sys.path.insert(0,str(ROOT))
from recovery_controller import RecoveryController,Config
from reproduction.recovery_v2_20261012_01.recovery_controller import RecoveryController as V2

def main(receipt='mechanism_tests_a.json'):
    trace=next((ROOT/'reproduction/recovery_v2_20261012_01/dev_a').glob('bc_k2_clean/trace.jsonl'),None)
    if trace is None:trace=next((ROOT/'reproduction/recovery_v2_20261012_01/dev_a').glob('*/trace.jsonl'))
    current=None;steps=0;episodes=0
    for line in trace.open():
        r=json.loads(line);x=np.array(r['state_before'],np.float32)
        if r['demo']!=current:
            current=r['demo'];episodes+=1;previous=np.zeros(7,np.float32)
            old=V2([.1975,.4025,.8],.8,x)
            new=RecoveryController([.1975,.4025,.8],.8,x,config=Config(alignment_switch=False,region_guard=False))
        proposal=np.array(r['original_proposal'],np.float32)
        a,da=old.choose(x,proposal,previous);b,db=new.choose(x,proposal,previous)
        np.testing.assert_array_equal(a,b);assert da==db and old.events==new.events
        previous=np.array(r['executed_action'],np.float32);steps+=1
    x=np.zeros(23,np.float32);x[:3]=[.17,.10,1.];x[3:7]=[1,0,0,0];x[7:9]=[.04,-.04];x[19:23]=[0,0,0,1]
    c=RecoveryController([.1975,.4025,.8],.8,x)
    cases=[('inside_corner',[.151,.077,.860],True),('divider',[.10,.20,.860],False),('outside',[.296,.308,.860],False),('wall_top',[.28,.308,.940],False),('between_bins',[.15,.015,.86],False),('overlapping_wall',[.12,.10,.86],False)]
    checked=[]
    for name,pos,expected in cases:
        x[16:19]=pos;c.plan_grasp(x);legal=c.resting_cell(x) is not None
        assert legal==expected,(name,legal)
        if not expected:assert c.approach_gap is None and np.all(c.grasp_offset==0)
        checked.append({'case':name,'legal':legal,'corner_adjusted':c.approach_gap is not None})
    x[16:19]=[.151,.077,.86];c.plan_grasp(x);assert c.approach_gap==.06
    x[16:19]=[.13,-.20,.86];x[:3]=[.20,-.14,1.]
    c=RecoveryController([.1975,.4025,.8],.8,x,config=Config(region_guard=False))
    c.start_attempt('fixture',x);c.enter('ALIGN','fixture',x);original=c.goal_rotation.copy()
    for i in range(30):
        c.choose(x,np.zeros(7,np.float32),np.zeros(7,np.float32))
        if c.direction_switched:break
    assert c.direction_switched and c.attempts==2 and c.mode=='RETRACT'
    np.testing.assert_allclose(c.planned_rotation,Rotation.from_rotvec([0,0,np.pi]).as_matrix()@original,atol=1e-12)
    assert c.events[-1]['reason']=='alignment_stalled_switch_equivalent'
    # Continued measurable progress must not be treated as stagnation.
    x[:3]=[.40,-.20,1.];p=RecoveryController([.1975,.4025,.8],.8,x,config=Config(region_guard=False))
    p.start_attempt('fixture',x);p.enter('ALIGN','fixture',x)
    for i in range(35):
        x[0]-=.005;p.choose(x,np.zeros(7,np.float32),np.zeros(7,np.float32))
    assert not p.direction_switched
    write(RUN/receipt,{'passed':True,'fallback_episodes':episodes,'fallback_steps_exact':steps,'regions':checked,
        'stagnation_switch_step':c.clock,'maximum_attempts_preserved':True,'continuous_progress_no_switch':True,
        'controller_sha256':digest(RUN/'recovery_controller.py')})
    print(json.dumps({'passed':True,'exact_v2_steps':steps,'region_cases':len(cases)}))
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'mechanism_tests_a.json')
