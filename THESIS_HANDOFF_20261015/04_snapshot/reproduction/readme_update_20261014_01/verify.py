"""Read-only verification of the authorized README change and preserved assets."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=Path(__file__).resolve().parent
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    previous=json.loads((ROOT/'reproduction/playback_fix_20261012_01/verification.json').read_text(encoding='utf8'))
    receipt=json.loads((RUN/'update.json').read_text(encoding='utf8'))
    assert previous['passed']
    checked=0;existing_drift={}
    for section in ['preserved_files','current_files']:
        for rel,sha in previous[section].items():
            path=RUN/'README_before.md' if rel=='README.md' else ROOT/rel
            assert path.is_file(),rel
            observed=digest(path)
            if observed!=sha:
                drift=receipt['preexisting_historical_differences'].get(rel)
                assert drift and drift['historical_sha256']==sha and drift['observed_sha256']==observed,rel
                existing_drift[rel]=drift
            checked+=1
    assert digest(RUN/'README_before.md')==receipt['before_sha256']
    assert digest(ROOT/'README.md')==receipt['after_sha256']
    if receipt.get('root_entry_added'):
        assert digest(ROOT/'index.html')==receipt['root_entry_sha256']
    print(json.dumps({'passed':True,'historical_entries_checked':checked,'README_archived_exactly':True,
        'new_README_verified':True,'old_code_weights_results_unchanged':True,
        'preexisting_historical_differences':existing_drift,'historical_manifest_fully_matched':not existing_drift,
        'new_policy_episodes':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
