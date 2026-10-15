"""Replay saved actions, without reevaluating policies or changing outcomes."""
from pathlib import Path
import argparse,json,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
sys.path.insert(0,str(ROOT/'reproduction/extensions_20261012_01'));sys.path.insert(0,str(ROOT))
import h5py,numpy as np
from common import DATA,make_env,restore_demo,pack_obs

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();stage=RUN/a.stage
    jobs=json.loads((stage/'jobs.json').read_text());selected=[]
    for v in ['v9','height','path','v10']:
        for suffix,demo in [('regression_6000005','demo_6000005'),('known_side_s41','demo_97'),
                            ('known_pressure','demo_11000013'),('full_noise','demo_133')]:
            selected.append((next(j for j in jobs if j['id']==v+'_'+suffix),demo))
    env=make_env(False);results=[];contact_diagnosis=[]
    try:
        for j,name in selected:
            with h5py.File(ROOT/j['dataset'] if j.get('dataset') else DATA) as f:obs=restore_demo(env,f['data'][name])
            joint_qadr=env.sim.model.jnt_qposadr[[env.sim.model.joint_name2id('robot0_joint'+str(i)) for i in range(1,8)]]
            n=0
            for line in (stage/j['id']/'trace.jsonl').open():
                r=json.loads(line)
                if r['demo']!=name:continue
                np.testing.assert_array_equal(pack_obs(obs),r['state_before'])
                np.testing.assert_array_equal(env.sim.data.qpos[joint_qadr],r['joint_positions'])
                obs,*_=env.step(np.array(r['executed_action'],np.float32))
                if name=='demo_6000005' and 270<=r['step']<=305:
                    contacts=[];model=env.sim.model
                    for k in range(env.sim.data.ncon):
                        contact=env.sim.data.contact[k];geom_a,geom_b=int(contact.geom1),int(contact.geom2)
                        names=[model.geom_id2name(i) or ('unnamed_'+str(i)) for i in [geom_a,geom_b]]
                        bodies=[model.body_id2name(int(model.geom_bodyid[i])) for i in [geom_a,geom_b]]
                        if any('can' in str(n).lower() for n in names+bodies):
                            contacts.append({'geoms':names,'bodies':bodies,'distance_m':float(contact.dist)})
                    contact_diagnosis.append({'version':j['version'],'step_after':r['step'],'contacts':contacts})
                np.testing.assert_array_equal(pack_obs(obs),r['state_after'])
                np.testing.assert_array_equal(np.asarray(env.staged_rewards()),r['stages_after'])
                assert bool(env._check_success())==r['success_after'];n+=1
            assert n>0
            results.append({'job':j['id'],'demo':name,'steps':n,'max_state_error':0.})
            print(json.dumps(results[-1]),flush=True)
    finally:env.close()
    result={'passed':True,'stage':a.stage,'episodes':len(results),'control_steps':sum(r['steps'] for r in results),'samples':results,
            'note':'Diagnostic sample selection includes the regression; this is physical replay validation, not new independent evaluation.'}
    with (RUN/'analysis'/f'{a.stage}_physics.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    with (RUN/'analysis'/f'{a.stage}_contacts.json').open('x',encoding='utf8') as f:json.dump(contact_diagnosis,f,indent=2)
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
