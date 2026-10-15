"""Training-only pilot acceptance followed by the previously registered dev test."""
import json
from dataclasses import asdict
from setup_study import ROOT,RUN,write,digest
from recovery_controller import Config

def main():
    pilot=RUN/'pilot_b';qa={}
    for name in ['v2_train','v2_loss','v2_held_stall','v2_geometry','v2_geometry_forced','full_v2_noise']:
        r=json.loads((pilot/name/'result.json').read_text());assert r['status']=='complete' and all(e['success'] for e in r['records']),name
        qa[name]={'success':len(r['records']),'episodes':len(r['records'])}
    old=json.loads((ROOT/'reproduction/recovery_20261012_01/pilot_v3/bc_original/result.json').read_text())['records']
    new=json.loads((pilot/'v2_train/result.json').read_text())['records']
    assert all(not o['success'] or (n['success'] and n['attempts']==0 and n['steps']==o['steps']) for o,n in zip(old,new))
    assert (pilot/'source/recovery_controller.py').read_bytes()==(RUN/'recovery_controller.py').read_bytes()
    assert (pilot/'source/evaluate_recovery.py').read_bytes()==(RUN/'evaluate_recovery.py').read_bytes()
    write(RUN/'pilot_acceptance.json',{'passed':True,'revision':'pilot_b','checks':qa,'six_original_successes_unchanged':True,
                                     'sha256':{p.name:digest(p) for p in [RUN/'recovery_controller.py',RUN/'evaluate_recovery.py']}})
    jobs=[]
    for oldjob in json.loads((ROOT/'reproduction/recovery_20261012_01/formal_jobs.json').read_text()):
        j={**oldjob,'version':'v2','config':asdict(Config()),'original_baseline_result':oldjob['baseline_result'],
           'baseline_result':f"reproduction/recovery_20261012_01/formal/{oldjob['id']}/result.json"}
        jobs.append(j)
    write(RUN/'dev_jobs.json',jobs);print(json.dumps({'pilot_passed':True,'development_episodes':240}))

if __name__=='__main__':main()
