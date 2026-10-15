"""Verified frozen-controller rollouts, exact action replay, and synced videos."""
import argparse,gc,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
import h5py,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
CONF=ROOT/'reproduction/confirmation_20261012_01'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(CONF))
from evaluate_confirmation import arguments,run_new
from common import make_env,restore_demo,pack_obs
from collect_rollout_branches import signature
from robosuite.utils.binding_utils import MjRenderContextOffscreen

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,ensure_ascii=False,allow_nan=False)

def validate_inputs():
    for relative,sha in read(CONF/'lock.json')['input_sha256'].items():assert digest(ROOT/relative)==sha,relative
    for relative,sha in read(RUN/'demo_design.json')['source_sha256'].items():assert digest(ROOT/relative)==sha,relative

def traces_phase():
    validate_inputs();design=read(RUN/'demo_design.json');checks=[]
    for condition in design['conditions']:
        cases=[x for x in design['cases'] if x['condition']==condition];names=[x['state_name'] for x in cases]
        for method in design['methods']:
            out=RUN/'demo'/'traces'/f'{method}_{condition}'
            args=arguments(method,17,0. if condition=='clean' else .05,out,names,True,'confirmation_demo')
            args.episodes=len(names)
            path=run_new(args,CONF/'starts.hdf5',names,names,
                {'purpose':'Illustrative replay; excluded from all success-rate statistics.',
                 'demo_design_sha256':digest(RUN/'demo_design.json')})
            result=read(path)
            for case,row in zip(cases,result['records']):
                expected=case['original_records'][method]
                for key,value in expected.items():
                    if key in ('mean_decision_ms','elapsed_s'):continue
                    assert row[key]==value,(method,condition,case['state_name'],key)
                checks.append({'method':method,'condition':condition,'state_name':case['state_name'],
                    'all_original_result_fields_except_timing_exact':True,'steps':row['steps']})
            print('trace_verified',method,condition,flush=True)
    write(RUN/'demo'/'trace_validation.json',{'passed':True,'checks':checks,'source_design_sha256':digest(RUN/'demo_design.json')})

FONT=Path('C:/Windows/Fonts/msyh.ttc')
def font(size):return ImageFont.truetype(str(FONT),size)
FONTS={s:font(s) for s in (15,17,20,23,27)}
METHOD_NAMES={'bc_k2':'BC k=2','full':'Full · 种子17','plain':'Plain · 种子17'}
COLORS={'bc_k2':'#94a3b8','full':'#38bdf8','plain':'#fbbf24'}
WIDTH=1440;HEIGHT=660;FPS=10

def camera(env,context=None):
    before=signature(env);warmstart=env.sim.data.qacc_warmstart.copy()
    if context is None:
        context=MjRenderContextOffscreen(env.sim,device_id=0)
        context.vopt.geomgroup[0]=0;context.vopt.geomgroup[1]=1
    context.gl_ctx.make_current()
    frame=env.sim.render(width=480,height=480,camera_name='agentview')[::-1].copy()
    # Rendering calls mj_forward and perturbs solver warmstart at roundoff.
    # Restore this auxiliary state; do not let display alter replay dynamics.
    env.sim.data.qacc_warmstart[:]=warmstart
    assert np.array_equal(signature(env),before),'Rendering changed physics/controller state'
    assert frame.std()>10 and np.mean(frame)>10,'Invalid/black camera frame'
    return frame,context

