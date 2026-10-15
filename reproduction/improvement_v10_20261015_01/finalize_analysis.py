from pathlib import Path
import csv,hashlib,json
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];STAGE=RUN/'pilot_a'
def records(folder,prefix):
    result={}
    for f in folder.glob(prefix+'_*/result.json'):
        d=json.loads(f.read_text());j=d['job']
        for r in d['records']:result[(j['id'].split('_',1)[1],r['demo'])]=(r,f)
    return result
if __name__=='__main__':
    assert (STAGE/'completed.json').exists()
    baseline=records(ROOT/'reproduction/improvement_v9_20261015_01/pilot_b','v6')
    rows={v:records(STAGE,v) for v in ['v9','height','path','v10']};summaries={};timing={};paired=[]
    for v,rs in rows.items():
        assert len(rs)==37 and set(rs)==set(baseline)
        regressions=[list(k) for k,(r,f) in rs.items() if baseline[k][0]['success'] and not r['success']]
        rescues=[list(k) for k,(r,f) in rs.items() if not baseline[k][0]['success'] and r['success']]
        summaries[v]={'success':sum(r['success'] for r,f in rs.values()),'episodes':37,'regressions':regressions,'rescues':rescues}
        arrays={k:[] for k in ['decision_ms','total_policy_and_supervisor_ms']};events=[];wait=0
        for f in STAGE.glob(v+'_*/result.json'):
            d=json.loads(f.read_text())
            for r in d['records']:events.extend(r.get('edge_events',[]))
            for r in map(json.loads,f.with_name('trace.jsonl').open()):
                for k in arrays:arrays[k].append(r[k])
                wait+=r['recovery']['mode']=='PLAN_WAIT'
        timing[v]={k:{'max_ms':max(a),'p99_ms':float(np.percentile(a,99)),'over_50ms':sum(x>50 for x in a),'steps':len(a)} for k,a in arrays.items()}
        timing[v]['planning_wait_steps']=wait;timing[v]['edge_searches']=len(events)
    for k in sorted(baseline):
        paired.append({'case':k[0],'demo':k[1],'v6_success':baseline[k][0]['success'],**{v+'_success':rs[k][0]['success'] for v,rs in rows.items()},**{v+'_steps':rs[k][0]['steps'] for v,rs in rows.items()}})
    with (RUN/'analysis/paired_outcomes.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(paired[0]));w.writeheader();w.writerows(paired)
    # Verify policy/control equality away from the targeted wall-edge episode.
    same=0;different=[]
    for v in ['height','path','v10']:
        for j in json.loads((STAGE/'jobs.json').read_text()):
            if j['version']!=v:continue
            p=STAGE/j['id']/'trace.jsonl';base=STAGE/('v9_'+j['id'].split('_',1)[1])/'trace.jsonl'
            a=[json.loads(l) for l in p.open()];b=[json.loads(l) for l in base.open()]
            equal=len(a)==len(b) and all(x['submitted_action']==y['submitted_action'] and x['state_after']==y['state_after'] for x,y in zip(a,b))
            if equal:same+=len(j['demos'])
            else:different.append(j['id'])
    gate=not summaries['v10']['regressions'] and len(summaries['v10']['rescues'])>=1
    assert not gate,'If gate passes, freeze and run development before finalizing.'
    result={'status':'接近路径可执行，任务成功率未改善 · 未采用','adopted':False,'stage':'pilot_a','variants':summaries,
        'completed_episodes':148,'actual_executions_total':166,'dev_240_launched':False,'gate_passed':False,'timing':timing,
        'unchanged_non_target_variant_episodes':same,'changed_jobs':different,
        'summary':'四组均为30/37；相对 v9 无新增成功，相对 v6 仍有箱沿1例退步。原地转向与接近已有实际执行证据，但接触后支撑变化仍导致恢复失败。未进入240回合开发，主版本仍为v5。',
        'scope':'37 reused diagnostic conditions, not independent confirmation. No training, no new weights, no paper.'}
    for name,data in [('timing.json',timing),('final_receipt.json',result)]:
        with (RUN/'analysis'/name).open('x',encoding='utf8') as f:json.dump(data,f,indent=2,ensure_ascii=False)
    print(json.dumps(result,ensure_ascii=False))
