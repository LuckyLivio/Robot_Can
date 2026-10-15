from pathlib import Path
import csv,json
import numpy as np
RUN=Path(__file__).resolve().parent
def stats(values):
    a=np.asarray(values)
    return {'steps':len(a),'median_ms':float(np.median(a)),'p95_ms':float(np.percentile(a,95)),
            'p99_ms':float(np.percentile(a,99)),'max_ms':float(a.max()),'over_50ms':int(sum(a>50))}
def main():
    report=json.loads((RUN/'analysis/pilot_b.json').read_text());assert report['complete']
    check=json.loads((RUN/'analysis/pilot_b_verification.json').read_text());assert check['passed']
    physics=json.loads((RUN/'analysis/pilot_b_physics.json').read_text());assert physics['passed']
    assert json.loads((RUN/'analysis/frame_validation.json').read_text())['passed']
    outcomes={v:{k:r[k] for k in ['success','episodes','rescues','regressions']} for v,r in report['variants'].items()}
    timing={};flat=[];mechanisms={}
    for v in outcomes:
        decision=[];total=[];supervisor=[];wait=0;joint_events=[];work=[]
        for p in (RUN/'pilot_b').glob(v+'_*/result.json'):
            d=json.loads(p.read_text());job=d['job']
            for r in d['records']:
                flat.append({'version':v,'case':job['id'].split('_',1)[1],'method':job['method'],'seed':job['seed'],
                             'noise':job['noise'],'demo':r['demo'],'success':r['success'],'steps':r['steps'],'attempts':r['attempts'],
                             'verified_regrasps':r['verified_regrasps']})
                joint_events.extend(r.get('joint_events',[]))
            for r in map(json.loads,p.with_name('trace.jsonl').open()):
                decision.append(r['decision_ms']);total.append(r['total_policy_and_supervisor_ms'])
                if 'planning_ms' in r['recovery']:supervisor.append(r['recovery']['planning_ms'])
                wait+=r['recovery']['mode']=='PLAN_WAIT'
                if 'planning_work_units' in r['recovery']:work.append({'kind':r['recovery']['planning_kind'],'units':r['recovery']['planning_work_units']})
        timing[v]={'selection_and_supervisor':stats(decision),'policy_and_selection_and_supervisor':stats(total),
                   'supervisor_only':stats(supervisor) if supervisor else None}
        mechanisms[v]={'planning_wait_steps':wait,'joint_check_count':len(joint_events),
                       'chosen_original':sum(e['chosen_flip']==0 for e in joint_events),
                       'chosen_equivalent':sum(e['chosen_flip']==1 for e in joint_events),
                       'no_validated_solution':sum(e['chosen_flip'] is None for e in joint_events),
                       'max_mesh_candidates_per_wait_step':max([x['units'] for x in work if x['kind']=='mesh'],default=0),
                       'max_joint_work_per_wait_step':max([x['units'] for x in work if x['kind']=='joint'],default=0)}
    with (RUN/'analysis/paired_outcomes.csv').open('x',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    with (RUN/'analysis/timing.json').open('x') as f:json.dump({'variants':timing,'mechanisms':mechanisms,
        'scope':'Measured during four-worker evaluation; not worst-case execution certification. Total includes BC and WM selection and supervisor but excludes physics, rendering and file writes.'},f,indent=2)
    gate=not outcomes['v9']['regressions'] and len(outcomes['v9']['rescues'])>0 and timing['v9']['supervisor_only']['p99_ms']<50
    completed=sum(json.loads((RUN/stage/'completed.json').read_text())['episodes'] for stage in ['smoke_a','smoke_b','pilot_a','pilot_b'])
    receipt={'status':'验证通过，可进入开发对照' if gate else '耗时改善，成功率未达标 · 未采用','stage':'pilot_b','adopted':False,
             'pilot_gate_passed':gate,'dev_240_launched':False,'completed_episodes':completed,'current_pilot_episodes':185,'variants':outcomes,
             'mechanisms':mechanisms,'timing':timing,'training_performed':False,'paper_written':False,'weights_changed':False,
             'protected_paths':check['old_assets_or_exact_entrypoint_backups_verified'],'verified_steps':check['control_steps'],
             'physics_replays':physics['episodes'],'physics_steps':physics['control_steps'],
             'excluded_from_method_conclusions':'smoke_a/smoke_b/pilot_a contain pre-repair implementation; preserve as debugging evidence only.',
             'protocol_amendment':'verification_repair_c.md declares one frame-repair exception to the initial two-revision cap; no threshold/parameter changes.'}
    with (RUN/'analysis/final_receipt.json').open('x',encoding='utf8') as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
    print(json.dumps({'status':receipt['status'],'completed':completed,'outcomes':outcomes,'timing':timing,'mechanisms':mechanisms},ensure_ascii=False))
if __name__=='__main__':main()
