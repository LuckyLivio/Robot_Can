"""Read-only axial/lateral decomposition of recorded v19-stage descents.

The planned orientation is read from the preceding accepted EDGE_APPROACH
receipt. No simulator, controller replay, new IK, or case-dependent runtime
rule is created by this evidence extraction.
"""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v19_20261019_01.recovery.recovery_controller import Config


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def main():
    old_run = ROOT / 'reproduction/improvement_v19_20261019_01'
    diagnosis_path = old_run / 'analysis/smoke_a_control_diagnosis.json'
    diagnosis = json.loads(diagnosis_path.read_text(encoding='utf8'))
    assert diagnosis['passed'] and diagnosis['selected_evaluation_executions'] == 72
    output = RUN / 'analysis/directional_axis_diagnosis.json'
    assert not output.exists(), 'Preserve previous receipts; use a new file for a new diagnosis.'
    sources = [Path(__file__), diagnosis_path]
    cfg = Config()
    cases = []
    for version in ['v18', 'transition']:
        for condition in ['regression_6000005', 'known_full_s23_clean_demo_12000036']:
            job = version + '_' + condition
            result_path = old_run / 'smoke_a' / job / 'result.json'
            trace_path = old_run / 'smoke_a' / job / 'trace.jsonl'
            for path in [result_path, trace_path]:
                assert sha(path) == diagnosis['source_sha256'][rel(path)]
                sources.append(path)
            record = json.loads(result_path.read_text(encoding='utf8'))['records'][0]
            rows = [json.loads(line) for line in trace_path.read_text(encoding='utf8').splitlines()]
            handoff = {e['step']: e for e in record['handoff18_events']
                       if e['event'] == 'descent_handoff_control'}
            preceding_rotation = None
            per_control = []
            for row in rows:
                receipt = row['recovery'].get('mixed_pose', {})
                update = receipt.get('state_update', {})
                if (row['recovery']['mode'] == 'EDGE_APPROACH'
                        and receipt.get('accepted') and 'rotation' in update):
                    preceding_rotation = np.asarray(update['rotation'], float)
                if row['step'] not in handoff:
                    continue
                assert preceding_rotation is not None
                event = handoff[row['step']]
                assert event['accepted'] and event['applied']
                np.testing.assert_array_equal(event['actual_submitted_action'], row['submitted_action'])
                x = np.asarray(row['state_before'], float)
                goal = np.asarray(event['goal'], float)
                motion = np.r_[receipt['observed_translation_per_step_m'],
                               receipt['observed_rotation_per_step_rad']]
                axis = preceding_rotation[:, 2]
                error = goal - x[:3]
                axial_error, axial_motion = float(error @ axis), float(motion[:3] @ axis)
                lateral_error = error - axis * axial_error
                lateral_motion = motion[:3] - axis * axial_motion
                forecast_error = lateral_error - cfg.delay * lateral_motion
                per_control.append({
                    'control_step': row['step'], 'state_before': x.tolist(), 'goal_m': goal.tolist(),
                    'target_rotation': preceding_rotation.tolist(), 'descent_axis': axis.tolist(),
                    'motion_per_control': motion.tolist(),
                    'previous_submitted_action': receipt['previous_submitted_action'],
                    'actual_submitted_action': row['submitted_action'],
                    'aperture_motion': receipt['aperture_motion'],
                    'descent_controls': receipt.get('transition19', {}).get('descent_controls'),
                    'axial_error_m': axial_error, 'axial_motion_m_per_control': axial_motion,
                    'lateral_error_m': lateral_error.tolist(),
                    'lateral_motion_m_per_control': lateral_motion.tolist(),
                    'lateral_error_norm_m': float(np.linalg.norm(lateral_error)),
                    'lateral_motion_norm_m_per_control': float(np.linalg.norm(lateral_motion)),
                    'lateral_closing_dot_m2': float(lateral_error @ lateral_motion),
                    'nominal_lateral_error_after_delay_m': forecast_error.tolist(),
                    'nominal_lateral_error_after_delay_norm_m': float(np.linalg.norm(forecast_error)),
                    'nominal_lateral_crossing_dot_m2': float(lateral_error @ forecast_error),
                    'original_raw_translation_m': receipt['raw_translation_m'],
                    'original_geometry_work': receipt['work'],
                })
            assert per_control
            cases.append({'job': job, 'version': version, 'condition': condition,
                          'per_control': per_control})
    facts = {
        'passed': True, 'scope': 'Read-only decomposition of four original saved traces; no candidate performance claim.',
        'new_physical_episodes': 0, 'new_evaluation_samples': 0, 'saved_controller_replay_performed': False,
        'cases': cases,
        'findings_zh': [
            '6000005的原A在304步横向距中心约1.13mm、朝中心运动约1.52mm每步；D2名义外推已跨中心，305步开始向外，310步横向误差约11.13mm。固定年龄退出阻尼没有区分这段横向风险。',
            '12000036原A在230–236步横向误差约3.69→1.74mm并接近中心；正常轴向误差约40.98→8.42mm。持续全向阻尼对这段轴向进展产生额外代价。',
            '运动分解只能支持候选控制设计，不能证明新动作会改变未来实际轨迹、通过几何检查或提高成功率。'
        ],
        'input_boundary': 'Only saved current observation, known prior submitted command, measured past displacement, and previously planned orientation are used.',
        'source_sha256': {rel(path): sha(path) for path in sources}
    }
    with output.open('x', encoding='utf8') as f:
        json.dump(facts, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'passed': True, 'cases': len(cases),
                      'saved_controls': sum(len(c['per_control']) for c in cases),
                      'output': rel(output), 'new_physical_episodes': 0}))


if __name__ == '__main__':
    main()
