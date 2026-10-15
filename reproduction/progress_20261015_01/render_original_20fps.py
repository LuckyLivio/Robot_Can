"""Re-render frozen original videos at every control step, without policy reruns."""
from pathlib import Path
import gc,hashlib,json,sys,time
import h5py,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from reproduction.release_20261012_01 import make_demo as old
from common import make_env,restore_demo,pack_obs

def main():
    out=RUN/'demo';videos=out/'videos20';videos.mkdir(exist_ok=False);checks=[];media=[]
    design=old.read(old.RUN/'demo_design.json');old.FPS=20
    assert old.read(old.RUN/'demo/replay_validation.json')['passed']
    env=make_env(False)
    try:
        with h5py.File(old.CONF/'starts.hdf5') as states:
            for case in design['cases']:
                frames={};rows={}
                for method in design['methods']:
                    folder=old.RUN/'demo/traces'/f"{method}_{case['condition']}";result=old.read(folder/'results.json')
                    source=folder/result['trace_files'][case['state_name']];rr=[json.loads(l) for l in source.open()];rows[method]=rr
                    obs=restore_demo(env,states['data'][case['state_name']]);first,context=old.camera(env);ff={0:first}
                    for r in rr:
                        np.testing.assert_array_equal(pack_obs(obs),r['state_before'])
                        obs,*_=env.step(np.array(r['executed_action'],np.float32))
                        np.testing.assert_array_equal(pack_obs(obs),r['state_after'])
                        np.testing.assert_array_equal(env.staged_rewards(),r['stages_after']);assert bool(env._check_success())==r['success_after']
                        ff[r['step']],context=old.camera(env,context)
                    frames[method]=ff
                    context.gl_ctx.make_current();env.sim._render_context_offscreen=None;context.sim=None;del context;gc.collect()
                    checks.append({'case':case['id'],'method':method,'steps':len(rr),'state_reward_success_exact':True,'source_sha256':old.digest(source)})
                longest=max(map(len,rows.values()))
                def iterator():
                    for step in range(longest+1):yield old.panel_frame(case,design['methods'],frames,rows,step)
                    for _ in range(20):yield old.panel_frame(case,design['methods'],frames,rows,longest)
                video=videos/(case['id']+'.mp4');n=old.encode(video,iterator())
                poster=videos/(case['id']+'.png');Image.fromarray(old.panel_frame(case,design['methods'],frames,rows,0)).save(poster)
                media.append({'id':case['id'],'video':video.relative_to(out).as_posix(),'firstFrame':poster.relative_to(out).as_posix(),'poster':poster.relative_to(out).as_posix(),
                              'frames':n,'fps':20,'duration_s':n/20,'sha256':old.digest(video)})
                print(json.dumps(media[-1]),flush=True);del frames,rows;gc.collect()
    finally:env.close()
    receipt={'passed':True,'fps':20,'checks':checks,'media':media,'note':'Saved executed actions only. Same physical states and outcomes; every 20Hz step rendered. Final 1s hold. No interpolated robot frames or new statistical episodes.'}
    with (RUN/'original_20fps_validation.json').open('x') as f:json.dump(receipt,f,indent=2)
    p=out/'data.js';raw=p.read_text(encoding='utf8').strip();data=json.loads(raw[raw.index('=')+1:].rstrip(';'))
    for m in media:next(c for c in data['cases'] if c['id']==m['id']).update(m)
    p.write_text('const DEMO_DATA = '+json.dumps(data,ensure_ascii=False,indent=2)+';\n',encoding='utf8')
    p=out/'index.html';s=p.read_text(encoding='utf8').replace('当前录像 10 fps','逐控制步回放 20 fps');p.write_text(s,encoding='utf8')
    print('Completed all 6 verified 20fps videos.',flush=True)
if __name__=='__main__':main()
