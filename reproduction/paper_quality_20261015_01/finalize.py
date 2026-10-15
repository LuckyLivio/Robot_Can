"""Freeze current presentation assets without changing historical manifests."""
from pathlib import Path
import json,hashlib
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    changes=json.loads((RUN/'document_changes.json').read_text(encoding='utf8'))['updated']
    paths=[ROOT/p for p in changes]
    paths += [p for p in RUN.rglob('*') if p.is_file() and 'builds' not in p.relative_to(RUN).parts and p.name not in ['MANIFEST.json','integrity_receipt.json']]
    files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
    (RUN/'MANIFEST.json').write_text(json.dumps({'scope':'Current paper-quality deliverables and authorized active documents; historical originals preserved separately.','files':files},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'current_manifest_files':len(files),'authorized_document_changes':len(changes)}))
if __name__=='__main__':main()
