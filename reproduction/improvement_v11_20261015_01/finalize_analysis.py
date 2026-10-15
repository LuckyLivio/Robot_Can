from pathlib import Path
import csv,json
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];stage=RUN/'pilot_a'
if __name__=='__main__':
    pilot=json.loads((RUN/'analysis/pilot_a.json').read_text());dev=json.loads((RUN/'analysis/development.json').read_text());variants={};timing={};paired={}
    for v in ['v10','axis','guard','v11']:
        d=pilot['variants'][v];variants[v]={k:d[k] for k in ['success','episodes','rescues','regressions']};a=[];wait=0
        for f in stage.glob(v+'_*/result.json'):
            data=json.loads(f.read_text());suffix=data['job']['id'].split('_',1)[1]
            for r in data['records']:paired.setdefault((suffix,r['demo']),{'condition':suffix,'demo':r['demo']}).update({v+'_success':r['success'],v+'_steps':r['steps']})
            for r in map(json.loads,f.with_name('trace.jsonl').open()):a.append(r['total_policy_and_supervisor_ms']);wait+=r['recovery']['mode']=='PLAN_WAIT'
        timing[v]={'steps':len(a),'p99_ms':float(np.percentile(a,99)),'max_ms':max(a),'over50':sum(t>50 for t in a),'planning_wait_steps':wait}
    comparison=[]
    for key,row in sorted(paired.items()):comparison.append(row)
    with (RUN/'analysis/pilot_pairs.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(comparison[0]));w.writeheader();w.writerows(comparison)
    assert dev['v11_success']==235 and dev['v6_success']==236 and len(dev['regressions'])==1
    # Establish unchanged scope on all other known conditions.
    unchanged=0;changed=[]
    for v in ['axis','guard','v11']:
        for f in stage.glob(v+'_*/trace.jsonl'):
            base=stage/('v10_'+f.parent.name.split('_',1)[1])/'trace.jsonl';a=list(map(json.loads,f.open()));b=list(map(json.loads,base.open()))
            same=len(a)==len(b) and all(r['state_after']==s['state_after'] and r['submitted_action']==s['submitted_action'] for r,s in zip(a,b))
            if same:unchanged+=len(json.loads(f.with_name('result.json').read_text())['records'])
            else:changed.append(f.parent.name)
    result={'status':'箱沿修复成立，开发有1例继承退步 · 未采用','adopted':False,'stage':'pilot_a','variants':variants,'completed_episodes':148,'actual_executions_total':397,'dev_240_launched':True,'development':dev,'timing':timing,
        'pilot_gate_passed':True,'adoption_gate_passed':False,'new_independent_confirmation':False,'unchanged_non_target_variant_episodes':unchanged,'changed_pilot_jobs':changed,
        'summary':'已知诊断：v11为31/37，其余三组30/37；箱沿380步完成。开发：v11为235/240，v6为236/240；新箱沿模块未触发，1例继承的等待逻辑退步已定位。保留修复候选，主版本仍为v5。'}
    with (RUN/'analysis/final_receipt.json').open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'variants':variants,'development':[dev['v11_success'],dev['v6_success']],'unchanged':unchanged,'timing':timing},ensure_ascii=False))
