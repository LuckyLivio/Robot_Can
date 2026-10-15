"""Frozen-weight supplemental development evaluations; exclusive output files."""
import argparse, hashlib, json, sys, time
from collections import deque
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import h5py, numpy as np, torch
from common import DATA, make_env, pack_obs, restore_demo, load_policy
from world_model import WorldModel, score, target_score
from collect_rollout_branches import signature
from snapshot import true_branches


def load_model(seed):
    path = ROOT/f'models/multiseed_20261012_01_full_s{seed}/model.pt'
    ck = torch.load(path, map_location='cpu', weights_only=True)
    cfg = ck['config']
    model = WorldModel(cfg['dim'], cfg['width'], cfg['future_only'])
    model.load_state_dict(ck['state_dict'])
    return model.eval()


def sequences(queue, commands, horizon):
    prefix = np.asarray(queue, np.float32).reshape(-1, 7)
    return np.asarray([np.concatenate([prefix, np.repeat(a[None], horizon, 0)])[:horizon]
                       for a in commands], np.float32)


def select(scores, ids):
    fallback = ids.index(2)
    raw = int(np.argmax(scores))
    chosen = fallback if raw != fallback and float(scores[raw] - scores[fallback]) < .02 else raw
    return raw, chosen


@torch.no_grad()
def predict(model, state, seqs, persistence=False):
    xb = torch.from_numpy(np.repeat(state[None], len(seqs), 0))
    if persistence:
        future = xb[:, None].repeat(1, seqs.shape[1], 1)
        labels = model.labels((future - model.mean) / model.scale)
    else:
        future, labels = model(xb, torch.from_numpy(seqs))
    return future.numpy(), labels.sigmoid().numpy(), score(labels, .5).numpy()


def run(job, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    assert not (output/'result.json').exists(), output
    assert not (output/'decisions.jsonl').exists(), output
    torch.set_num_threads(2)
    ids, horizon, method = job['candidate_ids'], job['horizon'], job['method']
    assert 2 in ids and len(ids) == len(set(ids)) and all(0 <= i < 8 for i in ids)
    policy = load_policy(ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt')
    model = load_model(job.get('seed') or 17) if method != 'oracle' else None
    env = make_env(False)
    records = []
    payload = {'status': 'running', 'job': job, 'input': 'PRIVILEGED_STATE_DIAGNOSTIC',
               'records': records, 'split': 'dev', 'resolved_demos': job['demos']}
    with (output/'result.json').open('x', encoding='utf-8') as result, \
         (output/'decisions.jsonl').open('x', encoding='utf-8') as traces, h5py.File(DATA) as data:
        def save(status):
            payload['status'] = status
            result.seek(0)
            json.dump(payload, result, indent=2, allow_nan=False)
            result.truncate(); result.flush()
        save('running')
        try:
            for name in job['demos']:
                obs = restore_demo(env, data['data'][name])
                if hasattr(policy, 'reset'): policy.reset()
                queue = deque([np.zeros(7, np.float32) for _ in range(2)], maxlen=3)
                rng = np.random.default_rng(70000 + int(name.split('_')[1]))
                selected_ids, timing, spreads = [], [], []
                peak, grasped, success = 0., False, False
                started = time.perf_counter()
                for step in range(job.get('steps', 400)):
                    x = pack_obs(obs)
                    base = policy.best(torch.from_numpy(x[None]))[0].numpy()
                    commands = base[ids].copy()
                    seqs = sequences(list(queue), commands, horizon)
                    tic = time.perf_counter()
                    if method == 'oracle':
                        before = signature(env)
                        future, probabilities = true_branches(env, list(queue), commands, horizon)
                        assert np.array_equal(signature(env), before), 'Branch changed live state'
                        scores = target_score(torch.from_numpy(probabilities), .5).numpy()
                    else:
                        future, probabilities, scores = predict(model, x, seqs, method == 'persistence')
                    assert np.isfinite(future).all() and np.isfinite(scores).all()
                    raw, selected = select(scores, ids)
                    elapsed = time.perf_counter() - tic
                    submitted = commands[selected].copy()
                    trace = {'demo': name, 'step': step+1, 'candidate_ids': ids,
                             'scores': scores.tolist(), 'raw_shift': ids[raw], 'selected_shift': ids[selected],
                             'fallback_shift': 2, 'overrode_fallback': ids[selected] != 2,
                             'gate_blocked': raw != selected, 'score_spread': float(np.ptp(scores)),
                             'raw_advantage': float(scores[raw] - scores[ids.index(2)]),
                             'submitted_action': submitted.tolist(), 'decision_ms': elapsed*1000}
                    # Full traces only for validation; population runs retain compact decisions.
                    if job.get('full_trace'):
                        trace.update(state_before=x.tolist(), base_chunk=base.tolist(),
                                     queue_before=np.asarray(queue).tolist(), model_sequences=seqs.tolist(),
                                     predicted_states=future.tolist(), predicted_probabilities=probabilities.tolist())
                    selected_ids.append(ids[selected]); timing.append(elapsed); spreads.append(float(np.ptp(scores)))
                    queue.append(submitted)
                    executed = queue.popleft()
                    trace['executed_action_before_noise'] = executed.copy().tolist()
                    if job['noise']:
                        executed[:3] += rng.normal(0, job['noise'], 3)
                    applied = np.clip(executed, -1, 1)
                    obs, *_ = env.step(applied)
                    stages = env.staged_rewards()
                    peak = max(peak, float(max(stages)))
                    grasped = bool(grasped or stages[1] > .3)
                    success = bool(env._check_success())
                    trace.update(executed_action=applied.tolist(), success_after=success,
                                 stages_after=np.asarray(stages).tolist())
                    if job.get('full_trace'): trace['state_after'] = pack_obs(obs).tolist()
                    if method == 'oracle':
                        trace['true_progress'] = probabilities[:, :, 0].tolist()
                        trace['true_grasp_loss'] = probabilities[:, :, 1].tolist()
                    traces.write(json.dumps(trace, allow_nan=False)+'\n')
                    if success: break
                row = {'demo': name, 'success': success, 'steps': step+1, 'peak_stage_reward': peak,
                       'ever_grasped': grasped, 'delay': 2, 'fraction_override': 1-float(np.mean(np.array(selected_ids) == 2)),
                       'selection_counts': {str(k): selected_ids.count(k) for k in sorted(set(selected_ids))},
                       'max_score_spread': max(spreads), 'mean_decision_ms': float(np.mean(timing)*1000),
                       'elapsed_s': time.perf_counter()-started}
                records.append(row); traces.flush(); save('running')
                print(json.dumps(row), flush=True)
            save('complete')
        finally:
            env.close()
    return output/'result.json'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', required=True)
    args = parser.parse_args()
    jobs = json.loads((RUN/'jobs.json').read_text(encoding='utf-8'))
    job = next(j for j in jobs if j['id'] == args.job)
    run(job, RUN/'evaluations'/job['id'])
