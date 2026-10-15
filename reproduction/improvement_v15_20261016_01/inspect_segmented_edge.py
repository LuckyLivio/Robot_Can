"""Offline known-input checks of the v15 edge helper; no physics episodes."""
from pathlib import Path
import hashlib
import json
import sys
import time

import numpy as np

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import RecoveryController as V13, Config as C13
from reproduction.improvement_v15_20261016_01.recovery.edge_path import SegmentedEdgeSearch


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def advance(search):
    slices = []
    elapsed = []
    while not search.done:
        before = search.work
        tic = time.perf_counter()
        search.advance(16)
        elapsed.append(1000 * (time.perf_counter() - tic))
        slices.append(search.work - before)
        assert 0 < slices[-1] <= 16
        assert len(slices) < 1000
    return {
        'chosen': plain(search.chosen), 'receipts': plain(search.receipts),
        'work_units': search.work, 'advance_calls': len(slices),
        'maximum_work_units_per_call': max(slices, default=0),
        'maximum_observed_call_ms': max(elapsed, default=0),
    }


def first_wall_input(path):
    result = json.loads((path / 'result.json').read_text(encoding='utf-8'))
    assert result['status'] == 'complete' and result['job']['version'] == 'v13'
    controller = None
    previous = np.zeros(7, np.float32)
    for row in map(json.loads, (path / 'trace.jsonl').open(encoding='utf-8')):
        x = np.asarray(row['state_before'], np.float32)
        if controller is None:
            controller = V13([.1975, .4025, .8], .8, x, True, C13(**result['job']['config']))
        controller.set_joint_positions(np.asarray(row['joint_positions']))
        if controller.eligible(x):
            return controller, x, row['step']
        action, _ = controller.choose(x, np.asarray(row['original_proposal'], np.float32), previous)
        np.testing.assert_allclose(action, row['submitted_action'], atol=1e-7, rtol=0)
        assert controller.clock == row['step']
        previous = np.asarray(row['executed_action'], np.float32)
    raise AssertionError('No wall-top path entry in source trajectory')


def main():
    prior = ROOT / 'reproduction/improvement_v14_20261016_01/smoke_b'
    cases = ['v13_known13_full_s41_noise005_demo_13000022', 'v13_regression_6000005']
    report = {
        'validation_scope': 'Offline saved-input replay, fixed geometry and bounded IK only; no new physics or success claim.',
        'cases': [], 'negative_checks': [],
        'thresholds': {'box_margin_m': .001, 'can_margin_m': .003, 'joint_margin_rad': .04},
    }
    for name in cases:
        path = prior / name
        controller, x, step = first_wall_input(path)
        search = SegmentedEdgeSearch(controller, x, controller.joints)
        outcome = advance(search)
        report['cases'].append({'source_job': name, 'source_step': step, **outcome})
        if name == cases[0]:
            impossible = x.copy()
            impossible[:3] += 10.
            denial = advance(SegmentedEdgeSearch(controller, impossible, controller.joints))
            assert denial['chosen'] is None
            report['negative_checks'].append({'case': 'synthetic_unreachable_pretranslation', **denial})
    source = RUN / 'recovery/edge_path.py'
    report['helper_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    report['passed'] = True
    output = RUN / 'analysis/segmented_edge_static.json'
    output.parent.mkdir(exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({'passed': True, 'report': str(output), 'cases': [
        {'job': case['source_job'], 'step': case['source_step'], 'chosen': case['chosen'] is not None,
         'calls': case['advance_calls'], 'units': case['work_units'],
         'maximum_call_ms': case['maximum_observed_call_ms']} for case in report['cases']]}))


if __name__ == '__main__':
    main()
