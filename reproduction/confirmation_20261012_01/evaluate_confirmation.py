"""Use an unchanged, previously validated planner with locked new initial states."""
import argparse,datetime,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
import evaluator_core as core

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def arguments(method,seed,noise,output,names=None,trace=False,split='confirmation'):
    model=f'multiseed_20261012_01_{method}_s{seed}' if method!='bc_k2' else 'multiseed_20261012_01_full_s17'
    return argparse.Namespace(method='bc_shift' if method=='bc_k2' else 'wm',model=model,
        policy='bc_chunk_dev_v4',policy_checkpoint='policy_15000.pt',split=split,episodes=60,steps=400,
        delay=2,shift_index=2,fallback_index=2,candidates=4,horizon=8,noise=noise,risk_weight=.5,
        readout_weight=.02,gate_margin=.02,fallback='shift',score_only=True,candidate_mode='shift',
        demos=names,output_dir=str(output),trace=trace)

def run_new(args,dataset,names,trace_names=(),extra_provenance=None):
    # Only data routing, output routing and provenance change. The entire
    # policy/model/queue/gate/noise/physics loop remains byte-identical.
    old_data,old_plan,old_prov=core.DATA,core.output_plan,core.provenance
    core.DATA=dataset
    def plan(_):
        directory=Path(args.output_dir);out=directory/'results.json'
        traces={n:directory/'traces'/f'{n}.jsonl' for n in trace_names}
        for p in [out,*traces.values()]:
            if p.exists():raise FileExistsError(p)
        return list(names),out,traces
    def provenance(a,c):
        p=old_prov(a,c)
        p.update(confirmation_wrapper_sha256=digest(Path(__file__)),
            registered_design_sha256=digest(RUN/'design.json'),
            execution_started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            **(extra_provenance or {}))
        return p
    core.output_plan=plan;core.provenance=provenance
    try:return core.run(args)
    finally:core.DATA,core.output_plan,core.provenance=old_data,old_plan,old_prov

def main(job_id):
    lock=json.loads((RUN/'lock.json').read_text())
    for relative,sha in lock['input_sha256'].items():
        assert digest(ROOT/relative)==sha,relative
    assert json.loads((RUN/'validation.json').read_text())['passed']
    jobs=json.loads((RUN/'jobs.json').read_text());job=next(j for j in jobs if j['id']==job_id)
    design=json.loads((RUN/'design.json').read_text())
    args=arguments(job['method'],job['seed'],job['noise'],ROOT/job['output_dir'])
    run_new(args,RUN/'starts.hdf5',design['state_names'],design['state_names'][:2],
        {'confirmation_lock_sha256':digest(RUN/'lock.json'),'job_id':job_id,
         'noise':'Paired positional noise from default_rng(70000 + state numeric ID); exact sequence saved in starts.hdf5.',
         'scope':'Independent fresh native initial states; fixed BC and fixed training data/three model seeds.'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--job',required=True);main(p.parse_args().job)
