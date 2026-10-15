"""Read all unique tracked JSONL/checkpoints/numeric datasets and image assets."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import json,csv,sys,subprocess,platform,importlib.metadata as md,xml.etree.ElementTree as ET
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
def save(name,data):
    with (RUN/name).open('x',encoding='utf8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
def reject_constant(s):raise ValueError('nonfinite JSON constant:'+s)
def main():
    before=json.loads((RUN/'before_manifest.json').read_text());unique=defaultdict(list)
    for rel,h in before.items():unique[(Path(rel).suffix.lower(),h)].append(rel)
    tracegroups=[ps for (ext,h),ps in unique.items() if ext=='.jsonl']
    def trace(ps):
        n=0;error=None
        try:
            with (ROOT/ps[0]).open(encoding='utf-8-sig') as f:
                for n,line in enumerate(f,1):
                    if line.strip():json.loads(line,parse_constant=reject_constant)
        except Exception as e:error=str(e)[:300]
        return {'paths':ps,'lines':n,'error':error}
    with ThreadPoolExecutor(max_workers=4) as pool:traces=list(pool.map(trace,tracegroups))
    save('jsonl_validation.json',{'passed':not any(x['error'] for x in traces),'unique_files':len(traces),'paths':sum(len(x['paths']) for x in traces),'unique_lines':sum(x['lines'] for x in traces),'files':traces})
    print('JSONL',len(traces),sum(x['lines'] for x in traces),'errors',sum(bool(x['error']) for x in traces),flush=True)
    import torch,numpy as np,h5py
    from PIL import Image
    torch.set_num_threads(2)
    checks=[]
    def finite(obj):
        if torch.is_tensor(obj):assert bool(torch.isfinite(obj).all())
        elif isinstance(obj,dict):
            for v in obj.values():finite(v)
        elif isinstance(obj,(tuple,list)):
            for v in obj:finite(v)
    for (ext,h),ps in unique.items():
        if ext not in ['.pt','.hdf5','.npz','.png','.jpg','.svg','.csv']:continue
        p=ROOT/ps[0];rec={'paths':ps,'type':ext,'passed':False}
        try:
            if ext=='.pt':
                obj=torch.load(p,map_location='cpu',weights_only=True);finite(obj);rec['keys']=list(obj) if isinstance(obj,dict) else []
            elif ext=='.npz':
                arrays={}
                with np.load(p,allow_pickle=False) as data:
                    for k in data.files:
                        a=data[k];arrays[k]=list(a.shape)
                        if np.issubdtype(a.dtype,np.number):assert np.isfinite(a).all(),k
                rec['arrays']=arrays
            elif ext=='.hdf5':
                count=[0]
                def visit(name,obj):
                    if isinstance(obj,h5py.Dataset):
                        a=obj[()];count[0]+=1
                        if np.issubdtype(obj.dtype,np.number):assert np.isfinite(a).all(),name
                with h5py.File(p,'r') as f:f.visititems(visit)
                rec['datasets']=count[0]
            elif ext in ['.png','.jpg']:
                with Image.open(p) as im:rec['dimensions']=list(im.size);im.verify()
            elif ext=='.svg':ET.parse(p)
            elif ext=='.csv':
                with p.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.reader(f))
                assert rows;rec['rows']=len(rows);width=len(rows[0]);assert all(len(r)==width for r in rows), 'ragged rows'
            rec['passed']=True
        except Exception as e:rec['error']=str(e)[:500]
        checks.append(rec)
    save('binary_numeric_assets.json',{'passed':all(r['passed'] for r in checks),'unique_assets':len(checks),'files':checks})
    print('Assets',len(checks),'errors',sum(not x['passed'] for x in checks),flush=True)
    from common import load_policy,OBS_KEYS
    from world_model import WorldModel
    splits=json.loads((ROOT/'data/splits.json').read_text());sets={k:set(v) for k,v in splits.items() if isinstance(v,list)}
    assert len(set.union(*sets.values()))==200 and sum(map(len,sets.values()))==200
    with h5py.File(ROOT/'data/can_ph_lowdim_v15.hdf5','r') as f:
        assert set(f['data'])==set.union(*sets.values())
        name=next(iter(sets['dev']));x=np.concatenate([f['data'][name]['obs'][k][0] for k in OBS_KEYS]).astype('float32')
    assert x.shape==(23,)
    policy=load_policy(ROOT/'policy/bc_chunk_dev_v4/policy_15000.pt')
    with torch.no_grad():actions=policy.best(torch.from_numpy(x)[None])
    assert actions.shape==(1,8,7) and torch.isfinite(actions).all()
    forwards=[]
    for kind in ['full','plain']:
        for seed in [17,23,41]:
            p=ROOT/f'models/multiseed_20261012_01_{kind}_s{seed}/model.pt';ck=torch.load(p,map_location='cpu',weights_only=True);cfg=ck['config']
            model=WorldModel(cfg['dim'],cfg['width'],cfg.get('future_only',False));model.load_state_dict(ck['state_dict']);model.eval()
            with torch.no_grad():states,labels=model(torch.from_numpy(x)[None],actions)
            assert states.shape==(1,8,23) and labels.shape==(1,8,2) and torch.isfinite(states).all() and torch.isfinite(labels).all()
            forwards.append({'path':p.relative_to(ROOT).as_posix(),'states_shape':list(states.shape),'scores_shape':list(labels.shape)})
    env={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'packages':{k:md.version(k) for k in ['torch','numpy','robosuite','mujoco','h5py','scipy','matplotlib','mink']},'cuda_available':torch.cuda.is_available(),'cuda_build':torch.version.cuda}
    if env['cuda_available']:
        env['cuda_device']=torch.cuda.get_device_name();v=torch.ones(4,device='cuda');assert v.sum().item()==4;env['cuda_tensor_check']=True
    pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True)
    env.update(pip_check_passed=pip.returncode==0,pip_check_output=pip.stdout.strip())
    save('environment_and_inference.json',{'passed':True,'environment':env,'data_split':{k:len(v) for k,v in sets.items()},'bc_shape':list(actions.shape),'world_model_forwards':forwards,'scope':'One saved observation, no environment creation, training, policy episode or physical replay.'})
    print('Environment, split, BC and six WM forwards passed',flush=True)
if __name__=='__main__':main()
