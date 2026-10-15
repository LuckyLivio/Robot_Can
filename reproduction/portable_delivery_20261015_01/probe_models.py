"""Target-machine inference probe; never creates a simulation environment."""
from pathlib import Path
import importlib.metadata as md
import json
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    import h5py
    import numpy as np
    import torch
    from common import OBS_KEYS, load_policy
    from world_model import WorldModel
    torch.set_num_threads(2)
    name = json.loads((ROOT / 'data/splits.json').read_text())['dev'][0]
    with h5py.File(ROOT / 'data/can_ph_lowdim_v15.hdf5', 'r') as dataset:
        x = np.concatenate([dataset['data'][name]['obs'][key][0] for key in OBS_KEYS]).astype('float32')
    if x.shape != (23,) or not np.isfinite(x).all():
        raise ValueError('Invalid saved observation')
    policy = load_policy(ROOT / 'policy/bc_chunk_dev_v4/policy_15000.pt')
    with torch.no_grad():
        action = policy.best(torch.from_numpy(x)[None])
    if action.shape != (1, 8, 7) or not torch.isfinite(action).all():
        raise ValueError('Invalid BC output')
    checked = []
    for kind in ['full', 'plain']:
        for seed in [17, 23, 41]:
            rel = f'models/multiseed_20261012_01_{kind}_s{seed}/model.pt'
            ck = torch.load(ROOT / rel, map_location='cpu', weights_only=True)
            c = ck['config']
            model = WorldModel(c['dim'], c['width'], c.get('future_only', False))
            model.load_state_dict(ck['state_dict'])
            model.eval()
            with torch.no_grad():
                states, scores = model(torch.from_numpy(x)[None], action)
            if states.shape != (1, 8, 23) or scores.shape != (1, 8, 2):
                raise ValueError('Invalid world-model shapes')
            if not torch.isfinite(states).all() or not torch.isfinite(scores).all():
                raise ValueError('Nonfinite world-model output')
            checked.append(rel)
    pip = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True)
    result = {'passed': pip.returncode == 0, 'python': sys.version, 'platform': platform.platform(),
              'packages': {k: md.version(k) for k in ['torch', 'numpy', 'h5py', 'robosuite', 'mujoco']},
              'pip_check': pip.stdout.strip(), 'bc_forwards': 1, 'wm_forwards': checked,
              'cuda_available': torch.cuda.is_available(), 'observation_demo': name,
              'simulation_episodes': 0, 'scope': 'Saved-observation CPU inference, no physical replay.'}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
