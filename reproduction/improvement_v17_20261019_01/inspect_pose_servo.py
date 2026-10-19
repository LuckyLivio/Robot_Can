"""v17 bounded saved-state and synthetic tests, without simulator stepping."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import types

import h5py
import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import Config
from reproduction.improvement_v17_20261019_01.recovery.pose_servo import (
    ServoState, propose, certify_action, mixed_certificate, observed_motion,
    _hand_box_translation_envelope, arc_displacement_bound, _rotation_grid,
)
from reproduction.improvement_v15_20261016_01.recovery.carry_path import HeldEnvelope
from reproduction.improvement_v9_20261015_01.recovery.geometry import LOCAL
from reproduction.improvement_v8_20261015_01.recovery.geometry import CAN, BOXES
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin

PRIOR = ROOT/'reproduction/improvement_v16_20261016_01'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def trace(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def dense_check(x, action, held, aperture_motion, receipt):
    """Finite product sanity check, distinct from analytical coverage proof."""
    rotation = Rotation.from_quat(x[3:7]).as_matrix()
    delta, turn = action[:3].astype(float)*.05, action[3:6].astype(float)*.5
    gaps = np.linspace(0., .085, 9) if aperture_motion else [abs(x[7]-x[8])]
    envelope = HeldEnvelope.from_state(x) if held else None
    minimum_hand = minimum_second = float('inf')
    count = 0
    for a in np.linspace(0., 1., 9):
        pose = Rotation.from_rotvec(a*turn).as_matrix() @ rotation
        for t in np.linspace(0., 1., 9):
            position = x[:3]+t*delta
            for gap in gaps:
                hand = _hand_box_translation_envelope(position, position, pose, gap)
                second = envelope.sweep_margin(position, position, pose) if held else object_margin(position, position, pose, [gap], x)
                minimum_hand, minimum_second = min(minimum_hand, hand), min(minimum_second, second)
                assert hand >= .001 and second >= receipt['required_can_margin_m']
                count += 1
    return {'sampled_translation_rotation_aperture_combinations': count,
            'minimum_hand_box_m': minimum_hand, 'minimum_second_margin_m': minimum_second,
            'scope': 'Finite sanity grid; analytical convex-aperture/translation and radius-arc bounds cover intervals.'}


def archived_carry_fixtures():
    """Recover exact stage goals by replaying frozen v16 on its saved inputs."""
    stage = PRIOR/'smoke_a'
    started = read(stage/'started.json')
    for rel, digest in started['source_sha256'].items():
        assert sha(stage/'source'/Path(rel).relative_to(PRIOR.relative_to(ROOT))) == digest
    for rel, digest in started['dependency_sha256'].items():
        assert sha(ROOT/rel) == digest
    package = types.ModuleType('v17_diagnose_archived_v16')
    package.__path__ = [str(stage/'source/recovery')]
    sys.modules[package.__name__] = package
    spec = importlib.util.spec_from_file_location(package.__name__+'.recovery_controller', stage/'source/recovery/recovery_controller.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    directory = stage/'v16_known13_bc_k2_noise005_demo_13000021'
    result = read(directory/'result.json')
    assert result['status'] == 'complete'
    rows = trace(directory/'trace.jsonl')
    job = result['job']
    controller = module.RecoveryController([.1975,.4025,.8], .8, np.asarray(rows[0]['state_before'], np.float32), True, module.Config(**job['config']))
    previous = np.zeros(7, np.float32)
    fixtures = []
    for row in rows:
        x = np.asarray(row['state_before'], np.float32)
        controller.set_joint_positions(row['joint_positions'])
        if row['step'] in [325,345,365,366,380,400]:
            stage = controller.carry_plan['stages'][controller.carry_index]
            fixtures.append({'step': row['step'], 'x': x.copy(), 'goal': stage['goal'].copy(),
                             'rotation': stage['rotation'].copy(), 'label': stage['label'],
                             'motion': observed_motion(x, rows[row['step']-2]['state_before']),
                             'previous_action': np.asarray(rows[row['step']-2]['submitted_action'])})
        action, info = controller.choose(x, np.asarray(row['original_proposal'], np.float32), previous)
        assert np.array_equal(action, row['submitted_action'])
        original, replay = dict(row['recovery']), dict(info)
        original.pop('planning_ms', None); replay.pop('planning_ms', None)
        assert original == replay
        previous = np.asarray(row['executed_action'], np.float32)
    for field in ['events','carry15_events','held16_events','ik16_events']:
        assert getattr(controller, field) == result['records'][0][field]
    return fixtures, [directory/'result.json', directory/'trace.jsonl', PRIOR/'smoke_a/started.json']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='pose_servo_static_a')
    args = parser.parse_args()
    assert Path(args.name).name == args.name
    destination = RUN/'analysis'/(args.name+'.json')
    assert not destination.exists(), 'Preserve prior test receipts; use another --name'
    cfg = Config()
    output = {'passed': True, 'new_physical_episodes': 0, 'new_evaluation_samples': 0,
              'scope': 'Nominal geometric certificates, finite grids, explicit servo-state tests and proposals on saved old observations. No closed-loop improvement claim.',
              'positive_saved_state_proposals': [], 'negative_checks': [], 'state_checks': [],
              'osc_evidence': {}, 'source_sha256': {},
              'unchanged': {'delay': 2, 'total_controls': 400, 'phase_timeout': 70,
                            'arrival_position_m': .009, 'arrival_angle_rad': .08, 'arrival_frames': 5,
                            'translation_cap_m': .035, 'rotation_cap_rad': .15, 'work_cap': 16,
                            'hand_box_m': .001, 'held_can_box_m': .001,
                            'empty_execution_can_m': .001, 'empty_planning_can_m': .003}}
    sources = [Path(__file__), RUN/'recovery/pose_servo.py']
    osc = ROOT/'.venv/Lib/site-packages/robosuite/controllers/parts/arm/osc.py'
    composite = ROOT/'.venv/Lib/site-packages/robosuite/controllers/composite/composite_controller.py'
    gripper = ROOT/'.venv/Lib/site-packages/robosuite/models/grippers/panda_gripper.py'
    sources += [osc, composite, gripper, ROOT/'common.py']
    with h5py.File(ROOT/'data/can_ph_lowdim_v15.hdf5') as data:
        meta = json.loads(data['data'].attrs['env_args'])
    control = meta['env_kwargs']['controller_configs']
    assert control['type'] == 'BASIC' and control['body_parts']['right']['input_ref_frame'] == 'world'
    output['osc_evidence'] = {
        'metadata': control,
        'source_verified_semantics': 'BASIC set_goal -> OSC scaled delta; reset_goal defaults achieved, goal=achieved_pose+delta; kp150 and kd=2sqrt(kp), no interpolator.',
        'v16_translation_equivalent': 'For unclipped commands: 0.5*error - (0.5*2+1.5)*observed_displacement = 0.5*error-2.5*displacement.',
        'v16_angular_local_equivalent': 'Locally near a fixed orientation axis: 0.5*angle_error-(0.5*2+0.3)*observed_angle = 0.5*error-1.3*observed_angle; SO(3) rotations need not commute.',
        'v17_command_change': 'One near-goal observed damping term, bounded committed position bias; far translation retains original proportional command. Original arrival/queue/phase rules remain external.',
        'gripper_semantics': 'sign(grip) changes hidden desired gripper target; no small-amplitude continuous aperture guarantee. Parallel empty motion therefore certifies full 0..85mm aperture.',
        'inference_limit': 'The saved drift and source semantics motivate a controlled candidate; neither proves these gains improve future dynamics.'}
    edge_path = PRIOR/'analysis/smoke_a_edge_diagnosis.json'
    cases = read(edge_path)['cases']; sources.append(edge_path)
    exemplar = None
    for condition, steps in [('known13_full_s41_noise005_demo_13000022',[156,166,176,204,260,274,394,400]),
                             ('regression_6000005',[186,196,202,224,293,324])]:
        case = next(c for c in cases if c['version']=='v16' and c['condition']==condition)
        trace_path = PRIOR/'smoke_a'/('v16_'+condition)/'trace.jsonl'
        rows = trace(trace_path); sources.append(trace_path)
        for step in steps:
            metric = next(m for m in case['per_control_observations'] if m['step']==step)
            row = rows[step-1]
            x = np.asarray(row['state_before'])
            motion = observed_motion(x, rows[step-2]['state_before'])
            opening = not metric['gap_ready_after_observation'] or row['recovery']['mode']=='EDGE_APERTURE'
            grip = float(row['submitted_action'][6]) if opening else 0.
            state = ServoState()
            action, receipt = propose(x, metric['goal_m'], metric['goal_rotation'], motion, cfg,
                                      state=state, phase=(metric['attempt_before'], metric['logical_phase_before']),
                                      grip=grip, aperture_motion=opening)
            assert receipt['accepted'], (condition,step,receipt)
            assert receipt['work'] <= 16
            assert state.goal is None
            assert state.commit(action,receipt)
            entry={'job':'v16_'+condition,'step':step,'action':action.tolist(),'receipt':receipt,
                   'old_position_error_m':metric['position_error_m'],
                   'old_angle_error_rad':metric['orientation_error_rad'],
                   'old_submitted_action':row['submitted_action'],
                   'old_actual_next_displacement_m':(np.asarray(row['state_after'][:3])-x[:3]).tolist()}
            if exemplar is None and opening:
                entry['dense_grid']=dense_check(x,action,False,True,receipt)
                exemplar=(x,metric['goal_m'],metric['goal_rotation'],motion)
            output['positive_saved_state_proposals'].append(entry)
    fixtures, carry_sources=archived_carry_fixtures(); sources+=carry_sources
    output['archived_v16_decisions_replayed']=400
    for fixture in fixtures:
        action, receipt=propose(fixture['x'],fixture['goal'],fixture['rotation'],fixture['motion'],cfg,
                                state=ServoState(),phase=('carry',fixture['label']),held=True,grip=1.,
                                previous_action=fixture['previous_action'])
        assert receipt['accepted'], receipt
        assert np.linalg.norm(action[:3].astype(float)*.05-fixture['previous_action'][:3]*.05)<=.035/3+1e-8
        assert np.linalg.norm(action[3:6].astype(float)*.5-fixture['previous_action'][3:6]*.5)<=.15/3+1e-8
        entry={'family':'held_carry','step':fixture['step'],'segment':fixture['label'],'action':action.tolist(),'receipt':receipt}
        if fixture['step']==325:entry['dense_grid']=dense_check(fixture['x'],action,True,False,receipt)
        output['positive_saved_state_proposals'].append(entry)

    x,goal,rotation,motion=exemplar
    current_rotation=Rotation.from_quat(x[3:7]).as_matrix()
    state=ServoState()
    local_goal=x[:3]+[.02,0,0]
    args=(x,local_goal,current_rotation,np.zeros(6),cfg)
    first,first_receipt=propose(*args,state=state,phase='fixed')
    repeat,repeat_receipt=propose(*args,state=state,phase='fixed')
    assert first_receipt==repeat_receipt and np.array_equal(first,repeat) and state.goal is None
    for _ in range(30):
        action,receipt=propose(*args,state=state,phase='fixed')
        assert receipt['accepted'] and state.commit(action,receipt)
        assert np.linalg.norm(state.bias)<=.009+1e-12
    output['state_checks'].append({'check':'propose_does_not_mutate_and_committed_bias_bounded','passed':True,'bias_after_30_fixed_observations_m':state.bias.tolist(),'not_a_simulation':True})
    action,receipt=propose(*args,state=state,phase='changed')
    assert receipt['state_reset_reason']=='phase_or_held_state_changed'
    assert np.allclose(receipt['position_bias_m'],[.002,0,0])
    state.commit(action,receipt)
    altered_goal=local_goal.copy();altered_goal[0]+=1e-8
    action,receipt=propose(x,altered_goal,current_rotation,np.zeros(6),cfg,state=state,phase='changed')
    assert receipt['state_reset_reason']=='target_changed'
    assert state.commit(action,receipt)
    replaced=action.copy();replaced[0]=0
    assert not state.commit(replaced,receipt) and state.goal is None
    output['state_checks'].append({'check':'exact_phase_goal_change_and_replaced_command_reset','passed':True})
    action,receipt=propose(*args,state=state,phase='pause_test')
    assert state.commit(action,receipt)
    paused=np.zeros(7,np.float32)
    action,receipt=propose(*args,state=state,phase='pause_test',previous_action=paused)
    assert receipt['state_reset_reason']=='interrupted_by_uncertified_command'
    assert np.allclose(receipt['position_bias_m'],[.002,0,0])
    output['state_checks'].append({'check':'parent_pause_or_hold_resets_old_bias_before_resume','passed':True})

    no_pulse=certify_action(x,np.array([.1,0,0,0,0,0,-1]),aperture_motion=False)
    assert not no_pulse['accepted'] and no_pulse['work']==0
    output['negative_checks'].append({'check':'pulse_without_full_aperture_certificate_rejected','passed':True,'receipt':no_pulse})
    # A real saved open-hand pose is safe at its current gap but would not be
    # certified over the full closing/opening range. This distinguishes the
    # aperture product check from merely recycling the narrow-gap certificate.
    near_path=PRIOR/'smoke_a/v16_regression_6000005/trace.jsonl'
    near_state=np.asarray(trace(near_path)[334]['state_before'])
    narrow=mixed_certificate(near_state,[0,0,0],[0,0,0])
    wide=mixed_certificate(near_state,[0,0,0],[0,0,0],aperture_motion=True)
    assert narrow['accepted'] and not wide['accepted']
    output['negative_checks'].append({'check':'narrow_gap_acceptance_does_not_authorize_full_aperture_motion','passed':True,
                                     'source_step':335,'narrow_can_margin_m':narrow['can_margin_m'],
                                     'full_aperture_can_margin_m':wide['can_margin_m']})
    insufficient=mixed_certificate(x,[.005,0,0],[0,.15,0],work_limit=5,aperture_motion=True)
    assert not insufficient['accepted'] and insufficient['work']==0
    output['negative_checks'].append({'check':'insufficient_geometry_work_rejected','passed':True})
    release=certify_action(x,np.array([0,0,0,0,0,0,-1]),held=True)
    assert not release['accepted'] and release['work']==0
    output['negative_checks'].append({'check':'held_release_cannot_claim_rigid_holding_certificate','passed':True})
    bad=x.copy();bad[7]=.1;bad[8]=-.1
    certificate=mixed_certificate(bad,[0,0,0],[0,0,0],aperture_motion=True)
    assert not certificate['accepted'] and certificate['work']==0
    output['negative_checks'].append({'check':'observed_gap_outside_certified_range_rejected','passed':True})
    hand_center=LOCAL[0][1].mean(0)@current_rotation.T+x[:3]
    collision=x.copy();can_rotation=Rotation.from_quat(x[19:23]).as_matrix()
    collision[16:19]=hand_center-CAN.mean(0)@can_rotation.T
    action,receipt=propose(collision,collision[:3]+[.02,0,0],current_rotation,np.zeros(6),cfg,state=ServoState(),phase='blocked',grip=-1,aperture_motion=True)
    assert not receipt['accepted'] and np.array_equal(action[:6],np.zeros(6)) and receipt['work']<=16
    output['negative_checks'].append({'check':'full_aperture_can_overlap_rejected','passed':True,'receipt':receipt})
    collision=x.copy();shift=BOXES[0][0]-hand_center;collision[:3]+=shift;collision[16:19]+=shift
    certificate=mixed_certificate(collision,[.005,0,0],[0,.1,0],aperture_motion=True)
    assert not certificate['accepted'] and certificate['box_margin_m']<.001
    output['negative_checks'].append({'check':'full_aperture_box_overlap_rejected','passed':True,'receipt':certificate})
    for translation,turn in [([.036,0,0],[0,0,0]),([0,0,0],[.151,0,0])]:
        certificate=mixed_certificate(x,translation,turn)
        assert not certificate['accepted'] and certificate['work']==0
    output['negative_checks'].append({'check':'original_motion_caps_preserved','passed':True})
    invalid=x.copy();invalid[0]=np.nan
    action,receipt=propose(invalid,x[:3],current_rotation,np.zeros(6),cfg,held=True,grip=1)
    assert not receipt['accepted'] and np.array_equal(action,[0,0,0,0,0,0,1])
    output['negative_checks'].append({'check':'nonfinite_input_rejected_preserves_hold','passed':True})
    try:
        mixed_certificate(x,[0,0,0],[0,0,0],can_margin_m=.0005)
        raise AssertionError('Loosened margin accepted')
    except ValueError:
        output['negative_checks'].append({'check':'loosened_clearance_rejected','passed':True})
    rng=np.random.default_rng(170019);vertices=rng.normal(size=(64,3));vertices*=.23/np.linalg.norm(vertices,axis=1).max()
    turn=np.array([.06,-.08,.11]);turn*=.15/np.linalg.norm(turn)
    grid,angle,intervals=_rotation_grid(current_rotation,turn)
    bound=arc_displacement_bound(float(np.linalg.norm(vertices,axis=1).max()),angle,intervals)
    maximum=0.
    for fraction in np.linspace(0,1,1001):
        actual=Rotation.from_rotvec(fraction*turn).as_matrix()@current_rotation
        d=float(np.linalg.norm(vertices@actual.T-vertices@grid[int(round(fraction*intervals))].T,axis=1).max())
        maximum=max(maximum,d);assert d<=bound+1e-12
    output['rotation_arc_test']={'passed':True,'vertices':64,'fractions':1001,'bound_m':bound,'observed_max_m':maximum}
    output['maximum_proposal_work']=max(p['receipt']['work'] for p in output['positive_saved_state_proposals'])
    output['source_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
    output['limitations']=['No v17 physics or closed-loop success result.','Static certificate does not cover future D2 tracking error or full-arm collision.','A rigid carried hull does not prove force closure or absence of slip.','Pure held servo does not decide whether a large-angle candidate fits remaining task budget.']
    destination.write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({'passed':True,'saved_proposals':len(output['positive_saved_state_proposals']),
                      'negatives':len(output['negative_checks']),'new_physics':0,'output':str(destination)},ensure_ascii=False))


if __name__=='__main__':main()
