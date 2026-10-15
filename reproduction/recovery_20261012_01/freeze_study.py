"""Validate the training pilot, then preregister the development comparison."""
import datetime,importlib.metadata,json
from dataclasses import asdict
from setup_study import ROOT,RUN,digest,write
from recovery_controller import Config
from audit_traces import audit


def main():
    qa=json.loads((RUN/'small_validation/validation.json').read_text());assert qa['passed']
    for name,sha in qa['source_sha256'].items():assert digest(RUN/name)==sha
    assert json.loads((RUN/'extra_pilot/validation.json').read_text())['passed']
    original=json.loads((RUN/'pilot_v3/bc_original/result.json').read_text())['records']
    recovery=json.loads((RUN/'pilot_v3/bc_recovery/result.json').read_text())['records']
    assert len(original)==len(recovery)==8
    assert all(b['success'] and (not a['success'] or b['attempts']==0) for a,b in zip(original,recovery))
    assert any(not a['success'] and b['success'] for a,b in zip(original,recovery))
    losses=json.loads((RUN/'pilot_v3/bc_forced_loss/result.json').read_text())['records']
    assert all(r['fault_step'] is not None and r['success'] and r['verified_regrasps']>=1 for r in losses)
    audits=[audit(p.parent) for folder in ['pilot_v3','extra_pilot'] for p in (RUN/folder).glob('*/result.json')]
    write(RUN/'pilot_acceptance.json',{'passed':True,'selected_revision':'pilot_v3','physical_and_equivalence':qa,
          'training_normal_successes_preserved_without_intervention':6,'training_natural_failures_rescued':2,
          'forced_loss_successes':2,'held_stall_successes':1,'full_noisy_train_successes':2,'trace_audits':audits,
          'earlier_pilots':'v1 failed; v2 exposed avoidable timeouts. Both complete attempts and source snapshots retained.'})
    demos=json.loads((ROOT/'data/splits.json').read_text())['dev'];assert len(demos)==30
    oldjobs=json.loads((ROOT/'reproduction/multiseed_20261012_01/jobs.json').read_text());jobs=[]
    for noise in [0.,.05]:
        for method,seed in [('bc_k2',None),('full',17),('full',23),('full',41)]:
            old=next(j for j in oldjobs if j['phase']=='evaluate' and j['method']==method and j['seed']==seed and j['noise']==noise)
            baseline=old['outputs'][0];b=json.loads((ROOT/baseline).read_text())
            assert b['status']=='complete' and [r['demo'] for r in b['records']]==demos
            args=b['args'];assert args['delay']==2 and args['steps']==400 and args['noise']==noise and args['split']=='dev'
            tag=f'{method}'+(f'_s{seed}' if seed else '')+('_clean' if not noise else '_noise005')
            jobs.append({'id':tag,'method':method,'seed':seed,'noise':noise,'enabled':True,'demos':demos,
                         'steps':400,'config':asdict(Config()),'baseline_result':baseline})
    write(RUN/'formal_jobs.json',jobs)
    files=[*RUN.glob('*.py'),RUN/'formal_jobs.json',RUN/'pilot_acceptance.json',ROOT/'common.py',ROOT/'world_model.py',
           ROOT/'collect_branches.py',ROOT/'collect_rollout_branches.py',ROOT/'reproduction/extensions_20261012_01/evaluate.py',
           ROOT/'reproduction/extensions_20261012_01/snapshot.py',ROOT/'reproduction/multiseed_20261012_01/evaluate_suite.py',
           ROOT/'data/splits.json',ROOT/'data/can_ph_lowdim_v15.hdf5',ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt']
    files.extend(ROOT/f'models/multiseed_20261012_01_full_s{s}/model.pt' for s in [17,23,41])
    files.extend(ROOT/j['baseline_result'] for j in jobs)
    lock={'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'episodes':240,
          'design':'30 shared development starts x 2 noise settings x (one fixed BC and three Full training seeds)',
          'inputs':'Current privileged 23D state history and fixed task geometry; no reward or simulator future in supervisor',
          'attribution':'Shared scripted engineering recovery, no learned weight improvement',
          'policy':'No tuning after development launch. Include all failures. Existing independent confirmation is not reused.',
          'statistics':'Paired start bootstrap, 20000 draws, seed 20261012. Full compared using mean over its three training seeds; fixed BC is not replicated as three seeds.',
          'primary':'Task success within 400 original D2 steps; paired rescued and regressed episodes versus corresponding original.',
          'secondary':'Intervention fraction, confirmed hold, confirmed regrasp, loss-trigger outcomes, completion steps and capped mean steps.',
          'packages':{n:importlib.metadata.version(n) for n in ['numpy','torch','robosuite','mujoco','scipy','h5py']},
          'sha256':{p.relative_to(ROOT).as_posix():digest(p) for p in files}}
    write(RUN/'frozen_protocol.json',lock);print(json.dumps({'pilot_passed':True,'jobs':len(jobs),'episodes':240,'frozen_utc':lock['frozen_utc']}),flush=True)

if __name__=='__main__':main()
