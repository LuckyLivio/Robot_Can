"""Standard-library verification: current repository or extracted figure package."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse, hashlib, json
RUN=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def check(base,manifest):
    def item(pair):
        rel,h=pair;p=base/rel
        if not p.is_file() or sha(p)!=h:raise ValueError('Missing or changed: '+str(p))
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(item,manifest.items()))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--package',action='store_true');args=parser.parse_args()
    if args.package or not (RUN/'before_manifest.json').exists():
        manifest=json.loads((RUN/'PACKAGE_MANIFEST.json').read_text(encoding='utf8'))['files'];check(RUN,manifest)
        print(json.dumps({'passed':True,'package_files':len(manifest),'scope':'Saved figures and plotting inputs, not simulation reproducibility.'}));return
    root=RUN.parents[1];before=json.loads((RUN/'before_manifest.json').read_text(encoding='utf8'))
    changed=json.loads((RUN/'document_changes.json').read_text(encoding='utf8'))['updated']
    check(root,{p:h for p,h in before.items() if p not in changed})
    check(RUN/'before',{p:before[p] for p in changed})
    manifest=json.loads((RUN/'MANIFEST.json').read_text(encoding='utf8'))['files'];check(root,manifest)
    print(json.dumps({'passed':True,'historical_paths':len(before),'authorized_current_documents':len(changed),'current_files':len(manifest),'old_code_weights_results_unchanged':True,'new_simulation_episodes':0}))
if __name__=='__main__':main()
