"""Execute only the frozen, additive 240-episode comparison."""
import argparse,concurrent.futures,datetime,json,subprocess,sys
from setup_study import ROOT,RUN,digest,write

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    lock=json.loads((RUN/'frozen_protocol.json').read_text())
    for name,sha in lock['sha256'].items():assert digest(ROOT/name)==sha,name
    jobs=json.loads((RUN/'formal_jobs.json').read_text());out=RUN/'formal';out.mkdir(exist_ok=False)
    write(out/'started.json',{'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            'frozen_protocol_sha256':digest(RUN/'frozen_protocol.json'),'jobs':len(jobs),'workers':a.workers})
    def work(job):
        cmd=[sys.executable,'-X','utf8','-B','-u',str(RUN/'evaluate_recovery.py'),'--job-file',str(RUN/'formal_jobs.json'),
             '--job-id',job['id'],'--output-dir',str(out/job['id'])]
        with (out/f"{job['id']}.log").open('x',encoding='utf-8') as log:r=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError(job['id'])
        result=json.loads((out/job['id']/'result.json').read_text());assert result['status']=='complete'
        print(json.dumps({'job':job['id'],'success':sum(r['success'] for r in result['records']),'episodes':len(result['records'])}),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:list(pool.map(work,jobs))
    for name,sha in lock['sha256'].items():assert digest(ROOT/name)==sha,name
    write(out/'completed.json',{'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'episodes':240,'code_and_inputs_unchanged':True})

if __name__=='__main__':main()
