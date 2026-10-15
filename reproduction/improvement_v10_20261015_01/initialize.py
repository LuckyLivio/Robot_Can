"""Protect the current checkout before this isolated experiment."""
from pathlib import Path
import concurrent.futures,hashlib,json,shutil,subprocess
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    for d in ['before','analysis','protocols','recovery']:(RUN/d).mkdir(exist_ok=True)
    paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if p]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:hashes=dict(zip([p.relative_to(ROOT).as_posix() for p in paths],ex.map(sha,paths)))
    with (RUN/'before_manifest.json').open('x') as f:json.dump(hashes,f,indent=2)
    for n in ['README.md','index.html']:shutil.copy2(ROOT/n,RUN/'before'/n)
    print('protected',len(hashes))
