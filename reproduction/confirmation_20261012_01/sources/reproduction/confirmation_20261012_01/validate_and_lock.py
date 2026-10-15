"""Validate only historical/QA data, then lock all confirmation inputs."""
import datetime,hashlib,json,sys
from pathlib import Path
import h5py,numpy as np,torch
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from common import DATA
from world_model import WorldModel
from evaluate_confirmation import arguments,run_new,digest
from prepare_states import write

def main():
    design=json.loads((RUN/'design.json').read_text())
    assert json.loads((RUN/'state_validation.json').read_text())['passed']
    assert digest(RUN/'evaluator_core.py')==digest(ROOT/'reproduction/multiseed_20261012_01/evaluate_suite.py')
    for relative,sha in design['weights_sha256'].items():assert digest(ROOT/relative)==sha
    model_checks=[]
    for method in ('full','plain'):
        for seed in design['seeds']:
            path=ROOT/f'models/multiseed_20261012_01_{method}_s{seed}/model.pt'
            ck=torch.load(path,map_location='cpu',weights_only=True);cfg=ck['config']
            model=WorldModel(cfg['dim'],cfg['width'],cfg.get('future_only',False))
            model.load_state_dict(ck['state_dict']);model.eval()
            assert cfg['method']==method and cfg['future_only']
            model_checks.append({'method':method,'seed':seed,'load_ok':True,'sha256':digest(path)})
    checks=[]
    for condition,noise in [('clean',0.),('noise005',.05)]:
        args=arguments('full',17,noise,RUN/'validation'/condition,names=['demo_105'],trace=True,split='dev')
        args.model='headcal_20261012_01_calibrated_s17'
        path=run_new(args,DATA,['demo_105'],['demo_105'])
        old_dir=ROOT/'reproduction/multiseed_20261012_01/validation'/('clean' if noise==0 else 'noise_new')
        old_path=next(old_dir.glob('delay_*.json'))
        new=json.loads(path.read_text());old=json.loads(old_path.read_text())
        ra=new['records'][0];rb=next(r for r in old['records'] if r['demo']=='demo_105')
        for key in ('demo','success','steps','peak_stage_reward','ever_grasped','selection_counts'):assert ra[key]==rb[key],key
        aa=[json.loads(line) for line in (path.parent/new['trace_files']['demo_105']).read_text().splitlines()]
        bb=[json.loads(line) for line in (old_path.parent/old['trace_files']['demo_105']).read_text().splitlines()]
        assert len(aa)==len(bb)
        for a,b in zip(aa,bb):
            for key in a:
                if key!='decision_ms':assert a[key]==b[key],(condition,a['step'],key)
        checks.append({'condition':condition,'historical_demo':'demo_105','trace_steps':len(aa),'all_fields_except_timing_exact':True})
    with h5py.File(RUN/'starts.hdf5','r') as f:
        for name,seed in zip(design['state_names'],design['noise_seeds']):
            rng=np.random.default_rng(seed)
            # Validate repeated per-step draws as used by the unchanged core.
            assert np.array_equal(np.asarray([rng.normal(0,.05,3) for _ in range(400)]),f['data'][name]['execution_noise'][:])
    write(RUN/'validation.json',{'passed':True,'evaluator_core_byte_identical':True,'historical_trace_checks':checks,
        'all60_noise_arrays_match_evaluator':True,'models':model_checks,
        'scope':'No confirmation policy rollout performed before lock. Historical demos only for evaluator regression; separate QA starts for state restoration.'})
    jobs=[]
    for method,seed in [('bc_k2',None)]+[(m,s) for m in ('full','plain') for s in design['seeds']]:
        for condition,noise in design['conditions'].items():
            job_id=f'{method}'+(f'_s{seed}' if seed is not None else '')+f'_{condition}'
            output=RUN/'evaluations'/job_id
            jobs.append({'id':job_id,'method':method,'seed':seed,'noise':noise,'condition':condition,
                'output_dir':output.relative_to(ROOT).as_posix(),
                'command':[str(ROOT/'.venv/Scripts/python.exe'),'-X','utf8','-B','-u',str(RUN/'evaluate_confirmation.py'),'--job',job_id],
                'outputs':[(output/'results.json').relative_to(ROOT).as_posix()]})
    write(RUN/'jobs.json',jobs)
    inputs=list(design['weights_sha256'])+['common.py','world_model.py','collect_branches.py','collect_rollout_branches.py','data/splits.json',str(DATA.relative_to(ROOT)).replace('\\','/')]
    inputs += [p.relative_to(ROOT).as_posix() for p in RUN.glob('*.py')]
    inputs += [(RUN/name).relative_to(ROOT).as_posix() for name in ('design.json','jobs.json','starts.hdf5','qa_starts.hdf5','state_validation.json','validation.json')]
    # Include configuration files for the exact six selected checkpoints.
    inputs += [f'models/multiseed_20261012_01_{m}_s{s}/config.json' for m in ('full','plain') for s in design['seeds'] if (ROOT/f'models/multiseed_20261012_01_{m}_s{s}/config.json').exists()]
    hashes={relative:digest(ROOT/relative) for relative in sorted(set(inputs))}
    write(RUN/'lock.json',{'locked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'locked_before_any_confirmation_rollout','input_sha256':hashes,
        'jobs':len(jobs),'episodes':840,'independent_initial_states':60,'workers':3,
        'trace_states':design['state_names'][:2],
        'analysis_note':'First two IDs traced prospectively for audit, not selected for good performance. All60 retained.'})
    print(json.dumps({'lock':'complete','jobs':len(jobs),'episodes':840,'regression_steps':sum(c['trace_steps'] for c in checks)}),flush=True)

if __name__=='__main__':main()
