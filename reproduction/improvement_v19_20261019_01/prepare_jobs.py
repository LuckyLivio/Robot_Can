"""Register the same 9/94 known profiles; never generate confirmation starts."""
from pathlib import Path
from dataclasses import asdict
import copy,json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
OLD=ROOT/'reproduction/improvement_v18_20261019_01'
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import Config as C15
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import Config as C16
from reproduction.improvement_v17_20261019_01.recovery.recovery_controller import Config as C17
from reproduction.improvement_v18_20261019_01.recovery.recovery_controller import Config as C18
VERSIONS=['v17','v18','budget','transition','candidate','settling','ab','v19']
FLAGS={'transition_window':['transition','ab','v19'],
       'candidate_budget':['candidate','ab','v19'],
       'terminal_settling':['settling','v19']}
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
    assert any((RUN/'protocols'/name).is_file() for name in ['PLAN_DRAFT.md','PLAN.md']),'Write protocol draft first'
    previous=read(OLD/'protocols/pilot_jobs.json');parents={(j['version'],suffix(j)):j for j in previous}
    bases=[copy.deepcopy(j) for j in previous if j['version']=='v18']
    assert sum(len(j['demos']) for j in bases)==94
    keys=[identity(j,n) for j in bases for n in j['demos']];assert len(keys)==len(set(keys))
    jobs=[]
    for base in bases:
        tail=suffix(base);c18=asdict(C18(**base['config']))
        c17=asdict(C17(**parents['v17',tail]['config']))
        c16=asdict(C16(**parents['v16',tail]['config']))
        c15=asdict(C15(**{key:c18[key] for key in asdict(C15())}))
        budget=asdict(C15(**parents['budget',tail]['config']))
        assert len(c15)==100 and len(c16)==103 and len(c17)==106 and len(c18)==108
        assert all(c18[k]==v for k,v in c17.items()) and all(c17[k]==v for k,v in c16.items())
        assert all(c16[k]==v for k,v in c15.items())
        assert c18['handoff_continuity'] and c18['short_route_selection']
        assert budget==dict(c15,carry_path=False,segmented_edge=False,budget_recenter=True)
        configs={'v17':c17,'v18':c18,'budget':budget}
        for version in ['transition','candidate','settling','ab','v19']:
            configs[version]=dict(c18,**{flag:version in active for flag,active in FLAGS.items()})
            assert len(configs[version])==111 and all(configs[version][key]==value for key,value in c18.items())
        # Prefer the latest actual rerun where present; retain valid older
        # references when this parent stage did not execute that older class.
        for ref in ['v15','v16','v17','v18','budget']:
            historical=OLD/'smoke_a'/f'{ref}_{tail}'/'result.json'
            if historical.is_file():base['baseline_result_'+ref]=rel(historical)
        expected_configs={'v15':c15,'v16':c16,**configs}
        classes={'v15':C15,'v16':C16,'v17':C17,'v18':C18,'budget':C15}
        for ref in ['v6','v13','v14','v15','v16','v17','v18','budget']:
            path=base.get('baseline_result_'+ref)
            if not path:continue
            raw=read(ROOT/path);assert raw['status']=='complete';old=raw['job']
            for field in ['method','seed','noise','dataset','fault','fault_policy','force_recovery_at']:
                assert base.get(field)==old.get(field),(tail,ref,field)
            assert set(base['demos'])<={r['demo'] for r in raw['records']}
            if ref in classes:assert asdict(classes[ref](**old['config']))==expected_configs[ref],(tail,ref,'Changed baseline profile')
        for version in VERSIONS:
            job=copy.deepcopy(base);job.update(id=version+'_'+tail,version=version,steps=400,config=configs[version].copy());jobs.append(job)
    smoke=[j for j in jobs if suffix(j) in SMOKE_NAMES]
    assert len(smoke)==sum(len(j['demos']) for j in smoke)==72
    assert sum(len(j['demos']) for j in jobs)==752
    outputs=[(RUN/'protocols/pilot_jobs.json',jobs),(RUN/'protocols/smoke_jobs.json',smoke)]
    assert all(not path.exists() for path,_ in outputs),'Registered jobs already exist'
    for path,items in outputs:
        with path.open('x',encoding='utf8') as stream:json.dump(items,stream,indent=2)
    coverage={ref:sum(len(j['demos']) for j in jobs if j['version']=='v19' and j.get('baseline_result_'+ref))
              for ref in ['v6','v13','v14','v15','v16','v17','v18','budget']}
    print(json.dumps({'pilot_profiles':94,'pilot_executions':752,'smoke_profiles':9,'smoke_executions':72,
                      'saved_reference_coverage':coverage,'physical_executions':0,
                      'interpretation':'A/B/C/AB repair full actual v18; budget is unchanged v15 C-only with different protection. Nine profiles reuse eight starts.'}))
if __name__=='__main__':main()
