"""Immutable-source gated physical runner; every output stage is newly created."""
from pathlib import Path
import argparse,concurrent.futures,datetime,hashlib,json,subprocess,sys,shutil
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))
def runtime_dependencies(jobs):
    paths=[]
    for version in range(6,17):
        for directory in (ROOT/'reproduction').glob(f'improvement_v{version}_*/recovery'):
            paths.extend(path for path in directory.iterdir() if path.suffix in ['.py','.json'])
    paths+=list((ROOT/'reproduction/recovery_v5_20261012_01').glob('*.py'))
    paths+=[ROOT/name for name in ['common.py','world_model.py','reproduction/extensions_20261012_01/evaluate.py','policy/bc_chunk_dev_v4/policy_15000.pt']]
    paths+=[ROOT/f"models/multiseed_20261012_01_full_s{seed}/model.pt" for seed in {job['seed'] for job in jobs if job['method']=='full'}]
    from common import DATA
    paths+=[ROOT/job['dataset'] if job.get('dataset') else Path(DATA) for job in jobs]
    assert all(path.is_file() for path in paths),'Missing runtime, dataset or weight dependency'
    return sorted(set(paths))
def checked_receipt_sources(receipt):
    if receipt.get('source_sha256'):return receipt['source_sha256']
    # The independent carry-search checker records its helper/script and each
    # saved input separately. Normalize that explicit schema without rewriting
    # its original receipt or accepting an unbound generic passed flag.
    assert all(key in receipt for key in ['script_sha256','helper_sha256','prior_input_receipt_sha256','sources'])
    old=ROOT/'reproduction/improvement_v16_20261016_01'
    hashes={
        (RUN/'inspect_carry_search.py').relative_to(ROOT).as_posix():receipt['script_sha256'],
        (RUN/'recovery/carry_search.py').relative_to(ROOT).as_posix():receipt['helper_sha256'],
        (old/'analysis/ik_continuation_a.json').relative_to(ROOT).as_posix():receipt['prior_input_receipt_sha256'],
    }
    assert receipt['sources']
    for source in receipt['sources']:
        assert source['submitted_actions_exact']
        for filename,key in [('result.json','result_sha256'),('trace.jsonl','trace_sha256')]:
            hashes[(old/'smoke_a'/source['job']/filename).relative_to(ROOT).as_posix()]=source[key]
    return hashes
def verify_mechanism_receipt(name):
    path=RUN/'analysis'/f'{name}.json';receipt=read(path)
    assert receipt['passed'],('Missing or failed mechanism check',name)
    hashes=checked_receipt_sources(receipt)
    assert hashes
    for rel,digest in hashes.items():assert sha(ROOT/rel)==digest,('Stale mechanism check',name,rel)
    return path
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',required=True);parser.add_argument('--jobs',required=True)
    parser.add_argument('--workers',type=int,default=4);parser.add_argument('--smoke',default='smoke_a')
    parser.add_argument('--mechanisms',default='mechanisms_c');parser.add_argument('--components',default='components_c')
    parser.add_argument('--route-static',default='carry_search_static_b');parser.add_argument('--pose-static',default='pose_servo_static_b');args=parser.parse_args()
    assert args.workers>0
    requested=RUN/args.jobs;jobs=read(requested)
    preflight=[verify_mechanism_receipt(name) for name in [args.mechanisms,args.components,args.route_static,args.pose_static]]
    receipt_dependencies={ROOT/rel for path in preflight for rel in checked_receipt_sources(read(path))}
    if args.stage.startswith('smoke'):
        assert jobs==read(RUN/'protocols/smoke_jobs.json') and sum(len(job['demos']) for job in jobs)==63
    elif args.stage.startswith('pilot'):
        from freeze_development import verify_stage
        preflight+=verify_stage(args.smoke,63)
        assert jobs==read(RUN/'protocols/pilot_jobs.json') and sum(len(job['demos']) for job in jobs)==658
    elif args.stage.startswith('dev'):
        lock=read(RUN/'protocols/development_freeze.json')
        assert lock['gate_passed'] and lock['episodes']==720 and lock['versions']==['v15','v16','v17']
        for rel,digest in lock['source_sha256'].items():assert sha(ROOT/rel)==digest,('Development freeze changed',rel)
        assert jobs==read(RUN/'protocols/dev_jobs.json')
        preflight.append(RUN/'protocols/development_freeze.json')
    else:raise ValueError('Only registered smoke, pilot or development stages can run here')
    dependencies={path.relative_to(ROOT).as_posix():sha(path) for path in sorted(set(runtime_dependencies(jobs))|receipt_dependencies)}
    # Include every new helper and the exact locked protocol/evidence used to
    # authorize this stage. All parent v16/v15 files are dependencies above.
    source_paths=[path for path in (RUN/'recovery').iterdir() if path.suffix in ['.py','.json']]
    source_paths += [RUN/name for name in ['evaluate_recovery.py','variants.py','run_batch.py','protocols/PLAN.md']]
    source_paths += [requested]+preflight;source_paths=sorted(set(source_paths))
    assert all(path.is_file() for path in source_paths)
    hashes={path.relative_to(ROOT).as_posix():sha(path) for path in source_paths}
    out=RUN/args.stage;out.mkdir(exist_ok=False)
    with (out/'jobs.json').open('x',encoding='utf8') as stream:json.dump(jobs,stream,indent=2)
    source=out/'source';source.mkdir()
    for path in source_paths:
        destination=source/path.relative_to(RUN);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
    with (out/'started.json').open('x',encoding='utf8') as stream:
        json.dump({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':hashes,
                   'dependency_sha256':dependencies,'jobs_sha256':sha(out/'jobs.json'),
                   'gate_receipts':[path.relative_to(ROOT).as_posix() for path in preflight],
                   'episodes':sum(len(job['demos']) for job in jobs)},stream,indent=2)
    def work(job):
        command=[sys.executable,'-X','utf8','-B','-u',str(RUN/'evaluate_recovery.py'),'--job-file',str(out/'jobs.json'),'--job-id',job['id'],'--output-dir',str(out/job['id'])]
        with (out/f"{job['id']}.log").open('x',encoding='utf8') as stream:
            result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert result.returncode==0,(job['id'],'see job log')
        result=read(out/job['id']/'result.json');assert result['status']=='complete'
        print(json.dumps({'job':job['id'],'success':sum(row['success'] for row in result['records']),'episodes':len(result['records'])}),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:list(executor.map(work,jobs))
    assert all(sha(ROOT/path)==digest for path,digest in hashes.items()),'New runtime/protocol/evidence changed during execution'
    assert all(sha(ROOT/path)==digest for path,digest in dependencies.items()),'Runtime dependency, dataset or weight changed during execution'
    with (out/'completed.json').open('x',encoding='utf8') as stream:json.dump({'episodes':sum(len(job['demos']) for job in jobs),'source_unchanged':True},stream,indent=2)
if __name__=='__main__':main()
