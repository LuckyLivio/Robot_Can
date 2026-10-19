"""Register the unchanged 9/94 known profiles; never create confirmation states."""
from pathlib import Path
from dataclasses import asdict
import copy,json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
OLD=ROOT/'reproduction/improvement_v19_20261019_01'
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import Config as C15
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import Config as C16
from reproduction.improvement_v17_20261019_01.recovery.recovery_controller import Config as C17
from reproduction.improvement_v18_20261019_01.recovery.recovery_controller import Config as C18
from reproduction.improvement_v19_20261019_01.recovery.recovery_controller import Config as C19
VERSIONS=['v17','v19','budget','directional','braking','v20']
FLAGS={'directional_transition':['directional','v20'],'delay_braking':['braking','v20']}
SMOKE_NAMES=['held_wait_demo87','regression_6000005','known_side_s17',
             'known_bc_k2_clean_demo_12000011','known_full_s23_clean_demo_12000036',
             'known_full_s23_noise005_demo_12000021','known13_bc_k2_noise005_demo_13000021',
             'known13_full_s41_noise005_demo_13000022','clearance_profile_6000005']

def read(path):return json.loads(path.read_text(encoding='utf8'))
def rel(path):return path.relative_to(ROOT).as_posix()
def suffix(job):
    prefix=job['version']+'_';assert job['id'].startswith(prefix),(job['id'],job['version'])
    return job['id'][len(prefix):]
def identity(job,name):
    return (job.get('dataset',''),job['method'],job['seed'],job['noise'],job.get('fault'),
            job.get('fault_policy'),job.get('force_recovery_at'),job['comparison_profile'],name)

def main():
    assert any((RUN/'protocols'/name).is_file() for name in ['PLAN_DRAFT.md','PLAN.md'])
    previous=read(OLD/'protocols/pilot_jobs.json');parents={(j['version'],suffix(j)):j for j in previous}
    bases=[copy.deepcopy(j) for j in previous if j['version']=='v19']
    assert sum(len(j['demos']) for j in bases)==94
    keys=[identity(j,n) for j in bases for n in j['demos']];assert len(keys)==len(set(keys))
    jobs=[]
    for base in bases:
        tail=suffix(base);c19=asdict(C19(**base['config']))
        c18=asdict(C18(**parents['v18',tail]['config']))
        c17=asdict(C17(**parents['v17',tail]['config']))
        c16=asdict(C16(**{k:c17[k] for k in asdict(C16())}))
        c15=asdict(C15(**{k:c16[k] for k in asdict(C15())}))
        budget=asdict(C15(**parents['budget',tail]['config']))
        assert [len(c) for c in [c15,c16,c17,c18,c19]]==[100,103,106,108,111]
        for inherited,new in [(c15,c16),(c16,c17),(c17,c18),(c18,c19)]:
            assert all(new[k]==v for k,v in inherited.items())
        assert all(c19[k] for k in ['handoff_continuity','short_route_selection','transition_window','candidate_budget','terminal_settling'])
        assert budget==dict(c15,carry_path=False,segmented_edge=False,budget_recenter=True)
        configs={'v17':c17,'v19':c19,'budget':budget}
        for version in ['directional','braking','v20']:
            configs[version]=dict(c19,**{flag:version in active for flag,active in FLAGS.items()})
            assert len(configs[version])==113 and all(configs[version][k]==v for k,v in c19.items())
        for ref in ['v15','v16','v17','v18','v19','budget']:
            historical=OLD/'smoke_a'/f'{ref}_{tail}'/'result.json'
            if historical.is_file():base['baseline_result_'+ref]=rel(historical)
        expected_configs={'v15':c15,'v16':c16,'v18':c18,**configs}
        classes={'v15':C15,'v16':C16,'v17':C17,'v18':C18,'v19':C19,'budget':C15}
        for ref in ['v6','v13','v14','v15','v16','v17','v18','v19','budget']:
            path=base.get('baseline_result_'+ref)
            if not path:continue
            raw=read(ROOT/path);assert raw['status']=='complete';old=raw['job']
            for field in ['method','seed','noise','dataset','fault','fault_policy','force_recovery_at']:
                assert base.get(field)==old.get(field),(tail,ref,field)
            assert set(base['demos'])<={row['demo'] for row in raw['records']}
            if ref in classes:assert asdict(classes[ref](**old['config']))==expected_configs[ref],(tail,ref,'Changed baseline profile')
        for version in VERSIONS:
            job=copy.deepcopy(base);job.update(id=version+'_'+tail,version=version,steps=400,config=configs[version].copy());jobs.append(job)
    smoke=[job for job in jobs if suffix(job) in SMOKE_NAMES]
    assert len(smoke)==sum(len(job['demos']) for job in smoke)==54
    assert sum(len(job['demos']) for job in jobs)==564
    outputs=[(RUN/'protocols/pilot_jobs.json',jobs),(RUN/'protocols/smoke_jobs.json',smoke)]
    assert all(not path.exists() for path,_ in outputs),'Registered jobs already exist'
    for path,items in outputs:
        with path.open('x',encoding='utf8') as stream:json.dump(items,stream,indent=2)
    coverage={ref:sum(len(job['demos']) for job in jobs if job['version']=='v20' and job.get('baseline_result_'+ref))
              for ref in ['v6','v13','v14','v15','v16','v17','v18','v19','budget']}
    print(json.dumps({'pilot_profiles':94,'pilot_executions':564,'smoke_profiles':9,'smoke_executions':54,
                      'saved_reference_coverage':coverage,'physical_executions':0,
                      'interpretation':'A/B repair full actual v19; budget is unchanged v15 C-only with different protection. Nine profiles reuse eight starts.'}))
if __name__=='__main__':main()
