"""Record all prior tracked files before v17; preserve the nine active entry docs."""
from pathlib import Path
import concurrent.futures,datetime,hashlib,json,shutil,subprocess
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
DOCS=['README.md','index.html','STATUS.md','DEMO_GUIDE.md','RESULTS.md','EVIDENCE_INDEX.md','PROJECT_NAVIGATION.md','THESIS_HANDOFF_LATEST.md','PROGRAM_GUIDE.md']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    for d in ['before','analysis','protocols','recovery','validation']:(RUN/d).mkdir(exist_ok=True)
    paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if p]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:hashes=dict(zip([p.relative_to(ROOT).as_posix() for p in paths],ex.map(sha,paths)))
    with (RUN/'before_manifest.json').open('x') as f:json.dump(hashes,f,indent=2)
    for n in DOCS:shutil.copy2(ROOT/n,RUN/'before'/n)
    with (RUN/'protocols/before.json').open('x') as f:json.dump({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'protected_files':len(hashes),'mutable_entry_docs':DOCS},f,indent=2)
    print('protected',len(hashes))
