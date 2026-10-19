"""Seal final protocol and runtime after preflight, before any new physics."""
from pathlib import Path
import argparse,datetime,hashlib,json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))
def verify_protocol_lock():
    path=RUN/'protocols/protocol_lock.json';lock=read(path)
    assert lock['locked_before_new_physics'] and lock['versions']==['v19','v20','budget','recenter','place','v21']
    assert lock['smoke_executions']==54 and lock['pilot_executions']==564
    assert lock['inherited_fields']==111 and lock['new_fields']==2
    assert lock['step_budget']==400 and lock['delay']==2 and lock['max_attempts']==2
    assert lock['mechanism_receipts'] and lock['source_sha256']
    for rel,digest in lock['source_sha256'].items():assert sha(ROOT/rel)==digest,('Protocol/runtime changed after lock',rel)
    return path
def main():
    from run_batch import runtime_dependencies,verify_mechanism_receipt,checked_receipt_sources
    parser=argparse.ArgumentParser();parser.add_argument('--mechanisms',default='mechanisms_a');parser.add_argument('--components',default='components_a')
    parser.add_argument('--transition-static',default='transition_static_a');parser.add_argument('--place-static',default='place_scope_static_b');args=parser.parse_args()
    path=RUN/'protocols/protocol_lock.json';assert not path.exists()
    assert (RUN/'protocols/PLAN.md').is_file(),'Final protocol must exist; draft alone cannot authorize physics'
    assert not any(RUN.glob('*/started.json')),'Cannot declare a pre-experiment lock after physical evaluation started'
    assert not any((RUN/'protocols'/name).exists() for name in ['dev_jobs.json','development_freeze.json','confirmation_lock.json'])
    smoke=read(RUN/'protocols/smoke_jobs.json');pilot=read(RUN/'protocols/pilot_jobs.json')
    versions=['v19','v20','budget','recenter','place','v21']
    assert {job['version'] for job in smoke}==set(versions)=={job['version'] for job in pilot}
    for group,total in [(smoke,9),(pilot,94)]:
        assert all(sum(len(job['demos']) for job in group if job['version']==version)==total for version in versions)
    receipts=[verify_mechanism_receipt(name) for name in [args.mechanisms,args.components,args.transition_static,args.place_static]]
    off=read(receipts[0]);assert off['inherited_config_fields']==111 and off['disabled_episodes']==9 and off['disabled_controls']==3423
    paths=set(runtime_dependencies(pilot))|set(receipts)
    paths|={ROOT/rel for receipt in receipts for rel in checked_receipt_sources(read(receipt))}
    paths|={p for p in (RUN/'recovery').iterdir() if p.suffix in ['.py','.json']}
    paths|={RUN/name for name in ['evaluate_recovery.py','variants.py','run_batch.py','lock_protocol.py','protocols/PLAN.md','protocols/smoke_jobs.json','protocols/pilot_jobs.json']}
    assert all(p.is_file() for p in paths)
    lock={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'locked_before_new_physics':True,
          'versions':versions,'smoke_executions':54,'pilot_executions':564,'inherited_fields':111,'new_fields':2,
          'step_budget':400,'delay':2,'max_attempts':2,
          'mechanism_receipts':[p.relative_to(ROOT).as_posix() for p in receipts],
          'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)},
          'note':'Registration and source lock only; no outcome claim, new state generation, development or confirmation authorization.'}
    with path.open('x',encoding='utf8') as stream:json.dump(lock,stream,indent=2)
    verify_protocol_lock();print('Final v21 protocol and all runtime dependencies locked; no physical execution performed.')
if __name__=='__main__':main()
