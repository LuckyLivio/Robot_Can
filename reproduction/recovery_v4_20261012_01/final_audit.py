"""Final archival check; this is not promotion or an independent-test freeze."""
import ast,datetime,json,re
from setup_study import ROOT,RUN,write,digest
def main():
    before=json.loads((RUN/'before_manifest.json').read_text())
    for name,sha in before.items():assert (ROOT/name).is_file() and digest(ROOT/name)==sha,name
    a=json.loads((RUN/'validation_pilot_a.json').read_text())
    b=json.loads((RUN/'pilot_acceptance.json').read_text())
    dev=json.loads((RUN/'validation_dev_a.json').read_text())
    promotion=json.loads((RUN/'promotion_dev_a.json').read_text())
    probes=json.loads((RUN/'mechanism_physics.json').read_text())
    assert a['passed'] and b['passed'] and dev['passed'] and not promotion['passed']
    assert promotion['study_plan_sha256']==digest(RUN/'study_plan.json')
    for path,sha in json.loads((RUN/'dev_a/started.json').read_text())['sha256'].items():assert digest(ROOT/path)==sha,path
    for path,sha in dev['outputs_sha256'].items():assert digest(RUN/path)==sha,path
    for name,sha in b['source_sha256'].items():assert digest(RUN/name)==sha,name
    for stage in ['pilot_a','pilot_b','dev_a']:
        jobs=json.loads((RUN/stage/'jobs.json').read_text())
        for job in jobs:
            r=json.loads((RUN/stage/job['id']/'result.json').read_text());assert r['status']=='complete' and r['job']==job
            assert [e['demo'] for e in r['records']]==job['demos']
    absent=['promotion.json','freeze_before_states.json','confirmation_starts.hdf5','geometry_starts.hdf5','confirmation_lock.json','confirmation','geometry_confirmation']
    for name in absent:assert not (RUN/name).exists(),name
    for p in RUN.glob('*.py'):ast.parse(p.read_text())
    for p in RUN.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if target=='delivery_validation.json':continue
            assert (p.parent/target).is_file(),(p.name,target)
    steps=a['control_steps']+b['verified_control_steps']+dev['controls_checked']
    episodes=a['episodes']+b['verified_episodes']+dev['episodes']
    assert steps==168058 and episodes==920
    physics=b['physical_replays']+dev['physical_replays']
    assert all(p['max_state_error']==0 for p in physics) and all(p['physics_replay_exact'] for p in probes['results'])
    protected_names=[str(p.relative_to(ROOT)).replace('\\','/') for p in ROOT.glob('reproduction/recovery_v[23]_20261012_01/recovery_controller.py')]
    result={'passed':True,'audited_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'old_files_unchanged':len(before),
        'evaluated_episodes':episodes,'control_steps_verified':steps,'physics_replay_count':len(physics)+len(probes['results']),
        'physical_observation_max_error':0.,'v2_formal_baseline_reused_episodes':240,
        'dev_counts':json.loads((RUN/'analysis_dev_a/summary.json').read_text())['totals'],
        'promotion_passed':False,'independent_confirmation_run':False,'reason':'No candidate reached the prospectively registered 232/240 total-success gate.',
        'no_heldout_states_generated':True,'old_weights_and_results_preserved':True,
        'preservation_excludes':['.venv','.git','.idea','__pycache__'],
        'artifacts_sha256':{p.relative_to(RUN).as_posix():digest(p) for p in RUN.rglob('*') if p.is_file() and '__pycache__' not in p.parts}}
    write(RUN/'delivery_validation.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='artifacts_sha256'},indent=2),flush=True)
if __name__=='__main__':main()
