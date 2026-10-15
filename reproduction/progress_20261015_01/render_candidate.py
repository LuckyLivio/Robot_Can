"""Paired saved-action v6/v8 diagnostic videos, including every Full seed."""
from pathlib import Path
import gc,json,sys
import h5py,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from reproduction.release_20261012_01 import make_demo as renderer
from common import DATA,make_env,restore_demo,pack_obs
STAGE=ROOT/'reproduction/improvement_v8_20261015_01/pilot_b'
CASES=[('full17','known_side_s17','demo_97','Full · seed17'),('full23','known_side_s23','demo_188','Full · seed23'),
       ('full41','known_side_s41','demo_97','Full · seed41'),('bc_edge','regression_6000005','demo_6000005','BC k=2 · 箱沿退步')]

def panel(label,demo,frames,rows,step):
    image=Image.new('RGB',(960,660),'#101318');d=ImageDraw.Draw(image)
    d.text((20,12),label+' / '+demo,font=renderer.FONTS[23],fill='white')
    d.text((20,46),'同起点、同噪声 · 保存动作回放 · 候选 v8 尚未采用',font=renderer.FONTS[17],fill='#bdc6d7')
    for i,v in enumerate(['v6','v8']):
        n=min(step,len(rows[v]));r=rows[v][max(0,n-1)];done=n==len(rows[v]);success=done and r['success_after']
        color='#aeb8c8' if v=='v6' else '#6ac3e5';x=480*i
        d.rectangle((x,80,x+479,110),fill=color)
        d.text((x+15,82),v+' · '+('参考候选' if v=='v6' else '本轮未达标候选'),font=renderer.FONTS[20],fill='#0b1220')
        image.paste(Image.fromarray(frames[v][n]),(x,110))
        status='成功 · 保持终点' if success else ('400 步未完成' if done else '运行中')
        d.rectangle((x+10,120,x+220,153),fill='#14543b' if success else '#323a48')
        d.text((x+20,124),status,font=renderer.FONTS[17],fill='white')
        d.text((x+15,598),f"{n:03d}/400 · {r['recovery']['mode']}",font=renderer.FONTS[17],fill='white')
    d.text((20,632),f'20 fps / 20 Hz · t={step/20:.2f}s · 2步FIFO · 说明案例，不新增统计样本',font=renderer.FONTS[17],fill='#bdc6d7')
    return np.asarray(image)

def main():
    out=RUN/'demo/recovery20';out.mkdir(exist_ok=False);renderer.FPS=20;renderer.WIDTH=960;renderer.HEIGHT=660
    manifest=[];checks=[];env=make_env(False)
    try:
        for identity,suffix,demo,label in CASES:
            rows={};frames={};sources=[]
            for v in ['v6','v8']:
                folder=STAGE/(v+'_'+suffix);result=json.loads((folder/'result.json').read_text());job=result['job']
                rr=[json.loads(l) for l in (folder/'trace.jsonl').open() if json.loads(l)['demo']==demo];rows[v]=rr
                with h5py.File(ROOT/job['dataset'] if job.get('dataset') else DATA) as f:obs=restore_demo(env,f['data'][demo])
                first,context=renderer.camera(env);ff={0:first}
                for r in rr:
                    np.testing.assert_array_equal(pack_obs(obs),r['state_before']);obs,*_=env.step(np.array(r['executed_action'],np.float32))
                    np.testing.assert_array_equal(pack_obs(obs),r['state_after']);np.testing.assert_array_equal(env.staged_rewards(),r['stages_after'])
                    assert bool(env._check_success())==r['success_after'];ff[r['step']],context=renderer.camera(env,context)
                frames[v]=ff;context.gl_ctx.make_current();env.sim._render_context_offscreen=None;context.sim=None;del context;gc.collect()
                checks.append({'case':identity,'version':v,'steps':len(rr),'states_rewards_success_exact':True,'source_sha256':renderer.digest(folder/'trace.jsonl')})
                sources.append((folder/'result.json').relative_to(ROOT).as_posix())
            longest=max(map(len,rows.values()))
            def iterator():
                for step in range(longest+1):yield panel(label,demo,frames,rows,step)
                for _ in range(20):yield panel(label,demo,frames,rows,longest)
            video=out/(identity+'.mp4');n=renderer.encode(video,iterator());poster=out/(identity+'.png')
            Image.fromarray(panel(label,demo,frames,rows,0)).save(poster)
            manifest.append({'id':identity,'label':label,'demo':demo,'video':'recovery20/'+video.name,'poster':'recovery20/'+poster.name,
                             'fps':20,'frames':n,'sha256':renderer.digest(video),'sources':sources,
                             'results':{v:{'success':bool(rows[v][-1]['success_after']),'steps':len(rows[v])} for v in rows}})
            print(json.dumps(manifest[-1],ensure_ascii=False),flush=True);del rows,frames;gc.collect()
    finally:env.close()
    with (RUN/'candidate_replay_validation.json').open('x') as f:json.dump({'passed':True,'checks':checks,'cases':manifest,'selection':'Known diagnostics covering Full seeds17/23/41 and the v8 regression; different seeds may use different cases. Only comparisons within a video share an initial state.'},f,indent=2)
    (RUN/'demo/recovery-media.js').write_text('const RECOVERY_MEDIA = '+json.dumps(manifest,ensure_ascii=False,indent=2)+';\n',encoding='utf8')
if __name__=='__main__':main()
