"""Losslessly restore selected existing JSONL traces; never runs experiments."""
from pathlib import Path
import argparse,csv,gzip,hashlib,json
PACK=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prefix',required=True,help='Original repo path prefix; e.g. reproduction/recovery_v5_20261012_01/confirmation/')
    p.add_argument('--destination',type=Path,default=PACK/'04_snapshot')
    a=p.parse_args(); prefix=a.prefix.replace('\\','/')
    with (PACK/'07_provenance/SOURCE_ASSETS.csv').open(encoding='utf-8-sig') as f:
        rows=[r for r in csv.DictReader(f) if r['storage']=='gzip' and r['source_repo_path'].startswith(prefix)]
    if not rows:raise SystemExit('No matching compressed trace')
    target=a.destination.resolve();done=0
    for r in rows:
        out=(target/r['source_repo_path']).resolve()
        assert out.is_relative_to(target)
        if out.exists():
            h=hashlib.sha256(out.read_bytes()).hexdigest()
            if h!=r['original_sha256']:raise FileExistsError(out)
            continue
        src=PACK/r['package_path'];out.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256()
        with gzip.open(src,'rb') as source,out.open('xb') as dest:
            for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk);dest.write(chunk)
        assert h.hexdigest()==r['original_sha256'],out
        done+=1
    print(json.dumps({'restored_existing_traces':done,'matched':len(rows),'new_simulation_episodes':0}))
if __name__=='__main__':main()
