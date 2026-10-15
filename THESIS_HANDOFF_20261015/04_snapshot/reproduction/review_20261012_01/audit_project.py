"""Read-only evidence audit. Writes exclusively into this review directory."""
import ast, csv, hashlib, importlib.metadata, json, platform, subprocess, sys
from collections import Counter
from pathlib import Path
import h5py, numpy as np, torch
ROOT=Path(__file__).resolve().parents[2]; RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from world_model import WorldModel,DirectScore
from common import load_policy
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):
    if (RUN/name).exists():
        assert read(RUN/name)==value,f'Existing audit artifact differs: {name}'
        return
    with (RUN/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
def csvrows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def verify_jobs(folder,expected):
    jobs=read(folder/'jobs.json'); rows=[];phasecounts=Counter()
    for job in jobs:
        done=read(folder/'completed'/f"{job['id']}.json")
        assert done['status']=='complete' and done['command']==job['command'],job['id']
        hashes=done.get('outputs',done.get('output_sha256'))
        for rel,sha in hashes.items():assert digest(ROOT/rel)==sha,rel
        phase=job.get('phase','evaluate');phasecounts[phase]+=1
        row={'job':job['id'],'phase':phase,'output_files':len(hashes),'status':'complete'}
        if phase=='evaluate':
            raw=read(ROOT/job['outputs'][0]); records=raw['records']
            assert raw['status']=='complete' and len(records)==expected
            names=[x['demo'] for x in records];assert len(set(names))==expected
            assert all(isinstance(x['success'],bool) and 1<=x['steps']<=400 and (x['success'] or x['steps']==400) for x in records)
            row.update(method=job['method'],seed=job.get('seed'),noise=job['noise'],success=sum(x['success'] for x in records),episodes=len(records),source=job['outputs'][0])
        rows.append(row)
    return {'jobs':len(jobs),'phases':dict(phasecounts),'evaluated_episodes':sum(r.get('episodes',0) for r in rows),'rows':rows}
def main():
    before=read(RUN/'before_manifest.json'); problems=[]
    inventory=[];json_errors=[];pyerrors=[];syntax=[];raw_results=[]
    for rel in before:
        p=ROOT/rel;inventory.append({'path':rel,'bytes':p.stat().st_size,'suffix':p.suffix})
        if p.suffix=='.py':
            try:ast.parse(p.read_text(encoding='utf-8-sig'));syntax.append(rel)
            except Exception as e:pyerrors.append({'path':rel,'error':str(e)})
        if p.suffix=='.json':
            try:value=read(p)
            except Exception as e:json_errors.append({'path':rel,'error':str(e)});continue
            if isinstance(value,dict) and isinstance(value.get('records'),list) and value['records'] and all(isinstance(r,dict) and 'success' in r for r in value['records']):
                records=value['records'];args=value.get('args',{})
                raw_results.append({'path':rel,'status':value.get('status','legacy_no_status'),'episodes':len(records),
                    'requested_episodes':args.get('episodes'),'success':sum(bool(r['success']) for r in records),
                    'split':args.get('split'),'main_registered':rel.startswith('reproduction/confirmation_20261012_01/evaluations/') or '/multiseed_20261012_01/evaluations/' in rel})
    assert not pyerrors,pyerrors
    assert not json_errors,json_errors
    write('file_inventory.json',inventory);write('raw_result_inventory.json',raw_results)
    splits=read(ROOT/'data/splits.json');ss=[set(v) for v in splits.values()]
    assert sorted(map(len,ss))==[30,30,140] and len(set.union(*ss))==200
    assert all(not a&b for i,a in enumerate(ss) for b in ss[i+1:])
    original=ROOT/'data/can_ph_lowdim_v15.hdf5'
    assert digest(original)==read(original.with_suffix('.manifest.json'))['sha256']
    with h5py.File(original,'r') as f:assert len(f['data'])==200
    npzchecks=[]
    for p in (ROOT/'data').glob('*.npz'):
        with np.load(p,allow_pickle=False) as data:
            finite=all(np.isfinite(data[k]).all() for k in data.files if data[k].dtype.kind in 'fc')
            assert finite,p
            npzchecks.append({'path':p.relative_to(ROOT).as_posix(),'shapes':{k:list(data[k].shape) for k in data.files},'all_numeric_finite':True})
    write('dataset_inventory.json',npzchecks)
    multi=ROOT/'reproduction/multiseed_20261012_01';confirm=ROOT/'reproduction/confirmation_20261012_01'
    protocol=read(multi/'protocol.json')
    assert digest(multi/'jobs.json')==protocol['jobs_sha256']
    for rel,sha in protocol['source_sha256'].items():assert digest(ROOT/rel)==sha,rel
    for split in ('train','dev'):
        p=ROOT/'data'/f'branches_{split}_{protocol["dataset"]}.npz'
        assert digest(p)==protocol['data'][split]['sha256']
        with np.load(p) as d:
            assert sorted(set(d['parent'].tolist()))==protocol['data'][split]['parents']
            assert set(d['parent']).issubset(splits[split])
            assert d['a'].shape==(protocol['data'][split]['groups'],4,8,7)
            assert np.array_equal(d['a'][:,0,:2],d['a'][:,1,:2])
    lock=read(confirm/'lock.json')
    for rel,sha in lock['input_sha256'].items():assert digest(ROOT/rel)==sha,rel
    dev=verify_jobs(multi,30);test=verify_jobs(confirm,60)
    assert dev['phases']=={'train':15,'evaluate':60} and test['jobs']==14
    write('registered_job_verification.json',{'passed':True,'development':dev,'confirmation':test})
    # Independently recalculate table entries from raw results.
    for folder,checks in ((multi,dev),(confirm,test)):
        for row in csvrows(folder/'analysis/summary.csv'):
            if row.get('condition')=='joint_equal_weight':continue
            noise=float(row.get('noise',0 if row.get('condition')=='clean' else .05))
            matching=[r for r in checks['rows'] if r['phase']=='evaluate' and r['method']==row['method'] and r['noise']==noise]
            assert matching,(folder,row)
            rate=100*np.mean([r['success']/r['episodes'] for r in matching])
            assert np.isclose(rate,float(row['mean_success_percent'])),(row,rate)
    results={(j['method'],j['seed'],j['condition']):read(ROOT/j['outputs'][0]) for j in read(confirm/'jobs.json')}
    names=read(confirm/'design.json')['state_names']
    for r in results.values():assert [x['demo'] for x in r['records']]==names
    def mat(method,condition):
        if method=='bc_k2':return np.repeat([[float(x['success']) for x in results[(method,None,condition)]['records']]],3,axis=0)
        return np.array([[float(x['success']) for x in results[(method,s,condition)]['records']] for s in (17,23,41)])
    def matrix(m,c):return (mat(m,'clean')+mat(m,'noise005'))/2 if c=='joint_equal_weight' else mat(m,c)
    rng=np.random.default_rng(2026101203);si=rng.integers(0,3,(20000,3));ii=rng.integers(0,60,(20000,60))
    paired=[]
    for row in csvrows(confirm/'analysis/paired_comparisons.csv'):
        d=matrix(row['left'],row['condition'])-matrix(row['right'],row['condition'])
        ci=np.quantile(d[si[:,:,None],ii[:,None,:]].mean((1,2)),[.025,.975])*100
        assert np.allclose([100*d.mean(),*ci],[float(row[k]) for k in ('mean_difference_pp','paired_crossed_bootstrap_low_pp','paired_crossed_bootstrap_high_pp')])
        paired.append({'left':row['left'],'right':row['right'],'condition':row['condition'],'difference_pp':100*d.mean(),'ci95':ci.tolist()})
    write('statistics_recomputed.json',{'passed':True,'paired_comparisons':paired,'summary_tables_match_raw':True,'confirmation_records':840,'independent_confirmation_starts':60})
    # Load all current selected checkpoints and perform finite forward passes.
    torch.set_num_threads(2)
    with np.load(ROOT/'data/branches_dev_queuepair_20261012_01_real.npz') as d:
        x=torch.from_numpy(np.repeat(d['x'][:2],4,axis=0));a=torch.from_numpy(d['a'][:2].reshape(8,8,7))
    checkpoint_checks=[]
    selected=read(multi/'training_verification.json');assert selected['passed']
    for r in selected['selected']:
        method,seed=r['method'],r['seed']
        name=f'multiseed_20261012_01_head_s{seed}_{method}_s{seed}' if method in ('control','calibrated') else f'multiseed_20261012_01_{method}_s{seed}'
        ck=torch.load(ROOT/'models'/name/'model.pt',map_location='cpu',weights_only=True);cfg=ck['config']
        model=DirectScore(23,8,cfg['width']) if cfg['method']=='direct' else WorldModel(23,cfg['width'],True)
        model.load_state_dict(ck['state_dict'],strict=True);model.eval()
        assert all(torch.isfinite(v).all() for v in model.state_dict().values())
        with torch.inference_mode():future,labels=model(x,a)
        assert torch.isfinite(labels).all() and (future is None or torch.isfinite(future).all())
        assert sum(p.numel() for p in model.parameters())==cfg['parameters']
        checkpoint_checks.append({'model':name,'selected_step':ck['selected_step'],'parameters':cfg['parameters'],'forward_finite':True})
    policy=load_policy(ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt')
    with torch.inference_mode():actions=policy.best(x)
    assert actions.shape==(8,8,7) and torch.isfinite(actions).all()
    write('checkpoint_validation.json',{'passed':True,'world_models':checkpoint_checks,'bc_finite_forward':True})
    packages={p:importlib.metadata.version(p) for p in ('torch','numpy','robosuite','mujoco','h5py','matplotlib','scipy','opencv-python','Pillow','mink')}
    pipcheck=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True)
    assert pipcheck.returncode==0,pipcheck.stdout+pipcheck.stderr
    freeze=subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True,check=True).stdout
    with (RUN/'environment-freeze.txt').open('x',encoding='utf-8') as f:f.write(freeze)
    cuda={'available':torch.cuda.is_available(),'torch_cuda':torch.version.cuda}
    if cuda['available']:
        z=torch.ones((32,32),device='cuda');assert float((z@z).mean())==32.;torch.cuda.synchronize()
        cuda.update(device=torch.cuda.get_device_name(0),matrix_operation_passed=True)
    write('environment.json',{'python':sys.version,'platform':platform.platform(),'executable':sys.executable,'packages':packages,'cuda':cuda,'pip_check':pipcheck.stdout.strip(),'freeze_scope':'Observed installed versions; not an offline installer or a portable binary lock.'})
    result={'passed':True,'preexisting_files_scanned':len(inventory),'root_python_files':len(list(ROOT.glob('*.py'))),'python_files_syntax_checked':len(syntax),'json_parse_errors':json_errors,'python_parse_errors':pyerrors,
            'finite_npz_files':len(npzchecks),'raw_closed_loop_result_files':len(raw_results),'legacy_result_files_without_status':sum(r['status']=='legacy_no_status' for r in raw_results),
            'development_train_jobs':15,'selected_world_model_checkpoints':18,'development_evaluation_jobs':60,'development_episode_records':1800,
            'confirmation_jobs':14,'confirmation_episode_records':840,'confirmation_distinct_starts':60,'paired_statistics_recomputed':9,
            'legacy_incomplete_or_partial_results':[r for r in raw_results if r['status'] not in ('complete','legacy_no_status') or (r['requested_episodes'] and r['requested_episodes']!=r['episodes'])]}
    write('audit_validation.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
