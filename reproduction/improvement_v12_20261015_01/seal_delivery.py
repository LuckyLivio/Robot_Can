"""Create the final delivery inventory once, then verify all protected bytes."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from verify_integrity import sha, verify

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]

if __name__ == '__main__':
    manifest = RUN / 'delivery_manifest.json'
    if manifest.exists():
        raise SystemExit('Delivery already sealed; use verify_integrity.py for read-only checks.')
    for name in ['artifacts', 'documents', 'browser_validation', 'visual_review']:
        assert json.loads((RUN / 'validation' / f'{name}.json').read_text())['passed'], name
    changed = json.loads((RUN / 'document_changes.json').read_text())['updated']
    excluded = {'delivery_manifest.json', 'integrity_receipt.json'}
    files = [p for p in RUN.rglob('*') if p.is_file() and p.name not in excluded
             and '__pycache__' not in p.parts and p.suffix != '.pyc']
    files += [ROOT / p for p in changed]
    files = sorted(set(files))
    with ThreadPoolExecutor(max_workers=4) as ex:
        hashes = dict(zip([p.relative_to(ROOT).as_posix() for p in files], ex.map(sha, files)))
    data = {'utc': datetime.now(timezone.utc).isoformat(), 'files': hashes,
            'scope': 'All v12 delivery files and 9 updated active documents; historical bytes protected by before_manifest.',
            'excluded_receipts': sorted(excluded)}
    manifest.write_text(json.dumps(data, indent=2), encoding='utf8')
    result = verify()
    (RUN / 'integrity_receipt.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(result))