def panel_frame(case,methods,frames,rows,step):
    canvas=Image.new('RGB',(WIDTH,HEIGHT),'#0b1220');draw=ImageDraw.Draw(canvas)
    condition='干净执行' if case['condition']=='clean' else '位置动作噪声 σ=0.05'
    draw.text((22,12),case['label'],font=FONTS[27],fill='white')
    draw.text((22,48),f"{case['state_name']}  |  {condition}  |  同一起点、同一噪声、同一时间轴",font=FONTS[17],fill='#cbd5e1')
    draw.text((1140,21),f'仿真时间 {step/20:05.2f} 秒',font=FONTS[20],fill='white')
    for col,m in enumerate(methods):
        rr=rows[m];actual=min(step,len(rr));available=max(k for k in frames[m] if k<=actual)
        canvas.paste(Image.fromarray(frames[m][available]),(480*col,110))
        draw.rectangle((480*col,80,480*(col+1)-1,109),fill=COLORS[m])
        draw.text((480*col+12,82),METHOD_NAMES[m],font=FONTS[20],fill='#0b1220')
        success=actual>=len(rr) and rr[-1]['success_after']
        end=actual>=len(rr)
        status='成功 · 画面保持' if success else ('400步未完成' if end else '运行中')
        draw.rectangle((480*col+8,122,480*col+202,153),fill='#166534' if success else ('#991b1b' if end else '#1e293b'))
        draw.text((480*col+17,126),status,font=FONTS[17],fill='white')
        selected=rr[actual-1]['selected'] if actual else '-'
        draw.text((480*col+12,599),f'控制步 {actual:03d} / 400  ·  本步新提交 k={selected}',font=FONTS[17],fill='white')
        if col:draw.line((480*col,80,480*col,625),fill='#0b1220',width=2)
    draw.text((20,633),'低维状态仿真  |  FIFO延迟2步 / 100ms  |  策略不读取展示图像  |  说明性案例，不替代60起点统计',font=FONTS[17],fill='#cbd5e1')
    return np.asarray(canvas)

