"""Physical actuator checks and exact comparison with the unchanged evaluator."""
import argparse,json,sys
from pathlib import Path
from types import SimpleNamespace
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
sys.path.insert(0,str(ROOT));sys.path.append(str(ROOT/'reproduction/extensions_20261012_01'))
import h5py,numpy as np
from scipy.spatial.transform import Rotation
from common import DATA,make_env,restore_demo,pack_obs
from snapshot import Snapshot
from recovery_controller import RecoveryController
from reproduction.multiseed_20261012_01.evaluate_suite import run as original_run
from setup_study import write,digest


def physical():
    env=make_env(False)
    try:
        with h5py.File(DATA) as data:obs=restore_demo(env,data['data']['demo_54'])
        x=pack_obs(obs);saved=Snapshot(env);gaps=[];heights=[]
        for grip in [-1,1]:
            saved.restore()
            for _ in range(14):o,*_=env.step(np.array([0,0,0,0,0,0,grip],np.float32))
            xx=pack_obs(o);gaps.append(float(abs(xx[7]-xx[8])))
        assert gaps[0]>gaps[1]+.04,(gaps,'gripper sign')
        for direction in [-1,1]:
            saved.restore()
            for _ in range(6):o,*_=env.step(np.array([0,0,.2*direction,0,0,0,-1],np.float32))
            heights.append(float(pack_obs(o)[2]))
        assert heights[0]<x[2]<heights[1],(heights,'world z')
        saved.restore();o=obs
        supervisor=RecoveryController([.1975,.4025,.8],.8,x)
        supervisor.goal_rotation=Rotation.from_euler('z',np.pi/2).as_matrix()@Rotation.from_quat([1,0,0,0]).as_matrix()
        def error(o):return np.linalg.norm(Rotation.from_matrix(supervisor.goal_rotation@Rotation.from_quat(pack_obs(o)[3:7]).as_matrix().T).as_rotvec())
        before=float(error(o))
        for _ in range(70):o,*_=env.step(supervisor.pose_action(pack_obs(o),x[:3],-1))
        after=float(error(o));assert after<.15 and after<before/4,(before,after,'orientation frame')
        return {'open_gap_m':gaps[0],'closed_gap_m':gaps[1],'initial_height_m':float(x[2]),
                'negative_positive_z_heights_m':heights,'rotation_error_before_after_rad':[before,after]}
    finally:env.close()


def equivalence(pilot,out):
    names=json.loads((RUN/'pilot_plan.json').read_text())['training_demos'][:2];results=[]
    for method,noise,newjob in [('bc_shift',0.,'bc_original'),('bc_shift',.05,'bc_k2_disabled_noise'),('wm',.05,'full_disabled_noise')]:
        directory=out/newjob
        args=SimpleNamespace(method=method,model='multiseed_20261012_01_full_s17',policy='bc_chunk_dev_v4',policy_checkpoint='policy_15000.pt',
            split='train',episodes=2,steps=400,delay=2,shift_index=2,fallback_index=2,candidates=4,horizon=8,noise=noise,
            risk_weight=.5,readout_weight=.02,gate_margin=.02,fallback='shift',score_only=True,candidate_mode='shift',
            demos=names,output_dir=str(directory),trace=True)
        path=original_run(args);old=json.loads(path.read_text());new=json.loads((pilot/newjob/'result.json').read_text())
        assert [(r['success'],r['steps']) for r in old['records']]==[(r['success'],r['steps']) for r in new['records'][:2]]
        newrows={n:[] for n in names}
        for line in (pilot/newjob/'trace.jsonl').open():
            row=json.loads(line)
            if row['demo'] in newrows:newrows[row['demo']].append(row)
        checked=0
        for name,relpath in old['trace_files'].items():
            aa=[json.loads(l) for l in (path.parent/relpath).open()];bb=newrows[name];assert len(aa)==len(bb)
            for a,b in zip(aa,bb):
                for key in ['state_before','state_after','base_chunk','queue_before','submitted_action','executed_action_before_noise','executed_action','stages_after','success_after']:
                    assert a[key]==b[key],(newjob,name,a['step'],key)
                assert a['selected']==b['original_selected']
                if method=='wm':np.testing.assert_array_equal(a['learned_scores'],b['original_scores'])
                checked+=1
        results.append({'job':newjob,'exact_steps':checked,'episodes':2})
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pilot',default='pilot_v3');a=p.parse_args()
    out=RUN/'small_validation';out.mkdir(exist_ok=False)
    result={'physical':physical(),'equivalence':equivalence(RUN/a.pilot,out),'passed':True,
            'source_sha256':{n:digest(RUN/n) for n in ['recovery_controller.py','evaluate_recovery.py']}}
    write(out/'validation.json',result);print(json.dumps(result),flush=True)
