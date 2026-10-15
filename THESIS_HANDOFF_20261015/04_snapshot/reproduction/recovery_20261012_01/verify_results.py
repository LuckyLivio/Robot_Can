"""Verify preservation, frozen inputs, every logged control, and physical replay samples."""
import argparse,datetime,json,sys
from pathlib import Path
from setup_study import ROOT,RUN,digest,write
from audit_traces import audit
import numpy as np


def physical_replay(jobs):
    import h5py
    sys.path.insert(0,str(ROOT))
    from common import DATA,make_env,restore_demo,pack_obs
    selected=[]
    for noise in [0.,.05]:
        for method in ['bc_k2','full']:
            job=next(j for j in jobs if j['noise']==noise and j['method']==method)
            records=json.loads((RUN/'formal'/job['id']/'result.json').read_text())['records']
            # Fixed selection rule: first failure; if none, first intervention.
            row=next((r for r in records if not r['success']),next((r for r in records if r['attempts']),records[0]))
            selected.append((job,row['demo']))
    env=make_env(False);out=[]
    try:
        with h5py.File(DATA) as data:
            for job,name in selected:
                obs=restore_demo(env,data['data'][name]);maximum=0.;count=0
                for line in (RUN/'formal'/job['id']/'trace.jsonl').open():
                    r=json.loads(line)
                    if r['demo']!=name:continue
                    np.testing.assert_array_equal(pack_obs(obs),r['state_before'])
                    obs,*_=env.step(np.asarray(r['executed_action'],np.float32));after=pack_obs(obs)
                    maximum=max(maximum,float(np.max(np.abs(after-np.asarray(r['state_after'])))))
                    np.testing.assert_array_equal(after,r['state_after']);count+=1
                    assert bool(env._check_success())==r['success_after']
                out.append({'job':job['id'],'demo':name,'steps':count,'maximum_state_error':maximum})
    finally:env.close()
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--receipt',default='final_validation.json');a=p.parse_args()
    before=json.loads((RUN/'before_manifest.json').read_text());bad=[name for name,sha in before.items() if not (ROOT/name).is_file() or digest(ROOT/name)!=sha]
    assert not bad,{'old_files_changed':bad}
    lock=json.loads((RUN/'frozen_protocol.json').read_text());assert all(digest(ROOT/name)==sha for name,sha in lock['sha256'].items())
    for path in RUN.glob('*.py'):compile(path.read_text(encoding='utf-8'),str(path),'exec')
    assert json.loads((RUN/'formal/completed.json').read_text())['episodes']==240
    jobs=json.loads((RUN/'formal_jobs.json').read_text());audits=[];complete=0
    for job in jobs:
        directory=RUN/'formal'/job['id'];r=json.loads((directory/'result.json').read_text())
        assert r['job']==job and not job.get('fault') and job['enabled']
        audits.append(audit(directory));complete+=len(r['records'])
        grouped={}
        for line in (directory/'trace.jsonl').open():
            t=json.loads(line);grouped.setdefault(t['demo'],[]).append(t)
            assert not t['fault_injected']
        for episode in r['records']:
            traces=grouped[episode['demo']]
            assert len(traces)==episode['steps'] and traces[-1]['success_after']==episode['success']
            assert not any(t['success_after'] for t in traces[:-1])
        print(json.dumps({'validated':job['id'],'controls':audits[-1]['controls']}),flush=True)
    assert complete==240
    replays=physical_replay(jobs)
    manifest={p.relative_to(RUN).as_posix():digest(p) for p in (RUN/'formal').rglob('*') if p.is_file()}
    result={'passed':True,'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'protected_old_files_unchanged':len(before),'frozen_inputs_unchanged':len(lock['sha256']),
            'completed_episodes':complete,'trace_controls_checked':sum(r['controls'] for r in audits),
            'trace_audits':audits,'physical_replays':replays,'formal_output_sha256':manifest}
    path=RUN/a.receipt;assert path.parent.resolve()==RUN.resolve();write(path,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['trace_audits','formal_output_sha256']},indent=2),flush=True)

if __name__=='__main__':main()
