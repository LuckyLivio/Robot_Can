"""Require completed diagnostic gates before 240 paired conditions / 720 runs."""
from pathlib import Path
from dataclasses import asdict
import argparse,copy,datetime,hashlib,json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from recovery.recovery_controller import Config
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import Config as ParentConfig
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import Config as C14
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def verify_stage(stage, expected):
    """Require outcome, every decision, and the registered physical replay set."""
    folder=RUN/stage;analysis=read(RUN/'analysis'/f'{stage}.json')
    assert analysis['stage']==stage and analysis['outcome_gate_passed'],stage
    jobs=read(folder/'jobs.json');started=read(folder/'started.json');completed=read(folder/'completed.json')
    assert len({j['id'] for j in jobs})==len(jobs)
    assert sum(len(j['demos']) for j in jobs)==expected
    assert analysis['evaluated_executions']==completed['episodes']==started['episodes']==expected
    assert completed['source_unchanged']
    assert sha(folder/'jobs.json')==started['jobs_sha256']
    for rel,h in started['dependency_sha256'].items():assert sha(ROOT/rel)==h,(stage,rel,'Dependency changed since test')
    for rel,h in started['source_sha256'].items():
        assert sha(ROOT/rel)==h,(stage,rel,'Untested source change')
        archive=folder/'source'/Path(rel).relative_to(RUN.relative_to(ROOT))
        assert sha(archive)==h,(stage,rel,'Archived source changed')
    selected={};controls=0
    events=['wait_hold_events','support13_events','escape_events','tracking14_events','clearance14_events','carry15_events','edge15_events','budget15_events','ik16_events','held16_events','edge16_events']
    for j in jobs:
        result=read(folder/j['id']/'result.json');rows=result['records']
        assert result['status']=='complete' and result['job']==j
        assert [r['demo'] for r in rows]==j['demos']
        assert all(0<r['steps']<=400 for r in rows)
        controls+=sum(r['steps'] for r in rows)
        names={rows[0]['demo']}|{r['demo'] for r in rows if not r['success'] or any(r.get(k) for k in events)}
        selected.update({(j['id'],r['demo']):r['steps'] for r in rows if r['demo'] in names})
    decision=read(RUN/'analysis'/f'{stage}_verification.json')
    assert decision['passed'] and decision['stage']==stage and decision['source_snapshot_verified']
    assert decision['episodes']==expected and decision['controls']==controls
    physics=read(RUN/'analysis'/f'{stage}_physics.json')
    assert physics['passed'] and physics['stage']==stage
    actual={(r['job'],r['demo']):r['steps'] for r in physics['samples']}
    assert len(actual)==len(physics['samples'])==physics['episodes']
    assert actual==selected and physics['steps']==sum(selected.values()),(stage,'Incomplete physical replay')
    return [folder/'jobs.json',folder/'started.json',folder/'completed.json',RUN/'analysis'/f'{stage}.json',RUN/'analysis'/f'{stage}_verification.json',RUN/'analysis'/f'{stage}_physics.json']
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--smoke',default='smoke_a');p.add_argument('--pilot',default='pilot_a');p.add_argument('--mechanisms',default='mechanisms_a');p.add_argument('--components',default='components_a');a=p.parse_args()
    evidence=[]
    for stage,expected in [(a.smoke,63),(a.pilot,658)]:evidence+=verify_stage(stage,expected)
    for name in [a.mechanisms,a.components]:
        receipt=read(RUN/'analysis'/f'{name}.json');assert receipt['passed'],name
        assert receipt['source_sha256'],(name,'Missing checked sources')
        for rel,h in receipt['source_sha256'].items():assert sha(ROOT/rel)==h,(name,rel,'Mechanism check is stale')
        evidence.append(RUN/'analysis'/f'{name}.json')
    pilot=read(RUN/a.pilot/'jobs.json');parents={j['id'].split('_',1)[1]:j for j in pilot if j['version']=='v15'}
    for j in pilot:
        suffix=j['id'].split('_',1)[1];old=asdict(ParentConfig(**parents[suffix]['config']))
        if j['version'] in ['v14','v15','budget']:continue
        current=asdict(Config(**j['config']));assert all(current[k]==v for k,v in old.items()),(j['id'],'Inherited parameter changed')
    base=next(j for j in pilot if j['version']=='v16' and j.get('comparison_profile')=='standard')
    cfg=asdict(Config(**base['config']));parent=asdict(ParentConfig(**parents[base['id'].split('_',1)[1]]['config']))
    assert cfg['horizon_steps']==400 and cfg['max_attempts']==2 and cfg['delay']==2
    jobs=[]
    baseline14=next(j for j in pilot if j['version']=='v14' and j['id'].split('_',1)[1]==base['id'].split('_',1)[1])
    config14=asdict(C14(**baseline14['config']))
    for version,version_config in [('v14',config14),('v15',parent),('v16',cfg)]:
        for b in read(ROOT/'reproduction/improvement_v6_20261015_01/protocols/dev_jobs.json'):
            assert all(version_config[k]==v for k,v in b['config'].items())
            suffix=b['id'].split('_',1)[1];j=copy.deepcopy(b)
            j.update(id=version+'_'+suffix,version=version,config=version_config.copy(),steps=400,comparison_profile='standard')
            j['baseline_result_v6']=f"reproduction/improvement_v6_20261015_01/dev_a/{b['id']}/result.json"
            j['baseline_result_v13']=f"reproduction/improvement_v13_20261016_01/dev_a/v13_{suffix}/result.json"
            for ref in ['v14','v15','budget']:j.pop('baseline_result_'+ref,None)
            assert (ROOT/j['baseline_result_v13']).is_file();jobs.append(j)
    assert len(jobs)==24 and sum(len(j['demos']) for j in jobs)==720
    assert all(sum(len(j['demos']) for j in jobs if j['version']==v)==240 for v in ['v14','v15','v16'])
    assert not (RUN/'protocols/dev_jobs.json').exists() and not (RUN/'protocols/development_freeze.json').exists(),'Development registration already exists'
    with (RUN/'protocols/dev_jobs.json').open('x',encoding='utf8') as f:json.dump(jobs,f,indent=2)
    sources=[p for p in (RUN/'recovery').iterdir() if p.suffix in ['.py','.json']]
    sources += [RUN/n for n in ['evaluate_recovery.py','variants.py','run_batch.py','protocols/dev_jobs.json','audit_core.py','verify_run.py','verify_physics.py','verify_mechanisms.py','verify_components.py','analyze.py','freeze_development.py','protocols/PLAN.md']]
    sources += evidence
    sources += list((ROOT/'reproduction').glob('improvement_v[6789]_*/recovery/*.py'))
    sources += list((ROOT/'reproduction').glob('improvement_v[6789]_*/recovery/*.json'))
    for v in [10,11,12]:sources+=[p for p in (ROOT/f'reproduction/improvement_v{v}_20261015_01/recovery').iterdir() if p.suffix in ['.py','.json']]
    for v in [13,14,15]:sources+=[p for p in (ROOT/f'reproduction/improvement_v{v}_20261016_01/recovery').iterdir() if p.suffix in ['.py','.json']]
    sources += list((ROOT/'reproduction/recovery_v5_20261012_01').glob('*.py'))
    sources += [ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt']+[ROOT/f'models/multiseed_20261012_01_full_s{s}/model.pt' for s in [17,23,41]]
    sources += [ROOT/n for n in ['common.py','world_model.py','reproduction/extensions_20261012_01/evaluate.py']]
    assert all(p.is_file() for p in sources),'Required runtime/evidence/weight file missing'
    sources=sorted(set(sources))
    lock={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gate_passed':True,'config':cfg,'parent_config':parent,
          'gate_stages':{'smoke':a.smoke,'pilot':a.pilot,'mechanisms':a.mechanisms,'components':a.components},'inherited_config_unchanged':True,
          'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sources},'episodes':720,
          'versions':['v14','v15','v16'],'paired_conditions_per_version':240,'episodes_by_version':{'v14':240,'v15':240,'v16':240},
          'note':'240 common conditions, three freshly executed versions = 720 runs. Independent confirmation requires development gate and a separate pre-state lock.'}
    with (RUN/'protocols/development_freeze.json').open('x',encoding='utf8') as f:json.dump(lock,f,indent=2)
    print('Frozen development: v14 240 + v15 240 + v16 240 = 720 paired executions')
