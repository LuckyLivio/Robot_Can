"""Read-only v17 approach/descent handoff diagnosis; no simulator or tuning.

Replay the frozen v17 saved controller inputs exactly, then inspect observed
poses, requested targets, submitted commands, FIFO contents and controller
memory at the phase seam. Budget is a historical local reference, not evidence
that its disabled later protections may be removed.
"""
from collections import Counter, deque
from pathlib import Path
import argparse, copy, hashlib, importlib.util, json, sys, types
import numpy as np
from scipy.spatial.transform import Rotation

RUN=Path(__file__).resolve().parent; ROOT=RUN.parents[1]
OLD=ROOT/'reproduction/improvement_v17_20261019_01'; STAGE=OLD/'smoke_a'
sys.path.insert(0,str(ROOT))
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import RecoveryController as V16,Config as C16
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import RecoveryController as V15,Config as C15
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin
from reproduction.improvement_v11_20261015_01.recovery.path_search import sweep_margin

spec=importlib.util.spec_from_file_location('v18_prior_diagnosis',OLD/'inspect_smoke_edge.py')
prior=importlib.util.module_from_spec(spec);sys.modules[spec.name]=prior;spec.loader.exec_module(prior)
sha=prior.sha; finite=prior.finite
CONDITIONS=['regression_6000005','clearance_profile_6000005','known13_full_s41_noise005_demo_13000022']
VERSIONS=['budget','v16','v17']


def servo_snapshot(controller):
    result={}
    for name,state in getattr(controller,'servo17',{}).items():
        result[name]={k:copy.deepcopy(getattr(state,k,None)) for k in ['phase','held','goal','rotation','bias','last_action']}
    return result


def action_metrics(action, axis):
    action=np.asarray(action,float);delta=action[:3]*.05
    lateral=delta-axis*np.dot(delta,axis) if axis is not None else None
    return {'action':action.tolist(),'translation_m':delta.tolist(),
            'translation_norm_m':float(np.linalg.norm(delta)),
            'rotation_rad':(action[3:6]*.5).tolist(),
            'rotation_norm_rad':float(np.linalg.norm(action[3:6]*.5)),
            'axial_translation_m':float(np.dot(delta,axis)) if axis is not None else None,
            'lateral_translation_m':None if lateral is None else lateral.tolist(),
            'lateral_translation_norm_m':None if lateral is None else float(np.linalg.norm(lateral))}


def observe_pose(x,goal,rotation,axis,motion):
    if goal is None:return None
    r=Rotation.from_quat(x[3:7]).as_matrix();err=x[:3]-goal
    side=err-axis*np.dot(err,axis)
    gap=abs(float(x[7]-x[8]))
    return {'goal_m':np.asarray(goal).tolist(),'target_rotation':np.asarray(rotation).tolist(),
            'position_error_m':float(np.linalg.norm(err)),
            'angle_error_rad':float(np.linalg.norm(Rotation.from_matrix(rotation@r.T).as_rotvec())),
            'axial_error_m':float(np.dot(err,axis)),
            'lateral_error_m':side.tolist(),'lateral_error_norm_m':float(np.linalg.norm(side)),
            'forecast_lateral_error_m':float(np.linalg.norm(side+2*(motion[:3]-axis*np.dot(motion[:3],axis)))),
            'fixed_current_rotation_hand_box_margin_m':float(sweep_margin(x[:3],goal,r,min(.085,gap+.002))),
            'fixed_current_rotation_hand_can_margin_m':float(object_margin(x[:3],goal,r,[gap-.001,gap+.001],x))}


