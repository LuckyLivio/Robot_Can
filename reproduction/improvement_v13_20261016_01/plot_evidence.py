"""Source-backed figures, true endpoints and paired-start uncertainty only."""
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
def read(p):return json.loads(p.read_text())
def save(fig,name,caption,rows,sources):
    for ext in ['png','pdf','svg']:fig.savefig(OUT/f'{name}.{ext}',dpi=600,facecolor='white')
    plt.close(fig)
    with (OUT/f'{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    catalog.append({'id':name,'caption':caption,'width_mm':180.34,'dpi':600,'no_smoothing':True,'rows':len(rows),
                    'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}})
for number,suffix,title in [(1,'known_bc_k2_clean_demo_12000011','侧倒箱沿：BC k=2，已知demo12000011'),
                            (2,'known_full_s23_noise005_demo_12000021','斜靠物体：Full s23，噪声0.05，已知demo12000021')]:
    fig,axes=plt.subplots(3,1,figsize=(7.1,5.3),layout='constrained',sharex=True);rows=[];sources=[]
    for v,color,style in [('v12','#D55E00','--'),('v13','#0072B2','-')]:
        p=RUN/'smoke_e'/f'{v}_{suffix}/trace.jsonl';sources.append(p);rr=list(map(json.loads,p.open()))
        x=np.array([r['state_after'] for r in rr]);t=np.array([r['step']/20 for r in rr]);ys=[x[:,18],np.linalg.norm(x[:,16:18]-[.1975,.4025],axis=1)*1000,np.abs(x[:,7]-x[:,8])*1000]
        for ax,y in zip(axes,ys):ax.plot(t,y,c=color,ls=style,label=v,lw=1.1);ax.grid(alpha=.2)
        for r,vals in zip(rr,zip(*ys)):rows.append({'version':v,'step':r['step'],'time_s':r['step']/20,'can_height_m':vals[0],'goal_xy_mm':vals[1],'gap_mm':vals[2],'phase':r['recovery']['mode']})
    for ax,label in zip(axes,['罐体高度（m）','目标水平距离（mm）','夹爪开度（mm）']):ax.set_ylabel(label)
    axes[0].set_title(title);axes[0].legend(frameon=False);axes[-1].set(xlabel='仿真时间（s）',xlim=(0,20))
    save(fig,f'V13_F0{number}_known_trace',title+'。smoke_e实际20Hz执行后状态，无平滑或插值；成功即停止曲线，不延长到400步。已知诊断，不是独立泛化证据。',rows,sources)
if (RUN/'analysis/pilot_a.json').exists():
    d=read(RUN/'analysis/pilot_a.json');fig,ax=plt.subplots(figsize=(7.1,3.1),layout='constrained');rows=[]
    for i,v in enumerate(['v12','support','escape','v13']):
        s=d['variants'][v];rate=s['success']/s['episodes']*100
        ax.barh(i,rate,color=['#606a74','#E69F00','#009E73','#0072B2'][i],height=.55)
        ax.text(rate+1,i,f"{s['success']}/{s['episodes']}",va='center')
        rows.append({'version':v,'success':s['success'],'executions':s['episodes'],'success_percent':rate})
    ax.set(xlim=(0,100),yticks=range(4),yticklabels=['v12','仅支撑 S','仅等待撤退 R','组合 v13'],xlabel='已知条件成功率（%）',title='四组消融：原38条件 + 新加入12个已知条件');ax.invert_yaxis();ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
    save(fig,'V13_F03_ablation','50条件中包含重复起点的不同策略/噪声，不能当作50个独立确认起点。S含新支撑家族与受检路径入口，R含一次有界撤退/重规划。图为描述统计，不给独立推断区间。',rows,[RUN/'analysis/pilot_a.json'])
if (RUN/'analysis/dev_a.json').exists():
    fig,ax=plt.subplots(figsize=(7.1,4.1),layout='constrained');rows=[];sources=[];labels=[]
    for i,j in enumerate(read(RUN/'dev_a/jobs.json')):
        suffix=j['id'].split('_',1)[1];labels.append(suffix.replace('_clean',' · 干净').replace('_noise005',' · 噪声'))
        for v,delta,color,marker in [('v6',-.16,'#606a74','s'),('v12',0,'#D55E00','x'),('v13',.16,'#0072B2','o')]:
            p=RUN/'dev_a'/j['id']/'result.json' if v=='v13' else ROOT/f'reproduction/improvement_{v}_20261015_01/dev_a/{v}_{suffix}/result.json'
            sources.append(p);rr=read(p)['records'];n=sum(r['success'] for r in rr)
            ax.scatter(n/30*100,i+delta,c=color,marker=marker,s=22,clip_on=False,label=v if i==0 else None)
            rows.append({'condition':suffix,'version':v,'success':n,'executions':30,'success_percent':n/30*100})
    ax.set(yticks=range(8),yticklabels=labels,xlim=(0,100),xlabel='成功率（%）',title='开发对照：30个共同起点 × 八条件');ax.invert_yaxis();ax.grid(axis='x',alpha=.2);ax.legend(frameon=False,loc='lower left')
    save(fig,'V13_F04_development','v6/v12历史同起点同噪声参考，v13新跑240次。开发用于筛选，不作为独立泛化证据。不将八条件相连成伪连续曲线。',rows,sources)
if (RUN/'analysis/confirmation.json').exists():
    d=read(RUN/'analysis/confirmation.json');fig,ax=plt.subplots(figsize=(7.1,3.1),layout='constrained');rows=[]
    for i,v in enumerate(['v6','v12','v13']):
        s=d['statistics'][v];mean=s['estimate_percent'];lo,hi=s['ci95_percent'];ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',color=['#606a74','#D55E00','#0072B2'][i],capsize=3)
        rows.append({'quantity':v,'estimate_percent':mean,'ci_low_percent':lo,'ci_high_percent':hi,'independent_starts':60})
    effect=d['statistics']['v13_minus_v6'];ax.set(yticks=range(3),yticklabels=['v6','v12','v13'],xlim=(0,100),ylim=(2.35,-.35),xlabel='八条件固定组合成功率（%）',title='独立确认：60个新起点，各版本480次执行');ax.grid(axis='x',alpha=.2)
    ax.text(.03,.60,f"主要差值 v13-v6：{effect['estimate_percent']:+.2f} pp\n95% CI [{effect['ci95_percent'][0]:.2f}, {effect['ci95_percent'][1]:.2f}] pp",transform=ax.transAxes,fontsize=8,va='center')
    for ref in ['v6','v12']:
        s=d['statistics']['v13_minus_'+ref];rows.append({'quantity':'v13_minus_'+ref+'_pp','estimate_percent':s['estimate_percent'],'ci_low_percent':s['ci95_percent'][0],'ci_high_percent':s['ci95_percent'][1],'independent_starts':60})
    save(fig,'V13_F05_confirmation','按60个起点成组重采样20000次，保留每起点八个固定关联条件。95%百分位bootstrap，主比较v13-v6，次比较v13-v12；未做多重比较校正。区间不覆盖任意重新训练的不确定性。',rows,[RUN/'analysis/confirmation.json'])
(OUT/'CATALOG.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8');print('Saved',len(catalog),'figures')
