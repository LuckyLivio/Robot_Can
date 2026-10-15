"""Lock all choices before native states; never choose starts by policy outcomes."""
from pathlib import Path
import copy,datetime,hashlib,importlib.metadata,json,re,sys
import h5py,numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from common import DATA,make_env,restore_demo,pack_obs
from reproduction.confirmation_20261012_01.prepare_states import native_reset

INITIALIZATION_SEEDS=list(range(2026102601,2026102661))
STATE_NAMES=[f'demo_{14000000+i}' for i in range(60)]
BOOTSTRAP_SEED=2026102614
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,d):
    with p.open('x',encoding='utf8') as f:json.dump(d,f,indent=2,allow_nan=False)

def verify_reserved_identifiers_unused(before):
    """Search the immutable prior inventory, excluding this version's new plan."""
    seeds=set(INITIALIZATION_SEEDS+[BOOTSTRAP_SEED]);names=set(STATE_NAMES);checked=[]
    for rel in before:
        p=ROOT/rel
        if p.suffix not in ['.json','.md']:continue
        if p.suffix=='.md' and p.name not in ['PLAN.md','PROTOCOL.md']:continue
        if p.suffix=='.json' and not any(s in rel.lower() for s in ['protocol','design','freeze','lock','jobs','state_validation']):continue
        text=p.read_text(encoding='utf8');numbers={int(s) for s in re.findall(r'(?<![0-9])20[0-9]{8}(?![0-9])',text)}
        assert not seeds.intersection(numbers),(rel,'initialization/bootstrap seed already recorded')
        assert not names.intersection(re.findall(r'demo_[0-9]+',text)),(rel,'state name already recorded')
        checked.append(rel)
    assert checked,'Prior protocol inventory is empty'
    return checked

