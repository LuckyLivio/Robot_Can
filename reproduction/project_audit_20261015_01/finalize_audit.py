"""Finalize audit receipts and protect both current guides and immutable old evidence."""
from pathlib import Path
import hashlib,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
    with p.open('x',encoding='utf8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
if __name__=='__main__':
    passed=['syntax.json','json_validation.json','jsonl_validation.json','binary_numeric_assets.json','environment_and_inference.json','handoff_verification.json','media_validation.json','zip_validation.json','contracts.json','statistics_validation.json','active_document_validation.json']
    for n in passed:assert read(RUN/n)['passed'],n
    results=read(RUN/'result_validation.json');assert len(results['issues'])==3 and all('improvement_v7_20261015_01/pilot_a/' in x['path'] for x in results['issues'])
    assert all(not j['missing'] for j in read(RUN/'job_output_validation.json'))
    fsck=(RUN/'git_fsck.txt').read_text(encoding='utf-8-sig')
    assert all(not l.strip() or l.startswith('dangling ') for l in fsck.splitlines())
    browser={'passed':True,'url':'http://127.0.0.1:8766/reproduction/project_audit_20261015_01/index.html',
        'observed_checklist_rows':26,'heading_observed':True,'console_errors':0,'screenshot':'audit_preview.jpg','screenshot_sha256':digest(RUN/'audit_preview.jpg'),
        'scope':'Actual IAB rendering of new audit dashboard; HTTP and local links checked separately. Existing v11 demo bytes unchanged.'}
    write(RUN/'browser_validation.json',browser)
    completion={'complete':True,'baseline_commit':read(RUN/'inventory_summary.json')['git_head'],'historical_tracked_files':10146,
        'checklist_items':26,'active_documents_updated_or_added':len(read(RUN/'document_changes.json')['updated_or_added']),
        'new_training_steps':0,'new_simulation_episodes':0,'single_observation_model_forward_checks':7,'files_deleted':0,
        'historical_results_rewritten':0,'historical_controller_changes':0,'main_recovery_version':'v5','latest_candidate':'v11, not adopted',
        'verification_receipt_sha256':{n:digest(RUN/n) for n in passed},
        'open_scope':['Inherited held-object waiting bug','World-model generalization and independent ranking advantage','Second-device clean installation','Updated v6-v11 portable handoff supplement','Formal manuscript and advisor requirements'],
        'notes':['Three incomplete v7 pilot_a records are intentional failure archives superseded by complete pilot_b.','No claim of exhaustive behavioral proof or real-robot validity.','Original desktop source weights are absent; repository copies match archived replacement hashes.']}
    write(RUN/'completion_receipt.json',completion)
    files=[ROOT/p for p in read(RUN/'document_changes.json')['updated_or_added']]
    files += [p for p in RUN.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ['delivery_manifest.json','integrity_receipt.json']]
    write(RUN/'delivery_manifest.json',{p.relative_to(ROOT).as_posix():digest(p) for p in sorted(set(files))})
    print(json.dumps({'delivery_files':len(set(files)),'historical':10146,'docs':completion['active_documents_updated_or_added'],'deleted':0,'new_episodes':0}))
