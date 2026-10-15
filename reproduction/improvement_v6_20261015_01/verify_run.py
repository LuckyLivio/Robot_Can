"""Audit archived controller, every D2/noise step, and protected file hashes."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,types,concurrent.futures
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'reproduction/recovery_v5_20261012_01'))
import verify_stage as legacy_verify
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5,Config as V5Config

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
    pkg=types.ModuleType('audited_recovery');pkg.__path__=[str(path.parent)];sys.modules[pkg.__name__]=pkg
    name='audited_recovery.recovery_controller';spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--protected',action='store_true');a=p.parse_args()
    stage=RUN/a.stage;start=json.loads((stage/'started.json').read_text());assert (stage/'completed.json').exists()
    for rel,h in start['source_sha256'].items():
        source=stage/'source'/Path(rel).relative_to(RUN.relative_to(ROOT));assert digest(source)==h
    m=load(stage/'source/recovery/recovery_controller.py');stats={'guarded_descents':0,'blocked_frames':0}
    class Audited(m.RecoveryController):
        def choose(self,x,p,previous):
            action,info=super().choose(x,p,previous)
            if self.cfg.aperture_guard and self.guard_scope and info.get('next_mode')=='DESCEND' and info['mode']!='DESCEND':
                assert self.gap_ready(x),(a.stage,'unsettled aperture descent',self.clock)
                stats['guarded_descents']+=1
            if self.cfg.prevent_repeat and info['mode']=='DESCEND' and self.guard_scope:
                assert self.plan_ok,(a.stage,'infeasible descent',self.clock)
            if info['mode']=='BLOCKED':
                # A feedback hold can command downward corrections after an
                # overshoot. Check its elevated target, not the velocity sign.
                assert self.waypoint[2]>=self.floor+self.cfg.approach_clearance_m-1e-7 and action[6]==0
                assert info.get('next_mode','BLOCKED')=='BLOCKED'
                stats['blocked_frames']+=1
            return action,info
    legacy_verify.controller_class=lambda v:(V5,V5Config) if v=='v5' else (Audited,m.Config)
    jobs=json.loads((stage/'jobs.json').read_text());audits=[]
    for j in jobs:audits.append(legacy_verify.audit(stage/j['id']))
    protected=None
    if a.protected:
        manifest=json.loads((RUN/'before_manifest.json').read_text())
        def check(item):
            rel,h=item;assert (ROOT/rel).is_file() and digest(ROOT/rel)==h,rel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(check,manifest.items()))
        protected=len(manifest)
    report={'passed':True,'stage':a.stage,'episodes':sum(r['episodes'] for r in audits),
            'control_steps':sum(r['controls'] for r in audits),'mechanism_checks':stats,
            'old_files_unchanged':protected,'source_archive_verified':True,
            'note':'Controller/FIFO/noise replay from recorded inputs; physical state replay is a separate check.'}
    with (RUN/'analysis'/f'{a.stage}_verification.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
