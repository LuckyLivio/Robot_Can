"""Same-start v10/v11 raw action replay. No interpolation or outcome selection loop."""
from pathlib import Path
import gc,json,sys
import h5py,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from reproduction.release_20261012_01 import make_demo as renderer
from common import make_env,restore_demo,pack_obs
STAGE=ROOT/'reproduction/improvement_v11_20261015_01/pilot_a'
def panel(frames,rows,step):
    im=Image.new('RGB',(960,660),'#101318');d=ImageDraw.Draw(im)
    d.text((20,12),'BC k=2 / 箱沿 demo_6000005',font=renderer.FONTS[23],fill='white')
    d.text((20,46),'同起点、同噪声 · 保存动作逐步回放 · 已知诊断，非独立确认',font=renderer.FONTS[17],fill='#bdc6d7')
    for i,v in enumerate(['v10','v11']):
        n=min(step,len(rows[v]));r=rows[v][max(0,n-1)];done=n==len(rows[v]);success=done and r['success_after'];left=480*i
        d.rectangle((left,80,left+479,110),fill='#aeb8c8' if v=='v10' else '#6ac3e5')
        d.text((left+15,82),v+(' · 冻结参考' if v=='v10' else ' · 方向与罐体包络合用'),font=renderer.FONTS[20],fill='#0b1220')
        im.paste(Image.fromarray(frames[v][n]),(left,110));status='成功 · 保持终点' if success else ('400 步未完成' if done else '运行中')
        d.rectangle((left+10,120,left+220,153),fill='#14543b' if success else '#323a48');d.text((left+20,124),status,font=renderer.FONTS[17],fill='white')
        d.text((left+15,598),f"{n:03d}/400 · {r['recovery']['mode']}",font=renderer.FONTS[17],fill='white')
    d.text((20,632),f'20 fps / 20 Hz · t={step/20:.2f}s · 2步FIFO · 回放不新增统计样本',font=renderer.FONTS[17],fill='#bdc6d7');return np.asarray(im)
if __name__=='__main__':
    out=RUN/'demo/v11_edge20';out.mkdir(exist_ok=False);renderer.FPS=20;renderer.WIDTH=960;renderer.HEIGHT=660
    env=make_env(False);rows={};frames={};checks=[];initial=None
    try:
        for v in ['v10','v11']:
            folder=STAGE/(v+'_regression_6000005');job=json.loads((folder/'result.json').read_text())['job'];rr=[json.loads(l) for l in (folder/'trace.jsonl').open()];rows[v]=rr
            with h5py.File(ROOT/job['dataset']) as f:obs=restore_demo(env,f['data/demo_6000005'])
            if initial is None:initial=pack_obs(obs)
            else:np.testing.assert_array_equal(initial,pack_obs(obs))
            first,context=renderer.camera(env);ff={0:first}
            for r in rr:
                np.testing.assert_array_equal(pack_obs(obs),r['state_before']);obs,*_=env.step(np.array(r['executed_action'],np.float32));np.testing.assert_array_equal(pack_obs(obs),r['state_after'])
                np.testing.assert_array_equal(env.staged_rewards(),r['stages_after']);assert bool(env._check_success())==r['success_after'];ff[r['step']],context=renderer.camera(env,context)
            frames[v]=ff;context.gl_ctx.make_current();env.sim._render_context_offscreen=None;context.sim=None;del context;gc.collect()
            checks.append({'version':v,'steps':len(rr),'success':bool(rr[-1]['success_after']),'states_rewards_success_exact':True,'trace_sha256':renderer.digest(folder/'trace.jsonl')})
        def iterator():
            for step in range(401):yield panel(frames,rows,step)
            for _ in range(20):yield panel(frames,rows,400)
        video=out/'bc_wall_edge.mp4';count=renderer.encode(video,iterator());Image.fromarray(panel(frames,rows,0)).save(out/'poster.png');Image.fromarray(panel(frames,rows,400)).save(out/'final.png')
        data={'passed':True,'checks':checks,'same_initial_state':True,'fps':20,'frames':count,'video':'demo/v11_edge20/bc_wall_edge.mp4','sha256':renderer.digest(video),'selection':'Previously targeted known failure, not a new independent success sample. Raw every-step physics replay; successful endpoint held through comparison finish.'}
        with (RUN/'edge_replay_validation.json').open('x') as f:json.dump(data,f,indent=2)
        print(json.dumps(data),flush=True)
    finally:env.close()
