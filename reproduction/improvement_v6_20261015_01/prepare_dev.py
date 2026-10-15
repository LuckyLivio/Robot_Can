"""Freeze pilot-selected combined controller before the paired 240-episode run."""
from pathlib import Path
from dataclasses import asdict
import copy,datetime,hashlib,json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from recovery.recovery_controller import Config

def main():
    pilot=json.loads((RUN/'analysis/pilot_b.json').read_text())
    assert pilot['complete'] and not pilot['variants']['v6']['regressions']
    for name in ['pilot_b_verification','pilot_b_physics','mechanisms_b','guard_unit_checks_b']:
        assert json.loads((RUN/'analysis'/f'{name}.json').read_text())['passed']
    old=ROOT/'reproduction/recovery_v5_20261012_01'
    jobs=[]
    for b in json.loads((old/'dev_jobs.json').read_text()):
        if b['version']!='v5':continue
        j=copy.deepcopy(b);j['id']='v6'+j['id'][2:];j['version']='v6';j['steps']=400
        j['config']=asdict(Config(**b['config']));jobs.append(j)
    assert len(jobs)==8 and sum(len(j['demos']) for j in jobs)==240
    files=list((RUN/'recovery').glob('*.py'))+[RUN/n for n in ['evaluate_recovery.py','variants.py','run_batch.py']]
    files += [ROOT/'common.py',ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt',ROOT/'data/can_ph_lowdim_v15.hdf5',ROOT/'data/splits.json']
    files += [ROOT/f'models/multiseed_20261012_01_full_s{s}/model.pt' for s in [17,23,41]]
    files += [old/'recovery_controller.py',old/'clearance.py',old/'gripper_geometry.json']
    files += [old/'dev_a'/('v5'+j['id'][2:])/name for j in jobs for name in ['result.json','trace.jsonl']]
    hashes={f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    with (RUN/'protocols/dev_jobs.json').open('x',encoding='utf8') as f:json.dump(jobs,f,indent=2)
    lock={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'selected':'pilot_b_combined_v6','sha256':hashes,
          'pilot_successes':31,'pilot_baseline_successes':29,'pilot_episodes_per_variant':37,'protected_regressions':0,
          'development_episodes':240,'baseline':'frozen v5 dev_a, paired same starts/noise/weights/400 steps',
          'scope':'Known development set, not independent confirmation. Do not adjust controller after viewing dev results.'}
    with (RUN/'protocols/dev_lock.json').open('x',encoding='utf8') as f:json.dump(lock,f,indent=2)
    print(json.dumps({k:v for k,v in lock.items() if k!='sha256'}),flush=True)
if __name__=='__main__':main()
