"""Exact completed saved-input recenter audit; no environment or new samples."""
from pathlib import Path
import argparse,copy,csv,hashlib,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
import audit_core
from variants import controller_class
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin
VERSIONS=['v19','v20','recenter','place','v21']
CONDITIONS=['regression_6000005','clearance_profile_6000005']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))
def rel(path):return path.relative_to(ROOT).as_posix()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',default='smoke_a');parser.add_argument('--name',default=None);args=parser.parse_args()
    stage=RUN/args.stage
    assert read(stage/'completed.json')=={'episodes':54,'source_unchanged':True}
    started=read(stage/'started.json');jobs=read(stage/'jobs.json')
    assert sha(stage/'jobs.json')==started['jobs_sha256'] and len(jobs)==54
    # Replay the original controllers only while every used source is still
    # identical to the stage freeze. This is not a new-policy counterfactual.
    hashes={}
    for name,digest in {**started['source_sha256'],**started['dependency_sha256']}.items():
        if (ROOT/name).suffix in ['.py','.json']:
            assert sha(ROOT/name)==digest,name;hashes[name]=digest
    folders={(v,c):stage/(v+'_'+c) for c in CONDITIONS for v in VERSIONS}
    paths=[Path(__file__).resolve(),RUN/'audit_core.py',RUN/'variants.py',stage/'completed.json',stage/'started.json',stage/'jobs.json']
    for folder in folders.values():paths += [folder/'result.json',folder/'trace.jsonl']
    hashes.update({rel(p):sha(p) for p in sorted(set(paths))})
    output=RUN/'analysis'/((args.name or args.stage+'_recenter_diagnosis')+'.json')
    csv_path=output.with_suffix('.csv');assert not output.exists() and not csv_path.exists()
    samples=[];table=[]
    for (version,condition),folder in folders.items():
        base,config=controller_class(version);controls=[];instances=[]
        class Monitored(base):
            def __init__(self,*a,**kw):super().__init__(*a,**kw);instances.append(self)
            def choose(self,x,proposal,previous):
                before=copy.deepcopy(self.recenter);before_count=self.recenter_settled
                action,info=super().choose(x,proposal,previous)
                plan=before if before is not None else self.recenter
                if plan is not None:
                    item={'step':self.clock,'mode':info['mode'],'phase_age':self.age,'recenter_age':self.recenter_age,
                          'settled_count':self.recenter_settled,'before_settled_count':before_count,
                          'plan_retained':self.recenter is not None,'fixed_center_goal':np.asarray(plan['goal']).tolist(),
                          'motion_m':self.motion[:3].tolist(),'action':action.tolist()}
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
        spans=[]
        for row in controls:
            if not row.get('ready'):continue
            if spans and spans[-1]['last']==row['step']-1:
                spans[-1]['last']=row['step'];spans[-1]['controls']+=1
            else:spans.append({'first':row['step'],'last':row['step'],'controls':1})
        events=[e for e in controller.clearance14_events if str(e['event']).startswith('recenter_')]
        sample={'version':version,'condition':condition,'job':receipt['job'],'episodes_replayed':receipt['episodes'],
                'saved_controls_replayed':receipt['controls'],'source_result':rel(folder/'result.json'),
                'max_ready_streak':max((row['settled_count'] for row in controls),default=0),
                'ready_spans':spans,'controls':controls,'clearance_events':events}
        samples.append(sample)
        for row in controls:
            table.append({'version':version,'condition':condition,**{k:row.get(k) for k in ['step','mode','phase_age','recenter_age',
                 'settled_count','before_settled_count','plan_retained','side_error_m','fixed_center_distance_m',
                 'angle_error_rad','remaining_path_margin_m','ready']},
                 **{'predicate_'+k:row.get('predicates',{}).get(k) for k in ['side','fixed_center','angle','remaining_path','aperture']}})
        print(json.dumps({'job':receipt['job'],'passed':True,'controls':receipt['controls'],'recenter_controls':len(controls),
                          'maximum_ready_streak':sample['max_ready_streak']}),flush=True)
    assert all(sha(ROOT/path)==digest for path,digest in hashes.items()),'Source changed during original-input replay'
    result={'passed':True,'source_sha256':hashes,'saved_episodes_replayed':len(samples),
            'saved_controls_replayed':sum(s['saved_controls_replayed'] for s in samples),
            'new_evaluation_samples':0,'new_physical_episodes':0,'physical_simulation_run':False,'samples':samples,
            'thresholds_unchanged':{'side_m':.009,'fixed_center_m':.009,'angle_rad':.08,'remaining_path_m':.003,
                                    'ready_frames':5,'recenter_timeout_controls':24,'D2':2,'total_controls':400},
            'scope':'Exact original saved-input action/diagnostic/FIFO replay with read-only recenter predicate extraction. No environment steps or counterfactual rollout.',
            'interpretation':'Recenter failures are classified from actual individual predicates and phase age. Same phase duration does not establish equal continuous state. Replays are not extra statistical observations.'}
    with output.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    with csv_path.open('x',encoding='utf-8-sig',newline='') as f:
        if table:
            writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    print(json.dumps({'passed':True,'saved_episodes_replayed':len(samples),'new_evaluation_samples':0,'output':rel(output)}))
if __name__=='__main__':main()
