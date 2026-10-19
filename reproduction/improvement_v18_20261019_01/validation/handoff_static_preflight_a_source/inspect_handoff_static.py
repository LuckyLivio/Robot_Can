"""Offline positive/negative handoff-helper checks; no new physics or tuning."""
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import argparse,copy,hashlib,json,sys
import numpy as np
from scipy.spatial.transform import Rotation

RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from reproduction.improvement_v17_20261019_01.recovery.recovery_controller import Config
from reproduction.improvement_v18_20261019_01.recovery import handoff as H

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def finite(v):
    if isinstance(v,dict):return {str(k):finite(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,np.ndarray)):return [finite(x) for x in v]
    if isinstance(v,(np.integer,int)):return int(v)
    if isinstance(v,(np.floating,float)):return float(v) if np.isfinite(v) else None
    if isinstance(v,np.bool_):return bool(v)
    return v

def verify_output(action,receipt,cfg,previous):
    assert action.dtype==np.float32 and action.shape==(7,) and np.isfinite(action).all()
    assert 0<=receipt['work']<=16 and receipt['work']==receipt['work_units']
    assert receipt['work']==sum(t['work'] for t in receipt['trials'])
    if receipt['accepted']:
        np.testing.assert_array_equal(action,receipt['submitted_action'])
        assert np.linalg.norm(action[:3].astype(float)*.05)<=cfg.max_delta_m+1e-12
        assert np.linalg.norm(action[3:6].astype(float)*.5)<=cfg.max_rotation_rad+1e-12
        assert np.linalg.norm((action[:3].astype(float)-previous[:3])*.05)<=cfg.max_delta_m/3+1e-8
        assert np.linalg.norm((action[3:6].astype(float)-previous[3:6])*.5)<=cfg.max_rotation_rad/3+1e-8
        assert receipt['box_margin_m']>=.001 and receipt['can_margin_m']>=.001
        assert receipt['required_can_margin_m']==.001 and not receipt['servo_bias_used']
        np.testing.assert_array_equal(np.asarray(receipt['translation_m']),action[:3].astype(float)*.05)
        np.testing.assert_array_equal(np.asarray(receipt['rotation_vector_rad']),action[3:6].astype(float)*.5)
    else:np.testing.assert_array_equal(action[:6],np.zeros(6))