def encode(path,frames):
    if path.exists():raise FileExistsError(path)
    ffmpeg=shutil.which('ffmpeg');assert ffmpeg
    command=[ffmpeg,'-hide_banner','-loglevel','error','-n','-f','rawvideo','-vcodec','rawvideo',
        '-pix_fmt','rgb24','-s',f'{WIDTH}x{HEIGHT}','-r',str(FPS),'-i','-',
        '-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    count=0
    try:
        for frame in frames:process.stdin.write(frame.tobytes());count+=1
    finally:process.stdin.close()
    err=process.stderr.read().decode('utf-8',errors='replace');code=process.wait()
    assert code==0,err
    return count

def render_phase():
    validate_inputs();assert read(RUN/'demo/trace_validation.json')['passed'];design=read(RUN/'demo_design.json')
    assert read(RUN/'render_validation.json')['passed']
    out=RUN/'demo';(out/'videos').mkdir(exist_ok=True);(out/'posters').mkdir(exist_ok=True)
    env=make_env(False);checks=[];media=[]
    with h5py.File(CONF/'starts.hdf5','r') as states:
        for case in design['cases']:
            started=time.perf_counter();frames={};rows={}
            for method in design['methods']:
                rp=out/'traces'/f"{method}_{case['condition']}"/'results.json';r=read(rp)
                tp=rp.parent/r['trace_files'][case['state_name']]
                rr=[json.loads(line) for line in tp.read_text(encoding='utf-8').splitlines()];rows[method]=rr
                obs=restore_demo(env,states['data'][case['state_name']])
                assert np.array_equal(pack_obs(obs),np.asarray(rr[0]['state_before'],np.float32))
                first,context=camera(env);ff={0:first};maxerr=0.
                for row in rr:
                    assert np.array_equal(pack_obs(obs),np.asarray(row['state_before'],np.float32))
                    env.staged_rewards()
                    obs,*_=env.step(np.asarray(row['executed_action'],np.float32))
                    stages=env.staged_rewards();success=bool(env._check_success())
                    err=float(np.max(np.abs(pack_obs(obs)-np.asarray(row['state_after'],np.float32))))
                    maxerr=max(maxerr,err);assert err==0,(case['id'],method,row['step'],err)
                    assert np.array_equal(stages,np.asarray(row['stages_after'])) and success==row['success_after']
                    if row['step']%2==0 or row['step']==len(rr):ff[row['step']],context=camera(env,context)
                frames[method]=ff
                # Dispose this context while ITS GL context is still current.
                # Otherwise a delayed destructor after XML reset may free GPU
                # resources belonging to the next context and yield black frames.
                context.gl_ctx.make_current()
                env.sim._render_context_offscreen=None
                context.sim=None
                del context
                gc.collect()
                checks.append({'case':case['id'],'method':method,'steps':len(rr),'max_observation_error':maxerr,
                    'stage_rewards_and_success_exact':True,'render_preserves_physics_controller_signature':True})
                print('replay_verified',case['id'],method,len(rr),flush=True)
            longest=max(len(r) for r in rows.values());timeline=list(range(0,longest+1,2))
            if timeline[-1]!=longest:timeline.append(longest)
            def video_frames():
                for step in timeline:yield panel_frame(case,design['methods'],frames,rows,step)
                for _ in range(FPS):yield panel_frame(case,design['methods'],frames,rows,longest)
            video=out/'videos'/f"{case['id']}.mp4";count=encode(video,video_frames())
            poster=out/'posters'/f"{case['id']}.png"
            Image.fromarray(panel_frame(case,design['methods'],frames,rows,longest)).save(poster)
            # Three fixed timeline positions; includes t=0 and terminal outcome.
            points=sorted(set([0,min(100,longest),longest]));story=Image.new('RGB',(WIDTH,HEIGHT*len(points)))
            for i,step in enumerate(points):story.paste(Image.fromarray(panel_frame(case,design['methods'],frames,rows,step)),(0,i*HEIGHT))
            story.save(out/'posters'/f"{case['id']}_storyboard.jpg",quality=90)
            media.append({**{k:case[k] for k in ('id','label','condition','state_name','eligible_count')},
                'video':video.relative_to(out).as_posix(),'poster':poster.relative_to(out).as_posix(),
                'frames':count,'fps':FPS,'duration_s':count/FPS,'control_steps':longest,
                'sha256':digest(video),'elapsed_render_s':time.perf_counter()-started,
                'results':{m:{'success':bool(rows[m][-1]['success_after']),'steps':len(rows[m])} for m in design['methods']}})
            print('video_complete',case['id'],count,'frames',flush=True)
    env.close()
    write(out/'media_manifest.json',media)
    write(out/'replay_validation.json',{'passed':True,'checks':checks,'total_replayed_control_steps':sum(c['steps'] for c in checks),
        'render_source_sha256':digest(Path(__file__)),'trace_phase_excluded_from_statistics':True,
        'time_scale':'20Hz control, camera every2steps ->10fps video; final1second hold. Successful panels stop at actual success and retain final frame.'})
    build_page(media)

def build_page(media):
    template='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>机器人同起点对比 · 冻结实验</title>
<style>*{box-sizing:border-box}body{margin:0;background:#0b1220;color:#e2e8f0;font:16px/1.65 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1480px;margin:auto;padding:30px 24px}header{display:flex;justify-content:space-between;gap:30px;align-items:start}.tag{letter-spacing:.12em;color:#38bdf8;font-size:12px;font-weight:700}h1{font-size:30px;line-height:1.2;margin:12px 0}p{color:#a8b7ca;margin:10px 0}.badge{padding:6px 14px;background:#142c32;color:#7dd3c7;border:1px solid #265459;border-radius:30px;white-space:nowrap}nav{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0 18px}button{font:inherit;font-size:14px;border:1px solid #334155;background:#172337;color:#cbd5e1;border-radius:8px;padding:10px 14px;cursor:pointer}button[aria-pressed=true]{background:#123d57;border-color:#38bdf8;color:white}video{display:block;width:100%;background:#030712;border-radius:12px;border:1px solid #263449;aspect-ratio:1440/660}.meta{display:flex;justify-content:space-between;gap:15px;margin:12px 0}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:25px}.card{padding:18px 20px;background:#111e30;border:1px solid #263449;border-radius:10px}.card h2{font-size:18px;margin:0 0 8px}.card p{font-size:14px}.data{font-size:27px;color:white;font-weight:650}a{color:#7dd3fc}details{margin-top:24px;border-top:1px solid #334155;padding:16px 0}summary{cursor:pointer}.controls{display:flex;gap:10px;align-items:center}.controls label{font-size:14px}select{color:white;background:#172337;padding:5px;border:1px solid #334155}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid #263449;padding:9px;text-align:left}@media(max-width:850px){header{display:block}h1{font-size:24px}.cards{grid-template-columns:1fr}.meta{display:block}main{padding:18px 10px}}</style>
<main><header><div><div class="tag">PICKPLACECAN / FROZEN CONFIRMATION</div><h1>同一起点，三种控制方法</h1><p>BC k=2 · Full · Plain　|　FIFO延迟100ms　|　世界模型种子17</p></div><span class="badge">冻结权重 · 回放逐步核验</span></header>
<nav id="cases" aria-label="演示案例"></nav><video id="player" controls playsinline preload="metadata"></video>
<div class="meta"><div id="caseInfo"></div><div class="controls"><label for="speed">播放速度</label><select id="speed"><option value="0.5">0.5倍</option><option value="1" selected>1倍</option><option value="2">2倍</option></select><a id="download" download>下载当前视频</a></div></div>
<div class="cards"><section class="card"><h2>60个新起点 · 全部结果</h2><div class="data">Full 90.0% / 86.1%</div><p>干净 / 加噪；三个种子均值。BC为85.0% / 81.7%，Plain为88.3% / 83.9%。</p></section><section class="card"><h2>公平的画面与时间</h2><p>三个控制器使用同一保存状态、同一逐步噪声、同一相机与时间轴。成功后停帧，其余方法继续至400步。</p></section><section class="card"><h2>案例说明，不替代统计</h2><p>结果已知后，按三类案例各取最小编号。固定种子17，不挑最优种子。包含共同失败；不计作新的确认样本。</p></section></div>
<details open><summary>怎样讲解这段演示</summary><p id="explanation"></p><p>画面中的k是本步新提交命令的候选索引；真正执行的命令还要经过两步FIFO。输入为含物体真值的低维状态，展示图像没有输入控制策略。失败表示400步内未达到任务成功，不代表所有阶段都未完成。</p></details>
<details><summary>六个案例与完整证据</summary><table><thead><tr><th>条件/类别</th><th>起点</th><th>BC / Full / Plain</th></tr></thead><tbody id="caseTable"></tbody></table><p><a href="../demo_design.json">案例选择规则</a> · <a href="trace_validation.json">结果复跑核验</a> · <a href="replay_validation.json">渲染回放核验</a> · <a href="../../confirmation_20261012_01/analysis/report.txt">完整确认报告</a></p><p>逐步渲染为真实仿真动作回放。20Hz控制、每2步取一帧，以10fps播放；结尾增加1秒停帧。分条件配对区间仍接触零，排序增益未确立，视频不能证明普遍优势。</p></details></main>
<script>const cases=__DATA__;const player=document.getElementById('player'),nav=document.getElementById('cases');const methods=['bc_k2','full','plain'];function choose(i){const c=cases[i];player.pause();player.src=c.video;player.poster=c.poster;player.load();player.playbackRate=Number(document.getElementById('speed').value);nav.querySelectorAll('button').forEach((b,j)=>b.setAttribute('aria-pressed',String(i===j)));document.getElementById('caseInfo').textContent=c.state_name+' · '+(c.condition==='clean'?'干净':'噪声0.05')+' · '+c.label;document.getElementById('download').href=c.video;document.getElementById('explanation').textContent=c.id.includes('full_only')?'关注相同起点下动作选择如何带来不同后果。此例Full成功，BC与Plain未完成；它是按结果类别选出的解释案例，不表示所有起点都有同样收益。':c.id.includes('failure')?'这个起点三种方法都未完成。展示夹爪和物体的实际过程，说明局部候选筛选仍有失败边界，不把低评分门限描述为安全保证。':'这个起点三种方法都能完成，说明强BC本身可以解决很多任务。世界模型在这里的动作变化不应被夸大为任务成功必需。';}cases.forEach((c,i)=>{const b=document.createElement('button');b.textContent=(c.condition==='clean'?'干净':'加噪')+' · '+(c.id.includes('full_only')?'Full独胜':c.id.includes('failure')?'共同失败':'共同成功');b.onclick=()=>choose(i);nav.append(b);const tr=document.createElement('tr');[b.textContent,c.state_name,methods.map(m=>(c.results[m].success?'成功':'未完成')+' '+c.results[m].steps+'步').join(' / ')].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td)});document.getElementById('caseTable').append(tr)});document.getElementById('speed').onchange=e=>player.playbackRate=Number(e.target.value);choose(0);</script></html>'''
    path=RUN/'demo/index.html'
    with path.open('x',encoding='utf-8') as f:f.write(template.replace('__DATA__',json.dumps(media,ensure_ascii=False)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['traces','render','all'],default='all');args=p.parse_args()
    if args.phase in ('traces','all'):traces_phase()
    if args.phase in ('render','all'):render_phase()
