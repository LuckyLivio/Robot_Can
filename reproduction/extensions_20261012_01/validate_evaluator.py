import importlib.util, json, sys
from pathlib import Path
import numpy as np, torch
RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from evaluate import run, load_model, predict, sequences, select


def main():
    spec = importlib.util.spec_from_file_location('previous_evaluator', ROOT/'reproduction/multiseed_20261012_01/evaluate_suite.py')
    previous = importlib.util.module_from_spec(spec); spec.loader.exec_module(previous)
    from argparse import Namespace
    checks = []
    for label, noise in [('clean', 0.), ('noise', .05)]:
        names = ['demo_105', 'demo_97']
        args = Namespace(method='wm', model='multiseed_20261012_01_full_s17',
                         policy='bc_chunk_dev_v4', policy_checkpoint='policy_15000.pt', split='dev',
                         episodes=2, steps=400, delay=2, shift_index=None, fallback_index=2,
                         candidates=4, horizon=8, noise=noise, risk_weight=.5, readout_weight=.02,
                         gate_margin=.02, fallback='shift', score_only=True, candidate_mode='shift',
                         demos=names, output_dir=str(RUN/'validation_v2'/label/'old'), trace=True)
        oldpath = previous.run(args)
        job = {'id': 'validation', 'method': 'full', 'seed': 17, 'noise': noise,
               'candidate_ids': [0, 1, 2, 3], 'horizon': 8, 'demos': names, 'full_trace': True}
        newpath = run(job, RUN/'validation_v2'/label/'new')
        old = json.loads(oldpath.read_text()); new = json.loads(newpath.read_text())
        for a, b in zip(old['records'], new['records']):
            for key in ['demo', 'success', 'steps', 'peak_stage_reward', 'ever_grasped', 'selection_counts', 'fraction_override']:
                assert a[key] == b[key], (key, a[key], b[key])
        newtraces = [json.loads(line) for line in (newpath.parent/'decisions.jsonl').read_text().splitlines()]
        for name in names:
            oldtraces = [json.loads(line) for line in (oldpath.parent/old['trace_files'][name]).read_text().splitlines()]
            selected = [t for t in newtraces if t['demo'] == name]
            assert len(oldtraces) == len(selected)
            worst = 0.
            for a, b in zip(oldtraces, selected):
                for key in ['state_before', 'state_after', 'queue_before', 'base_chunk', 'submitted_action', 'executed_action_before_noise', 'executed_action', 'model_sequences', 'predicted_states', 'stages_after']:
                    worst = max(worst, float(np.max(np.abs(np.asarray(a[key])-np.asarray(b[key])))))
                assert a['selected'] == b['selected_shift'] and a['raw_selected'] == b['raw_shift']
                assert np.array_equal(a['learned_scores'], b['scores'])
            assert worst == 0., worst
            checks.append({'noise': noise, 'demo': name, 'steps': len(selected), 'max_error': worst})
    rng = np.random.default_rng(19)
    branch = np.load(ROOT/'data/branches_dev_queuepair_20261012_01_real.npz')
    invariants = []
    for seed in [17, 23, 41]:
        model = load_model(seed)
        for index in [0, 15, 31, 63]:
            x, q = branch['x'][index], branch['queue'][index]
            commands = rng.uniform(-1, 1, (8, 7)).astype(np.float32)
            for ids, h, persist in [([0,1,2,3],1,False), ([0,1,2,3],8,True), ([2],8,False), ([0,2],8,False)]:
                seq = sequences(q, commands[ids], h)
                _, _, scores = predict(model, x, seq, persist)
                raw, chosen = select(scores, ids)
                if h == 1 or persist or len(ids) == 1:
                    assert ids[chosen] == 2 and np.ptp(scores) < .000001
                assert ids[ids.index(2)] == 2
                invariants.append({'seed': seed, 'group': index, 'ids': ids, 'horizon': h,
                                   'persistence': persist, 'selected_shift': ids[chosen], 'spread': float(np.ptp(scores))})
    with (RUN/'evaluator_validation.json').open('x', encoding='utf-8') as f:
        json.dump({'passed': True, 'comparisons': checks, 'steps': sum(c['steps'] for c in checks), 'invariants': invariants}, f, indent=2)


if __name__ == '__main__': main()
