"""Offline v20 target-band integral checks using frozen v19 observations.

No controller replay, simulator, future rollout, new success estimate or tuning
sweep. The actual parent proposals are reconstructed exactly before comparing
the new helper on each same observed input and same committed parent memory.
"""
from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json
import sys
from collections import Counter

import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v19_20261019_01.recovery import settling as parent
from reproduction.improvement_v19_20261019_01.recovery.recovery_controller import Config
from reproduction.improvement_v20_20261019_01.recovery import delay_settling as new


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value):
    if isinstance(value, dict):
        return {str(key): finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [finite(item) for item in value]
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def snapshot(state):
    return None if state is None else finite(vars(state))


def checks_for_proposal(args, kwargs):
    before = snapshot(kwargs.get('state'))
    arrays = [np.asarray(value).copy() for value in args[:4]]
    previous = copy.deepcopy(kwargs.get('previous_action'))
    action, receipt = new.propose(*args, **kwargs)
    assert snapshot(kwargs.get('state')) == before, 'propose mutated committed memory'
    for old, value in zip(arrays, args[:4]):
        np.testing.assert_array_equal(old, value)
    np.testing.assert_array_equal(previous, kwargs.get('previous_action'))
    assert receipt['work'] <= 16
    if receipt['accepted']:
        np.testing.assert_array_equal(action, receipt['submitted_action'])
        assert receipt['box_margin_m'] >= .001 and receipt['can_margin_m'] >= .001
        assert np.linalg.norm(receipt['position_bias_m']) <= .009+1e-12
        prev = kwargs.get('previous_action')
        if kwargs.get('held') and prev is not None:
            assert np.linalg.norm((action[:3].astype(float)-prev[:3])*.05) <= .035/3+1e-8
            assert np.linalg.norm((action[3:6].astype(float)-prev[3:6])*.5) <= .15/3+1e-8
    return action, receipt


def inspect_saved(job):
    folder = ROOT/'reproduction/improvement_v19_20261019_01/smoke_a'/job['id']
    result_path, trace_path = folder/'result.json', folder/'trace.jsonl'
    saved = read(result_path)
    assert saved['status'] == 'complete' and saved['job'] == job
    cfg = Config(**job['config'])
    state = parent.ServoState()
    cases, anchor = [], None
    for line in trace_path.read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        receipt = row['recovery'].get('mixed_pose', {})
        if receipt.get('held') and receipt.get('accepted') and receipt.get('state_update'):
            update = receipt['state_update']
            args = (np.asarray(row['state_before'], np.float32), np.asarray(update['goal']),
                    np.asarray(update['rotation']),
                    np.r_[receipt['observed_translation_per_step_m'], receipt['observed_rotation_per_step_rad']], cfg)
            kwargs = dict(held=True, grip=receipt['grip_command'], state=state,
                          phase=ast.literal_eval(update['phase']),
                          previous_action=np.asarray(receipt['previous_submitted_action'], np.float32),
                          aperture_motion=receipt['aperture_motion'])
            old_action, old_receipt = parent.propose(*args, **kwargs)
            assert finite(old_receipt) == receipt, (job['id'], row['step'], 'parent receipt')
            np.testing.assert_array_equal(old_action, row['submitted_action'])
            action, proposed = checks_for_proposal(args, kwargs)
            triggered = 'braking20' in proposed
            if not triggered:
                np.testing.assert_array_equal(action, old_action)
                assert finite(proposed) == finite(old_receipt)
            # The inherited event retains its exact original predicate and fields.
            assert proposed.get('settling19') == old_receipt.get('settling19')
            cases.append({'job': job['id'], 'step': row['step'], 'phase': update['phase'],
                          'triggered': triggered, 'accepted': proposed['accepted'],
                          'changed_action': not np.array_equal(action, old_action), 'work': proposed['work'],
                          'position_error_m': receipt['position_error_m'],
                          'old_error_m': (args[1]-args[0][:3]).tolist(),
                          'old_observed_motion_m': args[3][:3].tolist(),
                          'old_bias_m': old_receipt['position_bias_m'],
                          'proposed_bias_m': proposed['position_bias_m'],
                          'old_action': old_action.tolist(), 'proposed_action': action.tolist(),
                          'braking20': proposed.get('braking20'),
                          'settling19': proposed.get('settling19'),
                          'old_queue_before': row['queue_before']})
            if job['id'] == 'v19_regression_6000005' and row['step'] == 386:
                anchor = (copy.deepcopy(args), copy.deepcopy(kwargs))
            assert state.commit(np.asarray(row['submitted_action'], np.float32), receipt)
        else:
            state.reset()
    return cases, anchor, [result_path, trace_path]


def synthetic_checks(anchor):
    original_args, _ = copy.deepcopy(anchor)
    x, _, _, _, cfg = original_args
    displacement = np.array([0., 0., 1.5])-x[:3]
    x[:3] += displacement
    x[16:19] += displacement
    rotation = Rotation.from_quat(x[3:7]).as_matrix()
    phase = ('synthetic', 'CARRY_transport')
    previous = np.zeros(7, np.float32)
    records = []

    def context(error, motion, bias, *, held=True):
        goal = x[:3].astype(float)+np.asarray(error)
        state = parent.ServoState()
        assert state.commit(previous, {'accepted': True, 'submitted_action': previous.tolist(),
            'state_update': {'phase': repr(phase), 'held': held, 'goal': goal.tolist(),
                             'rotation': rotation.tolist(), 'bias': list(bias)}})
        return ((x.copy(), goal, rotation.copy(), np.asarray(motion, float), cfg),
                {'held': held, 'grip': 1. if held else 0., 'state': state,
                 'phase': phase, 'previous_action': previous.copy()})

    def check(name, args, kwargs, *, expected_capture=None, expected_hold=None,
              exact=False, reject=False, expected_bias=None):
        action, receipt = checks_for_proposal(args, kwargs)
        old_action, old_receipt = parent.propose(*args, **kwargs)
        if exact:
            np.testing.assert_array_equal(action, old_action)
            assert finite(receipt) == finite(old_receipt)
        if expected_capture is not None:
            assert receipt['braking20']['capture_brake_axes'] == expected_capture
        if expected_hold is not None:
            assert receipt.get('braking20', {}).get('inside_original_position_ball', False) == expected_hold
        if expected_bias is not None:
            np.testing.assert_allclose(receipt['position_bias_m'], expected_bias, atol=1e-12, rtol=0)
        if reject:
            assert not receipt['accepted']
        elif receipt['accepted']:
            committed = copy.deepcopy(kwargs.get('state')) or parent.ServoState()
            assert committed.commit(action, receipt)
            replaced = action.copy(); replaced[0] += np.float32(.001)
            assert not committed.commit(replaced, receipt)
            assert committed.goal is None and np.array_equal(committed.bias, np.zeros(3))
        records.append({'name': name, 'passed': True, 'accepted': receipt['accepted'],
                        'reason': receipt['reason'], 'work': receipt['work'],
                        'position_bias_m': receipt.get('position_bias_m'),
                        'braking20': receipt.get('braking20'),
                        'settling19': receipt.get('settling19')})
        return action, receipt

    args, kwargs = context([-.012, .002, .010], [-.004, 0., 0., 0., 0., 0.], [-.004, .002, .002])
    action, receipt = check('capture_band_brakes_before_original_center_crossing', args, kwargs,
                           expected_capture=[True,False,False], expected_hold=False)
    assert 'settling19' not in receipt
    assert not np.array_equal(action[:3], np.zeros(3)), 'No forced stationary command'
    expected = cfg.position_gain*(args[1]-args[0][:3])+np.asarray(receipt['position_bias_m'])-cfg.tracking_velocity_damping*args[3][:3]
    np.testing.assert_allclose(action[:3].astype(float)*.05, expected, rtol=0, atol=1e-8)
    args, kwargs = context([.003, -.004, .002], [.001, .001, 0., 0., 0., 0.], [.004, -.003, -.002])
    check('inside_ball_sign_reset_then_capture_clear_keeps_countermotion_bias', args, kwargs,
          expected_capture=[True,False,False], expected_hold=True, expected_bias=[0.,-.003,0.])
    args, kwargs = context([.020, 0., 0.], np.zeros(6), [.002,0.,0.])
    _, receipt = check('stationary_error_outside_ball_still_integrates_exact_parent', args, kwargs, exact=True)
    assert receipt['position_bias_m'][0] > .002
    for label, value, inside in [('inside',np.nextafter(.009,0.),True),('exact',.009,False),('outside',np.nextafter(.009,np.inf),False)]:
        args, kwargs = context([value,0.,0.],np.zeros(6),[.002,0.,0.])
        check('original_strict_ball_boundary_'+label,args,kwargs,expected_hold=inside,exact=not inside,
              expected_bias=[.002,0.,0.] if inside else None)
    boundary = new.AXIS_CAPTURE_BAND_M+cfg.delay*.004
    for label,value,trigger in [('exact',boundary,True),('outside',np.nextafter(boundary,np.inf),False)]:
        args,kwargs=context([value,0.,.020],[.004,0.,0.,0.,0.,0.],[.002,0.,.002])
        check('capture_axis_boundary_'+label,args,kwargs,
              expected_capture=[True,False,False] if trigger else None,exact=not trigger)
    for label,error,motion in [('far',[.060001,0.,0.],[.04,0.,0.,0.,0.,0.]),
                               ('moving_away',[.020,0.,0.],[-.02,0.,0.,0.,0.,0.])]:
        args,kwargs=context(error,motion,[.002,0.,0.]);check(label+'_exact_parent',args,kwargs,exact=True)
    args,kwargs=context([.006,0.,0.],[.004,0.,0.,0.,0.,0.],[.002,0.,0.],held=False)
    check('empty_hand_exact_parent',args,kwargs,exact=True)
    args,kwargs=context([.006,0.,0.],[.004,0.,0.,0.,0.,0.],[.002,0.,0.])
    check('no_memory_exact_parent',args,{**kwargs,'state':None},exact=True)
    for reason in ['phase','goal','rotation','previous_action']:
        aa,kk=copy.deepcopy(args),copy.deepcopy(kwargs)
        if reason=='phase':kk['phase']=('new_attempt','PLACE')
        if reason=='goal':aa=list(aa);aa[1]=aa[1]+[0.,.001,0.]
        if reason=='rotation':aa=list(aa);aa[2]=Rotation.from_rotvec([0.,0.,.001]).as_matrix()@aa[2]
        if reason=='previous_action':kk['previous_action']=np.array([.01,0,0,0,0,0,0],np.float32)
        actual,rec=check('reset_on_'+reason,aa,kk)
        fresh,fr=new.propose(*aa,**{**kk,'state':parent.ServoState()})
        np.testing.assert_array_equal(actual,fresh)
        assert rec['position_bias_m']==fr['position_bias_m'] and rec['state_reset_reason']
    invalid=list(copy.deepcopy(args));invalid[0][0]=np.nan
    check('nonfinite_observation_rejected',invalid,kwargs,reject=True)
    invalid=list(copy.deepcopy(args));invalid[3][0]=np.inf
    check('nonfinite_observed_motion_rejected',invalid,kwargs,reject=True)
    invalid=list(copy.deepcopy(args));invalid[0][3:7]=0.
    check('invalid_quaternion_rejected',invalid,kwargs,reject=True)
    check('held_opening_rejected',args,{**kwargs,'grip':-1.},reject=True)
    invalid=list(copy.deepcopy(args));offset=np.array([.1975,.4025,.8])-invalid[0][:3]
    invalid[0][:3]+=offset;invalid[0][16:19]+=offset;invalid[1]+=offset
    check('original_geometry_guard_still_rejects',invalid,kwargs,reject=True)
    return records


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='settling_static_a');args=parser.parse_args()
    output=RUN/'analysis'/(args.name+'.json');assert not output.exists()
    old_stage=ROOT/'reproduction/improvement_v19_20261019_01/smoke_a'
    all_jobs=read(old_stage/'jobs.json');jobs=[job for job in all_jobs if job['version']=='v19']
    assert len(jobs)==9
    cases=[];anchor=None;sources=[Path(__file__),RUN/'recovery/delay_settling.py',old_stage/'jobs.json',old_stage/'completed.json']
    for job in jobs:
        observed,found,paths=inspect_saved(job);cases.extend(observed);sources.extend(paths)
        anchor=found or anchor
    assert anchor is not None
    checks=synthetic_checks(anchor)
    for name,module in list(sys.modules.items()):
        path=getattr(module,'__file__',None)
        if name.startswith('reproduction.') and path:
            p=Path(path).resolve()
            if p.suffix=='.py' and p.is_relative_to(ROOT):sources.append(p)
    primary=[c for c in cases if c['job']=='v19_regression_6000005']
    interval=[c for c in primary if 380<=c['step']<=400]
    result={'passed':True,'scope':'Exact reconstruction of frozen v19 held helper proposals, then changed proposals on those same saved observations and committed parent memory; synthetic boundary/guard/commit tests. No controller, clock, queue, settling-counter or physics execution.',
            'new_physical_episodes':0,'new_evaluation_samples':0,'new_controller_replays':0,
            'saved_executions':9,'unique_dataset_demo_starts':8,'saved_parent_proposals_verified':len(cases),
            'triggered_proposals':sum(c['triggered'] for c in cases),
            'changed_proposed_actions':sum(c['changed_action'] for c in cases),
            'untriggered_exact_action_and_receipt_equivalence':sum(not c['triggered'] for c in cases),
            'maximum_geometry_work_per_proposal':max(c['work'] for c in cases+checks),
            'per_profile':{job['id']:{'proposals':sum(c['job']==job['id'] for c in cases),
                                    'changed_actions':sum(c['job']==job['id'] and c['changed_action'] for c in cases)} for job in jobs},
            'checks':checks,'cases':cases,'target_interval':interval,
            'preserved_thresholds':{'arrival_position_m':.009,'arrival_angle_rad':.08,'consecutive_arrival_frames':5,
                'joint_margin_rad':.04,'hand_box_margin_m':.001,'held_can_box_margin_m':.001,
                'max_translation_m':.035,'max_rotation_rad':.15,'near_region_m':.06,'bias_norm_m':.009,
                'maximum_geometry_work_per_proposal':16,'delay':2,'episode_steps':400,'held_stage_timeout':70},
            'control_rule':{'axis_capture_band_m':new.AXIS_CAPTURE_BAND_M,
                'source':'Existing9mm position sphere divided bysqrt(3), used only for conditional integration; never a new arrival condition.',
                'order':'original sign reset; approaching-axis capture clear; pause every increment inside actual strict9mm sphere; otherwise pause capture axes only; oldnormcap; unchangedP and one oldmotion damping; oldslew andmixedgeometry.',
                'retention':'Outside captured axes, already stored bias survives unless the inherited sign reset removes it. Inside the sphere no new integral is added. P and motion damping continue; no forced zero command.',
                'no_new_feedback_state':new.ServoState is parent.ServoState},
            'limitations':['These proposed actions are evaluated on old observations; their later trajectories and success are unknown.',
                'The per-axis delay band is a control heuristic, not a physical stopping-distance bound or future geometry certificate.',
                'Early removal of integral may slow overcoming static offsets. Existing successes and PLACE are changed and require controlled physical evaluation.',
                'Preserved counter-motion bias can remain during a near-stationary hold; this rule is not a guarantee of remaining inside the arrival sphere.'],
            'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(sources))}}
    with output.open('x',encoding='utf-8') as stream:json.dump(finite(result),stream,indent=2,ensure_ascii=False,allow_nan=False)
    print(json.dumps({k:result[k] for k in ['passed','saved_parent_proposals_verified','triggered_proposals','changed_proposed_actions','untriggered_exact_action_and_receipt_equivalence','maximum_geometry_work_per_proposal']}))


if __name__=='__main__':
    main()
