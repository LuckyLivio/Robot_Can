"""Frozen-dynamics head calibration with a matched head-only continuation control.

Only labels.* parameters can change. The new arm adds label supervision on true
future states to the unchanged predicted-state label and ranking objectives.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn

from common import ROOT
from world_model import WorldModel, score, target_score, grouped_rank_loss, rank_metrics


def write_json(path, value):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_from_checkpoint(checkpoint, device):
    cfg = checkpoint['config']
    if cfg.get('method') != 'full' or not cfg.get('future_only'):
        raise ValueError('Calibration requires the existing full future_only world model')
    model = WorldModel(cfg['dim'], cfg['width'], True).to(device)
    model.load_state_dict(checkpoint['state_dict'])
    for name, parameter in model.named_parameters():
        parameter.requires_grad_(name.startswith('labels.'))
    model.eval()
    return model


@torch.no_grad()
def prepare(model, path, split, device, split_names):
    with np.load(path) as source:
        parents = sorted(set(source['parent'].tolist()))
        if not set(parents).issubset(split_names[split]):
            raise ValueError('Branch parents do not belong to the declared split')
        x = torch.from_numpy(source['x']).to(device)
        a = torch.from_numpy(source['a']).to(device)
        y = torch.from_numpy(source['y']).to(device)
        labels = torch.from_numpy(source['labels']).to(device)
    n, k, h, _ = a.shape
    predictions = []
    for begin in range(0, n, 32):
        end = min(begin+32, n)
        state = x[begin:end, None].expand(-1, k, -1).reshape((end-begin)*k, -1)
        future, _ = model(state, a[begin:end].flatten(0, 1))
        predictions.append(future.reshape(end-begin, k, h, -1))
    predicted = torch.cat(predictions)
    features = {'predicted': ((predicted-model.mean)/model.scale).detach(),
                'real': ((y-model.mean)/model.scale).detach(), 'labels': labels,
                'groups': n, 'candidates': k, 'parents': parents}
    for key in ('predicted', 'real', 'labels'):
        if not torch.isfinite(features[key]).all() or features[key].requires_grad:
            raise ValueError('Invalid or differentiable cached dynamics features')
    return features


def label_loss(logits, labels):
    return (nn.functional.binary_cross_entropy_with_logits(logits[..., 0], labels[..., 0])
            + .5*nn.functional.binary_cross_entropy_with_logits(logits[..., 1], labels[..., 1]))


@torch.no_grad()
def evaluate_head(model, features, risk_weight=.5):
    n, k = features['groups'], features['candidates']
    labels = features['labels'].flatten(0, 1)
    truth = target_score(labels, risk_weight)
    result = {}
    for mode in ('predicted', 'real'):
        logits = model.labels(features[mode].flatten(0, 1))
        probabilities = logits.sigmoid()
        scores = score(logits, risk_weight)
        result[mode] = {
            'label_loss': float(label_loss(logits, labels)),
            'score_mae': float((scores-truth).abs().mean()),
            'progress_mae': float((probabilities[..., 0]-labels[..., 0]).abs().mean()),
            'risk_brier': float((probabilities[..., 1]-labels[..., 1]).square().mean()),
            'rank': rank_metrics(scores.cpu().numpy(), truth.cpu().numpy(), n, k)}
    return result


def main(args):
    if min(args.updates, args.batch, args.eval_every) < 1 or args.real_weight <= 0 or args.lr <= 0:
        raise ValueError('Counts, learning rate and calibration weight must be positive')
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.tag) or not args.tag:
        raise ValueError('Tag must be a safe single basename')
    directory = ROOT/'reproduction'/args.tag
    models = {arm: ROOT/'models'/f'{args.tag}_{arm}_s{args.seed}' for arm in ('control', 'calibrated')}
    if (directory/'protocol.json').exists() or any(path.exists() for path in models.values()):
        raise FileExistsError('Refusing to reuse an existing calibration experiment')
    directory.mkdir(parents=True, exist_ok=True)
    checkpoint_path = ROOT/'models'/args.base_model/'model.pt'
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    cfg = checkpoint['config']
    if cfg['dataset'] != args.dataset or cfg['risk_weight'] != .5 or cfg['rank_weight'] != .2:
        raise ValueError('The source model and frozen data/loss configuration must match')
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    original = model_from_checkpoint(checkpoint, device)
    split_names = json.loads((ROOT/'data/splits.json').read_text())
    if set(split_names['train']) & set(split_names['dev']):
        raise ValueError('Train/dev split overlap')
    paths = {split: ROOT/'data'/f'branches_{split}_{args.dataset}.npz' for split in ('train', 'dev')}
    features = {split: prepare(original, path, split, device, split_names) for split, path in paths.items()}
    if set(features['train']['parents']) & set(features['dev']['parents']):
        raise ValueError('Train/dev branch parent overlap')
    n, k = features['train']['groups'], features['train']['candidates']
    generator = torch.Generator(device='cpu').manual_seed(args.seed)
    batches_cpu = torch.randint(n, (args.updates, args.batch), generator=generator)
    batch_hash = hashlib.sha256(batches_cpu.numpy().tobytes()).hexdigest()
    batches = batches_cpu.to(device)
    source_paths = [checkpoint_path, *paths.values(), ROOT/'data/splits.json',
                    ROOT/'calibrate_score_head.py', ROOT/'world_model.py', ROOT/'common.py',
                    ROOT/'evaluate_delay.py', ROOT/'train_world.py']
    hashes = {p.relative_to(ROOT).as_posix(): fingerprint(p) for p in source_paths}
    protocol = {
        'status': 'frozen_before_training', 'args': vars(args), 'device': str(device),
        'base_selected_step': checkpoint['selected_step'],
        'train_parents': features['train']['parents'], 'dev_branch_parents': features['dev']['parents'],
        'train_groups': n, 'dev_groups': features['dev']['groups'],
        'trainable_parameters': sum(p.numel() for p in original.parameters() if p.requires_grad),
        'frozen_parameters': sum(p.numel() for p in original.parameters() if not p.requires_grad),
        'trainable_names': [name for name, p in original.named_parameters() if p.requires_grad],
        'objective': 'BCE(pred_progress,target_progress) + 0.5*BCE(pred_risk,target_risk) + 0.2*predicted_group_rank_loss + real_weight*(BCE(real_state_progress,target_progress) + 0.5*BCE(real_state_risk,target_risk))',
        'arm_weights': {'control': 0., 'calibrated': args.real_weight},
        'optimizer': 'Adam, original learning rate, clip_grad_norm=10; identical initial weights and minibatch indices',
        'selection': 'Original rule: minimum dev branch mean_regret on predicted-state scores; strict improvement, earliest tie. Step0 is a reference, not an eligible newly trained checkpoint. No closed-loop success or diagnostic anchor is used to choose a checkpoint.',
        'frozen': ['state predictor', 'normalization buffers', 'BC policy', 'score formula', 'gate margin 0.02', 'candidate expansion', 'FIFO/execution', 'train/dev parent split'],
        'evaluation': 'Both selected checkpoints on all 30 original dev episodes, D2/H8/K4, shift fallback k2, score-only, noise0, 400 steps. No sealed_test.',
        'minibatch_sha256': batch_hash, 'source_sha256': hashes,
        'limitations': 'One calibration seed and one frozen pretrained dynamics model; no multi-seed performance claim.'}
    write_json(directory/'protocol.json', protocol)
    initial_metrics = {split: evaluate_head(original, value) for split, value in features.items()}
    write_json(directory/'original_offline_metrics.json', initial_metrics)
    completed = {}
    for arm, real_weight in protocol['arm_weights'].items():
        out = models[arm]
        (out/'checkpoints').mkdir(parents=True, exist_ok=False)
        model = model_from_checkpoint(checkpoint, device)
        optimizer = torch.optim.Adam(model.labels.parameters(), lr=args.lr)
        model_cfg = dict(cfg)
        model_cfg.update(run=out.name, updates=args.updates, batch=args.batch, seed=args.seed, lr=args.lr,
                         calibration={'base_model': args.base_model, 'base_sha256': fingerprint(checkpoint_path),
                                      'arm': arm, 'real_weight': real_weight, 'frozen_dynamics': True,
                                      'selection': protocol['selection'], 'minibatch_sha256': batch_hash})
        write_json(out/'config.json', model_cfg)
        best, chosen, log = float('inf'), None, []
        started = time.perf_counter()
        for step, ids in enumerate(batches, 1):
            model.labels.train()
            target = features['train']['labels'][ids].flatten(0, 1)
            logits = model.labels(features['train']['predicted'][ids].flatten(0, 1))
            original_label_loss = label_loss(logits, target)
            ranking = grouped_rank_loss(score(logits, .5), target_score(target, .5), args.batch, k)
            real_logits = model.labels(features['train']['real'][ids].flatten(0, 1))
            real_loss = label_loss(real_logits, target)
            loss = original_label_loss + .2*ranking + real_weight*real_loss
            if not torch.isfinite(loss):
                raise RuntimeError('Non-finite loss')
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            if any(p.grad is not None for name, p in model.named_parameters() if not name.startswith('labels.')):
                raise RuntimeError('Gradient reached frozen dynamics')
            nn.utils.clip_grad_norm_(model.labels.parameters(), 10)
            optimizer.step()
            if step % args.eval_every == 0 or step == args.updates:
                model.eval()
                metrics = evaluate_head(model, features['dev'])
                state = {name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()}
                changed_frozen = [name for name, value in state.items()
                                  if not name.startswith('labels.') and not torch.equal(value, checkpoint['state_dict'][name])]
                if changed_frozen:
                    raise RuntimeError(f'Frozen tensors changed: {changed_frozen}')
                entry = {'step': step, 'loss': float(loss), 'predicted_label_loss': float(original_label_loss),
                         'predicted_ranking_loss': float(ranking), 'real_label_loss': float(real_loss),
                         'dev': metrics, 'elapsed_s': time.perf_counter()-started}
                log.append(entry)
                saved = {'state_dict': state, 'config': model_cfg, 'selected_step': step,
                         'dev_metrics': metrics['predicted']['rank'], 'calibration_dev_metrics': metrics,
                         'base_selected_step': checkpoint['selected_step']}
                with (out/'checkpoints'/f'step_{step:06d}.pt').open('xb') as handle:
                    torch.save(saved, handle)
                criterion = metrics['predicted']['rank']['mean_regret']
                if criterion < best:
                    best, chosen = criterion, saved
                print(json.dumps({'arm': arm, 'step': step, 'dev_regret': criterion,
                                  'dev_pred_score_mae': metrics['predicted']['score_mae'],
                                  'dev_real_score_mae': metrics['real']['score_mae']}), flush=True)
        with (out/'model.pt').open('xb') as handle:
            torch.save(chosen, handle)
        write_json(out/'log.json', log)
        selected_model = model_from_checkpoint(chosen, device)
        metrics = {split: evaluate_head(selected_model, value) for split, value in features.items()}
        completed[arm] = {'model': out.name, 'selected_step': chosen['selected_step'],
                          'selected_model_sha256': fingerprint(out/'model.pt'), 'offline_metrics': metrics,
                          'frozen_tensors_unchanged': True, 'minibatch_sha256': batch_hash}
        write_json(out/'calibration_summary.json', completed[arm])
    write_json(directory/'training_complete.json', {'status': 'complete', 'arms': completed,
                                                    'original': initial_metrics, 'source_sha256': hashes})
    print(json.dumps({'training_complete': completed}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--base-model', default='queuepair_20261012_01_real_s17')
    parser.add_argument('--dataset', default='queuepair_20261012_01_real')
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--updates', type=int, default=3000)
    parser.add_argument('--batch', type=int, default=16)
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--real-weight', type=float, default=1.)
    parser.add_argument('--eval-every', type=int, default=250)
    main(parser.parse_args())
