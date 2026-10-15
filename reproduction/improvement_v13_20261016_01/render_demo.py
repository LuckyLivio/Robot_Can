"""Same-start v12/v13 observed action replay, every control step at 20 fps."""
from pathlib import Path
import argparse,gc,json,sys
import h5py,numpy as np
from PIL import Image,ImageDraw
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from reproduction.release_20261012_01 import make_demo as renderer
from common import DATA,make_env,restore_demo,pack_obs
def panel(frames,rows,step):
    im=Image.new('RGB',(960,660),'#101318');d=ImageDraw.Draw(im)
    d.text((20,12),CAPTION,font=renderer.FONTS[23],fill='white')
    d.text((20,46),'同起点、同噪声、400步 · 保存动作逐步回放 · 不代表独立确认成功率',font=renderer.FONTS[17],fill='#bdc6d7')
    for i,v in enumerate(['v12','v13']):
        n=min(step,len(rows[v]));r=rows[v][max(0,n-1)];done=n==len(rows[v]);success=done and r['success_after'];left=480*i
        d.rectangle((left,80,left+479,110),fill='#aeb8c8' if v=='v12' else '#a7daca')
        d.text((left+15,82),v+(' · 冻结v12' if v=='v12' else ' · 支撑识别与重规划'),font=renderer.FONTS[20],fill='#0b1220')
        im.paste(Image.fromarray(frames[v][n]),(left,110));status='成功 · 保持终点' if success else ('400 步未完成' if done else '运行中')
        d.rectangle((left+10,120,left+220,153),fill='#14543b' if success else '#323a48');d.text((left+20,124),status,font=renderer.FONTS[17],fill='white')
        d.text((left+15,598),f"{n:03d}/400 · {r['recovery']['mode']}",font=renderer.FONTS[17],fill='white')
    d.text((20,632),f'20 fps / 20 Hz · t={step/20:.2f}s · D2 FIFO · 成功后保持终点，无动作插值',font=renderer.FONTS[17],fill='#bdc6d7')
    return np.asarray(im)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['side_perch','leaning'],required=True);args=parser.parse_args()
    if args.case=='side_perch':suffix='known_bc_k2_clean_demo_12000011';demo='demo_12000011';CAPTION='BC k=2 / 已知侧倒箱沿 / demo12000011 / 干净'
    else:suffix='known_full_s23_noise005_demo_12000021';demo='demo_12000021';CAPTION='Full s23 / 已知斜靠 / demo12000021 / 噪声0.05'
    out=RUN/'demo'/args.case;out.mkdir(parents=True,exist_ok=False);(out/'caption.json').write_text(json.dumps({'caption':CAPTION},ensure_ascii=False),encoding='utf8');renderer.FPS=20;renderer.WIDTH=960;renderer.HEIGHT=660
    env=make_env(False);rows={};frames={};checks=[];initial=None
    try:
        for v in ['v12','v13']:
            folder=RUN/'smoke_e'/f'{v}_{suffix}';job=json.loads((folder/'result.json').read_text())['job'];rr=[json.loads(l) for l in (folder/'trace.jsonl').open()];rows[v]=rr
            with h5py.File(ROOT/job['dataset'] if job.get('dataset') else DATA) as f:obs=restore_demo(env,f['data'][demo])
            if initial is None:initial=pack_obs(obs)
            else:np.testing.assert_array_equal(initial,pack_obs(obs))
            first,context=renderer.camera(env);ff={0:first}
            for r in rr:
                np.testing.assert_array_equal(pack_obs(obs),r['state_before']);obs,*_=env.step(np.array(r['executed_action'],np.float32));np.testing.assert_array_equal(pack_obs(obs),r['state_after'])
                assert bool(env._check_success())==r['success_after'];ff[r['step']],context=renderer.camera(env,context)
            frames[v]=ff;context.gl_ctx.make_current();env.sim._render_context_offscreen=None;context.sim=None;del context;gc.collect()
            checks.append({'version':v,'steps':len(rr),'success':bool(rr[-1]['success_after']),'physical_states_exact':True,'trace_sha256':renderer.digest(folder/'trace.jsonl')})
        def iterator():
            for s in range(401):yield panel(frames,rows,s)
            for _ in range(20):yield panel(frames,rows,400)
        video=out/'comparison.mp4';count=renderer.encode(video,iterator());Image.fromarray(panel(frames,rows,0)).save(out/'poster.png');Image.fromarray(panel(frames,rows,400)).save(out/'final.png')
        receipt={'passed':True,'checks':checks,'same_initial_state':True,'fps':20,'frames':count,'video_sha256':renderer.digest(video),
                 'selection':'Preselected known smoke_e diagnostic case; not a new independent success sample; endpoints held without motion interpolation.'}
        with (RUN/'analysis'/f'demo_replay_{args.case}.json').open('x') as f:json.dump(receipt,f,indent=2)
        print(json.dumps(receipt))
    finally:env.close()
