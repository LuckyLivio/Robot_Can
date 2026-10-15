"""Read-only audit: current figures, provenance, byte-identical archives and old assets."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent


def load(p):
    return json.loads(p.read_text(encoding='utf8'))


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    old = load(ROOT/'reproduction/playback_fix_20261012_01/verification.json')
    receipt = load(ROOT/'reproduction/readme_update_20261014_01/update.json')
    before = load(RUN/'before_manifest.json')
    current = load(RUN/'current_manifest.json')
    assert old['passed']
    for rel, sha in before.items():
        assert digest(RUN/'before'/rel) == sha, f'Archive: {rel}'
    assert before['README.md'] == receipt['after_sha256']
    drift, checked = {}, 0
    for section in ('preserved_files', 'current_files'):
        for rel, sha in old[section].items():
            if rel == 'README.md':
                path = ROOT/'reproduction/readme_update_20261014_01/README_before.md'
            else:
                path = RUN/'before'/rel if rel in before else ROOT/rel
            actual = digest(path)
            if actual != sha:
                known = receipt['preexisting_historical_differences'].get(rel)
                assert known and known['historical_sha256']==sha and known['observed_sha256']==actual, rel
                drift[rel] = known
            checked += 1
    assert digest(ROOT/'index.html') == receipt['root_entry_sha256']
    for rel, sha in current.items():
        assert digest(ROOT/rel) == sha, f'Current: {rel}'
    data = load(ROOT/'figures/figure_data.json')
    for rel, sha in data['sources_sha256'].items():
        assert digest(ROOT/rel) == sha, f'Figure source: {rel}'
    spec = importlib.util.spec_from_file_location('audited_plot', ROOT/'make_figures.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    conf, dev = mod.records(mod.CONF, 60), mod.records(mod.DEV, 30)
    mod.check_summary(conf, mod.CONF); mod.check_summary(dev, mod.DEV)
    for name, groups in [('figure_success_rate', conf), ('figure_ablation', dev)]:
        for row in data['figures'][name]:
            actual = mod.success_rates(groups, row['method'], row['condition'])
            assert actual == row['seed_rates_percent']
            assert abs(sum(actual)/len(actual)-row['mean_percent']) < 1e-10
    for suffix, condition in [('clean','clean'), ('noise005','noise005')]:
        for row in data['figures']['figure_paired_'+suffix]:
            bc, full = conf['bc_k2',None,condition], conf['full',row['seed'],condition]
            pairs = [(bc[k]['success'],full[k]['success']) for k in bc]
            assert row['counts'] == [pairs.count(p) for p in [(True,True),(False,True),(True,False),(False,False)]]
    for row in data['figures']['figure_success_steps']:
        b = conf['bc_k2',None,row['condition']][row['demo']]
        f = conf['full',row['seed'],row['condition']][row['demo']]
        assert b['success'] and f['success']
        assert (b['steps'], f['steps'], f['steps']-b['steps']) == (row['bc_steps'],row['full_steps'],row['difference'])
    for row in data['figures']['figure_training_curves']:
        folder = ROOT/f"models/multiseed_20261012_01_full_s{row['seed']}"
        raw = load(folder/'log.json')
        assert len(raw) == len(row['records'])
        for point, record in zip(row['records'],raw):
            assert all(record[k] == v for k,v in point.items())
        assert row['selected_step'] == load(folder/'training_complete.json')['selected_step']
    total = sum(map(len,conf.values())) + sum(map(len,dev.values()))
    assert total == data['validation']['raw_episodes_checked']
    print(json.dumps({'passed': True, 'historical_entries_checked': checked,
        'archived_files':len(before), 'current_files':len(current),
        'raw_episodes_checked':total, 'plotted_values_match_raw':True,
        'source_files_sha256_verified':len(data['sources_sha256']),
        'old_training_control_code_weights_results_unchanged':True,
        'preexisting_historical_differences':drift,
        'historical_manifest_fully_matched':not drift, 'new_simulation_episodes':0}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
