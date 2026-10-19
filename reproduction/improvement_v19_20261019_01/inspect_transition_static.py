"""Offline A-window boundaries and unchanged mixed-geometry protections."""
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import argparse,hashlib,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from reproduction.improvement_v19_20261019_01.recovery import transition as H
from reproduction.improvement_v19_20261019_01.recovery.recovery_controller import Config
from reproduction.improvement_v18_20261019_01.recovery.handoff import propose as old
from reproduction.improvement_v18_20261019_01.inspect_handoff_static import verify_output,finite
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='transition_static_a');args=parser.parse_args()
    output=RUN/'analysis'/f'{args.name}.json';assert not output.exists()
    source=ROOT/'reproduction/improvement_v18_20261019_01/analysis/handoff_diagnosis.json'
    data=json.loads(source.read_text(encoding='utf8'));assert data['passed']
    hashes=data['source_sha256'].copy()
    for rel,digest in hashes.items():assert sha(ROOT/rel)==digest,rel
    cfg=Config();cases=[]
    for case in data['cases']:
        if case['version']!='v17':continue
        for row in case['per_control']:
            if row['logical_phase_before']!='DESCEND' or row['command_mode']!='DESCEND':continue
            x=np.array(row['state_before']);goal=np.array(row['grasp']['goal_m']);rot=np.array(row['grasp']['target_rotation'])
            motion=np.array(row['actual_observed_motion']);prev=np.array(row['previous_submitted']['action'])
            inputs=[a.copy() for a in [x,goal,rot,motion,prev]]
            for age in [1,3,4,85]:
                action,receipt=H.propose(x,goal,rot,motion,cfg,prev,descent_controls=age)
                verify_output(action,receipt,cfg,prev)
                assert receipt['transition19']['window_active']==(age<=3)
                second,again=H.propose(x,goal,rot,motion,cfg,prev,descent_controls=age)
                np.testing.assert_array_equal(action,second);assert receipt==again
                for original,current in zip(inputs,[x,goal,rot,motion,prev]):np.testing.assert_array_equal(original,current)
                if age<=3:
                    previous,pr=old(x,goal,rot,motion,cfg,prev)
                    np.testing.assert_array_equal(action,previous)
                    normalized=dict(receipt);normalized.pop('transition19')
                    if normalized['accepted']:normalized['reason']='damped_slew_limited_descent_validated'
                    assert normalized==pr
                else:
                    np.testing.assert_array_equal(receipt['raw_translation_m'],cfg.position_gain*(goal-x[:3]))
                    np.testing.assert_array_equal(receipt['observed_translation_per_step_m'],motion[:3])
                cases.append({'old_job':case['job'],'old_step':row['step'],'synthetic_existing_age':age,
                              'candidate_action':action.tolist(),'receipt':receipt})
    assert cases
    x=inputs[0].copy();x[:3]=[0.,0.,1.5];x[16:19]=[.4,.4,.85]
    goal=x[:3]+[.02,0.,-.01];rot=Rotation.from_quat(x[3:7]).as_matrix();motion=np.zeros(6);prev=np.zeros(7)
    tests=[]
    def reject(label,xx=x,cc=cfg,rr=rot,pp=prev,age=4):
        a,r=H.propose(xx,goal,rr,motion,cc,pp,descent_controls=age)
        assert not r['accepted'] and np.isfinite(a).all() and np.array_equal(a[:6],np.zeros(6)),label
        tests.append({'name':label,'receipt':r})
    for age in [0,-1,1.5,True,None]:reject('invalid_existing_age_'+str(age),age=age)
    for name,cc in [('delay',replace(cfg,delay=3)),('translation',replace(cfg,max_delta_m=.036)),
                    ('rotation',replace(cfg,max_rotation_rad=.151)),('damping',replace(cfg,tracking_velocity_damping=1.))]:
        reject('unchanged_'+name,cc=cc)
    bad=x.copy();bad[0]=np.nan;reject('nonfinite_input',xx=bad)
    reject('invalid_rotation',rr=np.zeros((3,3)));reject('invalid_previous',pp=np.ones(7)*2)
    for age in [1,4,85]:
        a,r=H.propose(x,goal,rot,motion,cfg,prev,grip=-1.,aperture_motion=True,descent_controls=age)
        verify_output(a,r,cfg,prev);assert r['accepted'] and r['aperture_range_m']==[0.,.085] and a[6]==-1.
        tests.append({'name':'full_aperture_age_'+str(age),'receipt':r})
    calls=[]
    def forced(*a,**kw):
        calls.append(kw['work_limit']);return {'kind':'mixed_pose','accepted':False,'work':6,'work_units':6,'reason':'synthetic_rejection'}
    with patch.object(H,'certify_action',forced):
        a,r=H.propose(x,x[:3]+[.2,0,0],rot,motion,cfg,np.array([.7,0,0,0,0,0,0]),descent_controls=4)
    assert not r['accepted'] and len(calls)==1 and r['work']==6
    assert sum(t['reason']=='submitted_command_slew_unconfirmed' for t in r['trials'])==2
    tests.append({'name':'late_window_scaled_retry_cannot_bypass_slew','receipt':r})
    paths=[Path(__file__),source,Path(H.__file__),ROOT/'reproduction/improvement_v18_20261019_01/inspect_handoff_static.py',
           ROOT/'reproduction/improvement_v18_20261019_01/recovery/handoff.py']
    for version in range(6,20):
        for folder in (ROOT/'reproduction').glob(f'improvement_v{version}_*/recovery'):
            # Only the independent transition and inherited helpers; unrelated new helpers are covered separately.
            if version==19:continue
            paths+=list(folder.glob('*.py'))
    hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    result={'passed':True,'scope':'Saved poses with synthetic existing-phase ages; no new physics, sample, timing or performance claim.',
            'new_physical_episodes':0,'new_evaluation_samples':0,'saved_pose_proposals':len(cases),
            'boundary_and_negative_cases':len(tests),'entry_window_exact_v18':True,'window_controls':3,
            'max_geometry_work':max(r['receipt']['work'] for r in cases),'source_sha256':hashes,
            'cases':cases,'tests':tests,'limits':['All phase ages, including waits, are owned by the original controller.',
            'Caps, slew and geometry persist beyond the damping window; all arrival predicates remain external.',
            'Nominal geometry is not proof of noisy delayed tracking or full-arm safety.']}
    with output.open('x',encoding='utf8') as f:json.dump(finite(result),f,indent=2,allow_nan=False)
    print({k:result[k] for k in ['passed','saved_pose_proposals','boundary_and_negative_cases','max_geometry_work']})
if __name__=='__main__':main()