def main():
    p=argparse.ArgumentParser();p.add_argument('--name',default='handoff_static_a');args=p.parse_args()
    out=RUN/'analysis'/(args.name+'.json');assert not out.exists()
    diagnosis=RUN/'analysis/handoff_diagnosis.json';data=json.loads(diagnosis.read_text(encoding='utf8'))
    assert data['passed'] and data['new_physical_episodes']==0
    for rel,digest in data['source_sha256'].items():assert sha(ROOT/rel)==digest,rel
    archived=RUN/'analysis/handoff_diagnosis_a.json'
    if not archived.exists():archived.write_bytes(diagnosis.read_bytes())
    assert archived.read_bytes()==diagnosis.read_bytes()
    cfg=Config();cases=[];seen=set()
    for case in data['cases']:
        if case['version']!='v17':continue
        for row in case['per_control']:
            if row['logical_phase_before']!='DESCEND' or row['command_mode']!='DESCEND':continue
            x=np.array(row['state_before']);goal=np.array(row['grasp']['goal_m']);rot=np.array(row['grasp']['target_rotation'])
            motion=np.array(row['actual_observed_motion']);prev=np.array(row['previous_submitted']['action'])
            untouched=[a.copy() for a in [x,goal,rot,motion,prev]]
            action,receipt=H.propose(x,goal,rot,motion,cfg,prev)
            verify_output(action,receipt,cfg,prev)
            for old,now in zip(untouched,[x,goal,rot,motion,prev]):np.testing.assert_array_equal(old,now)
            second,again=H.propose(x,goal,rot,motion,cfg,prev)
            np.testing.assert_array_equal(action,second);assert receipt==again
            cases.append({'job':case['job'],'control_step':row['step'],'actual_original_action':row['submitted']['action'],
                          'candidate_action':action.tolist(),'receipt':receipt})
            seen.add((case['condition'],row['step']))
    assert cases and any(c['receipt']['accepted'] for c in cases)
    sample=next(c for c in data['cases'] if c['version']=='v17' and c['condition']=='regression_6000005')['handoffs'][0]['first_descend']
    x=np.array(sample['state_before']);goal=np.array(sample['grasp']['goal_m']);rot=np.array(sample['grasp']['target_rotation'])
    motion=np.array(sample['actual_observed_motion']);prev=np.array(sample['previous_submitted']['action'])
    negatives=[]
    def reject(label,xx=x,gg=goal,rr=rot,mm=motion,cc=cfg,pp=prev,grip=0.,full=False):
        action,receipt=H.propose(xx,gg,rr,mm,cc,pp,grip,full)
        assert not receipt['accepted'],label
        assert np.isfinite(action).all() and np.array_equal(action[:6],np.zeros(6))
        negatives.append({'name':label,'receipt':receipt});return action,receipt
    bad=x.copy();bad[0]=np.nan;reject('nonfinite_observation',xx=bad)
    reject('observation_shape',xx=x[:22]);reject('nonfinite_motion',mm=np.full(6,np.inf))
    reject('nonfinite_previous_command',pp=np.full(7,np.nan));reject('previous_command_out_of_range',pp=np.full(7,2.))
    reject('invalid_target_rotation',rr=np.zeros((3,3)))
    bad=x.copy();bad[3:7]=0.;reject('zero_quaternion',xx=bad)
    reject('larger_translation_cap',cc=replace(cfg,max_delta_m=.036))
    reject('larger_rotation_cap',cc=replace(cfg,max_rotation_rad=.151))
    reject('different_delay',cc=replace(cfg,delay=3));reject('different_velocity_damping',cc=replace(cfg,tracking_velocity_damping=1.))
    reject('nonfinite_grip',grip=float('nan'));reject('invalid_grip_type',grip='invalid')
    reject('pulse_without_full_aperture_certificate',grip=1.,full=False)
    stopped=next(c for c in data['cases'] if c['version']=='v17' and c['condition'].endswith('13000022'))['handoffs'][0]['last_descend']
    reject('actual_invalidated_398_geometry',xx=np.array(stopped['state_before']),gg=np.array(stopped['grasp']['goal_m']),
           rr=np.array(stopped['grasp']['target_rotation']),mm=np.array(stopped['actual_observed_motion']),pp=np.array(stopped['previous_submitted']['action']))
    # An open, high empty-hand state is an offline geometric positive case.
    free=x.copy();free[:3]=[0.,0.,1.5];free[16:19]=[.4,.4,.85]
    free_goal=free[:3]+[.02,0.,-.01];free_r=Rotation.from_quat(free[3:7]).as_matrix()
    pulse,pulse_receipt=H.propose(free,free_goal,free_r,np.zeros(6),cfg,np.zeros(7),-1.,True)
    verify_output(pulse,pulse_receipt,cfg,np.zeros(7));assert pulse_receipt['accepted'] and pulse_receipt['aperture_range_m']==[0.,.085]
    assert pulse[6]==-1.
    # Force only the certificate result to fail, to verify scaled retries do
    # not bypass slew. This is a mechanical negative test, not real geometry.
    calls=[]
    def forced_reject(*a,**kw):
        calls.append(kw['work_limit'])
        return {'kind':'mixed_pose','accepted':False,'work':6,'work_units':6,'reason':'synthetic_rejection'}
    prior_action=np.array([.7,0,0,0,0,0,0])
    with patch.object(H,'certify_action',forced_reject):
        action,receipt=H.propose(free,free[:3]+[.2,0,0],free_r,np.zeros(6),cfg,prior_action)
    assert not receipt['accepted'] and len(calls)==1 and receipt['work']==6
    assert sum(t['reason']=='submitted_command_slew_unconfirmed' for t in receipt['trials'])==2
    np.testing.assert_array_equal(action[:6],np.zeros(6))
    scale_test={'name':'scaled_retry_cannot_violate_slew','scope':'Synthetic certificate rejection, no geometric conclusion','receipt':receipt}
    sources=[Path(__file__),RUN/'recovery/handoff.py',diagnosis,archived,
             ROOT/'reproduction/improvement_v17_20261019_01/recovery/pose_servo.py',
             ROOT/'reproduction/improvement_v17_20261019_01/recovery/recovery_controller.py',
             ROOT/'reproduction/improvement_v9_20261015_01/recovery/geometry.py',
             ROOT/'reproduction/improvement_v11_20261015_01/recovery/object_clearance.py',
             ROOT/'reproduction/improvement_v15_20261016_01/recovery/carry_path.py']
    output={'passed':True,'scope':'Pure stateless handoff helper, saved-state offline geometry and mechanical negative tests only; central integration and closed-loop outcomes remain separate.',
            'new_physical_episodes':0,'new_evaluation_samples':0,'prior_saved_input_replay_controls':data['saved_controls_replayed'],
            'saved_state_proposals':len(cases),'accepted_saved_state_proposals':sum(c['receipt']['accepted'] for c in cases),
            'input_immutability_and_repeatability':True,'fixed_caps_m_rad':[.035,.15],'fixed_execution_margin_m':.001,
            'max_geometry_work':max(c['receipt']['work'] for c in cases),
            'saved_state_cases':cases,'negative_cases':negatives,'full_aperture_positive':pulse_receipt,'scaled_retry_negative':scale_test,
            'source_sha256':{s.relative_to(ROOT).as_posix():sha(s) for s in sources},
            'limits':['No approach bias is retained across goals. No phase, clock, pulse timestamp, history or queue is modified.',
                      'Prior source hashes and raw trace hashes are verified by the immutable handoff_diagnosis receipt.',
                      'A nominal certificate and bounded submitted-command changes do not prove noisy D2 tracking or closed-loop improvement.',
                      'Caller must retain all earlier 3mm path/planning guards, 1mm live guards, joint, pose, gap, arrival, timeout and 400-step rules.',
                      'Rejecting pose certification must prevent same-control CLOSE and must not commit a rejected aperture pulse timestamp.']}
    with out.open('x',encoding='utf8') as f:json.dump(finite(output),f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({k:output[k] for k in ['passed','saved_state_proposals','accepted_saved_state_proposals','max_geometry_work']}))

if __name__=='__main__':main()
