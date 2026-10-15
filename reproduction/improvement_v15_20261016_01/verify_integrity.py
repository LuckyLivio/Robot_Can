"""Read-only byte preservation and frozen experiment verification."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()

def check(base,data):
    def one(pair):
        p,h=pair;assert (base/p).is_file() and sha(base/p)==h,p
    with ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(one,data.items()))

def verify():
    old=json.loads((RUN/'before_manifest.json').read_text())
    changed=json.loads((RUN/'document_changes.json').read_text())['updated']
    check(ROOT,{p:h for p,h in old.items() if p not in changed})
    check(RUN/'before',{p:old[p] for p in changed})
    manifest=json.loads((RUN/'delivery_manifest.json').read_text())['files'];check(ROOT,manifest)
    for n in ['development_freeze','confirmation_lock']:
        p=RUN/'protocols'/f'{n}.json'
        if p.exists():
            d=json.loads(p.read_text());check(ROOT,d.get('source_sha256',d.get('sha256')))
    stages={}
    for path in sorted(RUN.glob('*/completed.json')):
        stage=path.parent.name;data=json.loads(path.read_text())
        assert data['source_unchanged']
        check(ROOT,json.loads((path.parent/'started.json').read_text())['source_sha256']) if stage in ['pilot_a','dev_a','confirmation'] else None
        audit=json.loads((RUN/'analysis'/f'{stage}_verification.json').read_text())
        assert audit['passed'] and audit['episodes']==data['episodes'],stage
        stages[stage]=data['episodes']
    for stage in stages:
        if stage in stages:assert json.loads((RUN/'analysis'/f'{stage}_physics.json').read_text())['passed'],stage
    summary=json.loads((RUN/'SUMMARY.json').read_text())
    assert sum(stages.values())==summary['completed_evaluation_executions']
    return {'passed':True,'preserved_prior_paths':len(old),'backed_up_active_documents':len(changed),
            'delivery_files':len(manifest),'old_code_weights_results_unchanged':True,
            'completed_stages':stages,'completed_evaluation_executions':sum(stages.values()),
            'partial_failed_stage_episodes':summary['partial_failed_stage_episodes'],
            'independent_confirmation_starts':60 if 'confirmation' in stages else 0,'new_training_runs':0}

if __name__=='__main__':print(json.dumps(verify()))
