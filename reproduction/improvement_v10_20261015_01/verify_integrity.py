"""Read-only validation of frozen evidence and authorized entrypoint backups."""
from pathlib import Path
import concurrent.futures,hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    before=json.loads((RUN/'before_manifest.json').read_text());delivery=json.loads((RUN/'delivery_manifest.json').read_text())
    def old(item):
        rel,h=item;p=RUN/'before'/rel if rel in ['README.md','index.html'] else ROOT/rel
        assert p.is_file() and digest(p)==h,rel
    def current(item):
        rel,h=item;p=ROOT/rel;assert p.is_file() and digest(p)==h,rel
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(old,before.items()));list(pool.map(current,delivery.items()))
    print(json.dumps({'passed':True,'historical_paths':len(before),'entrypoints_preserved_as_exact_backups':['README.md','index.html'],
                      'current_delivery_files':len(delivery),'note':'No training, simulation or file rewriting.'}),flush=True)
if __name__=='__main__':main()
