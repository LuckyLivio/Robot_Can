"""Replay archived decisions, queues and observation-only invariants."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,types
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
import audit_core
from reproduction.improvement_v12_20261015_01.recovery.recovery_controller import RecoveryController as V12,Config as C12
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as C6
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();stage=RUN/a.stage
    assert json.loads((stage/'completed.json').read_text())['source_unchanged']
    for rel,h in json.loads((stage/'started.json').read_text())['source_sha256'].items():
        assert sha(stage/'source'/Path(rel).relative_to(RUN.relative_to(ROOT)))==h
    pkg=types.ModuleType('archived_v13');pkg.__path__=[str(stage/'source/recovery')];sys.modules[pkg.__name__]=pkg
    spec=importlib.util.spec_from_file_location('archived_v13.recovery_controller',stage/'source/recovery/recovery_controller.py')
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    stats={'wait_transfer_steps':0,'protected_descent_steps':0,'planning_wait_steps':0};instances=[]
    class Audited(m.RecoveryController):
        def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);instances.append(self)
        def choose(self,x,proposal,previous):
            before=self.clock;action,info=super().choose(x,proposal,previous)
            assert self.clock==before+1 and self.clock<=400
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
            if info['mode']=='PLAN_WAIT':
                assert (action==0).all();stats['planning_wait_steps']+=1
                cap=self.cfg.mesh_candidates_per_step if info['planning_kind']=='mesh' else self.cfg.ik_iterations_per_step
                assert info['planning_work_units']<=cap
            return action,info
    audit_core.controller_class=lambda v:(V12,C12) if v=='v12' else ((V6,C6) if v=='v6' else (Audited,m.Config))
    result=[]
    for j in json.loads((stage/'jobs.json').read_text()):
        instances.clear();result.append(audit_core.audit(stage/j['id']))
        if j['version'] not in ['v12','v6']:
            records=json.loads((stage/j['id']/'result.json').read_text())['records']
            for r,c in zip(records,instances):
                for k in ['support13_events','escape_events','wait_hold_events','guard_events','pose_events','geometry_events','edge_events','joint_events','planning_events']:
                    assert r[k]==getattr(c,k),(j['id'],r['demo'],k)
    out={'passed':True,'stage':a.stage,'episodes':sum(r['episodes'] for r in result),
         'controls':sum(r['controls'] for r in result),'invariants':stats,'source_snapshot_verified':True}
    with (RUN/'analysis'/f'{a.stage}_verification.json').open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps(out))