def diagnose(version,condition,module):
    folder=STAGE/f'{version}_{condition}';result_path=folder/'result.json';trace_path=folder/'trace.jsonl'
    saved=json.loads(result_path.read_text());assert saved['status']=='complete'
    job=saved['job'];record=saved['records'][0]
    rows=[json.loads(line) for line in trace_path.read_text().splitlines()]
    cls,cfg=(V15,C15) if version=='budget' else ((V16,C16) if version=='v16' else (module.RecoveryController,module.Config))
    c=cls([.1975,.4025,.8],.8,np.asarray(rows[0]['state_before'],np.float32),job['enabled'],cfg(**job['config']))
    pose_calls=[];original_pose=c.pose_action
    def traced_pose(self,x,goal,grip):
        requested={'phase':self.mode,'goal_m':np.asarray(goal).copy(),
                   'rotation':self.goal_rotation.copy(),'requested_grip':grip}
        action=original_pose(x,goal,grip)
        requested['returned_action']=action.copy();pose_calls.append(requested)
        return action
    c.pose_action=types.MethodType(traced_pose,c)
    pending=deque([np.zeros(7,np.float32),np.zeros(7,np.float32)],maxlen=3)
    previous=np.zeros(7,np.float32);last_submitted=np.zeros(7,np.float32)
    rng=np.random.default_rng(70000+int(record['demo'].split('_')[1]))
    all_rows=[];max_error=0.
    for row in rows:
        assert not row['fault_injected']
        step=row['step'];x=np.asarray(row['state_before'],np.float32)
        c.set_joint_positions(np.asarray(row['joint_positions'],float))
        if job.get('force_recovery_at')==step:c.start_attempt('diagnostic_forced_start',x)
        phase,attempt,age,clock=c.mode,c.attempts,c.age,c.clock
        plan=copy.deepcopy(c.edge_plan);center=copy.deepcopy(c.recenter)
        grasp=c.grasp_target(x).copy() if plan is not None else None
        goal_r=c.goal_rotation.copy()
        axis=plan['rotation'][:,2].copy() if plan is not None else None
        motion=np.zeros(6)
        if c.last_observed is not None:
            motion[:3]=x[:3]-c.last_observed[:3]
            motion[3:]=Rotation.from_matrix(Rotation.from_quat(x[3:7]).as_matrix()@Rotation.from_quat(c.last_observed[3:7]).as_matrix().T).as_rotvec()
        memory=servo_snapshot(c);pose_calls.clear()
        counts={key:len(getattr(c,key,[])) for key in prior.EVENT_FIELDS}
        command,info=c.choose(x,np.asarray(row['original_proposal'],np.float32),previous)
        actual_info=dict(info);expected_info=dict(row['recovery'])
        actual_info.pop('planning_ms',None);expected_info.pop('planning_ms',None)
        assert actual_info==expected_info,(job['id'],step,'diagnostics')
        err=float(np.max(np.abs(command-np.asarray(row['submitted_action']))));max_error=max(max_error,err)
        assert err<=1e-7,(job['id'],step,'action',err)
        np.testing.assert_array_equal(row['queue_before'],list(pending));queue=copy.deepcopy(list(pending))
        pending.append(command.copy());executed=pending.popleft()
        np.testing.assert_array_equal(executed,row['executed_action_before_noise'])
        if job['noise']:executed[:3]+=rng.normal(0,job['noise'],3)
        previous=np.clip(executed,-1,1);np.testing.assert_array_equal(previous,row['executed_action'])
        selected=(phase in ['EDGE_APPROACH','DESCEND'] or center is not None or info.get('mode')=='PATH_RECENTER')
        if selected:
            assert axis is not None
            receipt=info.get('mixed_pose')
            item={'step':step,'logical_phase_before':phase,'command_mode':info['mode'],'mode_after':c.mode,
                  'attempt_before':attempt,'attempt_after':c.attempts,'clock_before':clock,'clock_after':c.clock,
                  'age_before':age,'age_after':c.age,'state_before':x.tolist(),'joint_positions':row['joint_positions'],
                  'actual_observed_motion':motion.tolist(),
                  'gap_m':abs(float(x[7]-x[8])),'target_gap_m':c.approach_gap,
                  'goal_rotation_before':goal_r.tolist(),'goal_rotation_after':c.goal_rotation.tolist(),
                  'approach':observe_pose(x,plan['above'],plan['rotation'],axis,motion),
                  'grasp':observe_pose(x,grasp,plan['rotation'],axis,motion),
                  'recenter_before':center,'recenter_after':copy.deepcopy(c.recenter),
                  'servo_memory_before':memory,'servo_memory_after':servo_snapshot(c),
                  'actual_v17_commit':getattr(c,'_committed17',False),
                  'pose_calls':copy.deepcopy(pose_calls),'mixed_pose':receipt,
                  'submitted':action_metrics(command,axis),'previous_submitted':action_metrics(last_submitted,axis),
                  'translation_command_change_m':float(np.linalg.norm((command[:3]-last_submitted[:3])*.05)),
                  'rotation_command_change_rad':float(np.linalg.norm((command[3:6]-last_submitted[3:6])*.5)),
                  'fifo_before': [action_metrics(a,axis) for a in queue],
                  'executed_before_noise':action_metrics(row['executed_action_before_noise'],axis),
                  'executed_with_noise':action_metrics(row['executed_action'],axis),
                  'events_emitted_this_control':{key:copy.deepcopy(getattr(c,key,[])[n:]) for key,n in counts.items() if len(getattr(c,key,[]))>n},
                  'original_decision_ms':row['decision_ms']}
            all_rows.append(item)
        last_submitted=command.copy()
    for key in prior.EVENT_FIELDS:
        if key in record and hasattr(c,key):assert getattr(c,key)==record[key],(job['id'],key)
    seams=[]
    for i,item in enumerate(all_rows):
        if item['logical_phase_before']=='EDGE_APPROACH' and item['mode_after']=='DESCEND':
            following=[r for r in all_rows[i+1:] if r['logical_phase_before']=='DESCEND' and r['attempt_before']==item['attempt_after']]
            seams.append({'transition_control':item['step'],'last_approach':item,'first_descend':following[0] if following else None,
                          'descend_controls':len(following),'descend_command_modes':dict(Counter(r['command_mode'] for r in following)),
                          'last_descend':following[-1] if following else None,
                          'recenter_control_steps':[r['step'] for r in following if r['recenter_before'] is not None or r['recenter_after'] is not None],
                          'max_lateral_error_m':max([r['grasp']['lateral_error_norm_m'] for r in following],default=None),
                          'first_recenter_event':next((r for r in following if r['events_emitted_this_control'].get('clearance14_events')),None)})
    return {'version':version,'condition':condition,'job':job['id'],'success':record['success'],'steps':record['steps'],
            'saved_controls_replayed':len(rows),'max_action_error':max_error,'diagnostics_queue_noise_events_exact':True,
            'new_physical_episodes':0,'handoffs':seams,'per_control':all_rows,
            'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in [result_path,trace_path]}}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='handoff_diagnosis');args=parser.parse_args()
    target=RUN/'analysis'/(args.name+'.json');assert not target.exists()
    module=prior.frozen_module(STAGE)
    output={'passed':True,'scope':'Exact saved-input replay and current-observation geometry only; no new physics, tuning, or closed-loop improvement claim.',
            'new_physical_episodes':0,'independent_start_count':2,'selected_execution_count':len(CONDITIONS)*len(VERSIONS),
            'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),OLD/'inspect_smoke_edge.py',STAGE/'started.json',STAGE/'completed.json',STAGE/'jobs.json']},
            'cases':[],
            'limitations':['FIFO contents are recorded controller history, not predicted future state.',
                           'Nominal fixed-rotation margins and mixed certificates are different checks; neither proves future D2 motion.',
                           'Budget successes are local historical references; later held-path protection was disabled.',
                           'Event step counters may precede the submitted control number when emitted before hold/choose increments the shared clock. Both are preserved.']}
    for condition in CONDITIONS:
        for version in VERSIONS:
            case=diagnose(version,condition,module);output['cases'].append(case);output['source_sha256'].update(case['source_sha256'])
            print(version,condition,'handoffs',len(case['handoffs']),flush=True)
    output['saved_controls_replayed']=sum(c['saved_controls_replayed'] for c in output['cases'])
    with target.open('x',encoding='utf8') as f:json.dump(finite(output),f,ensure_ascii=False,indent=2,allow_nan=False)
    print(target,flush=True)

if __name__=='__main__':main()
