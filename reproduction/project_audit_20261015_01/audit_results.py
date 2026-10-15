"""Recount saved episode results and match declared job outputs; no simulator."""
from pathlib import Path
from collections import defaultdict,Counter
import json,csv,math
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(name,obj):
    with (RUN/name).open('x',encoding='utf8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
def main():
    before=read(RUN/'before_manifest.json');ledger=[];issues=[];registries=[]
    for rel in before:
        if not rel.endswith('.json') or rel.startswith('THESIS_HANDOFF_'):continue
        if any(s in rel for s in ['/before/','/previous_documents/','/source/','/sources/']):continue
        p=ROOT/rel;d=read(p)
        if isinstance(d,list) and d and all(isinstance(x,dict) and 'id' in x for x in d) and 'job' in p.name:
            missing=[];declared=0
            for j in d:
                for op in j.get('outputs',[]):
                    declared+=1
                    if not (ROOT/op).exists():missing.append({'id':j['id'],'output':op})
            registries.append({'path':rel,'jobs':len(d),'declared_outputs':declared,'missing':missing})
        if not isinstance(d,dict) or not isinstance(d.get('records'),list) or not d['records']:continue
        rs=d['records']
        if not all(isinstance(r,dict) and 'success' in r for r in rs):continue
        n=len(rs);s=sum(bool(r['success']) for r in rs)
        job=d.get('job',{});names=[r.get('demo',r.get('episode')) for r in rs];expected=job.get('demos')
        errors=[]
        if expected is not None and names!=expected:errors.append('record demo order differs from declared job demos')
        if all(x is not None for x in names) and len(names)!=len(set(map(str,names))):errors.append('duplicate demo within result')
        if 'success_rate' in d and d['success_rate'] is not None and abs(d['success_rate']-s/n)>1e-6:errors.append('success_rate differs from records')
        limit=job.get('steps',d.get('args',{}).get('steps'))
        if limit and any(r.get('steps',0)>limit for r in rs):errors.append('episode exceeds declared step budget')
        status=d.get('status','not_recorded')
        row={'path':rel,'episodes':n,'success':s,'status':status,'distinct_demos':len(set(map(str,names))),'declared_step_limit':limit,'issues':'; '.join(errors)}
        ledger.append(row)
        if errors:issues.append(row)
    with (RUN/'RESULT_LEDGER.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(ledger[0]));w.writeheader();w.writerows(ledger)
    stages=defaultdict(lambda:{'files':0,'episodes':0,'success':0,'statuses':Counter()})
    for row in ledger:
        path=row['path'].split('/');key='/'.join(path[:3]) if path[0]=='reproduction' else path[0]+'/historical_results'
        s=stages[key];s['files']+=1;s['episodes']+=row['episodes'];s['success']+=row['success'];s['statuses'][row['status']]+=1
    save('result_validation.json',{'result_files':len(ledger),'issues':issues,'status_counts':dict(Counter(x['status'] for x in ledger)),'noncomplete_statuses':[x for x in ledger if x['status'] not in ['complete','completed','not_recorded']],'scope':'Counts are saved execution records; stages can reuse starts or contain historical diagnostic re-runs. Do not sum as independent samples.'})
    save('job_output_validation.json',registries);save('stage_counts.json',dict(stages))
    print(json.dumps({'results':len(ledger),'issues':issues,'registries':len(registries),'missing_declared_outputs':sum(len(x['missing']) for x in registries),'status_counts':dict(Counter(x['status'] for x in ledger))},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
