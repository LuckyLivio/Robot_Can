"""Select transparent illustrative cases before rendering; freeze the selection."""
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
CONF=ROOT/'reproduction/confirmation_20261012_01'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    design={'selected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'model_seed':17,'seed_rule':'First seed in the already registered [17,23,41], never best-seed selection.',
        'case_rule':'For each clean/noise005 condition, choose smallest numeric ID in each category: all3 succeed; Full succeeds and BC/Plain fail; all3 fail. Categories are illustrative and selected AFTER confirmation, BEFORE rendering. Not a new independent test or representative sample.',
        'methods':['bc_k2','full','plain'],'conditions':['clean','noise005'],
        'comparison':'Same saved XML and initial state, same execution-noise stream, same D2, H8, K4, gate0.02,400step cap. Same camera and time scale. Freeze completed panels instead of looping/speeding them up.',
        'render':'Recompute and trace frozen controllers headlessly; verify original result metrics. Replay exact applied actions and compare every state before rendering. Camera is for presentation only; policy receives no images.',
        'cases':[],'source_sha256':{}}
    for condition in design['conditions']:
        results={}
        for method in design['methods']:
            directory=f'{method}_{condition}' if method=='bc_k2' else f'{method}_s17_{condition}'
            path=CONF/'evaluations'/directory/'results.json';payload=read(path)
            results[method]={r['demo']:r for r in payload['records']}
            design['source_sha256'][path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        categories=[('shared_success','三种方法均成功',lambda v:all(v)),
                    ('full_only_success','Full成功，BC与Plain未完成',lambda v:v==[False,True,False]),
                    ('shared_failure','三种方法均未完成',lambda v:not any(v))]
        for category,label,predicate in categories:
            eligible=sorted([name for name in results['bc_k2'] if predicate([results[m][name]['success'] for m in design['methods']])],key=lambda n:int(n.split('_')[1]))
            if not eligible:raise RuntimeError(f'No case for predeclared category {condition}/{category}; disclose rather than substitute silently')
            name=eligible[0]
            design['cases'].append({'id':f'{condition}_{category}','label':label,'condition':condition,
                'noise':0. if condition=='clean' else .05,'state_name':name,'eligible_count':len(eligible),
                'original_records':{m:results[m][name] for m in design['methods']}})
    with (RUN/'demo_design.json').open('x',encoding='utf-8') as f:json.dump(design,f,indent=2,ensure_ascii=False)
    print(json.dumps(design['cases'],ensure_ascii=False,indent=2))

if __name__=='__main__':main()
