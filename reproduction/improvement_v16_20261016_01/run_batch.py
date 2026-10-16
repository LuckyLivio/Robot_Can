"""Immutable-source physical pilot/development runner. New directories only."""
from pathlib import Path
import argparse,concurrent.futures,datetime,hashlib,json,subprocess,sys,shutil
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def runtime_dependencies(jobs):
    paths=[]
    for version in range(6,16):
        for directory in (ROOT/'reproduction').glob(f'improvement_v{version}_*/recovery'):
            paths.extend(p for p in directory.iterdir() if p.suffix in ['.py','.json'])
    paths+=list((ROOT/'reproduction/recovery_v5_20261012_01').glob('*.py'))
    paths+=[ROOT/name for name in ['common.py','world_model.py','reproduction/extensions_20261012_01/evaluate.py','policy/bc_chunk_dev_v4/policy_15000.pt']]
    paths+=[ROOT/f"models/multiseed_20261012_01_full_s{seed}/model.pt" for seed in {j['seed'] for j in jobs if j['method']=='full'}]
    from common import DATA
    paths+=[ROOT/j['dataset'] if j.get('dataset') else Path(DATA) for j in jobs]
    assert all(path.is_file() for path in paths),'Missing runtime, dataset or weight dependency'
    return sorted(set(paths))
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--jobs',required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    jobs=json.loads((RUN/a.jobs).read_text(encoding='utf8'))
    if a.stage.startswith('dev'):
        lock=json.loads((RUN/'protocols/development_freeze.json').read_text(encoding='utf8'))
        assert lock['gate_passed'] and lock['episodes']==720
        for rel,digest in lock['source_sha256'].items():assert sha(ROOT/rel)==digest,('Development freeze changed',rel)
        assert jobs==json.loads((RUN/'protocols/dev_jobs.json').read_text(encoding='utf8'))
    dependencies={p.relative_to(ROOT).as_posix():sha(p) for p in runtime_dependencies(jobs)}
    out=RUN/a.stage;out.mkdir(exist_ok=False)
    with (out/'jobs.json').open('x',encoding='utf8') as f:json.dump(jobs,f,indent=2)
    source=out/'source';source.mkdir()
    source_paths=[p for p in (RUN/'recovery').iterdir() if p.suffix in ['.py','.json']]+[RUN/'evaluate_recovery.py',RUN/'variants.py',RUN/'run_batch.py']
    for f in source_paths:
        d=source/f.relative_to(RUN);d.parent.mkdir(exist_ok=True);shutil.copy2(f,d)
    hashes={f.relative_to(ROOT).as_posix():sha(f) for f in source_paths}
    with (out/'started.json').open('x',encoding='utf8') as f:json.dump({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':hashes,'dependency_sha256':dependencies,'jobs_sha256':sha(out/'jobs.json'),'episodes':sum(len(j['demos']) for j in jobs)},f,indent=2)
    def work(j):
        cmd=[sys.executable,'-X','utf8','-B','-u',str(RUN/'evaluate_recovery.py'),'--job-file',str(out/'jobs.json'),'--job-id',j['id'],'--output-dir',str(out/j['id'])]
        with (out/f"{j['id']}.log").open('x',encoding='utf8') as f:
            r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert r.returncode==0,(j['id'],'see job log')
        d=json.loads((out/j['id']/'result.json').read_text());assert d['status']=='complete'
        print(json.dumps({'job':j['id'],'success':sum(r['success'] for r in d['records']),'episodes':len(d['records'])}),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:list(ex.map(work,jobs))
    assert all(sha(ROOT/p)==s for p,s in hashes.items())
    assert all(sha(ROOT/p)==s for p,s in dependencies.items()),'Runtime dependency, dataset or weight changed during execution'
    with (out/'completed.json').open('x',encoding='utf8') as f:json.dump({'episodes':sum(len(j['demos']) for j in jobs),'source_unchanged':True},f,indent=2)
if __name__=='__main__':main()
