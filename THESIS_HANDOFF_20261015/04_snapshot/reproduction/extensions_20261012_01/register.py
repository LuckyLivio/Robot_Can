"""Register supplemental experiments before their population outcomes exist."""
import datetime, hashlib, json, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def write(name, obj):
    with (RUN/name).open('x', encoding='utf-8') as f: json.dump(obj, f, indent=2, ensure_ascii=False, allow_nan=False)


def main():
    assert not (RUN/'evaluations').exists()
    for name in ['snapshot_validation.json', 'evaluator_validation.json']:
        assert json.loads((RUN/name).read_text())['passed'], name
    preserved = {}
    for directory, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in {'.venv', '.git', '.idea', '__pycache__'} and Path(directory)/d != RUN]
        for filename in files:
            path = Path(directory)/filename
            preserved[path.relative_to(ROOT).as_posix()] = digest(path)
    write('before_manifest.json', preserved)
    names = json.loads((ROOT/'data/splits.json').read_text())['dev']
    jobs = []
    for label, horizon, ids in [('h1',1,[0,1,2,3]), ('h3',3,[0,1,2,3]),
                                ('k2',8,[0,2]), ('k8',8,list(range(8)))]:
        for seed in [17,23,41]:
            for condition, noise in [('clean',0.), ('noise',.05)]:
                jobs.append({'id': f'{label}_s{seed}_{condition}', 'variant': label, 'method': 'full',
                             'seed': seed, 'noise': noise, 'condition': condition, 'horizon': horizon,
                             'candidate_ids': ids, 'demos': names})
    for variant, method, ids in [('persistence','persistence',[0,1,2,3]), ('k1','full',[2])]:
        for condition, noise in [('clean',0.), ('noise',.05)]:
            jobs.append({'id': f'{variant}_{condition}', 'variant': variant, 'method': method,
                         'seed': None, 'readout_seed': 17, 'noise': noise, 'condition': condition,
                         'horizon': 8, 'candidate_ids': ids, 'demos': names})
    oracle = []
    for name in names:
        for condition, noise in [('clean',0.), ('noise',.05)]:
            oracle.append({'id': f'oracle_{condition}_{name}', 'variant': 'oracle', 'method': 'oracle',
                           'seed': None, 'noise': noise, 'condition': condition, 'horizon': 8,
                           'candidate_ids': [0,1,2,3], 'demos': [name]})
    # Interleave heavier oracle rollouts with ordinary evaluations.
    scheduled = []
    for i in range(max(len(jobs), len(oracle))):
        if i < len(oracle): scheduled.append(oracle[i])
        if i < len(jobs): scheduled.append(jobs[i])
    write('jobs.json', scheduled)
    oldjobs = json.loads((ROOT/'reproduction/multiseed_20261012_01/jobs.json').read_text())
    references = [j for j in oldjobs if j.get('phase') == 'evaluate' and j['method'] in ['full','plain','horizon4','bc_k2']]
    write('reference_jobs.json', references)
    protocol = {
        'registered_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'frozen_before_supplemental_population_runs', 'split': 'development_only',
        'demos': names, 'training': 'None; preserve all existing checkpoints and results',
        'seeds': [17,23,41], 'delay_steps': 2, 'step_limit': 400, 'control_hz': 20,
        'noises': [0.,.05], 'execution_noise': 'XYZ Gaussian; RNG70000+demo_id; clip[-1,1]; identical existing evaluator',
        'candidate_semantics': 'Constant submitted command BC chunk[k], appended behind real FIFO; commit one step and replan',
        'score': 'progress_final + 0.5 mean_progress - 0.5 max_grasp_loss',
        'gate': 'Fallback actual BC shift k=2 in EVERY set; require score advantage >=0.02',
        'horizons': {'new':[1,3], 'reused':[4,8], 'definition':'Total executed steps INCLUDING D=2 pending commands. H=1 sees no new candidate effect; H=3 sees exactly its first step.'},
        'candidate_counts': {'1':[2], '2':[0,2], '4':[0,1,2,3], '8':list(range(8)),
                             'caution':'K=8 adds shift values outside the K=4 branch-training distribution; this is a nested support/budget sensitivity, not a distribution-neutral compute scaling law'},
        'persistence': 'No learned dynamics: x_future=x_current for all H steps and candidates. Same frozen Full future-only readout s17 and same gate. Scores tie, so action sequence must equal BC k=2. Dynamics is parameter-free; do not count copied seed outcomes as extra evidence. Check head invariance across all 3 seeds offline.',
        'k1': 'Only candidate is k=2: no search; one run per condition because trained seed cannot affect action choice',
        'oracle': 'Closed-loop true future labels from exact simulator counterfactuals at EVERY decision. H=8, K=4, same score/gate. Branches have no execution noise, even when live execution has noise .05; no privileged future-noise knowledge. One policy, no training seed replication. Diagnostic local oracle, not deployable and not guaranteed global-success upper bound.',
        'oracle_recovery': 'Full native MjData copy plus controller/gripper/observable/buffer Python fields; validated against complete history replay and reverse branch order',
        'population_jobs': len(scheduled), 'new_closed_loop_episodes': sum(len(j['demos']) for j in scheduled),
        'reused_baselines': 'Existing exact-setting Full H8/K4, H4, Plain and BCk2; reference_jobs.json records immutable sources. Do not double count these as new runs.',
        'offline': 'Existing 64 dev branch groups/8 parents: Full/Plain dynamics versus state persistence, normalized state MSE and physical position error; same frozen head on predicted/true/persistent states, local ranking regret and gate agreement. No fitting or selection.',
        'statistics': '20,000 paired bootstrap resamples of 30 start IDs and 3 trained seed IDs when applicable; deterministic policies broadcast for pairing but not treated as independently trained models. RNG2026101204. Exploratory intervals, no multiplicity-adjusted claim.',
        'success_definition': 'Unchanged env._check_success, stop on first success or 400 controls',
        'confirmation': 'Previous 60-start confirmation remains frozen and is NOT reused for new tuning/testing.',
        'reporting': 'Report every registered variant and failure; no winner selection on confirmation; no manuscript writing.'
    }
    write('protocol.json', protocol)
    sources = [*RUN.glob('*.py'), RUN/'jobs.json', RUN/'reference_jobs.json', RUN/'protocol.json',
               RUN/'snapshot_validation.json',RUN/'evaluator_validation.json',
               ROOT/'common.py',ROOT/'world_model.py',ROOT/'collect_branches.py',ROOT/'collect_rollout_branches.py',
               ROOT/'data/splits.json',ROOT/'data/can_ph_lowdim_v15.hdf5',
               ROOT/'data/branches_dev_queuepair_20261012_01_real.npz',
               ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt']
    sources += [ROOT/f'models/multiseed_20261012_01_{method}_s{seed}/model.pt' for method in ['full','plain'] for seed in [17,23,41]]
    write('frozen_inputs.json', {p.relative_to(ROOT).as_posix():digest(p) for p in sources})
    print(json.dumps({'registered_jobs':len(scheduled),'new_episodes':protocol['new_closed_loop_episodes'],'preserved_files':len(preserved)}))


if __name__ == '__main__': main()
