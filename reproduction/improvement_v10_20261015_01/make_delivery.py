from pathlib import Path
import hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];WEB=ROOT/'reproduction/progress_v10_20261015_01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
if __name__=='__main__':
    old=read(RUN/'before_manifest.json');valid={}
    for name in ['mechanisms_a.json','mechanisms_b.json','guards_b.json','smoke_a_verification.json','smoke_b_verification.json','pilot_a_verification.json','pilot_a_current_verification.json','pilot_a_physics.json','guard_timing_microbenchmark.json']:
        p=RUN/'analysis'/name;assert read(p)['passed'];valid[name]=sha(p)
    current=read(RUN/'analysis/pilot_a_current_verification.json')['current_source_sha256']
    assert all(sha(RUN/p)==h for p,h in current.items())
    assert read(WEB/'frontend_validation.json')['passed']
    browser={'passed':True,'url':'http://127.0.0.1:8766/reproduction/progress_v10_20261015_01/demo/index.html#latest',
        'observed_checks':['root redirect to v10','status not adopted and no development run','expanded comparison table: four variants 30/37','expanded trajectory PNG loaded at 2240x1600','no browser console errors observed','historical video labels retained'],
        'screenshot':'frontend_preview.jpg','screenshot_sha256':sha(WEB/'frontend_preview.jpg'),'scope':'Actual desktop IAB interaction; video bytes checked separately, no claim of measured dropped frames.'}
    with (WEB/'browser_validation.json').open('x') as f:json.dump(browser,f,indent=2)
    summary={'complete':True,'experiment_runs':{'smoke_a':9,'smoke_b':9,'pilot_a':148},'total_executions':166,'dev_240_launched':False,'adopted':False,
        'outcome':'No success-rate gain; preserve main v5 and all old assets. Wall-edge approach reached, premature can-finger contact remains.',
        'old_paths':len(old),'old_pt_weights':sum(p.endswith('.pt') for p in old),'validation_sha256':valid,
        'current_controller_sha256':current,'physical_outcomes_source':'pilot_a/source (before timing-only guard short circuit)',
        'metadata_note':'Archived evaluator payload used inherited wording about v9-only joint inputs. All three v10-family variants also read the same current seven joint angles, as their code/traces show; current wording corrected without rewriting archived evidence.'}
    with (RUN/'analysis/completion_receipt.json').open('x') as f:json.dump(summary,f,indent=2)
    files=[ROOT/'README.md',ROOT/'index.html']
    for folder in [RUN,WEB]:files.extend(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ['delivery_manifest.json','integrity_receipt.json'])
    manifest={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)}
    with (RUN/'delivery_manifest.json').open('x') as f:json.dump(manifest,f,indent=2)
    print('delivery',len(manifest),'protected',len(old),'weights',summary['old_pt_weights'])
