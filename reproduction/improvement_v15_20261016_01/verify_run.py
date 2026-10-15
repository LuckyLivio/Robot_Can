"""Replay archived decisions, queues and observation-only invariants."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,types
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from reproduction.improvement_v9_20261015_01.recovery.kinematics import LIMITS
import audit_core
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import RecoveryController as V13,Config as C13
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import RecoveryController as V14,Config as C14
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as C6
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();stage=RUN/a.stage
    assert json.loads((stage/'completed.json').read_text())['source_unchanged']
    for rel,h in json.loads((stage/'started.json').read_text())['source_sha256'].items():
        assert sha(stage/'source'/Path(rel).relative_to(RUN.relative_to(ROOT)))==h
    pkg=types.ModuleType('archived_v15');pkg.__path__=[str(stage/'source/recovery')];sys.modules[pkg.__name__]=pkg
    spec=importlib.util.spec_from_file_location('archived_v15.recovery_controller',stage/'source/recovery/recovery_controller.py')
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    stats={'wait_transfer_steps':0,'protected_descent_steps':0,'planning_wait_steps':0,'path_recenter_steps':0,'bounded_planning_steps':0,
           'carry_planning_steps':0,'carry_path_steps':0,'carry_guard_steps':0,'carry_hold_steps':0,'edge_pretranslate_steps':0,'edge_pretranslate_transitions':0};instances=[]
    class Audited(m.RecoveryController):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);instances.append(self)
            assert self.cfg.delay==2 and self.cfg.horizon_steps==400 and self.cfg.max_attempts==2
            self.audit_pretranslate_settled=0
        def choose(self,x,proposal,previous):
            before=self.clock;before_mode=self.mode
            before_edge_plan=getattr(self,'edge_plan',None)
            before_carry_plan=getattr(self,'carry_plan',None);before_carry_search=getattr(self,'carry_search',None)
            before_lost_frames=self.lost_frames
            action,info=super().choose(x,proposal,previous)
            assert self.clock==before+1 and self.clock<=400
            assert self.attempts<=2
            if info.get('wait_hold_transition'):
                assert info['stable_hold'] and self.mode=='LIFT' and action[6]==1
                assert self.attempts<=2;stats['wait_transfer_steps']+=1
            if info['mode']=='DESCEND' or info.get('next_mode')=='DESCEND':
                assert self.refresh_feasibility(x)=='feasible' and not self.pose_changed(x)
                stats['protected_descent_steps']+=1
            if info['mode'] in ['POSE_WAIT','POSE_BLOCKED']:assert action[6]==0
            if info['mode']=='WAIT_ESCAPE':
                assert action[6]==0 and info['retreat_hand_margin_m']>=.001 and info['retreat_can_margin_m']>=.001
                assert self.escape_count<=self.cfg.escape_max_replans
            if info['mode']=='PATH_RECENTER':
                assert self.cfg.descent_clearance and action[6]==0
                assert info['hand_margin_m']>=.001 and info['can_margin_m']>=.001
                assert self.recenter_age<=self.cfg.recenter_timeout and self.age<=self.cfg.stage_timeout
                assert all(n<=self.cfg.recenter_max_per_attempt for n in self.recenter_counts.values())
                stats['path_recenter_steps']+=1
            if info['mode'] in ['CARRY_PLAN','CARRY_PATH']:
                assert self.cfg.carry_path and self.mode=='CARRY' and info['stable_hold']
                assert self.ever_stable and action[6]==1
                if info['mode']=='CARRY_PLAN':
                    assert np.array_equal(action[:6],np.zeros(6)) and info['planning_kind']=='v15_carry'
                    assert 'planning_work_units' in info
                    stats['carry_planning_steps']+=1
                else:
                    assert info['accepted'] and info['hand_margin_m']>=.001 and info['carried_can_margin_m']>=.001
                    margin=float(np.min(np.minimum(self.joints-LIMITS[:,0],LIMITS[:,1]-self.joints)))
                    assert margin>=self.cfg.joint_solution_margin_rad
                    stats['carry_path_steps']+=1
            if info['mode']=='CARRY_GUARD':
                assert np.array_equal(action[:6],np.zeros(6)) and action[6]==1
                assert info['next_mode']==self.mode and self.mode!='CARRY'
                stats['carry_guard_steps']+=1
            if info['mode']=='CARRY_HOLD':
                assert self.cfg.carry_path and self.mode=='CARRY' and not info['stable_hold']
                assert np.array_equal(action[:6],np.zeros(6)) and action[6]==1
                assert self.lost_frames==before_lost_frames+1 and self.lost_frames<self.cfg.stable_frames
                assert self.carry_plan is before_carry_plan and self.carry_search is before_carry_search
                stats['carry_hold_steps']+=1
            if before_mode=='EDGE_PRETRANSLATE' or info['mode']=='EDGE_PRETRANSLATE':
                assert self.cfg.segmented_edge
                plan=before_edge_plan if before_edge_plan is not None else self.edge_plan
                assert plan is not None and 'pre_goal' in plan and 'pre_rotation' in plan
                error=float(np.linalg.norm(np.asarray(x[:3])-plan['pre_goal']))
                angle=float(np.linalg.norm(Rotation.from_matrix(plan['pre_rotation']@Rotation.from_quat(x[3:7]).as_matrix().T).as_rotvec()))
                at=error<.009 and angle<.08
                self.audit_pretranslate_settled=self.audit_pretranslate_settled+1 if at else 0
                if info['mode']=='EDGE_PRETRANSLATE':
                    assert info['hand_margin_m']>=.001 and info['can_margin_m']>=.001
                    stats['edge_pretranslate_steps']+=1
                if self.mode=='EDGE_ROTATE':
                    assert at and self.audit_pretranslate_settled>=self.cfg.delay+3 and self.gap_ready(x)
                    stats['edge_pretranslate_transitions']+=1
            else:self.audit_pretranslate_settled=0
            if 'planning_work_units' in info:
                cap=self.cfg.mesh_candidates_per_step if info.get('planning_kind')=='mesh' else self.cfg.ik_iterations_per_step
                assert 0<=info['planning_work_units']<=cap
                stats['bounded_planning_steps']+=1
            if info['mode']=='PLAN_WAIT':
                assert (action==0).all();stats['planning_wait_steps']+=1
                cap=self.cfg.mesh_candidates_per_step if info['planning_kind']=='mesh' else self.cfg.ik_iterations_per_step
                assert info['planning_work_units']<=cap
            return action,info
    audit_core.controller_class=lambda v:(V14,C14) if v=='v14' else ((V13,C13) if v=='v13' else ((V6,C6) if v=='v6' else (Audited,m.Config)))
    result=[]
    for j in json.loads((stage/'jobs.json').read_text()):
        instances.clear();result.append(audit_core.audit(stage/j['id']))
        if j['version'] not in ['v14','v13','v6']:
            records=json.loads((stage/j['id']/'result.json').read_text())['records']
            for r,c in zip(records,instances):
                for k in ['support13_events','escape_events','tracking14_events','clearance14_events','carry15_events','edge15_events','budget15_events','wait_hold_events','guard_events','pose_events','geometry_events','edge_events','joint_events','planning_events']:
                    assert r[k]==getattr(c,k),(j['id'],r['demo'],k)
    out={'passed':True,'stage':a.stage,'episodes':sum(r['episodes'] for r in result),
         'controls':sum(r['controls'] for r in result),'invariants':stats,'source_snapshot_verified':True}
    with (RUN/'analysis'/f'{a.stage}_verification.json').open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps(out))
