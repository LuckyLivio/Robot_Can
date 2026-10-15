"""Read-only saved-input replay of the registered wall-top target; no physics."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import types
import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import RecoveryController as Parent, Config as ParentConfig
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stage = RUN/'smoke_a'
    started = json.loads((stage/'started.json').read_text())
    for rel, digest in started['source_sha256'].items():
        frozen = stage/'source'/Path(rel).relative_to(RUN.relative_to(ROOT))
        assert sha(frozen) == digest
    package = types.ModuleType('edge_diagnosis_frozen15')
    package.__path__ = [str(stage/'source/recovery')]
    sys.modules[package.__name__] = package
    spec = importlib.util.spec_from_file_location(package.__name__+'.recovery_controller', stage/'source/recovery/recovery_controller.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    condition = 'known13_full_s41_noise005_demo_13000022'
    output = {'passed': True, 'stage': 'smoke_a', 'new_physical_episodes': 0,
              'saved_input_replay': True, 'source': {}, 'cases': [],
              'unchanged_thresholds': {'position_m': .009, 'orientation_rad': .08,
                                       'stable_frames': 5, 'stage_timeout': 70, 'total_steps': 400}}
    for version in ['v14', 'edge', 'v15']:
        directory = stage/(version+'_'+condition)
        result_path = directory/'result.json'
        trace_path = directory/'trace.jsonl'
        result = json.loads(result_path.read_text())
        record = result['records'][0]
        job = result['job']
        rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
        cls, config = (Parent, ParentConfig) if version == 'v14' else (module.RecoveryController, module.Config)
        controller = cls([.1975,.4025,.8], .8, np.array(rows[0]['state_before'], np.float32), job['enabled'], config(**job.get('config', {})))
        previous = np.zeros(7, np.float32)
        metrics = []
        error = 0.
        for row in rows:
            x = np.array(row['state_before'], np.float32)
            q = np.array(row['joint_positions'])
            controller.set_joint_positions(q)
            old_phase = controller.mode
            old_plan = controller.edge_plan
            old_start = getattr(controller, 'edge_start', None)
            if old_start is not None:
                old_start = old_start.copy()
            action, info = controller.choose(x, np.array(row['original_proposal'], np.float32), previous)
            error = max(error, float(np.max(np.abs(action-np.array(row['submitted_action'])))))
            assert error <= 1e-7
            saved = dict(row['recovery']); saved.pop('planning_ms', None)
            reproduced = dict(info); reproduced.pop('planning_ms', None)
            assert saved == reproduced
            phase = info['mode']
            plan = old_plan if old_phase in ['EDGE_ROTATE','EDGE_APPROACH'] else controller.edge_plan
            if phase in ['EDGE_ROTATE','EDGE_APPROACH'] and plan is not None:
                goal = old_start if phase=='EDGE_ROTATE' else plan['above']
                if goal is None:
                    goal = controller.edge_start
                angle = float(np.linalg.norm(Rotation.from_matrix(plan['rotation'] @ Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec()))
                distance = float(np.linalg.norm(x[:3]-goal))
                metrics.append({'step': row['step'], 'phase': phase, 'attempt': controller.attempts,
                                'position_error_m': distance, 'orientation_error_rad': angle,
                                'within_both_pose_thresholds': distance<.009 and angle<.08,
                                'gap_ready': bool(controller.gap_ready(x)),
                                'joint_margin_rad': float(np.min(np.minimum(q-LIMITS[:,0], LIMITS[:,1]-q))),
                                'stable_hold': info['stable_hold']})
            previous = np.asarray(row['executed_action'], np.float32)
        assert controller.events == record['events']
        for field in ['edge15_events','budget15_events']:
            if hasattr(controller, field):
                assert getattr(controller, field) == record[field]
        first_turn = [item for item in metrics if item['phase']=='EDGE_ROTATE' and item['attempt']==1]
        streak = maximum = 0
        for item in first_turn:
            streak = streak+1 if item['within_both_pose_thresholds'] and item['gap_ready'] else 0
            maximum = max(maximum, streak)
        final = rows[-1]['recovery']
        output['cases'].append({
            'version': version, 'job': job['id'], 'success': record['success'], 'steps': record['steps'],
            'max_replay_action_error': error, 'events_exact': True,
            'phases': record['phases'], 'final_control_mode': final['mode'],
            'final_next_mode': final.get('next_mode'), 'final_recovery_diagnostic': final,
            'transitions': [{k:e[k] for k in ['step','from','to','reason']} for e in record['events']],
            'segmented_events': [{k:v for k,v in e.items() if k!='options'} for e in record.get('edge15_events',[])],
            'first_rotation': {'controls': len(first_turn), 'max_joint_pose_and_aperture_streak': maximum,
                               'min_joint_margin_rad': min(item['joint_margin_rad'] for item in first_turn),
                               'last_control': first_turn[-1],
                               'best_angle_control': min(first_turn, key=lambda item:item['orientation_error_rad']),
                               'best_position_control': min(first_turn, key=lambda item:item['position_error_m'])},
            'rotation_and_approach_observations': metrics,
        })
        for path in [result_path, trace_path]:
            output['source'][path.relative_to(ROOT).as_posix()] = sha(path)
    output['interpretation'] = [
        'The segmented candidate passed static path/IK checks and pretranslation settled, but the first rotation still timed out; certified waypoints do not establish delayed closed-loop tracking.',
        'The second attempt reaches DESCEND only at step 385, leaving 15 controls; all 400 steps end during path recentering, with no verified recovery grasp.',
        'No thresholds should be relaxed. Future isolated work should check delayed position/rotation settling and reserve full grasp/transport/release time before accepting a path. No such change or new experiment is performed by this diagnostic.',
    ]
    destination = RUN/'analysis/smoke_a_edge_diagnosis.json'
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    for case in output['cases']:
        print(case['version'], case['final_control_mode'], case['first_rotation'])


if __name__=='__main__':
    main()
