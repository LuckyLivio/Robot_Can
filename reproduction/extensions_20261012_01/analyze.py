"""Aggregate all registered outcomes; keep old experiments and documents intact."""
import csv, json, sys
from collections import defaultdict, deque
from pathlib import Path
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
from register import digest


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def write(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)


def main():
    jobs=read(RUN/'jobs.json');protocol=read(RUN/'protocol.json')
    names=protocol['demos']; nameset=set(names);groups=defaultdict(dict);records=defaultdict(list)
    verified=[];trace_steps=0;oracle_steps=0
    for job in jobs:
        done=read(RUN/'completed'/f"{job['id']}.json")
        assert done['status']=='complete' and done['job']==job
        for rel,sha in done['outputs'].items():assert digest(ROOT/rel)==sha,rel
        directory=RUN/'evaluations'/job['id'];result=read(directory/'result.json')
        assert result['status']=='complete' and result['job']==job
        assert [r['demo'] for r in result['records']]==job['demos']
        key=(job['variant'],job['noise'],job['seed'])
        records[key].extend(result['records'])
        trace=directory/'decisions.jsonl';queues={};rngs={};counts=defaultdict(int)
        for line in trace.open(encoding='utf-8'):
            t=json.loads(line);demo=t['demo'];counts[demo]+=1
            assert t['step']==counts[demo]
            if demo not in queues:
                queues[demo]=deque([np.zeros(7,np.float32) for _ in range(2)])
                rngs[demo]=np.random.default_rng(70000+int(demo.split('_')[1]))
            assert t['candidate_ids']==job['candidate_ids']
            ids=t['candidate_ids'];scores=np.asarray(t['scores'],np.float32);raw=int(scores.argmax());fallback=ids.index(2)
            chosen=fallback if raw!=fallback and float(scores[raw]-scores[fallback])<.02 else raw
            assert t['raw_shift']==ids[raw] and t['selected_shift']==ids[chosen]
            queues[demo].append(np.asarray(t['submitted_action'],np.float32));executed=queues[demo].popleft()
            assert np.array_equal(executed,t['executed_action_before_noise'])
            if job['noise']:executed[:3]+=rngs[demo].normal(0,job['noise'],3)
            assert np.array_equal(np.clip(executed,-1,1),t['executed_action'])
            if job['variant'] in ['h1','k1','persistence']:assert t['selected_shift']==2 and t['score_spread']<1e-6
            if job['method']=='oracle':
                progress=np.asarray(t['true_progress'],np.float32);risk=np.asarray(t['true_grasp_loss'],np.float32)
                assert np.array_equal(progress[:,:2],np.repeat(progress[:1,:2],4,0))
                assert np.array_equal(risk[:,:2],np.repeat(risk[:1,:2],4,0))
                true_score=progress[:,-1]+.5*progress.mean(1)-.5*risk.max(1)
                assert np.allclose(scores,true_score,rtol=0,atol=2e-7)
                if job['noise']==0:
                    actual=np.float32(1. if t['success_after'] else max(t['stages_after']))
                    assert progress[0,0]==actual,'Oracle branch/live first-step progress mismatch'
            trace_steps+=1;oracle_steps+=job['method']=='oracle'
        assert counts=={r['demo']:r['steps'] for r in result['records']}
        verified.append({'id':job['id'],'episodes':len(result['records']),'success':sum(r['success'] for r in result['records']),
                         'trace_steps':sum(counts.values())})
    references=read(RUN/'reference_jobs.json')
    for job in references:
        done=read(ROOT/'reproduction/multiseed_20261012_01/completed'/f"{job['id']}.json")
        assert done['status']=='complete' and done['command']==job['command']
        for rel,sha in done.get('outputs',done.get('output_sha256')).items():assert digest(ROOT/rel)==sha,rel
        rows=read(ROOT/job['outputs'][0])['records']
        records[(job['method'],job['noise'],job['seed'])].extend(rows)
    for (variant,noise,seed),rows in records.items():
        assert len(rows)==30 and {r['demo'] for r in rows}==nameset,(variant,noise,seed)
        byname={r['demo']:r for r in rows}
        groups[(variant,noise)][seed]=np.array([byname[n]['success'] for n in names],float)
    for (variant,noise,seed),rows in records.items():
        if variant in ['h1','k1','persistence']:
            baseline={r['demo']:r for r in records[('bc_k2',noise,None)]}
            for row in rows:
                for field in ['success','steps','peak_stage_reward','ever_grasped']:
                    assert row[field]==baseline[row['demo']][field],(variant,noise,seed,field)
    rng=np.random.default_rng(2026101204)
    parent_ids=rng.integers(0,30,(20000,30));seed_ids=rng.integers(0,3,(20000,3))
    def matrix(key):
        seeds=groups[key]
        return np.stack([seeds[s] for s in [17,23,41]]) if set(seeds)=={17,23,41} else np.repeat(seeds[None][None],3,0)
    def interval(m):
        samples=m[seed_ids[:,:,None],parent_ids[:,None,:]].mean((1,2))*100
        return np.percentile(samples,[2.5,97.5]).tolist()
    summary=[]
    for key in sorted(groups):
        variant,noise=key;data=groups[key];m=matrix(key)
        rows=[r for (v,n,s),rr in records.items() if v==variant and n==noise for r in rr]
        summary.append({'variant':variant,'noise':noise,'trained_seeds':0 if set(data)=={None} else 3,
                        'success_counts':[int(data[s].sum()) for s in sorted(data,key=lambda x:x or 0)],
                        'episodes_per_policy':30,'mean_success_percent':float(m.mean()*100),
                        'paired_bootstrap_ci_percent':interval(m),
                        'mean_episode_override_fraction':float(np.mean([r.get('fraction_override',0.) for r in rows])),
                        'steps_total':sum(r['steps'] for r in rows),
                        'mean_decision_ms_weighted':float(sum(r['steps']*r['mean_decision_ms'] for r in rows)/sum(r['steps'] for r in rows))})
    comparisons=[]
    for noise in [0.,.05]:
        for left,right in [('full','bc_k2'),('oracle','bc_k2'),('oracle','full'),('oracle','plain'),
                           ('persistence','full'),('h1','full'),('h3','full'),('horizon4','full'),
                           ('k1','full'),('k2','full'),('k8','full')]:
            delta=matrix((left,noise))-matrix((right,noise))
            comparisons.append({'left':left,'right':right,'noise':noise,'difference_pp':float(delta.mean()*100),'ci95_pp':interval(delta)})
    analysis=RUN/'analysis';analysis.mkdir(exist_ok=True)
    write(analysis/'summary.json',summary);write(analysis/'paired_comparisons.json',comparisons)
    write(analysis/'run_verification.json',{'passed':True,'new_jobs':len(verified),'new_episodes':sum(x['episodes'] for x in verified),
        'new_trace_steps':trace_steps,'oracle_decisions':oracle_steps,'oracle_counterfactual_branches':oracle_steps*4,
        'oracle_counterfactual_steps':oracle_steps*32,'reused_jobs':len(references),
        'h1_k1_persistence_exact_baseline_outcomes':True,'fifo_noise_gate_checks':True,
        'oracle_common_prefix_true_score_and_clean_live_progress_checks':True,'jobs':verified})
    with (analysis/'summary.csv').open('x',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    with (analysis/'paired_comparisons.csv').open('x',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(comparisons[0]));writer.writeheader();writer.writerows(comparisons)
    # A read-only explanation of the failure example already visible in the demo.
    cases=[]
    for p in sorted((ROOT/'reproduction/release_20261012_01/demo/traces').glob('*/traces/demo_1000000.jsonl')):
        tt=[json.loads(line) for line in p.read_text().splitlines()]
        stages=np.array([t['stages_after'] for t in tt]);states=np.array([t['state_after'] for t in tt])
        grasp=np.flatnonzero(stages[:,1]>.3)+1
        cases.append({'method_condition':p.parent.parent.name,'source':p.relative_to(ROOT).as_posix(),'source_sha256':digest(p),
                      'steps':len(tt),'success':tt[-1]['success_after'],'first_grasp_step':int(grasp.min()),
                      'last_grasp_step':int(grasp.max()),'grasped_steps':len(grasp),
                      'object_height_max_m':float(states[:,18].max()),'object_final_position':states[-1,16:19].tolist(),
                      'target_position':tt[-1]['target_position'],
                      'override_steps':sum(t.get('overrode_fallback',False) for t in tt),
                      'max_predicted_advantage':max(t.get('raw_advantage',0.) for t in tt)})
    write(analysis/'shared_failure_explanation.json',cases)
    print(json.dumps({'passed':True,'jobs':len(verified),'episodes':sum(x['episodes'] for x in verified),'trace_steps':trace_steps,'oracle_decisions':oracle_steps}))


if __name__=='__main__':main()