if __name__=='__main__':
    assert (RUN/'analysis/dev_a.json').is_file(),'No passed development result; confirmation remains disabled'
    outcome=read(RUN/'analysis/dev_a.json');s=outcome['variants']['v14']
    assert outcome['outcome_gate_passed'] and s['episodes']==240 and s['success']>=236
    assert not s['regressed_vs_v6'] and not s['regressed_vs_v13']
    assert s['paired_reference_v6']==240 and s['paired_reference_v13']==240
    for n in ['dev_a_verification','dev_a_physics']:assert read(RUN/'analysis'/f'{n}.json')['passed']
    freeze=read(RUN/'protocols/development_freeze.json')
    assert freeze['gate_passed'] and freeze['inherited_config_unchanged']
    assert freeze['config']['horizon_steps']==400 and freeze['config']['delay']==2 and freeze['config']['max_attempts']==2
    for p,h in freeze['source_sha256'].items():assert sha(ROOT/p)==h,p
    before=read(RUN/'before_manifest.json');unused_checked=verify_reserved_identifiers_unused(before)
    design={'registered_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'initialization_seeds':INITIALIZATION_SEEDS,'state_names':STATE_NAMES,
            'noise_seeds':[70000+int(n.split('_')[1]) for n in STATE_NAMES],
            'versions':['v6','v13','v14'],'episodes':1440,'unique_starts':60,
            'bootstrap_seed':BOOTSTRAP_SEED,'bootstrap_draws':20000,'bootstrap_unit':'paired start, averaging eight fixed conditions',
            'primary_effect':'v14 minus v6 equally weighted eight-condition success; 95% percentile CI',
            'secondary_effect':'v14 minus v13 equally weighted eight-condition success; 95% percentile CI',
            'adoption_gate':'At least both v6 and v13 total successes and no paired success regression against either. CI strictly above zero is a separate requirement to claim overall success-rate improvement. Passing does not prove superiority to v5.',
            'selection':'All first60 predefined seeds, no outcome filtering, no post-confirmation tuning',
            'prior_protocol_identifier_check':{'passed':True,'files':unused_checked},
            'source_sha256':dict(freeze['source_sha256'])}
    additional=[RUN/n for n in ['prepare_confirmation.py','analyze_confirmation.py','protocols/PLAN.md','protocols/development_freeze.json',
                                 'analysis/dev_a.json','analysis/dev_a_verification.json','analysis/dev_a_physics.json']]
    additional += [ROOT/'reproduction/improvement_v6_20261015_01/protocols/dev_jobs.json',
                   ROOT/'reproduction/improvement_v13_20261016_01/protocols/dev_jobs.json',
                   ROOT/'reproduction/confirmation_20261012_01/prepare_states.py']
    additional += [p for p in (ROOT/'reproduction/improvement_v13_20261016_01/recovery').iterdir() if p.suffix in ['.py','.json']]
    for p in additional:design['source_sha256'][p.relative_to(ROOT).as_posix()]=sha(p)
    write(RUN/'protocols/freeze_before_states.json',design)
    previous=[];files=[];seen=set()
    # Every distinct existing tracked HDF5 containing initial simulator states.
    for rel,h in before.items():
        if not rel.endswith(('.hdf5','.h5')) or h in seen:continue
        assert sha(ROOT/rel)==h,rel;seen.add(h)
        with h5py.File(ROOT/rel) as f:
            if 'data' not in f:continue
            assert not set(STATE_NAMES).intersection(f['data'].keys()),(rel,'existing state ID')
            states=[d['states'][0] for d in f['data'].values() if isinstance(d,h5py.Group) and 'states' in d]
            if states:previous.extend(states);files.append(rel)
    assert previous,'No prior simulator states available for overlap check'
    with h5py.File(DATA) as f:meta=f['data'].attrs['env_args']
    env=make_env(False);native=make_env(False);serialized=make_env(False);desc=[];regen=[]
    try:
        with h5py.File(RUN/'confirmation_starts.hdf5','x') as f:
            group=f.create_group('data');group.attrs['env_args']=meta;new=[]
            for seed,name,ns in zip(design['initialization_seeds'],STATE_NAMES,design['noise_seeds']):
                # native_reset clears the robosuite observation cache after env.reset.
                state,obs=native_reset(env,seed)
                assert state[0]==0 and np.isfinite(state).all() and np.isfinite(obs).all() and not env._check_success()
                compatible=[s for s in previous+new if s.shape==state.shape];assert compatible
                old=np.stack(compatible);distance=float(np.max(abs(old-state),axis=1).min())
                assert distance>1e-8;new.append(state.copy())
                d=group.create_group(name);d.attrs['model_file']=env.sim.model.get_xml();d.attrs['initialization_seed']=seed;d.attrs['noise_seed']=ns
                d.create_dataset('states',data=state[None]);d.create_dataset('initial_observation',data=obs)
                noise=np.random.default_rng(ns).normal(0,.05,(400,3));d.create_dataset('execution_noise',data=noise)
                desc.append({'name':name,'seed':seed,'noise_seed':ns,'state_sha256':hashlib.sha256(state.tobytes()).hexdigest(),
                             'noise_sha256':hashlib.sha256(noise.tobytes()).hexdigest(),'nearest_old_or_previous_new_distance':distance})
        with h5py.File(RUN/'confirmation_starts.hdf5') as f:
            for item in reversed(desc):
                state,obs=native_reset(native,item['seed']);d=f['data'][item['name']]
                np.testing.assert_array_equal(state,d['states'][0]);np.testing.assert_array_equal(obs,d['initial_observation'][:])
                assert env.control_freq==native.control_freq==serialized.control_freq==20
                err=float(np.max(abs(pack_obs(restore_demo(serialized,d))-obs)));assert err<1e-5
                regen.append({'name':item['name'],'native_regeneration_exact':True,'serialized_observation_error':err})
    finally:env.close();native.close();serialized.close()
    write(RUN/'analysis/confirmation_state_validation.json',{'passed':True,'no_old_overlap':True,'old_initial_states':len(previous),
          'old_files':files,'states':desc,'regeneration':regen,'note':'Three separate native/native/serialized environments; no policy evaluated during generation.'})
    jobs=[]
    sources={'v6':ROOT/'reproduction/improvement_v6_20261015_01/protocols/dev_jobs.json',
             'v13':ROOT/'reproduction/improvement_v13_20261016_01/protocols/dev_jobs.json','v14':RUN/'protocols/dev_jobs.json'}
    for version in design['versions']:
        bases=read(sources[version]);assert len(bases)==8
        for base in bases:
            assert base['version']==version
            j=copy.deepcopy(base);j['dataset']=(RUN/'confirmation_starts.hdf5').relative_to(ROOT).as_posix();j['demos']=STATE_NAMES;j['steps']=400
            # Development references refer to other starts and must not be paired here.
            for k in list(j):
                if k.startswith('baseline_result_'):del j[k]
            jobs.append(j)
    assert sum(len(j['demos']) for j in jobs)==1440 and len({j['id'] for j in jobs})==24
    write(RUN/'protocols/confirmation_jobs.json',jobs)
    hashes=dict(design['source_sha256'])
    for n in ['confirmation_starts.hdf5','protocols/confirmation_jobs.json','protocols/freeze_before_states.json','analysis/confirmation_state_validation.json']:
        hashes[(RUN/n).relative_to(ROOT).as_posix()]=sha(RUN/n)
    write(RUN/'protocols/confirmation_lock.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashes,
          'packages':{n:importlib.metadata.version(n) for n in ['numpy','torch','robosuite','mujoco','scipy','h5py']},'episodes':1440})
    print('Frozen and validated 60 new starts; 1440 paired v6/v13/v14 executions prepared')
