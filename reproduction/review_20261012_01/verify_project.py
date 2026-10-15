"""Read-only current review and historical experiment integrity verifier."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    path=RUN/'review_validation.json'
    if not path.exists():raise RuntimeError('Review not finalized yet.')
    manifest=json.loads(path.read_text(encoding='utf-8'));assert manifest['passed']
    for rel,sha in manifest['preserved_files'].items():
        assert (ROOT/rel).is_file() and digest(ROOT/rel)==sha,f'Historical file missing/changed: {rel}'
    for rel,sha in manifest['current_files'].items():
        assert (ROOT/rel).is_file() and digest(ROOT/rel)==sha,f'Current artifact missing/changed: {rel}'
    print(json.dumps({'passed':True,'preserved_historical_files':len(manifest['preserved_files']),
        'verified_current_files':len(manifest['current_files']),'changed_existing_files':manifest['changed_existing_files'],
        'deleted_existing_files':manifest['deleted_existing_files'],'old_weights_results_code_and_demo_unchanged':True},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
