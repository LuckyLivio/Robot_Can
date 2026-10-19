"""Compact source-bound control evidence from completed stored v21 trajectories."""
from pathlib import Path
import hashlib,json
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def main():
    path=RUN/'analysis/smoke_a_handoff_diagnosis.json';rp=RUN/'analysis/smoke_a_recenter_diagnosis.json'
    d=read(path);r=read(rp);assert d['passed'] and r['passed']
    assert d['selected_evaluation_executions']==54 and r['saved_episodes_replayed']==10
    sources=[Path(__file__),path,rp,RUN/'analysis/smoke_a.json',RUN/'validation/development_gate.json']
    cases={(c['version'],c['condition']):c for c in d['cases']}
    evidence={'passed':True,'new_physical_episodes':0,'new_evaluation_samples':0,
              'actual_completed_executions':54,'actual_controls':sum(c['steps'] for c in d['cases']),
              'saved_recenter_replays':10,'saved_recenter_replayed_controls':r['saved_controls_replayed'],
              'version_summary':d['version_summary'], 'recenter':[], 'terminal_12000036':[],
              'carry_6000005':[], 'phase_12000011':[]}
    for sample in r['samples']:
        evidence['recenter'].append({'version':sample['version'],'condition':sample['condition'],
            'related_controls_including_planning_exit':len(sample['controls']),
            'pure_PATH_RECENTER_controls':sum(x['mode']=='PATH_RECENTER' for x in sample['controls']),
            'ready_spans':sample['ready_spans'],'events':sample['clearance_events'],
            'step320':next((x for x in sample['controls'] if x['step']==320),None)})
    condition='known_full_s23_clean_demo_12000036'
    traces={}
    for v in ['v19','v20','recenter','place','v21']:
        c=cases[v,condition];tp=RUN/'smoke_a'/c['job']/'trace.jsonl';sources.append(tp)
        assert sha(tp)==d['source_sha256'][rel(tp)]
        rows=list(map(json.loads,tp.open(encoding='utf8')));traces[v]=rows
        samples=[]
        for step in [363,382,383,386,389,390,391,392,393,394,400]:
            row=rows[step-1];x=np.asarray(row['state_before']);m=row['recovery'];receipt=m.get('mixed_pose',{})
            samples.append({'step':step,'mode':m['mode'],'next_mode':m.get('next_mode'),
                'observed_object_height_m':float(x[18]),'observed_object_xy_error_m':float(np.linalg.norm(x[16:18]-[.1975,.4025])),
                'original_release_height_pass':bool(x[18]<.9),'original_release_xy_pass':bool(np.linalg.norm(x[16:18]-[.1975,.4025])<.05),
                'submitted_grip':row['submitted_action'][6],'executed_grip_before_noise':row['executed_action_before_noise'][6],
                'place21_present':'place21' in receipt,'braking20_present':'braking20' in receipt,
                'observed_state':row['state_before'],'submitted_action':row['submitted_action'],'fifo_before':row['queue_before']})
        evidence['terminal_12000036'].append({'version':v,'success':c['success'],'phase_segments':c['held_pose_segments'],
              'entry_CARRY':c['first_carry_clock'],'entry_PLACE':c['first_place_clock'],'entry_RELEASE':c['first_release_clock'],
              'release_tail':c['release_tails'],'place21_summary':c['place21_summary'],'samples':samples})
    evidence['terminal_same_clock_state_difference']=[x for x in d['paired_component_descriptions']
        if x['profile'][0]==condition and ((x['variant']=='v21' and x['reference']=='v20') or
                                        (x['variant']=='place' and x['reference']=='v19'))]
    for v in ['v19','v20','recenter','place','v21']:
        for condition in ['regression_6000005','clearance_profile_6000005']:
            c=cases[v,condition]
            evidence['carry_6000005'].append({k:c[k] for k in ['version','condition','success','steps','first_close_clock',
                'first_carry_clock','first_place_clock','held_pose_segments','handoff21_summary','place21_summary']})
        c=cases[v,'known_bc_k2_clean_demo_12000011']
        evidence['phase_12000011'].append({k:c[k] for k in ['version','subsequent_milestones','held_pose_segments',
                                                                          'place21_summary','success','steps']})
    evidence['entry_and_first_difference']=[x for x in d['paired_component_descriptions']
        if x['profile'][0] in ['regression_6000005','clearance_profile_6000005'] and x['reference']=='v19']
    evidence['interpretation_limits']=[
        'No new physics, alternative commands or counterfactual outcomes are generated.',
        'Equal phase-entry clocks do not imply equal observed poses, velocities, joints or pending commands.',
        'At PLACE-to-RELEASE, the release predicate is evaluated before the held helper. The later fallback cannot retroactively change the current predicate; its later physical effect remains a separate question.',
        'Four CARRY-ready frames at400 is not one control from task success: PLACE and RELEASE still remain, and no future readiness is assumed.',
        'Recenter-related frames and pure PATH_RECENTER commands are different counts. EDGE/recenter have their own five-frame requirements; held-pose streaks here concern guarded CARRY, not PLACE release.']
    evidence['source_sha256']={rel(p):sha(p) for p in sources}
    output=RUN/'analysis/control_conclusions_a.json';assert not output.exists()
    with output.open('x',encoding='utf8') as f:json.dump(evidence,f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({'passed':True,'output':rel(output),'actual_controls':evidence['actual_controls'],
                      'new_physical_episodes':0,'saved_recenter_controls':r['saved_controls_replayed']}))
if __name__=='__main__':main()
