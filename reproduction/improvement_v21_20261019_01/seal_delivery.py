"""Seal final delivery once; no overwriting experiment or prior artifacts."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
from verify_integrity import sha,verify,check
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
if __name__=='__main__':
    manifest=RUN/'delivery_manifest.json'
    assert not manifest.exists(),'Already sealed; use verify_integrity.py.'
    for name in ['artifacts_final','documents_final','browser_validation','visual_review','independent_review','content_review']:
        receipt=json.loads((RUN/'validation'/f'{name}.json').read_text())
        assert receipt['passed'],name
        check(ROOT,receipt.get('source_sha256',{}))
    changed=json.loads((RUN/'document_changes.json').read_text())['updated']
    excluded={'delivery_manifest.json','integrity_receipt.json'}
    files=[p for p in RUN.rglob('*') if p.is_file() and p.name not in excluded and '__pycache__' not in p.parts and p.suffix!='.pyc']
    files+= [ROOT/p for p in changed];files=sorted(set(files))
    with ThreadPoolExecutor(max_workers=4) as ex:
        hashes=dict(zip([p.relative_to(ROOT).as_posix() for p in files],ex.map(sha,files)))
    data={'utc':datetime.now(timezone.utc).isoformat(),'files':hashes,
          'scope':'All v21 delivery files and 9 backed-up active documents; historical bytes protected by before_manifest.',
          'excluded_receipts':sorted(excluded)}
    manifest.write_text(json.dumps(data,indent=2),encoding='utf8')
    result=verify();(RUN/'integrity_receipt.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))

