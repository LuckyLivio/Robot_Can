"""Run frozen jobs once; verify complete jobs when resuming."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import datetime,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run_job(job):
    done=RUN/'completed'/f"{job['id']}.json"; log=RUN/'logs'/f"{job['id']}.log"
    if done.exists():
        data=json.loads(done.read_text());assert data['command']==job['command']
        for relative,sha in data['outputs'].items():assert digest(ROOT/relative)==sha
        return {'id':job['id'],'status':'verified_existing'}
    if log.exists():raise FileExistsError(f'Incomplete earlier job; inspect without overwrite: {log}')
    started=time.perf_counter();env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    with log.open('x',encoding='utf-8') as f:
        result=subprocess.run(job['command'],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(f"{job['id']} failed; see {log}")
    output=json.loads((ROOT/job['outputs'][0]).read_text());assert output['status']=='complete' and len(output['records'])==60
    files=list((ROOT/job['output_dir']).rglob('*'))
    data={'command':job['command'],'status':'complete','completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'elapsed_s':time.perf_counter()-started,'outputs':{p.relative_to(ROOT).as_posix():digest(p) for p in files if p.is_file()}}
    with done.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
    return {'id':job['id'],'status':'complete','elapsed_s':data['elapsed_s']}

def main():
    lock=json.loads((RUN/'lock.json').read_text())
    for relative,sha in lock['input_sha256'].items():assert digest(ROOT/relative)==sha,relative
    jobs=json.loads((RUN/'jobs.json').read_text())
    (RUN/'logs').mkdir(exist_ok=True);(RUN/'completed').mkdir(exist_ok=True)
    started=time.perf_counter()
    with ThreadPoolExecutor(max_workers=lock['workers']) as pool:
        futures=[pool.submit(run_job,j) for j in jobs]
        for i,f in enumerate(as_completed(futures),1):print(json.dumps({'completed':i,'total':len(jobs),**f.result()}),flush=True)
    print(json.dumps({'all_complete':True,'elapsed_s':time.perf_counter()-started}),flush=True)

if __name__=='__main__':main()
