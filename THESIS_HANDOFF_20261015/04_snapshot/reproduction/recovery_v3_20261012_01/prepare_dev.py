"""Enforce registered small-test requirements, then compare on the same dev starts."""
import json,argparse
from dataclasses import asdict
from setup_study import ROOT,RUN,write,digest
from recovery_controller import Config
def main(revision,jobs_file,receipt):
    pilot=RUN/revision;qa={}
    for name in ['v3_train','v3_loss','v3_held_stall','v3_old_geometry','v3_full_noise']:
        r=json.loads((pilot/name/'result.json').read_text());assert r['status']=='complete' and all(e['success'] for e in r['records']),name
        qa[name]={'success':len(r['records']),'episodes':len(r['records'])}
    new=json.loads((pilot/'v3_new_geometry/result.json').read_text())['records'];assert all(r['success'] for r in new[2:])
    qa['new_fixtures']={'success':sum(r['success'] for r in new),'episodes':len(new),'remaining':[r['demo'] for r in new if not r['success']]}
    if (pilot/'v3_side_wall/result.json').exists():
        wall=json.loads((pilot/'v3_side_wall/result.json').read_text())['records'];assert all(r['success'] for r in wall[:2])
        qa['side_wall']={'success':sum(r['success'] for r in wall),'episodes':len(wall),'remaining':[r['demo'] for r in wall if not r['success']]}
    old=json.loads((ROOT/'reproduction/recovery_20261012_01/pilot_v3/bc_original/result.json').read_text())['records']
    natural=json.loads((pilot/'v3_train/result.json').read_text())['records']
    assert all(not o['success'] or (n['success'] and n['attempts']==0 and n['steps']==o['steps']) for o,n in zip(old,natural))
    probe=json.loads((RUN/'alignment_branch_probe_d.json').read_text())['results'];assert probe[0]['first_aligned_step'] is None and probe[1]['first_aligned_step'] is not None
    for name in ['recovery_controller.py','evaluate_recovery.py']:assert (pilot/'source'/name).read_bytes()==(RUN/name).read_bytes()
    write(RUN/receipt,{'passed':True,'revision':revision,'checks':qa,'six_original_successes_unchanged':True,'alignment_diagnostic':'Known dev state, equivalent neutral yaw converges within110; old yaw does not. Not held-out evidence.',
        'corner_contacts':json.loads((RUN/'corner_contact_probe.json').read_text()),'sha256':{name:digest(RUN/name) for name in ['recovery_controller.py','evaluate_recovery.py']}})
    jobs=[]
    for oldjob in json.loads((ROOT/'reproduction/recovery_v2_20261012_01/dev_jobs.json').read_text()):
        jobs.append({**oldjob,'version':'v3','config':asdict(Config()),'baseline_result':f"reproduction/recovery_v2_20261012_01/dev_a/{oldjob['id']}/result.json"})
    write(RUN/jobs_file,jobs);print(json.dumps({'pilot_passed':True,'development_episodes':240,'checks':qa}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--revision',default='pilot_d');p.add_argument('--jobs-file',default='dev_jobs_b.json');p.add_argument('--receipt',default='pilot_acceptance_d.json');a=p.parse_args();main(a.revision,a.jobs_file,a.receipt)
