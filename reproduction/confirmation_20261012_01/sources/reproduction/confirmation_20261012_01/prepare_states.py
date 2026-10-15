"""Prospective native-reset states; no policy rollout or outcome selection."""
import datetime, hashlib, json, random, sys
from pathlib import Path
import h5py
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from common import DATA,make_env,pack_obs,restore_demo
from collect_rollout_branches import signature,error

def write(path,payload):
    with path.open('x',encoding='utf-8') as f: json.dump(payload,f,indent=2,allow_nan=False)

def native_reset(env,seed):
    random.seed(seed); np.random.seed(seed)
    env.reset()
    env._obs_cache.clear(); env._get_observations(force_update=True)
    obs=env._get_observations(force_update=True)
    return env.sim.get_state().flatten().copy(),pack_obs(obs)

def main():
    design=json.loads((RUN/'design.json').read_text())
    env=make_env(False)
    print('native_environment_ready',flush=True)
    with h5py.File(DATA,'r') as old:
        old_states=np.stack([d['states'][0] for d in old['data'].values()])
        meta=old['data'].attrs['env_args']
    description=[]; noise=[]
    for filename,seeds,names in [('starts.hdf5',design['initialization_seeds'],design['state_names']),
        ('qa_starts.hdf5',design['qa_initialization_seeds'],['demo_2000000','demo_2000001'])]:
        exists=(RUN/filename).exists()
        with h5py.File(RUN/filename,'r' if exists else 'x') as f:
            group=f['data'] if exists else f.create_group('data')
            if not exists:group.attrs['env_args']=meta
            for i,(seed,name) in enumerate(zip(seeds,names)):
                state,obs=native_reset(env,seed)
                assert np.isfinite(state).all() and np.isfinite(obs).all()
                assert state[0]==0 and not env._check_success()
                if exists:
                    d=group[name]
                    assert np.array_equal(d['states'][0],state)
                    assert np.array_equal(d['initial_observation'][:],obs)
                    assert d.attrs['model_file']==env.sim.model.get_xml()
                else:
                    d=group.create_group(name);d.attrs['model_file']=env.sim.model.get_xml()
                    d.attrs['initialization_seed']=seed
                    d.create_dataset('states',data=state[None]);d.create_dataset('initial_observation',data=obs)
                if filename=='starts.hdf5':
                    noise_seed=design['noise_seeds'][i]
                    assert noise_seed==70000+int(name.split('_')[1])
                    samples=np.random.default_rng(noise_seed).normal(0,.05,(400,3))
                    if exists:assert np.array_equal(d['execution_noise'][:],samples)
                    else:
                        d.create_dataset('execution_noise',data=samples);d.attrs['noise_seed']=noise_seed
                    noise.append(samples)
                    distance=np.max(np.abs(old_states-state),axis=1)
                    assert distance.min()>1e-8
                    description.append({'name':name,'initialization_seed':seed,'noise_seed':noise_seed,
                        'state_sha256':hashlib.sha256(state.tobytes()).hexdigest(),
                        'noise_sha256':hashlib.sha256(samples.tobytes()).hexdigest(),
                        'can_position':obs[16:19].tolist(),'robot_qpos':state[1:8].tolist(),
                        'nearest_old_state_max_abs_distance':float(distance.min())})
    # Regenerate every state independently with the locked RNG seeds.
    regeneration=[]
    env2=make_env(False);env3=make_env(False)
    with h5py.File(RUN/'starts.hdf5','r') as f:
        for item in reversed(description):
            state,obs=native_reset(env2,item['initialization_seed']);d=f['data'][item['name']]
            assert np.array_equal(state,d['states'][0])
            assert np.array_equal(obs,d['initial_observation'][:])
            restored=restore_demo(env3,d)
            native_xml_error=error(pack_obs(restored),obs)
            # MuJoCo serializes XML numeric attributes with limited precision.
            # All controllers evaluate the SAME saved XML, not this native model.
            assert native_xml_error<1e-5
            regeneration.append({'name':item['name'],'state_exact':True,'observation_exact':True,
                                 'native_vs_serialized_xml_observation_error':native_xml_error})
    # Separate QA seeds, fixed random actions (not candidate/model outcomes).
    checks=[]; actions=np.random.default_rng(326101201).uniform(-.25,.25,(40,7))
    with h5py.File(RUN/'qa_starts.hdf5','r') as f:
        reference={}
        for name in f['data']:
            obs=restore_demo(env,f['data'][name]); rows=[(pack_obs(obs),signature(env))]
            for a in actions:
                obs,*_=env.step(a);rows.append((pack_obs(obs),signature(env)))
            reference[name]=rows
        for name in reversed(list(f['data'])):
            obs=restore_demo(env2,f['data'][name]);rows=[(pack_obs(obs),signature(env2))]
            for a in actions:
                obs,*_=env2.step(a);rows.append((pack_obs(obs),signature(env2)))
            maximum=max(error(a,b) for ra,rb in zip(reference[name],rows) for a,b in zip(ra,rb))
            assert maximum<=1e-7,maximum
            checks.append({'name':name,'steps':40,'max_observation_physics_controller_error':maximum})
    info={'prepared_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'states':description,'native_robot_initialization_noise':env.robots[0].initialization_noise,
          'native_robot_init_qpos':np.asarray(env.robots[0].init_qpos).tolist(),
          'target_can_bin':env.target_bin_placements[env.object_to_id['can']].tolist(),
          'regeneration':regeneration,'qa_replay_checks':checks,'passed':True,
          'old_initial_states_compared':len(old_states),'exact_old_state_overlap':0,
          'selection':'All first60 registered seeds retained. No policy evaluated during generation.'}
    info['preflight_note']='Initial native-vs-serialized XML check at1e-7 failed at1.19e-7. MuJoCo XML rounding; native state regeneration remains exact. Measured across all60 with1e-5 serialization tolerance. Saved-state replay tolerance stays1e-7. No states changed or regenerated with new seeds.'
    env.close();env2.close();env3.close();write(RUN/'state_validation.json',info)
    print(json.dumps({'states':len(description),'regeneration_exact':True,'qa_replay':checks}),flush=True)

if __name__=='__main__':main()
