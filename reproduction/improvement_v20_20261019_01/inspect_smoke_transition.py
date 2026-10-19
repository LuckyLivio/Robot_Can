"""Read completed saved trajectories for upstream timing; no control or physics."""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
VERSIONS=['v17','v19','budget','directional','braking','v20']
CASES=['regression_6000005','clearance_profile_6000005','known_full_s23_clean_demo_12000036',
       'known13_bc_k2_noise005_demo_13000021','known13_full_s41_noise005_demo_13000022']
PHASES=['DESCEND','CLOSE','TEST_LIFT','LIFT','CARRY','PLACE','RELEASE']

def read(path):return json.loads(path.read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def suffix(job):
    prefix=job['version']+'_';assert job['id'].startswith(prefix)
    return job['id'][len(prefix):]
def compact_schedule(value):
    return {k:value[k] for k in ['minimum_command_schedule','estimated_steps','remaining_steps_observed',
            'minimum_command_schedule_fits','nominal_estimate_fits','planning_steps_already_spent'] if k in value}
def option_summary(option):
    result={k:option[k] for k in ['candidate','accepted','status','reason','candidate_work','candidate_work_limit',
            'optional_endpoint_candidate','short_verified_route','endpoint_family','admission'] if k in option}
    for key in ['schedule_at_start','schedule_at_finish']:
        if key in option:result[key]=compact_schedule(option[key])
    ik=option.get('path_ik',[])
    if ik:
        result['ik_targets_recorded']=len(ik)
        result['last_ik']={k:ik[-1][k] for k in ['stage','success','iterations','position_error_m','angle_error_rad','limit_margin_rad'] if k in ik[-1]}
    return result
def search_summaries(record):
    # Inherited modules copy the same completed-search receipt into several
    # event lists. Choose one actual provenance list rather than count copies.
    for key in ['budget19_events','route18_events','route17_events','ik16_events','carry15_events']:
        events=[e for e in record.get(key,[]) if 'options' in e]
        if events:
            return [{'source_event_list':key,'step':e['step'],'event':e.get('event'),'chosen':e.get('chosen'),
                     'work':e.get('work'),'options':[option_summary(o) for o in e['options']]} for e in events]
    return []
def first_difference(left,right,field):
    for a,b in zip(left,right):
        av=a['recovery'].get('mode') if field=='mode' else a[field]
        bv=b['recovery'].get('mode') if field=='mode' else b[field]
        if av!=bv:return a['step']
    return None
def summarize(job,record,rows):
    assert len(rows)==record['steps'] and [r['step'] for r in rows]==list(range(1,len(rows)+1))
    assert bool(rows[-1]['success_after'])==bool(record['success'])
    modes=Counter(row['recovery']['mode'] for row in rows);segments=[]
    for row in rows:
        mode=row['recovery']['mode']
        if not segments or segments[-1]['mode']!=mode:segments.append({'mode':mode,'first':row['step'],'last':row['step'],'controls':1})
        else:segments[-1]['last']=row['step'];segments[-1]['controls']+=1
    first_modes={mode:next(row['step'] for row in rows if row['recovery']['mode']==mode) for mode in modes}
    entries={phase:next((e['step'] for e in record.get('events',[]) if e.get('to')==phase),None) for phase in PHASES}
    descend=[];recenter=[];directions=[]
    for row in rows:
        info=row['recovery'];receipt=info.get('mixed_pose',{})
        if info['mode']=='DESCEND':
            descend.append({'step':row['step'],'attempt':info['attempts'],'next_mode':info.get('next_mode'),
                            'position_error_m':receipt.get('position_error_m'),
                            'orientation_error_rad':receipt.get('orientation_error_rad'),
                            'accepted_certificate':receipt.get('accepted'),'handoff_applied':info.get('handoff18_applied'),
                            'eef_object_distance_m':info.get('eef_object_distance_m')})
        if info['mode']=='PATH_RECENTER':
            recenter.append({'step':row['step'],'side_error_m':info.get('side_error_m'),
                             'hand_margin_m':info.get('hand_margin_m'),'can_margin_m':info.get('can_margin_m')})
        d=receipt.get('direction20')
        if d is not None:
            directions.append({'step':row['step'],'applied':info.get('handoff18_applied'),
                               'accepted':receipt.get('accepted'),**d})
    return {'version':job['version'],'condition':suffix(job),'demo':record['demo'],
            'success':record['success'],'steps':record['steps'],'attempts':record['attempts'],
            'method':job['method'],'seed':job['seed'],'noise':job['noise'],'comparison_profile':job['comparison_profile'],
            'first_entry_step':entries,'first_output_mode_step':first_modes,'output_mode_controls':dict(modes),
            'mode_segments':segments,'transition_events':record.get('events',[]),
            'descend_controls':descend,'recenter_controls':recenter,'direction_controls':directions,
            'direction_summary':{'proposals':len(directions),'submitted':sum(d.get('applied') is True for d in directions),
                                 'axial_braking':sum(d.get('axial_braking',False) for d in directions),
                                 'lateral_braking':sum(d.get('lateral_braking',False) for d in directions)},
            'candidate_searches':search_summaries(record),
            'final_mode':rows[-1]['recovery']['mode'],'final_next_mode':rows[-1]['recovery'].get('next_mode')}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',default='smoke_a');parser.add_argument('--name',default='transition_diagnosis_a');args=parser.parse_args()
    stage=RUN/args.stage;completed=read(stage/'completed.json');assert completed=={'episodes':54,'source_unchanged':True}
    outputs=[RUN/'analysis'/f'{args.name}.json',RUN/'analysis'/f'{args.name}.csv'];assert all(not p.exists() for p in outputs)
    jobs=read(stage/'jobs.json');assert len(jobs)==54 and {j['version'] for j in jobs}==set(VERSIONS)
    paths=[Path(__file__).resolve(),stage/'jobs.json',stage/'started.json',stage/'completed.json',RUN/'protocols/protocol_lock.json']
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in paths};all_rows={};cases=[]
    for job in jobs:
        condition=suffix(job)
        if condition not in CASES:continue
        folder=stage/job['id'];result_path=folder/'result.json';trace_path=folder/'trace.jsonl'
        result=read(result_path);assert result['status']=='complete' and result['job']==job and len(result['records'])==1
        record=result['records'][0];rows=list(map(json.loads,trace_path.open(encoding='utf8')))
        assert all(row['demo']==record['demo'] for row in rows)
        cases.append(summarize(job,record,rows));all_rows[condition,job['version']]=rows
        for path in [result_path,trace_path]:sources[path.relative_to(ROOT).as_posix()]=sha(path)
    assert len(cases)==30
    for case in cases:
        key=case['condition'];own=all_rows[key,case['version']]
        for parent in ['v17','v19']:
            before=all_rows[key,parent];assert own[0]['state_before']==before[0]['state_before']
            case['first_difference_vs_'+parent]={field:first_difference(own,before,field) for field in ['submitted_action','state_after','mode']}
            # This describes a common trace prefix only; divergent trajectories
            # do not isolate later actions into same-state causal comparisons.
            case['length_difference_vs_'+parent]=len(own)-len(before)
    summaries=[]
    for condition in CASES:
        for version in VERSIONS:
            case=next(c for c in cases if c['condition']==condition and c['version']==version)
            entries=case['first_entry_step'];counts=case['output_mode_controls']
            summaries.append({'condition':condition,'version':version,'success':case['success'],'steps':case['steps'],
                **{'enter_'+phase:entries[phase] for phase in PHASES},
                'descend_controls':counts.get('DESCEND',0),'recenter_controls':counts.get('PATH_RECENTER',0),
                'first_descend_control':case['first_output_mode_step'].get('DESCEND'),
                'remaining_after_enter_carry':400-entries['CARRY'] if entries['CARRY'] is not None else None,
                'first_action_difference_vs_v19':case['first_difference_vs_v19']['submitted_action'],
                'candidate_search_completions':len(case['candidate_searches']),
                'accepted_searches':sum(bool(s['chosen']) for s in case['candidate_searches'])})
    assert all(sha(ROOT/rel)==digest for rel,digest in sources.items()),'Saved inputs changed while analyzing'
    out={'passed':True,'stage':args.stage,'scope':'Saved-trace upstream timing only; no new decisions, physics, starts or evaluation samples.',
         'selected_conditions':5,'selected_evaluations':30,'whole_stage_evaluations':54,'new_evaluation_samples':0,
         'phase_time_semantics':'enter_* is the controller event step; first_output_mode_step is the first command labeled with that mode. An event may enter the next phase on the prior phase final command.',
         'interpretation_limits':['Nine profiles in the experiment reuse eight physical starts; both 6000005 profiles are not independent starts.',
             'Shared search receipts are deduplicated by selecting the most specific existing event list.',
             'Unknown IK/admission/schedule means not confirmed under the bounded search, not proved physically impossible.',
             'Minimum command schedule and nominal lookahead are control heuristics, not physical time bounds or future state certificates.',
             'After the first action difference, later timing differences are whole-trajectory effects, not same-state isolated effects.',
             'Budget uses different protections and is descriptive only; no adoption or generalization claim follows.'],
         'source_sha256':sources,'summary':summaries,'cases':cases}
    with outputs[0].open('x',encoding='utf8') as f:json.dump(out,f,indent=2,allow_nan=False)
    with outputs[1].open('x',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)
    print(json.dumps({'passed':True,'selected_evaluations':30,'new_evaluation_samples':0,'summary':summaries}))
if __name__=='__main__':main()
