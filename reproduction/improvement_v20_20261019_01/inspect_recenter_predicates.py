"""Exact saved-input replay to expose original recenter predicates; no physics."""
from pathlib import Path
import argparse,copy,hashlib,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
import audit_core
from variants import controller_class
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='recenter_predicates_a');a=parser.parse_args()
    stage=RUN/'smoke_a';assert read(stage/'completed.json')=={'episodes':54,'source_unchanged':True}
    output=RUN/'analysis'/f'{a.name}.json';assert not output.exists()
    folders={v:stage/(v+'_regression_6000005') for v in ['v19','directional']}
    paths=[Path(__file__).resolve(),RUN/'audit_core.py',RUN/'variants.py',stage/'completed.json',stage/'started.json',stage/'jobs.json']
    for folder in folders.values():paths += [folder/'result.json',folder/'trace.jsonl']
    for v in range(6,21):
        for directory in (ROOT/'reproduction').glob(f'improvement_v{v}_*/recovery'):
            paths += [p for p in directory.iterdir() if p.suffix in ['.py','.json']]
    paths += list((ROOT/'reproduction/recovery_v5_20261012_01').glob('*.py'))
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))};samples=[]
    for version,folder in folders.items():
        base,config=controller_class(version);controls=[];instances=[]
        class Monitored(base):
            def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);instances.append(self)
            def choose(self,x,proposal,previous):
                before=copy.deepcopy(self.recenter);before_count=self.recenter_settled
                action,info=super().choose(x,proposal,previous)
                plan=before if before is not None else self.recenter
                if plan is not None and self.clock>=300:
                    item={'step':self.clock,'mode':info['mode'],'phase_age':self.age,'recenter_age':self.recenter_age,
                          'settled_count':self.recenter_settled,'before_settled_count':before_count,
                          'plan_retained':self.recenter is not None,'fixed_center_goal':np.asarray(plan['goal']).tolist()}
                    if info['mode']=='PATH_RECENTER':
                        gap=abs(float(x[7]-x[8]));rotation=Rotation.from_quat(x[3:7]).as_matrix();goal=self.grasp_target(x)
                        e=x[:3]-goal;side=e-plan['axis']*float(e@plan['axis'])
                        distance=float(np.linalg.norm(np.asarray(plan['goal'])-x[:3]))
                        angle=float(np.linalg.norm(Rotation.from_matrix(self.edge_plan['rotation']@rotation.T).as_rotvec()))
                        tail=object_margin(x[:3],goal,rotation,[gap-.001,gap+.001],x)
                        predicates={'side':np.linalg.norm(side)<self.cfg.recenter_settle_m,'fixed_center':distance<.009,
                                    'angle':angle<.08,'remaining_path':tail>=.003,'aperture':self.gap_ready(x)}
                        ready=all(predicates.values())
                        assert self.recenter_settled==(before_count+1 if ready else 0)
                        item.update(side_error_m=float(np.linalg.norm(side)),fixed_center_distance_m=distance,
                                    angle_error_rad=angle,remaining_path_margin_m=float(tail),
                                    predicates={k:bool(v) for k,v in predicates.items()},ready=ready,
                                    hand_margin_m=info['hand_margin_m'],can_margin_m=info['can_margin_m'])
                    controls.append(item)
                return action,info
        audit_core.controller_class=lambda _:(Monitored,config)
        receipt=audit_core.audit(folder);controller=instances[0]
        samples.append({'version':version,**receipt,'source_result':(folder/'result.json').relative_to(ROOT).as_posix(),
                        'max_ready_streak':max((row['settled_count'] for row in controls),default=0),
                        'controls':controls,'clearance_events':controller.clearance14_events})
    parent=list(map(json.loads,(folders['v19']/'trace.jsonl').open(encoding='utf8')))
    child=list(map(json.loads,(folders['directional']/'trace.jsonl').open(encoding='utf8')))
    first=next(i for i,(old,new) in enumerate(zip(parent,child)) if old['submitted_action']!=new['submitted_action'])
    old,new=parent[first],child[first];assert old['state_before']==new['state_before']
    source=old['recovery']['mixed_pose'];candidate=new['recovery']['mixed_pose']
    first_difference={'step':new['step'],'same_state_before':True,'same_queue_before':old['queue_before']==new['queue_before'],
                      'direction20':candidate['direction20'],'old_raw_translation_m':source['raw_translation_m'],
                      'new_raw_translation_m':candidate['raw_translation_m'],
                      'old_submitted_action':old['submitted_action'],'new_submitted_action':new['submitted_action'],
                      'first_state_before_difference':next(row['step'] for before,row in zip(parent,child) if before['state_before']!=row['state_before'])}
    assert all(sha(ROOT/rel)==digest for rel,digest in hashes.items()),'Sources changed during diagnostic replay'
    result={'passed':True,'source_sha256':hashes,'saved_episodes_replayed':2,'saved_controls_replayed':sum(s['controls'] if isinstance(s['controls'],int) else 400 for s in samples),
            'new_evaluation_samples':0,'physical_simulation_run':False,'first_difference':first_difference,'samples':samples,
            'scope':'Exact saved-input action/diagnostic/FIFO replay with read-only recenter predicate extraction. No environment step or counterfactual rollout.',
            'interpretation':'The first action difference occurs at identical state/queue; after that the complete trajectories differ. This establishes the observed control chain, not an isolated causal effect of one direction coefficient.'}
    # audit_core uses controls as a count; samples expose the detailed list.
    result['saved_controls_replayed']=sum(read(folder/'result.json')['records'][0]['steps'] for folder in folders.values())
    with output.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps({'passed':True,'saved_controls_replayed':result['saved_controls_replayed'],'new_evaluation_samples':0,
                      'first_difference':first_difference['step'],'first_state_difference':first_difference['first_state_before_difference'],
                      'max_ready_streak':{s['version']:s['max_ready_streak'] for s in samples}}))
if __name__=='__main__':main()
