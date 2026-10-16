"""Register the same nine/94 diagnostic profiles with seven fresh executions each."""
from pathlib import Path
from dataclasses import asdict
import copy,json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
OLD=ROOT/'reproduction/improvement_v15_20261016_01'
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import Config as C14
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import Config as C15
VERSIONS=['v14','v15','budget','ik','held','edge','v16']
FLAGS={'ik_continuation':['ik','v16'],'held_pose':['held','v16'],'edge_stability':['edge','v16']}
SMOKE_NAMES=['held_wait_demo87','regression_6000005','known_side_s17',
             'known_bc_k2_clean_demo_12000011','known_full_s23_clean_demo_12000036',
             'known_full_s23_noise005_demo_12000021','known13_bc_k2_noise005_demo_13000021',
             'known13_full_s41_noise005_demo_13000022','clearance_profile_6000005']
def read(path):return json.loads(path.read_text(encoding='utf8'))
def rel(path):return path.relative_to(ROOT).as_posix()
def identity(job,name):
    return (job.get('dataset',''),job['method'],job['seed'],job['noise'],job.get('fault'),
            job.get('fault_policy'),job.get('force_recovery_at'),job['comparison_profile'],name)
def main():
    assert (RUN/'protocols/PLAN.md').is_file(),'Write the v16 protocol before preparing jobs'
    bases=[copy.deepcopy(j) for j in read(OLD/'protocols/pilot_jobs.json') if j['version']=='v14']
    assert sum(len(j['demos']) for j in bases)==94
    keys=[identity(j,n) for j in bases for n in j['demos']];assert len(keys)==len(set(keys))
    jobs=[]
    for base in bases:
        suffix=base['id'].split('_',1)[1];c14=asdict(C14(**base['config']));c15=asdict(C15(**c14))
        assert len(c14)==97 and len(c15)==100
        assert c15['carry_path'] and c15['segmented_edge'] and c15['budget_recenter']
        configs={'v14':c14,'v15':c15,'budget':dict(c15,carry_path=False,segmented_edge=False,budget_recenter=True)}
        for version in ['ik','held','edge','v16']:
            configs[version]=dict(c15,**{flag:version in active for flag,active in FLAGS.items()})
            assert all(configs[version][key]==value for key,value in c15.items())
        for version in ['v14','v15','budget']:
            historical=OLD/'smoke_a'/f'{version}_{suffix}'/'result.json'
            if historical.is_file():base['baseline_result_'+version]=rel(historical)
            elif version!='v14':base.pop('baseline_result_'+version,None)
        for ref in ['v6','v13','v14','v15','budget']:
            path=base.get('baseline_result_'+ref)
            if not path:continue
            raw=read(ROOT/path);assert raw['status']=='complete';old=raw['job']
            for field in ['method','seed','noise','dataset','fault','fault_policy','force_recovery_at']:
                assert base.get(field)==old.get(field),(suffix,ref,field)
            assert set(base['demos'])<={r['demo'] for r in raw['records']}
            if ref in configs:
                cls=C14 if ref=='v14' else C15
                assert asdict(cls(**old['config']))==configs[ref],(suffix,ref,'Changed baseline profile')
        for version in VERSIONS:
            job=copy.deepcopy(base);job.update(id=version+'_'+suffix,version=version,steps=400,config=configs[version].copy())
            jobs.append(job)
    smoke=[j for j in jobs if j['id'].split('_',1)[1] in SMOKE_NAMES]
    assert len(smoke)==sum(len(j['demos']) for j in smoke)==63
    assert sum(len(j['demos']) for j in jobs)==658
    outputs=[(RUN/'protocols/pilot_jobs.json',jobs),(RUN/'protocols/smoke_jobs.json',smoke)]
    assert all(not path.exists() for path,_ in outputs),'Registered jobs already exist'
    for path,items in outputs:
        with path.open('x',encoding='utf8') as stream:json.dump(items,stream,indent=2)
    print(json.dumps({'pilot_profiles':94,'pilot_executions':658,'smoke_profiles':9,'smoke_executions':63,
                      'interpretation':'ik/held/edge add one repair to full v15; budget is unchanged v15 C-only. Profiles are not independent starts.'}))
if __name__=='__main__':main()
