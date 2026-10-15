from pathlib import Path
import copy,datetime,hashlib,json,sys
from dataclasses import asdict
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery.recovery_controller import Config
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    for n in ['mechanisms_a','smoke_a_verification','smoke_a_physics','pilot_a_verification','pilot_a_physics']:
        assert json.loads((RUN/'analysis'/f'{n}.json').read_text())['passed'],n
    assert json.loads((RUN/'analysis/pilot_a.json').read_text())['outcome_gate_passed']
    pilot=json.loads((RUN/'pilot_a/jobs.json').read_text());cfg=asdict(Config(**next(j['config'] for j in pilot if j['version']=='v12')))
    jobs=[]
    for b in json.loads((ROOT/'reproduction/improvement_v6_20261015_01/protocols/dev_jobs.json').read_text()):
        assert all(cfg[k]==v for k,v in b['config'].items())
        j=copy.deepcopy(b);j.update(id='v12_'+b['id'].split('_',1)[1],version='v12',config=cfg.copy(),steps=400)
        j['baseline_result_v6']=f"reproduction/improvement_v6_20261015_01/dev_a/{b['id']}/result.json";jobs.append(j)
    assert sum(len(j['demos']) for j in jobs)==240
    with (RUN/'protocols/dev_jobs.json').open('x') as f:json.dump(jobs,f,indent=2)
    sources=list((RUN/'recovery').glob('*.py'))+[RUN/n for n in ['evaluate_recovery.py','variants.py','run_batch.py','protocols/dev_jobs.json']]
    # Freeze every inherited controller and local scene/kinematics asset too.
    sources+=list((ROOT/'reproduction').glob('improvement_v[6789]_*/recovery/*.py'))
    for v in [10,11]:sources+=list((ROOT/f'reproduction/improvement_v{v}_20261015_01/recovery').glob('*.py'))
    sources+=list((ROOT/'reproduction/recovery_v5_20261012_01').glob('*.py'))
    sources+=list((ROOT/'reproduction').glob('improvement_v[6789]_*/recovery/*.json'))
    sources += [ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt']
    sources += [ROOT/f'models/multiseed_20261012_01_full_s{s}/model.pt' for s in [17,23,41]]
    sources += [ROOT/n for n in ['common.py','world_model.py','reproduction/extensions_20261012_01/evaluate.py']]
    lock={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gate_passed':True,'config':cfg,
          'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sources},'episodes':240,
          'note':'Frozen for development. Independent confirmation requires the development gate plus a separate pre-state lock.'}
    with (RUN/'protocols/development_freeze.json').open('x') as f:json.dump(lock,f,indent=2)
    print('Frozen development: 240 episodes')
