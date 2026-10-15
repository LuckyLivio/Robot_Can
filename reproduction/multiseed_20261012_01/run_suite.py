"""Run the registered suite; child processes are local jobs, not agents."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
RUN=Path(__file__).resolve().parent

def run_job(job):
    start=time.perf_counter();log=RUN/'logs'/f"{job['id']}.log"
    done=RUN/'completed'/f"{job['id']}.json"
    if done.exists():
        record=json.loads(done.read_text())
        assert record['command']==job['command']
        for relative,digest in record['output_sha256'].items():
            assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest,relative
        return {'id':job['id'],'status':'verified_existing_completion'}
    if log.exists():raise FileExistsError(f'Incomplete earlier job: inspect {log}; no automatic overwrite')
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
    with log.open('x',encoding='utf-8') as handle:
        process=subprocess.run(job['command'],cwd=ROOT,env=env,stdout=handle,stderr=subprocess.STDOUT)
    if process.returncode:
        raise RuntimeError(f"{job['id']} failed, exit {process.returncode}: {log}")
    output_hashes={}
    for relative in job['outputs']:
        path=ROOT/relative
        if not path.is_file():raise FileNotFoundError(path)
        output_hashes[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
        if path.suffix=='.json':
            payload=json.loads(path.read_text())
            if 'status' in payload:assert payload['status']=='complete',(relative,payload['status'])
            if job['phase']=='evaluate':assert len(payload['records'])==30
    record={'id':job['id'],'command':job['command'],'status':'complete','output_sha256':output_hashes,
            'elapsed_s':time.perf_counter()-start}
    with done.open('x',encoding='utf-8') as handle:json.dump(record,handle,indent=2)
    return {'id':job['id'],'status':'complete','elapsed_s':record['elapsed_s']}

def main(args):
    protocol=json.loads((RUN/'protocol.json').read_text())
    assert json.loads((RUN/'validation.json').read_text())['passed']
    for relative,digest in protocol['source_sha256'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest,relative
    jobs=json.loads((RUN/'jobs.json').read_text())
    assert hashlib.sha256((RUN/'jobs.json').read_bytes()).hexdigest()==protocol['jobs_sha256']
    (RUN/'logs').mkdir(exist_ok=True);(RUN/'completed').mkdir(exist_ok=True)
    total_start=time.perf_counter()
    if args.phase in ('all','train'):
        train=[j for j in jobs if j['phase']=='train']
        for i,job in enumerate(train,1):
            print(json.dumps({'starting':job['id'],'training_job':i,'total':len(train)}),flush=True)
            print(json.dumps(run_job(job)),flush=True)
    if args.phase in ('all','evaluate'):
        for job in jobs:
            if job['phase']=='train':assert (RUN/'completed'/f"{job['id']}.json").exists(),job['id']
        evaluations=[j for j in jobs if j['phase']=='evaluate']
        with ThreadPoolExecutor(max_workers=protocol['evaluation_workers']) as executor:
            futures={executor.submit(run_job,job):job for job in evaluations}
            for i,future in enumerate(as_completed(futures),1):
                print(json.dumps({'evaluation_completed':i,'total':len(evaluations),**future.result()}),flush=True)
    print(json.dumps({'phase_complete':args.phase,'elapsed_s':time.perf_counter()-total_start}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['all','train','evaluate'],default='all')
    main(parser.parse_args())
