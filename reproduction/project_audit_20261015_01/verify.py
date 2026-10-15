"""Read-only verification of old assets/authorized document backups and current delivery."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    before=json.loads((RUN/'before_manifest.json').read_text());current=json.loads((RUN/'delivery_manifest.json').read_text());changes=json.loads((RUN/'document_changes.json').read_text())['updated_or_added']
    def old(item):
        rel,h=item;p=RUN/'before'/rel if rel in changes else ROOT/rel
        assert p.is_file() and digest(p)==h,rel
    def now(item):
        rel,h=item;p=ROOT/rel;assert p.is_file() and digest(p)==h,rel
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(old,before.items()));list(pool.map(now,current.items()))
    print(json.dumps({'passed':True,'historical_files':len(before),'authorized_existing_documents':sum(p in before for p in changes),'current_delivery_files':len(current),'old_code_weights_results_unchanged':True,'scope':'Read-only hashes, no training/simulation or result rewriting.'}),flush=True)
if __name__=='__main__':main()
