"""Prepare fixed diagnostic profiles only after the new protocol exists."""
from pathlib import Path
from dataclasses import asdict
import copy,json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
OLD=ROOT/'reproduction/improvement_v14_20261016_01'
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import Config as ParentConfig
VERSIONS=['v14','carry','edge','budget','v15']
FLAGS={'carry_path':['carry','v15'],'segmented_edge':['edge','v15'],'budget_recenter':['budget','v15']}
SMOKE_NAMES=['held_wait_demo87','regression_6000005','known_side_s17',
             'known_bc_k2_clean_demo_12000011','known_full_s23_clean_demo_12000036',
             'known_full_s23_noise005_demo_12000021',
             'known13_bc_k2_noise005_demo_13000021','known13_full_s41_noise005_demo_13000022',
             'clearance_profile_6000005']
def read(path):return json.loads(path.read_text(encoding='utf8'))
def rel(path):return path.relative_to(ROOT).as_posix()
def record(path,name):
    d=read(path);assert d['status']=='complete'
    return next(r for r in d['records'] if r['demo']==name)
def identity(job,name):
    return (job.get('dataset',''),job['method'],job['seed'],job['noise'],job.get('fault'),
            job.get('fault_policy'),job.get('force_recovery_at'),job['comparison_profile'],name)
def main():
    assert (RUN/'protocols/PLAN.md').is_file(),'Write the v15 protocol before preparing jobs'
    bases=[copy.deepcopy(j) for j in read(OLD/'protocols/pilot_jobs.json') if j['version']=='v14']
    assert sum(len(j['demos']) for j in bases)==93
    for b in bases:
        b['comparison_profile']='standard'
        b['config']=asdict(ParentConfig(**b['config']))
        old=OLD/'smoke_b'/b['id']/'result.json'
        if old.is_file():b['baseline_result_v14']=rel(old)
        else:b.pop('baseline_result_v14',None)
    profile=copy.deepcopy(next(j for j in read(OLD/'smoke_b/jobs.json') if j['id']=='clearance_regression_6000005'))
    profile.update(id='v14_clearance_profile_6000005',version='v14',comparison_profile='clearance_only_parent',
                   baseline_result_v14=rel(OLD/'smoke_b/clearance_regression_6000005/result.json'))
    profile['config']=asdict(ParentConfig(**profile['config']))
    assert not profile['config']['trajectory_tracking'] and profile['config']['descent_clearance']
    bases.append(profile);assert sum(len(j['demos']) for j in bases)==94
    keys=[identity(j,n) for j in bases for n in j['demos']];assert len(keys)==len(set(keys))
    jobs=[]
    for b in bases:
        for ref in ['v6','v13','v14']:
            path=b.get('baseline_result_'+ref)
            if path:
                raw=read(ROOT/path);assert raw['status']=='complete';old=raw['job']
                for field in ['method','seed','noise','dataset','fault','fault_policy','force_recovery_at']:
                    assert b.get(field)==old.get(field),(b['id'],ref,field)
                for name in b['demos']:record(ROOT/path,name)
                if ref=='v14':assert asdict(ParentConfig(**old['config']))==b['config']
        for version in VERSIONS:
            j=copy.deepcopy(b);j.update(id=version+'_'+b['id'].split('_',1)[1],version=version,steps=400)
            if version!='v14':j['config'].update({flag:version in active for flag,active in FLAGS.items()})
            jobs.append(j)
    smoke=[j for j in jobs if j['id'].split('_',1)[1] in SMOKE_NAMES]
    assert len(smoke)==45 and sum(len(j['demos']) for j in smoke)==45
    assert sum(len(j['demos']) for j in jobs)==470
    for name,js in [('pilot_jobs.json',jobs),('smoke_jobs.json',smoke)]:
        with (RUN/'protocols'/name).open('x',encoding='utf8') as f:json.dump(js,f,indent=2)
    print(json.dumps({'pilot_conditions':94,'pilot_executions':470,'smoke_conditions':9,'smoke_executions':45,
                      'profile_note':'93 prior conditions plus one clearance-only parent profile; not 94 independent starts'}))
if __name__=='__main__':main()
