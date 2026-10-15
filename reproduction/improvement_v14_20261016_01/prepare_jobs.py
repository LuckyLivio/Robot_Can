"""Preselect all known diagnostics; no independent confirmation data are created here."""
from pathlib import Path
import copy,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
OLD=ROOT/'reproduction/improvement_v13_20261016_01'
OLDER=ROOT/'reproduction/improvement_v12_20261015_01'
VERSIONS=['v13','track','clearance','v14']
SMOKE_NAMES=['held_wait_demo87','regression_6000005','known_side_s17',
             'known_bc_k2_clean_demo_12000011','known_full_s23_clean_demo_12000036',
             'known_full_s23_noise005_demo_12000021',
             'known13_bc_k2_noise005_demo_13000021','known13_full_s41_noise005_demo_13000022']

def read(path):return json.loads(path.read_text(encoding='utf8'))
def rel(path):return path.relative_to(ROOT).as_posix()
def result(path,demo):
    d=read(path);assert d['status']=='complete'
    return next(r for r in d['records'] if r['demo']==demo)
def identity(job,demo):
    return (job.get('dataset',''),job['method'],job['seed'],job['noise'],
            job.get('fault'),job.get('fault_policy'),job.get('force_recovery_at'),demo)

def main():
    bases=[copy.deepcopy(j) for j in read(OLD/'protocols/pilot_jobs.json') if j['version']=='v13']
    assert sum(len(j['demos']) for j in bases)==50
    for b in bases:
        suffix=b['id'].split('_',1)[1]
        b['baseline_result_v13']=rel(OLD/'pilot_a'/b['id']/'result.json')
        if suffix.startswith('known_') and '_demo_120' in suffix:
            condition=suffix[6:].split('_demo_')[0]
            p=OLDER/'confirmation'/('v6_'+condition)/'result.json'
        else:p=ROOT/'reproduction/improvement_v9_20261015_01/pilot_b'/('v6_'+suffix)/'result.json'
        if p.exists() and all(any(r['demo']==n for r in read(p)['records']) for n in b['demos']):b['baseline_result_v6']=rel(p)
        else:b.pop('baseline_result_v6',None)
    confirm=[j for j in read(OLD/'confirmation/jobs.json') if j['version']=='v13']
    extras=[];counts={'v13_failed':0,'v12_failed_v13_succeeded':0}
    for b in confirm:
        condition=b['id'].split('_',1)[1]
        parent_path=OLD/'confirmation'/b['id']/'result.json'
        before={r['demo']:r for r in read(OLD/'confirmation'/('v12_'+condition)/'result.json')['records']}
        for r in read(parent_path)['records']:
            if not r['success'] or not before[r['demo']]['success']:
                counts['v13_failed' if not r['success'] else 'v12_failed_v13_succeeded']+=1
                j=copy.deepcopy(b)
                j.update(id='v13_known13_'+condition+'_'+r['demo'],demos=[r['demo']],
                         baseline_result_v13=rel(parent_path),
                         baseline_result_v6=rel(OLD/'confirmation'/('v6_'+condition)/'result.json'))
                extras.append(j)
    assert counts=={'v13_failed':32,'v12_failed_v13_succeeded':11},counts
    bases+=extras
    assert sum(len(j['demos']) for j in bases)==93
    keys=[identity(j,n) for j in bases for n in j['demos']]
    assert len(keys)==len(set(keys)), 'Duplicate conditions'
    jobs=[]
    for b in bases:
        for name in b['demos']:
            result(ROOT/b['baseline_result_v13'],name)
            if b.get('baseline_result_v6'):result(ROOT/b['baseline_result_v6'],name)
        for version in VERSIONS:
            j=copy.deepcopy(b);j.update(id=version+'_'+b['id'].split('_',1)[1],version=version,steps=400)
            j['config'].pop('trajectory_tracking',None);j['config'].pop('descent_clearance',None)
            if version!='v13':
                j['config'].update(trajectory_tracking=version in ['track','v14'],descent_clearance=version in ['clearance','v14'])
            jobs.append(j)
    smoke=[j for j in jobs if j['id'].split('_',1)[1] in SMOKE_NAMES]
    assert len(smoke)==32 and sum(len(j['demos']) for j in smoke)==32
    for name,js in [('pilot_jobs.json',jobs),('smoke_jobs.json',smoke)]:
        with (RUN/'protocols'/name).open('x',encoding='utf8') as f:json.dump(js,f,indent=2)
    print(json.dumps({'pilot_conditions':93,'pilot_executions':372,'smoke_conditions':8,'smoke_executions':32,'additional_known':counts}))
if __name__=='__main__':main()
