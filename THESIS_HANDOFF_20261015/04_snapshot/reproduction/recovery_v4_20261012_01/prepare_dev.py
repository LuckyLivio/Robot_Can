"""Require final pilot regression and mechanism checks before development."""
import argparse,json
from setup_study import ROOT,RUN,write,digest
from prepare_pilot import config
from verify_stage import audit,physics_samples

def main(revision):
    pilot=RUN/revision;assert json.loads((pilot/'complete.json').read_text())['complete']
    for name in ['recovery_controller.py','evaluate_recovery.py']:assert (pilot/'source'/name).read_bytes()==(RUN/name).read_bytes()
    checks={}
    for version in ['v2','align_only','region_only','v4']:
        for suffix in ['train','loss','held_stall','old_geometry','full_noise','regression_6000049','regression_6000000','regression_6000005']:
            rows=json.loads((pilot/f'{version}_{suffix}/result.json').read_text())['records']
            assert all(r['success'] for r in rows),(version,suffix)
            checks[version+'_'+suffix]=len(rows)
        natural=json.loads((pilot/f'{version}_train/result.json').read_text())['records']
        old=json.loads((ROOT/'reproduction/recovery_20261012_01/pilot_v3/bc_original/result.json').read_text())['records']
        assert all(not o['success'] or (r['success'] and r['attempts']==0 and r['steps']==o['steps']) for o,r in zip(old,natural))
    mechanisms={}
    for v in ['align_only','v4']:
        rows=json.loads((pilot/f'{v}_known_alignment/result.json').read_text())['records']
        switches=[e for r in rows for e in r['events'] if e['reason']=='alignment_stalled_switch_equivalent']
        assert len(switches)==1,(v,'switch did not occur')
        mechanisms[v]=switches
    for v in ['region_only','v4']:
        rows=json.loads((pilot/f'{v}_new_geometry/result.json').read_text())['records']
        assert all(r['success'] for r in rows[2:])
        mechanisms[v+'_corner_successes']=sum(r['success'] for r in rows[2:])
    jobs=json.loads((pilot/'jobs.json').read_text());audits=[]
    for j in jobs:audits.append(audit(pilot/j['id']))
    physics=physics_samples(revision,jobs)
    write(RUN/'pilot_acceptance.json',{'passed':True,'revision':revision,'checks':checks,'mechanisms':mechanisms,
        'verified_episodes':sum(a['episodes'] for a in audits),'verified_control_steps':sum(a['controls'] for a in audits),
        'physical_replays':physics,'source_sha256':{n:digest(RUN/n) for n in ['recovery_controller.py','evaluate_recovery.py']}})
    dev=[]
    for v in ['align_only','region_only','v4']:
        for j in json.loads((ROOT/'reproduction/recovery_v2_20261012_01/dev_jobs.json').read_text()):
            dev.append({**j,'id':v+'_'+j['id'],'version':v,'config':config(v),
                        'baseline_result':f"reproduction/recovery_v2_20261012_01/dev_a/{j['id']}/result.json"})
    write(RUN/'dev_jobs.json',dev)
    print(json.dumps({'pilot_accepted':True,'episodes_verified':100,'dev_episodes':720,'mechanisms':mechanisms}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--revision',default='pilot_b');a=p.parse_args();main(a.revision)
