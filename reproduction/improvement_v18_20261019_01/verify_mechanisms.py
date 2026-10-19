"""Disabled-component equivalence and inherited-config checks; no physics runs.

This validates backward compatibility for the nine registered diagnostic
profiles. Enabled component geometry/holding/budget predicates require their
own tests plus the complete-stage decision and physical replay audits.
"""
from pathlib import Path
from dataclasses import asdict
import argparse,hashlib,json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
import audit_core
from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v17_20261019_01.recovery.recovery_controller import Config as ParentConfig
FLAGS=['handoff_continuity','short_route_selection']
NEW_EVENTS=['handoff18_events','route18_events']
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def assert_inherited_unchanged(new,old):
    values=asdict(new);parent=asdict(old)
    assert all(values[k]==v for k,v in parent.items()),[(k,v,values.get(k)) for k,v in parent.items() if values.get(k)!=v]
    assert values['delay']==2 and values['horizon_steps']==400 and values['max_attempts']==2
    return len(parent)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='mechanisms_a');args=parser.parse_args()
    output=RUN/'analysis'/f'{args.name}.json';assert not output.exists(),output
    fields=assert_inherited_unchanged(Config(),ParentConfig())
    jobs=[j for j in read(RUN/'protocols/smoke_jobs.json') if j['version']=='v17']
    assert len(jobs)==9 and sum(len(j['demos']) for j in jobs)==9
    paths=[p for p in (RUN/'recovery').iterdir() if p.suffix in ['.py','.json']]
    paths += [RUN/'verify_mechanisms.py',RUN/'audit_core.py',RUN/'protocols/smoke_jobs.json',
              ROOT/'reproduction/improvement_v17_20261019_01/recovery/recovery_controller.py']
    for v in [15,16]:paths += list((ROOT/f'reproduction/improvement_v{v}_20261016_01/recovery').glob('*.py'))
    paths += list((ROOT/'reproduction/improvement_v17_20261019_01/recovery').glob('*.py'))
    for job in jobs:
        result=ROOT/job['baseline_result_v17'];paths += [result,result.parent/'trace.jsonl']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    instances=[]
    class Disabled(RecoveryController):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw);instances.append(self)
            assert not any(getattr(self.cfg,k) for k in FLAGS)
        def choose(self,x,proposal,previous):
            before=self.clock;command,info=super().choose(x,proposal,previous)
            assert self.clock==before+1 and self.clock<=400 and self.attempts<=2
            assert all(not getattr(self,k) for k in NEW_EVENTS)
            return command,info
    def disabled_config(**kw):
        parent=ParentConfig(**kw);new=Config(**{**kw,**{k:False for k in FLAGS}})
        assert_inherited_unchanged(new,parent);return new
    audit_core.controller_class=lambda version:(Disabled,disabled_config)
    results=[]
    for job in jobs:
        source=ROOT/job['baseline_result_v17'];raw=read(source);assert raw['status']=='complete'
        assert raw['job']['demos']==job['demos']
        assert asdict(ParentConfig(**raw['job']['config']))==asdict(ParentConfig(**job['config']))
        instances.clear();receipt=audit_core.audit(source.parent)
        assert len(instances)==len(raw['records'])
        for controller,record in zip(instances,raw['records']):
            for field in ['support13_events','escape_events','tracking14_events','clearance14_events','wait_hold_events',
                          'carry15_events','edge15_events','budget15_events','ik16_events','held16_events','edge16_events','route17_events','edge17_events','held17_events','guard_events','pose_events','geometry_events','edge_events','joint_events','planning_events']:
                assert record[field]==getattr(controller,field),(job['id'],field)
        results.append({'registered_job':job['id'],'comparison_profile':job['comparison_profile'],
                        'source_result':job['baseline_result_v17'],'source_result_sha256':sha(source),
                        'source_trace_sha256':sha(source.parent/'trace.jsonl'),**receipt})
        print(job['id'],receipt['episodes'],receipt['controls'],flush=True)
    assert sum(r['episodes'] for r in results)==9
    assert all(sha(ROOT/p)==h for p,h in hashes.items()),'Source changed during replay'
    out={'passed':True,'validation_scope':'Two new components disabled: exact saved-input decisions, diagnostics, FIFO, noise, clock and inherited configuration. No physical simulation or new evaluation samples.',
         'inherited_config_fields':fields,'inherited_defaults_unchanged':True,'profiles_checked':9,
         'disabled_episodes':sum(r['episodes'] for r in results),'disabled_controls':sum(r['controls'] for r in results),
         'new_component_effectiveness_not_established':True,'source_sha256':hashes,'cases':results}
    with output.open('x',encoding='utf8') as f:json.dump(out,f,indent=2)
    print(json.dumps({k:v for k,v in out.items() if k not in ['source_sha256','cases']}))
