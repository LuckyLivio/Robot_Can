"""Freeze v14 only after small-test/ablation outcome and verification gates pass."""
from pathlib import Path
import argparse,copy,datetime,hashlib,json,sys
from dataclasses import asdict
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery.recovery_controller import Config
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import Config as ParentConfig
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--smoke',default='smoke_b');p.add_argument('--pilot',default='pilot_a');p.add_argument('--mechanisms',default='mechanisms_b');a=p.parse_args()
    assert read(RUN/'analysis'/f'{a.smoke}.json')['outcome_gate_passed'],'Small-test outcome gate failed; development remains disabled'
    for n in [a.mechanisms,a.smoke+'_verification',a.smoke+'_physics',a.pilot+'_verification',a.pilot+'_physics']:
        assert read(RUN/'analysis'/f'{n}.json')['passed'],n
    for stage in [a.smoke,a.pilot]:assert read(RUN/'analysis'/f'{stage}.json')['outcome_gate_passed'],stage
    pilot=read(RUN/a.pilot/'jobs.json');cfg=asdict(Config(**next(j['config'] for j in pilot if j['version']=='v14')))
    parent=asdict(ParentConfig(**next(j['config'] for j in pilot if j['version']=='v13')))
    assert all(cfg[k]==v for k,v in parent.items()),'Inherited protection or control parameter changed'
    assert cfg['horizon_steps']==400 and cfg['max_attempts']==2 and cfg['delay']==2
    jobs=[]
    for b in read(ROOT/'reproduction/improvement_v6_20261015_01/protocols/dev_jobs.json'):
        assert all(cfg[k]==v for k,v in b['config'].items())
        suffix=b['id'].split('_',1)[1]
        j=copy.deepcopy(b);j.update(id='v14_'+suffix,version='v14',config=cfg.copy(),steps=400)
        j['baseline_result_v6']=f"reproduction/improvement_v6_20261015_01/dev_a/{b['id']}/result.json"
        j['baseline_result_v13']=f"reproduction/improvement_v13_20261016_01/dev_a/v13_{suffix}/result.json"
        assert (ROOT/j['baseline_result_v13']).is_file();jobs.append(j)
    assert sum(len(j['demos']) for j in jobs)==240
    with (RUN/'protocols/dev_jobs.json').open('x',encoding='utf8') as f:json.dump(jobs,f,indent=2)
    sources=[p for p in (RUN/'recovery').iterdir() if p.suffix in ['.py','.json']]
    sources += [RUN/n for n in ['evaluate_recovery.py','variants.py','run_batch.py','protocols/dev_jobs.json']]
    sources += list((ROOT/'reproduction').glob('improvement_v[6789]_*/recovery/*.py'))
    sources += list((ROOT/'reproduction').glob('improvement_v[6789]_*/recovery/*.json'))
    for v in [10,11,12]:sources+=list((ROOT/f'reproduction/improvement_v{v}_20261015_01/recovery').glob('*.*'))
    sources += list((ROOT/'reproduction/improvement_v13_20261016_01/recovery').glob('*.*'))
    sources += list((ROOT/'reproduction/recovery_v5_20261012_01').glob('*.py'))
    sources += [ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt']
    sources += [ROOT/f'models/multiseed_20261012_01_full_s{s}/model.pt' for s in [17,23,41]]
    sources += [ROOT/n for n in ['common.py','world_model.py','reproduction/extensions_20261012_01/evaluate.py']]
    sources=sorted(set(p for p in sources if p.is_file()))
    lock={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gate_passed':True,'config':cfg,
          'gate_stages':{'smoke':a.smoke,'pilot':a.pilot,'mechanisms':a.mechanisms},
          'inherited_config_unchanged':True,'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sources},'episodes':240,
          'note':'Frozen for development. Independent confirmation requires the development gate plus a separate pre-state lock.'}
    with (RUN/'protocols/development_freeze.json').open('x',encoding='utf8') as f:json.dump(lock,f,indent=2)
    print('Frozen development: 240 episodes')
