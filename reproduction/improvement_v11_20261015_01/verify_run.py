"""Replay archived pilot decisions and confirm the preserved project hashes."""
from pathlib import Path
import argparse, concurrent.futures, hashlib, importlib.util, json, sys, types
ROOT=Path(__file__).resolve().parents[2]; RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
import audit_core as legacy
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as V6Config
from reproduction.improvement_v10_20261015_01.recovery.recovery_controller import RecoveryController as V10,Config as V10Config

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
    pkg=types.ModuleType('audited_v11');pkg.__path__=[str(path.parent)];sys.modules[pkg.__name__]=pkg
    name=pkg.__name__+'.recovery_controller';spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--protected',action='store_true');p.add_argument('--current',action='store_true');a=p.parse_args()
    stage=RUN/a.stage;start=json.loads((stage/'started.json').read_text())
    assert json.loads((stage/'completed.json').read_text())['source_unchanged']
    for rel,h in start['source_sha256'].items():
        source=stage/'source'/Path(rel).relative_to(RUN.relative_to(ROOT));assert digest(source)==h
    m=load(RUN/'recovery/recovery_controller.py' if a.current else stage/'source/recovery/recovery_controller.py')
    stats={'unknown_guard_descent_steps':0,'pose_guard_descent_steps':0,'pose_wait_steps':0,'pose_blocked_steps':0}
    instances=[]
    class Audited(m.RecoveryController):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);instances.append(self)
        def choose(self,x,p,previous):
            action,info=super().choose(x,p,previous)
            descending=info['mode']=='DESCEND' or info.get('next_mode')=='DESCEND'
            if descending and self.cfg.unknown_guard:
                assert self.refresh_feasibility(x)=='feasible',(a.stage,'unknown descent',self.clock)
                stats['unknown_guard_descent_steps']+=1
            if descending and self.cfg.replan_on_change:
                assert not self.pose_changed(x),(a.stage,'stale pose descent',self.clock)
                stats['pose_guard_descent_steps']+=1
            if info['mode'] in ['POSE_WAIT','POSE_BLOCKED']:
                assert self.waypoint[2]>=self.floor+self.cfg.approach_clearance_m-1e-7
                assert action[6]==0
                stats['pose_wait_steps' if info['mode']=='POSE_WAIT' else 'pose_blocked_steps']+=1
            if info['mode']=='PLAN_WAIT':
                assert (action==0).all() and info['feasibility']=='unknown'
                if self.cfg.bounded_planning:
                    cap=self.cfg.mesh_candidates_per_step if info['planning_kind']=='mesh' else self.cfg.ik_iterations_per_step
                    assert info['planning_work_units']<=cap
            if descending:assert not self.kinematic_blocked
            if info['mode']=='DESCEND' and self.cfg.can_guard and self.edge_plan is not None:
                import numpy as np
                from scipy.spatial.transform import Rotation
                rot=Rotation.from_quat(x[3:7]).as_matrix();gap=abs(float(x[7]-x[8]))
                assert m.object_margin(x[:3],self.grasp_target(x),rot,[gap-.001,gap+.001],x)>=.001
                stats['can_guard_descents']=stats.get('can_guard_descents',0)+1
            return action,info
    legacy.controller_class=lambda v:(V10,V10Config) if v=='v10' else (Audited,m.Config)
    audits=[]
    for j in json.loads((stage/'jobs.json').read_text()):
        instances.clear();audits.append(legacy.audit(stage/j['id']))
        if j['version']!='v10':
            records=json.loads((stage/j['id']/'result.json').read_text())['records']
            assert len(records)==len(instances)
            for r,c in zip(records,instances):
                assert r['guard_events']==c.guard_events and r['pose_events']==c.pose_events
                assert r['pose_replans']==c.pose_replans
                assert r['geometry_events']==c.geometry_events and r['edge_events']==c.edge_events
                assert r['joint_events']==c.joint_events and r['planning_events']==c.planning_events
    protected=None
    if a.protected:
        manifest=json.loads((RUN/'before_manifest.json').read_text())
        def check(item):
            rel,h=item;path=RUN/'before'/rel if rel in ['README.md','index.html'] else ROOT/rel
            assert path.is_file() and digest(path)==h,rel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(check,manifest.items()))
        protected=len(manifest)
    report={'passed':True,'stage':a.stage,'episodes':sum(r['episodes'] for r in audits),
            'control_steps':sum(r['controls'] for r in audits),'mechanism_checks':stats,
            'old_assets_or_exact_entrypoint_backups_verified':protected,'source_archive_verified':True,
            'note':'Recorded-input controller/FIFO/noise equality and invariant audit, not a success gate or continuous collision certificate.'}
    report['controller_source']='current timing-only guard fix' if a.current else 'archived physical-run source'
    if a.current:report['current_source_sha256']={p.relative_to(RUN).as_posix():digest(p) for p in (RUN/'recovery').glob('*.py')}
    suffix='_current_verification.json' if a.current else '_verification.json'
    with (RUN/'analysis'/f'{a.stage}{suffix}').open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
