"""Run only registered supplemental jobs, with receipts and safe resume."""
import argparse, concurrent.futures, datetime, json, os, subprocess, sys, time
from pathlib import Path
from register import ROOT, RUN, digest, write


def execute(job):
    receipt = RUN/'completed'/f"{job['id']}.json"
    if receipt.exists():
        done = json.loads(receipt.read_text())
        assert done['status']=='complete' and done['job']==job
        for p, sha in done['outputs'].items(): assert digest(ROOT/p)==sha, p
        return {'id':job['id'], 'status':'verified_existing'}
    directory = RUN/'evaluations'/job['id']
    if directory.exists(): raise RuntimeError(f'Unreceipted output, inspect without overwriting: {directory}')
    cmd = [sys.executable,'-X','utf8','-B','-u',str(RUN/'evaluate.py'),'--job',job['id']]
    started = time.perf_counter()
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', OPENBLAS_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    with (RUN/'logs'/f"{job['id']}.log").open('x',encoding='utf-8') as log:
        proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    if proc.returncode: raise RuntimeError(f"Job failed: {job['id']}; see its log")
    result = json.loads((directory/'result.json').read_text())
    assert result['status']=='complete' and result['job']==job
    assert [r['demo'] for r in result['records']]==job['demos']
    assert all(1<=r['steps']<=400 and (r['success'] or r['steps']==400) for r in result['records'])
    output = {p.relative_to(ROOT).as_posix():digest(p) for p in directory.glob('*') if p.is_file()}
    with receipt.open('x',encoding='utf-8') as f:
        json.dump({'status':'complete','job':job,'command':cmd,'outputs':output,
                   'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'elapsed_s':time.perf_counter()-started},f,indent=2)
    return {'id':job['id'],'status':'complete','success':sum(r['success'] for r in result['records']),
            'episodes':len(result['records']),'elapsed_s':time.perf_counter()-started}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args()
    for rel,sha in json.loads((RUN/'frozen_inputs.json').read_text()).items():
        assert digest(ROOT/rel)==sha, f'Frozen input changed: {rel}'
    for name in ['completed','logs']: (RUN/name).mkdir(exist_ok=True)
    jobs=json.loads((RUN/'jobs.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        future=[pool.submit(execute,j) for j in jobs]
        for f in concurrent.futures.as_completed(future): print(json.dumps(f.result()),flush=True)
    print(json.dumps({'all_complete':True,'jobs':len(jobs)}),flush=True)


if __name__=='__main__': main()
