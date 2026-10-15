"""Immutable-source physical pilot/development runner. New directories only."""
from pathlib import Path
import argparse,concurrent.futures,datetime,hashlib,json,subprocess,sys,shutil
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--jobs',required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    out=RUN/a.stage;out.mkdir(exist_ok=False);jobs=json.loads((RUN/a.jobs).read_text(encoding='utf8'))
    (out/'jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf8')
    source=out/'source';source.mkdir()
    source_paths=[p for p in (RUN/'recovery').iterdir() if p.suffix in ['.py','.json']]+[RUN/'evaluate_recovery.py',RUN/'variants.py',RUN/'run_batch.py']
    for f in source_paths:
        d=source/f.relative_to(RUN);d.parent.mkdir(exist_ok=True);shutil.copy2(f,d)
    hashes={f.relative_to(ROOT).as_posix():sha(f) for f in source_paths}
    (out/'started.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':hashes,'episodes':sum(len(j['demos']) for j in jobs)},indent=2),encoding='utf8')
    def work(j):
        cmd=[sys.executable,'-X','utf8','-B','-u',str(RUN/'evaluate_recovery.py'),'--job-file',str(out/'jobs.json'),'--job-id',j['id'],'--output-dir',str(out/j['id'])]
        with (out/f"{j['id']}.log").open('x',encoding='utf8') as f:
            r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert r.returncode==0,(j['id'],'see job log')
        d=json.loads((out/j['id']/'result.json').read_text());assert d['status']=='complete'
        print(json.dumps({'job':j['id'],'success':sum(r['success'] for r in d['records']),'episodes':len(d['records'])}),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:list(ex.map(work,jobs))
    assert all(sha(ROOT/p)==s for p,s in hashes.items())
    (out/'completed.json').write_text(json.dumps({'episodes':sum(len(j['demos']) for j in jobs),'source_unchanged':True},indent=2),encoding='utf8')
if __name__=='__main__':main()
