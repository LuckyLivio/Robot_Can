"""Gate the next stage on paired outcomes and archived-source verification."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
from dataclasses import asdict
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery.recovery_controller import Config
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def paired(folder,v):
    out={}
    for p in folder.glob(v+'_*/result.json'):
        d=json.loads(p.read_text());assert d['status']=='complete'
        for r in d['records']:out[(d['job']['id'].split('_',1)[1],r['demo'])]=r
    return out
if __name__=='__main__':
    stage=RUN/'pilot_a';assert (stage/'completed.json').exists()
    for n in ['mechanisms_a','guards_a','smoke_a_verification','pilot_a_verification','pilot_a_physics']:
        assert json.loads((RUN/'analysis'/f'{n}.json').read_text())['passed']
    a=paired(stage,'v11');b=paired(stage,'v10');v6=paired(ROOT/'reproduction/improvement_v9_20261015_01/pilot_b','v6')
    assert len(a)==37 and set(a)==set(b)==set(v6)
    assert sum(r['success'] for r in a.values())>=31 and a[('regression_6000005','demo_6000005')]['success']
    assert all(a[k]['success'] for k in a if b[k]['success'] or v6[k]['success'])
    # Freeze exactly the full pilot configuration, including inherited defaults.
    pilot=json.loads((stage/'jobs.json').read_text());raw=next(j['config'] for j in pilot if j['version']=='v11');cfg=asdict(Config(**raw))
    jobs=[]
    for base in json.loads((ROOT/'reproduction/improvement_v6_20261015_01/protocols/dev_jobs.json').read_text()):
        assert base['version']=='v6'
        assert all(cfg[k]==v for k,v in base['config'].items()),'Do not silently change common baseline settings'
        j=copy.deepcopy(base);j['id']='v11_'+base['id'].split('_',1)[1];j['version']='v11';j['config']=cfg.copy();j['steps']=400
        j['baseline_result_v6']=f"reproduction/improvement_v6_20261015_01/dev_a/{base['id']}/result.json";jobs.append(j)
    assert sum(len(j['demos']) for j in jobs)==240
    with (RUN/'protocols/dev_jobs.json').open('x') as f:json.dump(jobs,f,indent=2)
    source=[p for p in (RUN/'recovery').iterdir() if p.suffix in ['.py','.json']]+[RUN/n for n in ['evaluate_recovery.py','variants.py','run_batch.py','protocols/dev_jobs.json']]
    out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gate_passed':True,'diagnostic_success':sum(r['success'] for r in a.values()),'diagnostic_episodes':37,'config':cfg,'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in source},'baseline':'frozen v6 development, same 240 conditions','note':'Gate authorizes development evaluation only; not adoption or independent confirmation.'}
    with (RUN/'protocols/development_freeze.json').open('x') as f:json.dump(out,f,indent=2)
    print('FROZEN: gate passed; 240 development episodes prepared')
