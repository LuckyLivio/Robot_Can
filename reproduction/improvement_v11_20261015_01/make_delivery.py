"""Freeze completed v11 artifacts after experimental and actual browser validation."""
from pathlib import Path
import hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
WEB=ROOT/'reproduction/progress_v11_20261015_01'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))

if __name__=='__main__':
    old=read(RUN/'before_manifest.json');valid={}
    for name in ['mechanisms_a.json','guards_a.json','smoke_a_verification.json','pilot_a_verification.json','pilot_a_physics.json','dev_a_verification.json','development_physics.json','development_regression_diagnosis.json']:
        p=RUN/'analysis'/name;assert read(p)['passed'];valid[name]=sha(p)
    frozen=read(RUN/'protocols/development_freeze.json')['source_sha256']
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    experiments={}
    for stage in ['smoke_a','pilot_a','dev_a']:
        assert (RUN/stage/'completed.json').is_file()
        experiments[stage]=sum(len(read(p)['records']) for p in (RUN/stage).glob('*/result.json'))
    assert experiments=={'smoke_a':9,'pilot_a':148,'dev_a':240}
    receipt=read(RUN/'analysis/final_receipt.json')
    assert receipt['actual_executions_total']==397 and not receipt['adopted']
    assert read(WEB/'frontend_validation.json')['passed'] and read(WEB/'edge_replay_validation.json')['passed']
    browser={'passed':True,'url':'http://127.0.0.1:8766/reproduction/progress_v11_20261015_01/demo/index.html#latest',
        'observed_checks':['root redirect to v11','final status: local repair, development regression, not adopted','expanded four-variant pilot table','expanded all eight development conditions:236/240 vs235/240','actual click played new video; currentTime advanced from0.223776 to21.05 and ended true','new video dimensions960x660,duration21.05','both new evidence PNGs loaded at2240x1280 and1760x1280','no browser console errors observed'],
        'screenshot':'frontend_preview.jpg','screenshot_sha256':sha(WEB/'frontend_preview.jpg'),
        'scope':'Actual IAB interaction. Encoded20fps and exact physics replay checked separately; no browser dropped-frame measurement claim.'}
    with (WEB/'browser_validation.json').open('x') as f:json.dump(browser,f,indent=2)
    summary={'complete':True,'experiment_runs':experiments,'total_executions':sum(experiments.values()),'dev_240_launched':True,'adopted':False,'independent_confirmation_launched':False,
        'outcome':'Known wall-edge success at380;31/37 vs v10 30/37, equal historical v6. Development235/240 vs v6 236/240. Inherited held-object waiting failure; preserve main v5.',
        'old_paths':len(old),'old_pt_weights':sum(p.endswith('.pt') for p in old),'validation_sha256':valid,
        'frozen_source_sha256':frozen,'physical_outcomes_source':'Unchanged stage source snapshots; no execution-time controller revision.',
        'metadata_note':'Evaluator supervisor_note inherits v9/v10-family wording; v11 also reads current seven joint angles. Runtime/config evidence takes precedence; archived records not rewritten.',
        'scope':'No new training or paper. Replays and video rendering do not add efficacy samples.'}
    with (RUN/'analysis/completion_receipt.json').open('x') as f:json.dump(summary,f,indent=2)
    files=[ROOT/'README.md',ROOT/'index.html']
    for folder in [RUN,WEB]:files.extend(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ['delivery_manifest.json','integrity_receipt.json'])
    manifest={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)}
    with (RUN/'delivery_manifest.json').open('x') as f:json.dump(manifest,f,indent=2)
    print(json.dumps({'delivery':len(manifest),'protected':len(old),'weights':summary['old_pt_weights'],'executions':summary['total_executions']}))
