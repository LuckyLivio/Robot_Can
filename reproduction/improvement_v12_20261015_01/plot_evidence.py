"""Publication-size plots from recorded data only; preserve true endpoints."""
from pathlib import Path
import csv,hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];OUT=RUN/'figures';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,
                     'legend.fontsize':8,'pdf.fonttype':42,'svg.fonttype':'path','axes.spines.top':False,'axes.spines.right':False})
catalog=[]
def save(fig,name,caption,rows,sources):
    for ext in ['png','pdf','svg']:fig.savefig(OUT/f'{name}.{ext}',dpi=600,facecolor='white')
    plt.close(fig)
    with (OUT/f'{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    catalog.append({'id':name,'caption':caption,'width_mm':180.34,'dpi':600,'no_smoothing':True,'rows':len(rows),
                    'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}})
def read(p):return json.loads(p.read_text())
stage=RUN/'pilot_a'
if (stage/'completed.json').exists():
    traces={v:[json.loads(l) for l in (stage/f'{v}_held_wait_demo87/trace.jsonl').open()] for v in ['v11','history','v12']}
    for a,b in zip(traces['v11'],traces['history']):np.testing.assert_array_equal(a['state_after'],b['state_after'])
    assert len(traces['v11'])==len(traces['history'])
    fig,axes=plt.subplots(3,1,figsize=(7.1,5.3),layout='constrained',sharex=True);export=[]
    for v,label,color,style in [('v11','v11 / 仅补历史','#D55E00','--'),('v12','v12 完整修复','#0072B2','-')]:
        rr=traces[v];x=np.array([r['state_after'] for r in rr]);t=np.array([r['step']/20 for r in rr])
        ys=[x[:,18],np.linalg.norm(x[:,16:18]-[.1975,.4025],axis=1)*1000,np.abs(x[:,7]-x[:,8])*1000]
        for ax,y in zip(axes,ys):ax.plot(t,y,label=label,c=color,ls=style,lw=1.1);ax.grid(alpha=.2)
        for r,vals in zip(rr,zip(*ys)):export.append({'version':v,'step':r['step'],'time_s':r['step']/20,'can_height_m':vals[0],'goal_xy_mm':vals[1],'gap_mm':vals[2],'phase':r['recovery']['mode']})
    for ax,label in zip(axes,['罐体高度（m）','到目标的水平距离（mm）','夹爪开度（mm）']):ax.set_ylabel(label)
    axes[0].legend(frameon=False);axes[-1].set(xlabel='仿真时间（s）',xlim=(0,20))
    axes[0].set_title('已知 demo87：等待阶段的抓持确认与搬运')
    transition=next(e['step'] for e in read(stage/'v12_held_wait_demo87/result.json')['records'][0]['events'] if e['reason']=='wait_follow_confirmed')
    for ax in axes:ax.axvline(transition/20,color='#777',ls=':',lw=.8)
    save(fig,'V12_F01_wait_trace','Full s41、噪声0.05、已知demo87。每20Hz控制步的实际执行后状态，无平滑。v11和history轨迹逐值一致，合并为一条；v12到实际成功264步即停止。竖线为149步确认。此图是诊断，不是独立泛化证据。',export,[stage/f'{v}_held_wait_demo87/trace.jsonl' for v in traces])
    d=read(RUN/'analysis/pilot_a.json');fig,ax=plt.subplots(figsize=(7.1,2.7),layout='constrained');export=[]
    for i,v in enumerate(['v11','history','v12']):
        r=d['variants'][v];value=r['success']/r['episodes']*100;ax.barh(i,value,color=['#7a8792','#D55E00','#0072B2'][i],height=.5)
        ax.text(value+1,i,f"{r['success']}/{r['episodes']}",va='center',fontsize=9);export.append({'variant':v,'success':r['success'],'episodes':r['episodes'],'success_percent':value})
    ax.set(yticks=[0,1,2],yticklabels=['v11','仅补历史','v12'],xlabel='已知条件成功率（%）',xlim=(0,100),title='37 个旧诊断条件 + 已知 demo87');ax.invert_yaxis();ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
    save(fig,'V12_F02_ablation','每组38次已知条件执行；包含同起点不同设置，不作为38个独立确认样本。无推断区间；核心37个条件三组均31成功，完整v12额外救回已知demo87。',export,[RUN/'analysis/pilot_a.json'])
if (RUN/'analysis/dev_a.json').exists():
    fig,ax=plt.subplots(figsize=(7.1,4.1),layout='constrained');export=[];sources=[]
    jobs=read(RUN/'dev_a/jobs.json')
    labels=[]
    for i,j in enumerate(jobs):
        suffix=j['id'].split('_',1)[1];labels.append(suffix.replace('_noise005',' · 噪声').replace('_clean',' · 干净'))
        for v,delta,col,marker in [('v6',-.16,'#606a74','s'),('v11',0,'#D55E00','x'),('v12',.16,'#0072B2','o')]:
            p=(RUN/'dev_a'/j['id']/'result.json') if v=='v12' else ROOT/f'reproduction/improvement_{v}_20261015_01/dev_a/{v}_{suffix}/result.json'
            sources.append(p);rr=read(p)['records'];n=sum(r['success'] for r in rr);ax.scatter(n/30*100,i+delta,c=col,marker=marker,s=22,clip_on=False,label=v if i==0 else None)
            export.append({'condition':suffix,'version':v,'success':n,'episodes':30,'success_percent':n/30*100})
    ax.set(yticks=range(8),yticklabels=labels,xlim=(0,100),xticks=[0,25,50,75,100],xlabel='成功率（%）',title='冻结开发对照：30个共同起点 × 8条件');ax.invert_yaxis();ax.grid(axis='x',alpha=.2);ax.legend(frameon=False,loc='lower left')
    save(fig,'V12_F03_development','v6和v11为历史同起点同噪声参考；v12新跑240次。点为各条件实际比例，无推断区间。开发集用于门槛筛选，不作为独立确认。',export,sources)
if (RUN/'analysis/confirmation.json').exists():
    d=read(RUN/'analysis/confirmation.json');fig,ax=plt.subplots(figsize=(7.1,2.7),layout='constrained');export=[]
    for i,k in enumerate(['v6','v12']):
        s=d['statistics'][k];mean=s['estimate_percent'];lo,hi=s['ci95_percent'];ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',color='#0072B2' if k=='v12' else '#606a74',capsize=3)
        export.append({'quantity':k,'estimate_percent':mean,'ci_low_percent':lo,'ci_high_percent':hi,'independent_starts':60})
    effect=d['statistics']['v12_minus_v6'];ax.set(yticks=[0,1],yticklabels=['v6','v12'],xlim=(0,100),xlabel='八条件固定执行组合成功率（%）',title='独立确认：60个新起点，各版本480次执行');ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
    ax.set_ylim(1.35,-.35)
    ax.text(.03,.50,f"配对差值：{effect['estimate_percent']:+.2f} pp\n95% CI [{effect['ci95_percent'][0]:.2f}, {effect['ci95_percent'][1]:.2f}] pp",transform=ax.transAxes,fontsize=8,va='center')
    export.append({'quantity':'v12_minus_v6_pp','estimate_percent':effect['estimate_percent'],'ci_low_percent':effect['ci95_percent'][0],'ci_high_percent':effect['ci95_percent'][1],'independent_starts':60})
    save(fig,'V12_F04_confirmation','以60个起点成组重采样20000次，保留各起点的8个关联条件；Full三个固定训练种子。区间为点态95%百分位bootstrap。若无不一致结果造成零宽区间，不代表总体等价。',export,[RUN/'analysis/confirmation.json'])
(OUT/'CATALOG.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
print('Saved',len(catalog),'figures with CSV, vector PDF/SVG and 600dpi PNG')
