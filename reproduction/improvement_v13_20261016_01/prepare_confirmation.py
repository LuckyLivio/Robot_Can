"""Lock design before native states; never choose starts by policy outcomes."""
from pathlib import Path
import copy,datetime,hashlib,importlib.metadata,json,sys
import h5py,numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from common import DATA,make_env,restore_demo,pack_obs
from reproduction.confirmation_20261012_01.prepare_states import native_reset
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
    with p.open('x',encoding='utf8') as f:json.dump(d,f,indent=2,allow_nan=False)
if __name__=='__main__':
    assert json.loads((RUN/'analysis/dev_a.json').read_text())['outcome_gate_passed']
    for n in ['dev_a_verification','dev_a_physics']:
        assert json.loads((RUN/'analysis'/f'{n}.json').read_text())['passed']
    freeze=json.loads((RUN/'protocols/development_freeze.json').read_text())
    for p,h in freeze['source_sha256'].items():assert sha(ROOT/p)==h,p
    names=[f'demo_{13000000+i}' for i in range(60)]
    design={'registered_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'initialization_seeds':list(range(2026101601,2026101661)), 'state_names':names,
            'noise_seeds':[70000+int(n.split('_')[1]) for n in names],
            'versions':['v6','v12','v13'],'episodes':1440,'unique_starts':60,
            'bootstrap_seed':2026101613,'bootstrap_draws':20000,'bootstrap_unit':'paired start, averaging eight fixed conditions',
            'primary_effect':'v13 minus v6 equally weighted eight-condition success; 95% percentile CI',
            'adoption_gate':'At least both v6 and v12 total successes and no paired success regression against either; CI strictly above zero required to claim overall success-rate improvement. Passing is relative to v6 on this batch, not proof of superiority to v5.',
            'selection':'All first60 predefined seeds, no outcome filtering, no post-confirmation tuning',
            'source_sha256':dict(freeze['source_sha256'])}
    for n in ['prepare_confirmation.py','analyze_confirmation.py','protocols/PLAN.md']:
        design['source_sha256'][(RUN/n).relative_to(ROOT).as_posix()]=sha(RUN/n)
    write(RUN/'protocols/freeze_before_states.json',design)
    previous=[];files=[];seen=set()
    # Every distinct existing tracked HDF5 containing initial simulator states.
    before=json.loads((RUN/'before_manifest.json').read_text())
    for rel,h in before.items():
        if not rel.endswith(('.hdf5','.h5')) or h in seen:continue
        seen.add(h)
        with h5py.File(ROOT/rel) as f:
            if 'data' not in f:continue
            states=[d['states'][0] for d in f['data'].values() if isinstance(d,h5py.Group) and 'states' in d]
            if states:previous.extend(states);files.append(rel)
    with h5py.File(DATA) as f:meta=f['data'].attrs['env_args']
    env=make_env(False);native=make_env(False);serialized=make_env(False);desc=[];regen=[]
    try:
        with h5py.File(RUN/'confirmation_starts.hdf5','x') as f:
            group=f.create_group('data');group.attrs['env_args']=meta;new=[]
            for seed,name,ns in zip(design['initialization_seeds'],names,design['noise_seeds']):
                state,obs=native_reset(env,seed)
                assert np.isfinite(state).all() and np.isfinite(obs).all() and not env._check_success()
                old=np.stack([s for s in previous+new if s.shape==state.shape]);distance=float(np.max(abs(old-state),axis=1).min())
                assert distance>1e-8;new.append(state.copy())
                d=group.create_group(name);d.attrs['model_file']=env.sim.model.get_xml();d.attrs['initialization_seed']=seed
                d.create_dataset('states',data=state[None]);d.create_dataset('initial_observation',data=obs)
                noise=np.random.default_rng(ns).normal(0,.05,(400,3));d.create_dataset('execution_noise',data=noise)
                desc.append({'name':name,'seed':seed,'noise_seed':ns,'state_sha256':hashlib.sha256(state.tobytes()).hexdigest(),
                             'noise_sha256':hashlib.sha256(noise.tobytes()).hexdigest(),'nearest_old_or_previous_new_distance':distance})
        with h5py.File(RUN/'confirmation_starts.hdf5') as f:
            for item in reversed(desc):
                state,obs=native_reset(native,item['seed']);d=f['data'][item['name']]
                np.testing.assert_array_equal(state,d['states'][0]);np.testing.assert_array_equal(obs,d['initial_observation'][:])
                err=float(np.max(abs(pack_obs(restore_demo(serialized,d))-obs)));assert err<1e-5
                regen.append({'name':item['name'],'native_regeneration_exact':True,'serialized_observation_error':err})
    finally:env.close();native.close();serialized.close()
    write(RUN/'analysis/confirmation_state_validation.json',{'passed':True,'no_old_overlap':True,'old_initial_states':len(previous),
          'old_files':files,'states':desc,'regeneration':regen,'note':'Three separate native/native/serialized environments; no policy evaluated during generation.'})
    jobs=[]
    for version in design['versions']:
        source=(ROOT/f'reproduction/improvement_{version}_20261015_01/protocols/dev_jobs.json') if version in ['v6','v12'] else RUN/'protocols/dev_jobs.json'
        for base in json.loads(source.read_text()):
            j=copy.deepcopy(base);j['dataset']=(RUN/'confirmation_starts.hdf5').relative_to(ROOT).as_posix();j['demos']=names;j['steps']=400
            jobs.append(j)
    assert sum(len(j['demos']) for j in jobs)==1440
    write(RUN/'protocols/confirmation_jobs.json',jobs)
    hashes=dict(design['source_sha256'])
    for n in ['confirmation_starts.hdf5','protocols/confirmation_jobs.json','protocols/freeze_before_states.json','analysis/confirmation_state_validation.json']:
        hashes[(RUN/n).relative_to(ROOT).as_posix()]=sha(RUN/n)
    write(RUN/'protocols/confirmation_lock.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashes,
          'packages':{n:importlib.metadata.version(n) for n in ['numpy','torch','robosuite','mujoco','scipy','h5py']},'episodes':1440})
    print('Frozen and validated 60 new starts; 1440 paired v6/v12/v13 executions prepared')
