"""Saved-state IK and held-hull diagnostics; no simulator or new episodes."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import hashlib
import json
import sys
import time
import numpy as np
from scipy.spatial.transform import Rotation

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import Config
from reproduction.improvement_v15_20261016_01.recovery import carry_path
from reproduction.improvement_v15_20261016_01.recovery.carry_path import CarryPathSearch, HeldEnvelope, translation_certificate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serial(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    raise TypeError(type(value).__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='carry_path_offline_b')
    parser.add_argument('--revision', default='fixed_current_then_outward30')
    parser.add_argument('--steps', nargs='+', type=int, default=[311, 312, 320, 350, 365, 400])
    args = parser.parse_args()
    destination = RUN/'analysis'/(args.output+'.json')
    assert not destination.exists(), 'Diagnostic records are append-only.'
    trace = ROOT/'reproduction/improvement_v14_20261016_01/smoke_b/v14_known13_bc_k2_noise005_demo_13000021/trace.jsonl'
    rows = list(map(json.loads, trace.open(encoding='utf8')))
    controller = SimpleNamespace(cfg=Config(), floor=.8, target=np.array([.1975, .4025, .8]))
    checks = []
    samples = []
    for step in args.steps:
        row = rows[step-1]
        x = np.array(row['state_before'])
        q = np.array(row['joint_positions'])
        envelope = HeldEnvelope.from_state(x)
        rotation = Rotation.from_quat(x[3:7]).as_matrix()
        expected = carry_path.CAN @ Rotation.from_quat(x[19:23]).as_matrix().T + x[16:19]
        np.testing.assert_allclose(envelope.world_vertices(x[:3], rotation), expected, rtol=0, atol=1e-12)
        np.testing.assert_allclose(envelope.held_offset(rotation), x[:3]-x[16:19], rtol=0, atol=1e-12)
        search = CarryPathSearch(controller, x, q)
        slices = []
        while not search.done:
            before = search.work
            started = time.perf_counter()
            search.advance(16)
            milliseconds = 1000*(time.perf_counter()-started)
            assert search.work-before <= 16 and search.last_geometry_work <= 4
            slices.append({'work': search.work-before, 'geometry_checks': search.last_geometry_work, 'elapsed_ms': milliseconds})
            assert len(slices) < 1000
        if search.chosen is not None and not search.chosen['preserve_current']:
            assert search.chosen['minimum_joint_margin_rad'] >= .04
            assert search.chosen['minimum_hand_margin_m'] >= .001
            assert search.chosen['minimum_carried_can_margin_m'] >= .001
            assert search.chosen['placement']['goal'][2] == controller.floor+.085+search.chosen['held_offset'][2]
            assert len(search.chosen['stages']) == 3
        samples.append({'step': step, 'recorded_mode': row['recovery']['mode'],
                        'recorded_stable_hold': row['recovery'].get('stable_hold'),
                        'candidate_order': [name for name, _ in search.options],
                        'work_units': search.work, 'control_slices_required': len(slices),
                        'slices': slices, 'chosen': search.chosen, 'receipts': search.receipts})
    checks.append({'check': 'actual_observed_can_hull_and_world_held_offset_reconstructed', 'passed': True})
    checks.append({'check': 'bounded_16_work_units_4_geometry_checks_per_advance', 'passed': True})
    checks.append({'check': 'chosen_paths_keep_0_04rad_IK_and_1mm_hand_and_carried_can_clearance', 'passed': True})
    # This deliberately non-graspable synthetic placement tests the hull
    # checker only: a clear hand may not hide a can intersecting fixed geometry.
    x = np.array(rows[311]['state_before'], float)
    x[:3] = [.1, -.25, 1.25]
    x[3:7] = [1., 0., 0., 0.]
    x[16:19] = carry_path.BOXES[0][0]
    x[19:23] = [0., 0., 0., 1.]
    collision = translation_certificate(x, x[:3])
    assert collision['hand_margin_m'] >= .001
    assert collision['carried_can_margin_m'] < .001 and not collision['accepted']
    checks.append({'check': 'clear_hand_with_colliding_can_is_rejected', 'passed': True,
                   'synthetic_not_a_valid_grasp_state': True, **collision})
    result = {'passed': True, 'revision': args.revision, 'new_physical_episodes': 0,
              'source_sha256': digest(Path(carry_path.__file__)), 'diagnostic_script_sha256': digest(Path(__file__)),
              'input_trace': trace.relative_to(ROOT).as_posix(), 'input_trace_sha256': digest(trace),
              'samples': samples, 'checks': checks,
              'interpretation': 'Known saved-state planning diagnostics only. Control slices are real budget costs if integrated; timings describe offline checks, not achieved control-loop timing.',
              'limitations': ['Observed rigid hand-can proxy; no grasp-force or full-arm collision certificate.',
                              'IK waypoint validity does not guarantee the operational-space controller follows the same joint branch.',
                              'Current-orientation preserve_current returns only original-endpoint reachability, not a new geometry certificate.',
                              'These diagnostics do not establish success-rate improvement.']}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf8') as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, default=serial, allow_nan=False)
    print(json.dumps({'passed': True, 'output': str(destination),
                      'samples': [{'step': s['step'], 'work': s['work_units'], 'slices': s['control_slices_required'],
                                   'chosen': None if s['chosen'] is None else s['chosen']['candidate']} for s in samples]}))


if __name__ == '__main__':
    main()
