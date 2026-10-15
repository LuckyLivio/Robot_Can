import hashlib
import json
import platform
from pathlib import Path

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parent


def main():
    path = ROOT / 'data/can_ph_lowdim_v15.hdf5'
    with h5py.File(path, 'r') as f:
        group = f['data']
        names = sorted(group, key=lambda n: int(n.split('_')[-1]))
        demo = group[names[0]]
        print('data_attrs', dict(group.attrs), flush=True)
        print('demo', names[0], 'datasets', {k: (v.shape if hasattr(v, 'shape') else list(v)) for k,v in demo.items()}, flush=True)
        print('obs', {k: v.shape for k,v in demo['obs'].items()}, flush=True)
        info = {'python': platform.python_version(), 'numpy': np.__version__, 'h5py': h5py.__version__,
                'n_trajectories': len(names), 'n_transitions': sum(group[n]['actions'].shape[0] for n in names),
                'env_args': json.loads(group.attrs['env_args']),
                'obs_shapes': {k:list(v.shape) for k,v in demo['obs'].items()}}
        rng = np.random.default_rng(817)
        order = rng.permutation(names).tolist()
        splits = {'train':order[:140], 'dev':order[140:170], 'sealed_test':order[170:]}
        assert not set(splits['train']) & set(splits['sealed_test'])
        ROOT.joinpath('data/splits.json').write_text(json.dumps(splits,indent=2), encoding='utf-8')
        ROOT.joinpath('data/data_inspection.json').write_text(json.dumps(info,indent=2), encoding='utf-8')
        print(json.dumps(info,indent=2), flush=True)


if __name__ == '__main__':
    main()
