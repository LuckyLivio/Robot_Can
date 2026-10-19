"""Audit observed joint margins of the actually rerun budget reference.

No controller, IK, physics or collision check is executed. Task success and
joint margins are separate evidence; neither certifies full-arm safety.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import numpy as np

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def audit_row(row):
    q = np.asarray(row['joint_positions'], float)
    margins = np.minimum(q-LIMITS[:, 0], LIMITS[:, 1]-q)
    return {'step': row['step'], 'phase': row['recovery']['mode'],
            'next_phase': row['recovery'].get('next_mode'),
            'observed_joint_positions_rad': q.tolist(),
            'observed_joint_margins_rad': margins.tolist(),
            'minimum_margin_rad': float(margins.min()),
            'limiting_joint_1based': int(margins.argmin())+1,
            'joints_below_004_1based': (np.where(margins < .04)[0]+1).tolist(),
            'joints_outside_nominal_range_1based': (np.where(margins < 0.)[0]+1).tolist(),
            'stable_hold': bool(row['recovery'].get('stable_hold')),
            'submitted_action': row['submitted_action'],
            'state_before_physics': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='smoke_a_budget_reference.json')
    args = parser.parse_args()
    stage = RUN/'smoke_a'
    output_path = RUN/'analysis'/args.output
    assert not output_path.exists()
    assert read(stage/'completed.json')['source_unchanged']
    jobs = [j for j in read(stage/'jobs.json') if j['version'] == 'budget']
    evidence = []
    for job in jobs:
        folder = stage/job['id']
        result = read(folder/'result.json')
        assert result['status'] == 'complete' and result['job'] == job
        record = result['records'][0]
        rows = list(map(json.loads, (folder/'trace.jsonl').open(encoding='utf8')))
        assert len(rows) == record['steps']
        assert job['config']['carry_path'] is False and job['config']['segmented_edge'] is False
        item = {'job': job['id'], 'profile': job['id'].split('_', 1)[1],
                'success': record['success'], 'steps': record['steps'],
                'dataset': job.get('dataset'), 'demo': record['demo'],
                'carry_path_enabled': False, 'segmented_edge_enabled': False,
                'later_v16_v17_live_held_guard_executed': False,
                'required_later_held_margin_rad': .04,
                'source_result_sha256': sha(folder/'result.json'),
                'source_trace_sha256': sha(folder/'trace.jsonl'), 'phases': {}}
        for phase in ['LIFT', 'CARRY', 'PLACE', 'RELEASE', 'RETREAT', 'EXHAUSTED']:
            selected = [audit_row(row) for row in rows if row['recovery']['mode'] == phase]
            if not selected:
                continue
            low = [row for row in selected if row['minimum_margin_rad'] < .04]
            minimum = min(selected, key=lambda row: row['minimum_margin_rad'])
            item['phases'][phase] = {'first_step': selected[0]['step'], 'last_step': selected[-1]['step'],
                                     'observed_steps': len(selected), 'minimum_margin_rad': minimum['minimum_margin_rad'],
                                     'minimum_margin_evidence': minimum,
                                     'below_004_steps': len(low),
                                     'outside_nominal_steps': sum(row['minimum_margin_rad'] < 0. for row in selected),
                                     'every_below_004_frame': low}
        item['carry_or_place_below_004'] = any(item['phases'].get(phase, {}).get('below_004_steps', 0) for phase in ['CARRY', 'PLACE'])
        item['carry_or_place_observed'] = any(phase in item['phases'] for phase in ['CARRY', 'PLACE'])
        evidence.append(item)
    assert len(evidence) == 9
    kin_path = ROOT/'reproduction/improvement_v9_20261015_01/recovery/kinematics.py'
    output = {'script_sha256': sha(__file__), 'kinematics_sha256': sha(kin_path),
              'jobs_sha256': sha(stage/'jobs.json'), 'completed_sha256': sha(stage/'completed.json'),
              'joint_names': ['robot0_joint'+str(i) for i in range(1, 8)],
              'nominal_joint_ranges_rad': LIMITS.tolist(), 'comparison_margin_rad': .04,
              'new_physical_episodes': 0, 'new_controller_replays': 0, 'new_ik_searches': 0,
              'analyzed_newly_executed_budget_profiles': 9,
              'task_successes': sum(item['success'] for item in evidence),
              'successful_profiles_with_carry_or_place_below_004': [item['profile'] for item in evidence if item['success'] and item['carry_or_place_below_004']],
              'profiles': evidence,
              'interpretation': [
                  'Budget 7/9 is a task-success count, not an adoptable result under all current protections.',
                  'Budget disables carry_path and segmented_edge; the later v16/v17 live held joint guard is not executed.',
                  'CARRY and PLACE are separated from RELEASE: current held guards do not apply unchanged to the intentional-release phase.',
                  'A negative margin means the saved observed q lies outside these nominal limits; it does not by itself prove a collision or hardware safety violation.',
                  'A positive joint margin does not certify hand/can geometry, full-arm collisions, force closure or future tracking.',
                  'The two 6000005 profiles share one physical start. Their successful short carry is a local design reference only, not independent generalization evidence.',
                  'Do not remove current guards to reproduce budget successes. Any future local transfer needs the same protection thresholds and new predeclared paired verification.']}
    with output_path.open('x', encoding='utf8') as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'output': str(output_path), 'successes': output['task_successes'],
                      'successes_below_004_in_carry_or_place': output['successful_profiles_with_carry_or_place_below_004']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
