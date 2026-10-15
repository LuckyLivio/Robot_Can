"""Freeze the delivery source, preserved files, and portable rerun inputs once."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import shutil
import subprocess
from portable import digest

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
DOCS = ['README.md', 'STATUS.md', 'THESIS_HANDOFF_LATEST.md', 'PROGRAM_GUIDE.md', 'WORKSPACE/index.html']


def main():
    if (RUN / 'baseline.json').exists():
        raise FileExistsError('Source already frozen')
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = [p for p in paths if p]
    with ThreadPoolExecutor(max_workers=4) as pool:
        hashes = dict(zip(paths, pool.map(lambda p: digest(ROOT / p), paths)))
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    for rel in DOCS:
        destination = RUN / 'before' / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, destination)
    (RUN / 'baseline.json').write_text(json.dumps({'source_commit': commit, 'files': hashes,
        'authorized_documents': DOCS}, ensure_ascii=False, indent=2), encoding='utf8')
    # Broad code coverage includes the cross-version recovery inheritance chain.
    chosen = {p for p in paths if p.endswith('.py') and not p.startswith('THESIS_HANDOFF_')}
    chosen |= {p for p in paths if '/recovery/' in p and p.endswith('.json')}
    chosen |= {'data/can_ph_lowdim_v15.hdf5', 'data/splits.json', 'policy/bc_chunk_dev_v4/policy_15000.pt'}
    chosen |= {f'models/multiseed_20261012_01_{kind}_s{seed}/model.pt'
               for kind in ['full', 'plain'] for seed in [17, 23, 41]}
    for folder, stage in [('improvement_v11_20261015_01', 'dev_a'),
                          ('recovery_v5_20261012_01', 'confirmation'),
                          ('recovery_v5_20261012_01', 'geometry_confirmation')]:
        rel = f'reproduction/{folder}/{stage}/jobs.json'
        chosen.add(rel)
        for job in json.loads((ROOT / rel).read_text()):
            if job.get('dataset'):
                chosen.add(job['dataset'])
    rows = [{'path': p, 'bytes': (ROOT / p).stat().st_size, 'sha256': hashes[p]} for p in sorted(chosen)]
    (RUN / 'REPRODUCTION_MANIFEST.json').write_text(json.dumps({'profile': 'repository-rerun-inputs',
        'source_commit': commit, 'files': rows, 'requires': 'Full source repository plus a compatible fresh environment',
        'not_included': ['virtual environment', 'new physical replay or new experiment'],
        'scope': 'Frozen v5 native/geometry and v11 development repeat-input checks; not every historical experiment.'}, indent=2), encoding='utf8')
    print(json.dumps({'source_commit': commit, 'baseline_files': len(paths), 'rerun_inputs': len(rows)}))


if __name__ == '__main__':
    main()
