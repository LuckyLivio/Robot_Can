"""Check frozen input hashes, branch split contracts, and original user weights."""
from pathlib import Path
import json,hashlib,numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    locks=[]
    for rel,key in [('reproduction/confirmation_20261012_01/lock.json','input_sha256'),('reproduction/recovery_v5_20261012_01/confirmation_lock.json','sha256'),('reproduction/improvement_v11_20261015_01/protocols/development_freeze.json','source_sha256')]:
        d=read(ROOT/rel);errors=[]
        for name,h in d[key].items():
            p=ROOT/name
            if not p.is_file() or sha(p)!=h:errors.append(name)
        locks.append({'file':rel,'inputs':len(d[key]),'mismatches':errors})
    splits=read(ROOT/'data/splits.json');branches={};parentsets={}
    for split in ['train','dev']:
        p=ROOT/f'data/branches_{split}_queuepair_20261012_01_real.npz'
        with np.load(p,allow_pickle=False) as d:
            parents=set(d['parent'].tolist());parentsets[split]=parents
            assert parents.issubset(splits[split]);branches[split]={'parents':len(parents),'parent_ids':sorted(parents),'arrays':{k:list(d[k].shape) for k in d.files},'sha256':sha(p)}
    assert not parentsets['train']&parentsets['dev']
    provided=[]
    for original,target in [('C:/Users/Livio/Desktop/model.pt','models/full_future_delay2_shift_v0/model.pt'),('C:/Users/Livio/Desktop/policy_15000.pt','policy/bc_chunk_dev_v4/policy_15000.pt')]:
        p=Path(original);q=ROOT/target;provided.append({'source':str(p),'target':target,'source_available':p.is_file(),'target_sha256':sha(q),'identical':sha(p)==sha(q) if p.is_file() else None})
    passed=not any(x['mismatches'] for x in locks) and not any(x['identical'] is False for x in provided)
    result={'passed':passed,'frozen_inputs':locks,'branches':branches,'parent_split_disjoint':True,'original_user_weights':provided}
    with (RUN/'contracts.json').open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'passed':passed,'locks':locks,'parents':{k:v['parents'] for k,v in branches.items()},'weights':provided},ensure_ascii=False))
