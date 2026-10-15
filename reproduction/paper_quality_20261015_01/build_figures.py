"""Paper figures from saved measurements only. No torch, simulation or smoothing.

Portable: needs numpy/matplotlib and a Chinese font (Microsoft YaHei or Noto CJK).
Every numerical plotted mark is exported to a companion CSV. Sources are frozen
under inputs/ and recorded in PLOT_SOURCES.json. Historical assets are not edited.
"""
from pathlib import Path
import argparse, csv, hashlib, json, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Patch

RUN=Path(__file__).resolve().parent; INPUT=RUN/'inputs'
WM='reproduction/multiseed_20261012_01'; CONF='reproduction/confirmation_20261012_01'
DEEP='reproduction/figures_deepcheck_20261014_01'; EXT='reproduction/extensions_20261012_01'
V5='reproduction/recovery_v5_20261012_01'; V6='reproduction/improvement_v6_20261015_01'
V10='reproduction/improvement_v10_20261015_01'; V11='reproduction/improvement_v11_20261015_01'
SEEDS=[17,23,41];COLORS=['#0072B2','#D55E00','#009E73','#CC79A7','#707070']
METHODS={'bc_k2':'BC k=2','full':'Full','plain':'Plain','direct':'Direct','prediction_only':'仅预测 + 物理代价','no_risk_score':'去风险评分','no_gate':'去门控','persistence':'持续性预测','oracle':'真值短期评分'}
VERSIONS=['v2','v4','timing_only','side_only','v5']; VN=['v2','v4','仅时机 T','仅间隙 S','v5（T+S）']
CAT=[];MARKS=[];OUT=None;USED=set()
def j(rel):
    USED.add(rel);return json.loads((INPUT/rel).read_text(encoding='utf8'))
def c(rel):
    USED.add(rel)
    with (INPUT/rel).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def mark(panel,series,x,y,low='',high='',n=''):
    vals=[v for v in [x,y,low,high] if isinstance(v,(int,float,np.number))]
    assert all(np.isfinite(v) for v in vals)
    MARKS.append(dict(panel=panel,series=series,x=x,y=y,low=low,high=high,n=n))
def line(ax,x,y,label,color=COLORS[0],style='-',panel='',markers=True):
    ax.plot(x,y,label=label,color=color,ls=style,lw=1.15,marker='o' if markers else None,ms=2.7)
    for a,b in zip(x,y):mark(panel,label,float(a),float(b))
def point(ax,y,value,lo,hi,label,color=COLORS[0],dy=0):
    assert lo<=value+1e-7 and value<=hi+1e-7
    ax.errorbar(value,y+dy,xerr=[[max(0,value-lo)],[max(0,hi-value)]],fmt='o',color=color,ms=4,capsize=2,lw=1,clip_on=False)
    mark(ax.get_title(),label,value,y,lo,hi)
def grid(ax):ax.grid(axis='x',color='#D5DADF',lw=.5,alpha=.7);ax.set_axisbelow(True)
def writecsv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['panel','series','x','y','low','high','n']);w.writeheader();w.writerows(rows)
def save(fig,id,title,caption,role='附录',old=None,extra=''):
    fig.canvas.draw()
    for fmt in ['png','pdf','svg']:fig.savefig(OUT/f'{id}.{fmt}',dpi=600,facecolor='white')
    writecsv(OUT/f'{id}.csv',MARKS)
    CAT.append({'id':id,'title':title,'role':role,'old_group':old or id[:3],
        'caption':caption,'limitations':extra,'sources':sorted(USED),'plotted_rows':len(MARKS),
        'width_mm':round(fig.get_figwidth()*25.4,1),'height_mm':round(fig.get_figheight()*25.4,1),'png_dpi':600,
        'formats':['png','pdf','svg','csv'],'font_pt':9,'no_smoothing':True})
    MARKS.clear();USED.clear();plt.close(fig)
def subplots(nrows=1,ncols=1,height=3.2,**kw):
    return plt.subplots(nrows,ncols,figsize=(7.1,height),layout='constrained',**kw)

def method():
    # Structure verified against the frozen original WM evaluator, not recovery.
    USED.update(['evaluate_delay.py','world_model.py','common.py',CONF+'/design.json'])
    fig,ax=subplots(height=3.25);ax.set(xlim=(0,10),ylim=(0,5));ax.axis('off')
    boxes=[(.1,3.35,'观测状态 xₜ\n23 维低维状态'),(3.5,3.35,'固定 BC 动作块\nk = 0, 1, 2, 3'),(6.9,3.35,'真实 D=2 队列前缀\n+ 候选重复动作，H=8'),
        (.1,1.25,'GRU 未来状态预测\n输入：状态与动作序列'),(3.5,1.25,'进展 p / 失抓 r 评分\n与 k=2 比较，差值门控'),(6.9,1.25,'提交一个新动作\n执行队首，再观测')]
    for x,y,t in boxes:
        ax.add_patch(FancyBboxPatch((x,y),2.95,1.05,boxstyle='round,pad=.04',fc='#F0F4F7',ec='#66717B',lw=.7));ax.text(x+1.475,y+.525,t,ha='center',va='center',fontsize=9)
    def arrow(a,b):ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','lw':.9,'color':'#4B5563'})
    arrow((3.1,3.88),(3.43,3.88));arrow((6.5,3.88),(6.83,3.88));arrow((1.57,3.28),(1.57,2.38))
    ax.plot([8.37,8.37,2.6],[3.28,2.8,2.8],c='#4B5563',lw=.9);arrow((2.6,2.8),(2.6,2.38))
    arrow((3.1,1.77),(3.43,1.77));arrow((6.5,1.77),(6.83,1.77))
    ax.plot([8.37,8.37,.02,.02,1.57],[1.2,.8,.8,4.85,4.85],color='#7C8792',lw=.7);arrow((1.57,4.85),(1.57,4.47))
    ax.text(5,.23,'S = p(H) + 0.5 mean(p) − 0.5 max(r)；差值 < 0.02 时回退 k=2',ha='center',fontsize=9)
    save(fig,'F01','延迟一致的世界模型候选选择','结构示意：世界模型确认配置，23维状态含物体真值，D=2，H=8，K=4。r监督失抓，不是通用失败概率。每次仅提交一个动作。','正文',extra='此图不含后续规则恢复，也不证明性能。')

def training():
    d=j(DEEP+'/diagnostics.json');f=j('figures/figure_data.json')['figures']
    metrics=[('total_loss','固定集总损失'),('prediction_mse','归一化状态 MSE'),('object_error_mm','物体位置平均欧氏误差（mm）')]
    for k,(field,label) in enumerate(metrics):
        USED.update([DEEP+'/diagnostics.json',DEEP+'/checkpoint_metrics.csv','figures/figure_data.json'])
        fig,axes=subplots(1,3,height=2.65,sharey=True)
        for ax,s in zip(axes,SEEDS):
            for split,col,style,name in [('train',COLORS[0],'-','训练集'),('dev',COLORS[1],'--','开发集')]:
                rows=[r for r in d['checkpoint_metrics'] if r['seed']==s and r['split']==split];assert len(rows)==12
                line(ax,[r['step'] for r in rows],[r[field] for r in rows],name,col,style,f's{s}')
            chosen=next(r['selected_step'] for r in f['figure_training_curves'] if r['seed']==s)
            ax.axvline(chosen,color='#707070',ls=':',lw=.8);ax.set(title=f's{s} · 原选择 {chosen}',xlabel='优化器更新次数',xticks=[250,1500,3000]);grid(ax)
        axes[0].set_ylabel(label);axes[0].legend(frameon=False,fontsize=8,loc='best')
        save(fig,f'F02{chr(97+k)}',label+'：训练与开发集',f'36个既存权重的固定数据集评估；每种子12个采样点（250至3000，每250更新一次），未平滑。训练160组/20父轨迹，开发64组/8父轨迹。竖点线为原选择权重，未重新选点。{label}；不是批次损失或闭环成功率。','正文','F02','总损失、全状态MSE与平均欧氏位置误差不同；真实泛化差距保留。')
    USED.add('figures/figure_data.json')
    fig,axes=subplots(1,3,height=2.7)
    for ax,key,title in zip(axes,['loss','prediction_loss','ranking_loss'],['总损失','状态预测损失','排序损失']):
        for s,col in zip(SEEDS,COLORS):
            r=next(r for r in f['figure_training_curves'] if r['seed']==s)
            entries=r['records']
            line(ax,[q['step'] for q in entries],[q[key] for q in entries],f's{s}',col,':',title)
        ax.set(title=title,xlabel='优化器更新次数',xticks=[250,1500,3000]);grid(ax)
    axes[0].set_ylabel('当前随机批次损失');axes[0].legend(frameon=False,fontsize=8)
    save(fig,'A01','原始批次训练日志','每250次更新采样当前随机批次，每种子12个点。虚线仅连接已记录点；不是每步连续轨迹或全训练集平均。','附录','root_training','稀疏、不同批次与多损失项会造成折线抖动；不插值、不平滑。')
    USED.add(DEEP+'/diagnostics.json');fig,axes=subplots(1,2,height=2.9)
    for s,col in zip(SEEDS,COLORS):
        rows=[r for r in d['checkpoint_metrics'] if r['seed']==s and r['split']=='dev']
        line(axes[0],[r['step'] for r in rows],[r['mean_regret'] for r in rows],f's{s}',col,':','均值')
    rows=[r for r in d['checkpoint_metrics'] if r['seed']==23 and r['split']=='dev'];detail=[r for r in d['dev_group_details'] if r['seed']==23]
    line(axes[1],[r['step'] for r in rows],[r['mean_regret'] for r in rows],'s23 整体均值',COLORS[0],':','贡献')
    line(axes[1],[r['step'] for r in detail],[r['regret'][5]/64 for r in detail],'组 5 / 64',COLORS[1],'--','贡献')
    for ax in axes:ax.set(xlabel='优化器更新次数',ylabel='开发集 regret',xticks=[250,1500,3000]);ax.legend(frameon=False,fontsize=8);grid(ax)
    save(fig,'F03','离散候选选择造成的 regret 跳变','64组来自8父轨迹。regret为同组最优真实短期分数减所选候选的真实分数。s23在1500步，组5贡献约0.005103/整体0.005604≈91%。点线仅连接12个权重评估点。','附录',extra='不是每步连续测量或闭环成功率；39个有效候选对不足以支持稳定泛化。')

def rates_and_pairs():
    for id,dev in [('F04',True),('F05',False)]:
        rows=c((WM if dev else CONF)+'/analysis/summary.csv')
        methods=['bc_k2','full','plain','direct','prediction_only','no_risk_score','no_gate'] if dev else ['bc_k2','full','plain']
        fig,axes=subplots(1,2,height=3.65 if dev else 2.7,sharex=True)
        for ax,cond,title in zip(axes,['clean','noise005'],['无噪声','动作噪声 σ=0.05']):
            ax.set_title(title)
            for i,m in enumerate(methods):
                r=next(r for r in rows if r['method']==m and (('clean' if float(r['noise'])==0 else 'noise005') if dev else r['condition'])==cond)
                pre='crossed_bootstrap_ci_' if dev else 'paired_crossed_bootstrap_';v=float(r['mean_success_percent']);lo=float(r[pre+'low_percent']);hi=float(r[pre+'high_percent'])
                point(ax,i,v,lo,hi,m,COLORS[0] if m=='full' else '#5B6268')
                ax.text(.02,i+.28,f'{v:.1f}%',transform=ax.get_yaxis_transform(),fontsize=8,color='#5B6268')
            ax.set(yticks=range(len(methods)),yticklabels=[METHODS[m] for m in methods],xlim=(0,100),xticks=[0,25,50,75,100],xlabel='成功率（%）',ylim=(len(methods)-.4,-.5));grid(ax)
        save(fig,id,'开发集公平消融' if dev else '原世界模型独立确认',f'每条件{30 if dev else 60}个共同起点；BC固定权重，其余方法三个训练种子。点为均值，线为原分析20000次起点/种子交叉bootstrap的95%区间。成功率轴严格0–100%。','正文',extra=('开发集不可称独立确认；' if dev else '原确认不含共享恢复；三个种子共享同批起点；')+'方法差异看配对差值区间，不能用种子SD替代抽样CI。')
    f=j('figures/figure_data.json')['figures']
    for id,cond in [('F06','clean'),('F07','noise005')]:
        USED.add('figures/figure_data.json');a=np.asarray([r['counts'] for r in f['figure_paired_'+cond]]);assert a.shape==(3,4) and (a.sum(1)==60).all()
        fig,ax=subplots(height=2.15);ax.pcolormesh(np.arange(5)-.5,np.arange(4)-.5,a,cmap='Blues',vmin=0,vmax=60);ax.set_ylim(2.5,-.5)
        for (i,k),n in np.ndenumerate(a):ax.text(k,i,str(n),ha='center',va='center',color='white' if n>30 else '#222');mark(cond,f's{SEEDS[i]}',k,int(n),n=60)
        ax.set(yticks=range(3),yticklabels=[f'Full s{s}' for s in SEEDS],xticks=range(4),xticklabels=['双方成功','仅 Full 成功','仅 BC 成功','双方失败'])
        save(fig,id,'相同起点的配对结果 · '+cond,'每行60个相同起点，三行共享起点与固定BC k=2。计数相同不表示权重或动作相同；三行不是180个独立起点。')
    USED.add('figures/figure_data.json');fig,axes=subplots(1,2,height=2.9,sharex=True,sharey=True)
    for ax,cond,title in zip(axes,['clean','noise005'],['无噪声','动作噪声 σ=0.05']):
        for s,col in zip(SEEDS,COLORS):
            a=np.array([r['difference'] for r in f['figure_success_steps'] if r['condition']==cond and r['seed']==s]);x=np.unique(a);y=np.array([100*np.mean(a<=v) for v in x]);ax.step(np.r_[x[0]-1,x],np.r_[0,y],where='post',color=col,lw=1.1,label=f's{s}, n={len(a)}')
            for k,v in enumerate(a):mark(cond,f's{s} raw difference',k,int(v),n=len(a))
            for v,p in zip(x,y):mark(cond,f's{s} ECDF',int(v),p,n=len(a))
        ax.axvline(0,c='#777',lw=.8,ls='--');ax.set(title=title,xlabel='完成步数差：Full − BC',ylim=(0,100));grid(ax);ax.legend(frameon=False,fontsize=8)
    axes[0].set_ylabel('经验累计比例（%）')
    save(fig,'F08','双方成功交集的完成步数差','负值表示Full更快；阶梯是整数步数的经验分布，不是画图错误。包含全部长尾：clean每种子51个共同成功，noise每种子49个。','附录',extra='成功交集条件分析，不能代表全体起点效率，不能把失败400步当真实完成时间。')

def forecast_and_extensions():
    rows=j(EXT+'/offline_metrics.json')['rows'];fig,axes=subplots(1,2,height=2.8)
    for ax,key,title in zip(axes,['eef_position_rmse_m','object_position_rmse_m'],['末端位置','物体位置']):
        for i,m in enumerate(['persistence','full','plain']):
            v=[r[key]*1000 for r in rows if r['method']==m];shown=v[:1] if m=='persistence' else v
            ax.scatter(np.full(len(shown),i),shown,c=COLORS[i],s=18);ax.plot([i-.18,i+.18],[np.mean(v)]*2,c='#333',lw=1.4)
            for n,y in enumerate(shown):mark(title,m,n,y)
            ax.text(i,max(v)+3,f'{np.mean(v):.2f}',ha='center',fontsize=8)
        ax.set(title=title,xticks=range(3),xticklabels=['持续性','Full','Plain'],ylabel='位置 RMSE（mm）',ylim=(0,70));ax.grid(axis='y',alpha=.2)
    save(fig,'F09','位置 RMSE 与持续性弱基线','64开发分支组/8父轨迹，K=4，H=8。点为各训练种子，横杠为均值；持续性为单个无参数预测器。数值与旧F19相同，合并为一张。','正文',extra='RMSE不等于平均欧氏误差。已用于选点的开发数据，不是独立测试。')
    rows=c(CONF+'/analysis/paired_comparisons.csv');fig,axes=subplots(1,3,height=2.8,sharex=True)
    for ax,cond,title in zip(axes,['clean','noise005','joint_equal_weight'],['无噪声','噪声 0.05','两条件等权']):
        ax.set_title(title)
        for i,(l,r) in enumerate([('full','bc_k2'),('plain','bc_k2'),('full','plain')]):
            q=next(q for q in rows if q['left']==l and q['right']==r and q['condition']==cond)
            point(ax,i,float(q['mean_difference_pp']),float(q['paired_crossed_bootstrap_low_pp']),float(q['paired_crossed_bootstrap_high_pp']),l+' − '+r)
        ax.set(yticks=range(3),yticklabels=['Full − BC','Plain − BC','Full − Plain'],ylim=(2.6,-.6),xlabel='成功率差（百分点）');ax.axvline(0,c='#777',ls='--',lw=.8);grid(ax)
    save(fig,'F10','原世界模型确认的配对差值','60个共同起点，BC固定，Full/Plain各3种子。95%起点/种子交叉bootstrap区间。联合Full−BC为+4.72[0.56,10.28]百分点；Full−Plain为+1.94[−0.56,6.11]。','正文',extra='排序相对Plain的区间跨零；联合条件仍共享60起点。')
    rows=j(EXT+'/analysis/summary.json');by={(r['variant'],r['noise']):r for r in rows}
    fig,axes=subplots(1,2,height=3.0)
    for ax,n,title in zip(axes,[0.,.05],['无噪声','噪声 0.05']):
        ax.set_title(title)
        ms=['bc_k2','persistence','full','plain','oracle']
        for i,m in enumerate(ms):
            r=by[m,n];v=r['mean_success_percent'];lo,hi=r['paired_bootstrap_ci_percent'];point(ax,i,v,lo,hi,m)
        ax.set(yticks=range(5),yticklabels=[METHODS[m] for m in ms],xlim=(0,100),xticks=[0,25,50,75,100],ylim=(4.6,-.6),xlabel='成功率（%）');grid(ax)
    save(fig,'F11','持续性与真值短期评分候选对照','30个共同开发起点。Full/Plain为3个冻结权重均值，其他策略每条件一次；95%配对bootstrap区间。真值候选使用特权无噪声短期反事实、H=8与相同门控。','正文',extra='oracle是局部短期评分诊断，不是任务成功上界；并不保证长期最佳。')
    for id,variants,labels,title in [('F12a',['h1','h3','horizon4','full'],['H=1','H=3','H=4','H=8'],'预测时域'),('F12b',['k1','k2','full','k8'],['K=1\n{2}','K=2\n{0,2}','K=4\n{0,1,2,3}','K=8\n{0,…,7}'],'候选集合')]:
        USED.add(EXT+'/analysis/summary.json');fig,ax=subplots(height=2.8)
        for n,col,delta,label in [(0.,COLORS[0],-.1,'无噪声'),(.05,COLORS[1],.1,'噪声 0.05')]:
            for x,v in enumerate(variants):
                r=by[v,n];ys=np.array(r['success_counts'])/30*100;mean=r['mean_success_percent']
                ax.scatter(np.full(len(ys),x+delta),ys,facecolors='none',edgecolors=col,s=22,label=label if x==0 else None)
                ax.plot([x+delta-.07,x+delta+.07],[mean]*2,c=col,lw=2)
                for i,y in enumerate(ys):mark(label,v,i,y,n=30)
                mark(label,v+' mean',x,mean,n=30)
        ax.set(xticks=range(4),xticklabels=labels,ylim=(0,100),ylabel='开发集成功率（%）');ax.grid(axis='y',alpha=.2);ax.legend(frameon=False,fontsize=8,loc='lower left')
        save(fig,id,title+'配置敏感性','空心点为各冻结种子，短横线为均值；每条件30开发起点，成功率轴0–100%。离散配置不连折线。H包含D=2 FIFO前缀；H=1尚不能看到新提交动作。K=8同时扩展到训练外索引。','正文','F12','K改变了候选内容，不能解释为纯数量因果效应；没有在确认集选配置。')
    rows=c(WM+'/offline/prediction_horizons.csv');fig,axes=subplots(1,2,height=2.85)
    for ax,key,title in zip(axes,['eef_error_mm','object_error_mm'],['末端位置','物体位置']):
        for r in rows:
            if r['method'] in ['control','calibrated']:
                ref=next(q for q in rows if q['method']=='full' and q['seed']==r['seed'] and q['horizon']==r['horizon'])
                assert float(r[key])==float(ref[key])
        for m,col,ls in zip(['full','plain'],COLORS,['-','--']):
            rr=[r for r in rows if r['method']==m];seeds=sorted({r['seed'] for r in rr});hs=sorted({int(r['horizon']) for r in rr});a=np.array([[float(next(r[key] for r in rr if r['seed']==s and int(r['horizon'])==h)) for h in hs] for s in seeds]);mu=a.mean(0);sd=a.std(0,ddof=1)
            line(ax,hs,mu,METHODS.get(m,m),col,ls,title);ax.fill_between(hs,mu-sd,mu+sd,color=col,alpha=.1)
            for s,ys in zip(seeds,a):
                for h,y in zip(hs,ys):mark(title,m+' s'+s,h,y)
        ax.set(title=title,xlabel='预测步',ylabel='平均欧氏位置误差（mm）',xticks=[1,2,4,6,8]);ax.legend(frameon=False,fontsize=8);grid(ax)
    save(fig,'F13','不同预测步的位置误差','64个已知开发组/8父轨迹。线为三个训练种子的均值，阴影为种子样本SD（ddof=1），不是95%CI。横轴是真实预测步。评分头续训control/calibrated的动力学与Full逐值完全一致，合并显示Full线，未删除不同结果。','附录',extra='此指标是平均欧氏距离，不是F09的RMSE。重叠的相同预测不构成三份独立证据。')

def recovery():
    for id,stage,role in [('F14','confirmation','正文'),('A02','dev_a','附录')]:
        d=j(V5+'/analysis_'+stage+'/summary.json');st=d['statistics'];fig,axes=subplots(1,2,height=3.2)
        for ax,cond,title in zip(axes,['clean','noise005'],['无噪声','噪声 0.05']):
            ax.set_title(title)
            for y,v in enumerate(VERSIONS):
                for method,col,dy in [('bc',COLORS[0],-.12),('full',COLORS[1],.12)]:
                    q=st[cond][v+'_'+method];point(ax,y,100*q['estimate'],100*q['ci95'][0],100*q['ci95'][1],v+' '+method,col,dy)
            ax.set(yticks=range(5),yticklabels=VN,ylim=(4.6,-.8),xlim=(0,100),xticks=[0,25,50,75,100],xlabel='成功率（%）');grid(ax)
        fig.legend(handles=[plt.Line2D([],[],c=COLORS[0],marker='o',ls='',label='BC k=2'),plt.Line2D([],[],c=COLORS[1],marker='o',ls='',label='Full 三种子均值')],loc='outside lower center',ncol=2,frameon=False,fontsize=8)
        save(fig,id,'共享恢复的'+('独立确认' if stage=='confirmation' else '开发对照'),f'{d["unique_starts"]}个共同起点；每版本每起点8个执行条件，Full固定3种子。点/线为成功率和按起点重采样95%区间。v5原生确认464/480，不能当480个独立样本。' if stage=='confirmation' else '30个已知开发起点，每版本240次执行；v5与后续v6均236/240。起点bootstrap，不能写成独立确认。',role,extra='与原无恢复世界模型确认是不同批次；不能直接相减估计恢复效应。')
    d=j(V5+'/analysis_confirmation/summary.json')['statistics']
    sets=[('F15a',[(name,d[cond][key]) for cond,key,name in [('clean','v5_bc_minus_v4','BC，无噪声'),('noise005','v5_bc_minus_v4','BC，噪声'),('clean','v5_full_minus_v4','Full，无噪声'),('noise005','v5_full_minus_v4','Full，噪声')]]+[('预设执行混合',d['overall_execution_mix']['v5_minus_v4'])]),('F15b',[(lab,d['overall_execution_mix'][v+'_minus_v4']) for lab,v in [('仅时机 T','timing_only'),('仅间隙 S','side_only'),('v5（T+S）','v5')]])]
    for id,rr in sets:
        USED.add(V5+'/analysis_confirmation/summary.json');fig,ax=subplots(height=2.7)
        for y,(lab,q) in enumerate(rr):
            v=q['estimate']*100;lo,hi=np.array(q['ci95'])*100;point(ax,y,v,lo,hi,lab)
        ax.set(yticks=range(len(rr)),yticklabels=[r[0] for r in rr],ylim=(len(rr)-.4,-.6),xlabel='成功率差：相对 v4（百分点）');ax.axvline(0,c='#777',ls='--',lw=.8);grid(ax)
        save(fig,id,'v5 起点配对效应与模块对照','同60起点，20000次起点bootstrap、逐项95%区间。原预设执行混合v5−v4=+1.46[0,4.17]百分点：7次执行改善仅来自2个起点；三个训练种子固定。','正文','F15','区间未多重比较校正，包含零不能称显著普遍优势；无v5同批关闭恢复组。')
    d=j(V5+'/analysis_geometry_confirmation/summary.json');kinds=[k for k in d['totals']['v5'] if k!='all'];a=np.array([[d['totals'][v][g]['successes'] for g in kinds] for v in VERSIONS]);fig,ax=subplots(height=2.65)
    ax.pcolormesh(np.arange(5)-.5,np.arange(6)-.5,a,cmap='Blues',vmin=0,vmax=4);ax.set_ylim(4.5,-.5)
    for (i,k),v in np.ndenumerate(a):ax.text(k,i,f'{v}/4',ha='center',va='center',color='white' if v>=3 else '#222');mark(kinds[k],VERSIONS[i],k,int(v),n=4)
    ax.set(yticks=range(5),yticklabels=VN,xticks=range(4),xticklabels=['远距离对齐','目标箱角落','源区域侧倒','目标区域侧倒'])
    save(fig,'F16','独立几何分层压力测试','四个人工几何层，每层4起点，共16；5版本共80次执行。固定静止开爪提议、第80步强制恢复，400步上限；v5合计12/16。','正文',extra='小样本描述计数；不能合并原生确认，也不能称一般分布成功率。')
    d=j(V5+'/mechanism_physics.json')['results'][:4]
    fig,ax=subplots(height=2.7);groups={'NORMAL':0,'RETRACT':1,'ALIGN':1,'DESCEND':2,'CLOSE':2,'TEST_LIFT':2,'LIFT':3,'CARRY':3,'PLACE':4,'RELEASE':4,'RETREAT':4,'EXHAUSTED':5}
    colors=['#A0A6AC',COLORS[0],COLORS[1],COLORS[2],COLORS[3],'#5E4C68'];labels=['基础策略','接近/对齐','抓取/确认','搬运','放置/释放','预算耗尽']
    for i,r in enumerate(d):
        vals=[groups[p] for p in r['phases']];start=0
        for k in range(1,len(vals)+1):
            if k==len(vals) or vals[k]!=vals[start]:ax.broken_barh([(start,k-start)],(i-.28,.56),facecolors=colors[vals[start]]);start=k
        for t,p in enumerate(r['phases'],1):mark(r['demo'],r['job'],t,groups[p])
    ax.set(yticks=range(4),yticklabels=['v4 / 73（失败）','时机修复 / 73','v4 / 124（失败）','时机修复 / 124'],xlim=(0,400),ylim=(3.5,-.5),xlabel='控制步（20 Hz，D=2，预算400）')
    fig.legend(handles=[Patch(color=co,label=la) for co,la in zip(colors,labels)],loc='outside lower center',ncol=3,fontsize=8,frameon=False)
    save(fig,'F17','已知开发案例的控制阶段时间线','从既有机制回放记录提取；案例73与124已知，不是独立确认。阶段是离散类别，因此用时间条而非数字折线。成功轨迹在真实结束步停止。','附录',extra='只说明机制，不把单例效果推广至所有起点。')
    ff=j('reproduction/consolidation_20261012_01/factorial_analysis.json');keys=['recovery_for_bc','recovery_for_full','world_model_without_recovery','world_model_with_recovery','interaction'];names=['恢复效应：BC','恢复效应：Full','Full−BC，无恢复','Full−BC，有恢复','交互项']
    for i,r in enumerate(ff):
        USED.add('reproduction/consolidation_20261012_01/factorial_analysis.json');fig,axes=subplots(1,2,height=3.1,sharex=True)
        for ax,cond,title in zip(axes,['clean','noise005'],['无噪声','噪声 0.05']):
            ax.set_title(title)
            for y,key in enumerate(keys):
                q=r['effects'][cond][key];v=100*q['estimate'];lo,hi=np.array(q['ci95'])*100;point(ax,y,0 if abs(v)<1e-10 else v,lo,hi,key)
            ax.set(yticks=range(5),yticklabels=names,ylim=(4.6,-.6),xlabel='成功率差（百分点）');ax.axvline(0,c='#777',ls='--',lw=.8);grid(ax)
        title=['v2批次 / v2恢复','v3批次 / v2恢复','v3批次 / v3恢复'][i]
        save(fig,'F18'+chr(97+i),'既有四组效应：'+title,'既有两批各60起点的事后分析；后两图共用v3批次。Full平均三个固定权重，按起点配对95%逐项区间。浮点负零规范显示为0，未改变数据。','附录','F18','不能拼成v5因果对照；不进行跨批次择优或宣称三次独立确认。')

def later_diagnostics():
    pilot=j(V6+'/analysis/pilot_b.json')['variants'];dev=j(V6+'/analysis/dev_comparison.json');fig,axes=subplots(1,2,height=2.6)
    for ax,names,vs,n,title in [(axes[0],['v5','R1','R2','R1+R2'],[pilot[v]['success'] for v in ['v5','r1','r2','v6']],37,'已知诊断条件'),(axes[1],['v5','v6'],[dev['v5_successes'],dev['v6_successes']],240,'开发执行混合')]:
        ax.scatter(range(len(vs)),np.array(vs)/n*100,c=COLORS[:len(vs)],s=25)
        for i,v in enumerate(vs):ax.text(i,v/n*100-10,f'{v}/{n}',ha='center',fontsize=8);mark(title,names[i],i,v,n=n)
        ax.set(title=title,xticks=range(len(vs)),xticklabels=names,xlim=(-.4,len(vs)-.6),ylim=(0,100),ylabel='成功率（%）');ax.grid(axis='y',alpha=.2)
    save(fig,'A03','v6 开度与不可行处理消融','37个已知诊断条件的R1/R2消融；开发240次执行共享30起点，v5与v6均236/240，没有开发成功率改善。','附录','v6_outcomes')
    fig,ax=subplots(height=2.7)
    for v,col,ls in [('v5',COLORS[1],'--'),('v6',COLORS[0],'-')]:
        r=[r for r in j('traces/v6_aperture_'+v+'.json') if 80<=r['step']<=146]
        line(ax,[r['step'] for r in r],[abs(r['state_before'][7]-r['state_before'][8])*1000 for r in r],v,col,ls,'state_before')
    ax.axhline(56,c='#555',ls=':',lw=.8,label='计划开度 56 mm');ax.axhspan(51.5,60.5,color=COLORS[0],alpha=.07,label='原 R1 容差');ax.set(xlim=(80,146),ylim=(0,90),xlabel='控制步',ylabel='观测指间距（mm）');ax.legend(frameon=False,fontsize=8,ncol=2);grid(ax)
    save(fig,'A04','恢复开度：观测与计划不一致','已知侧倒失抓案例11000013；采用原图state_before语义，每控制步一个原始观测，无平滑。','附录','v6_aperture','控制命令不等于实际开度，不能仅凭目标值判断抓取空间。')
    fig,ax=subplots(height=2.4);modes=['DESCEND','ABORT_RETRACT','BLOCKED'];colors=COLORS[:3]
    for y,v in enumerate(['v5','v6']):
        rr=j('traces/v6_infeasible_'+v+'.json')
        for mode,color in zip(modes,colors):
            steps=[r['step'] for r in rr if r['mode']==mode];ax.broken_barh([(s-1,1) for s in steps],(y-.25,.5),facecolors=color)
        for r in rr:mark(v,r['mode'],r['step'],modes.index(r['mode']) if r['mode'] in modes else -1)
    ax.set(yticks=[0,1],yticklabels=['v5','v6'],ylim=(1.5,-.5),xlim=(0,400),xlabel='控制步');fig.legend(handles=[Patch(color=co,label=m) for co,m in zip(colors,modes)],loc='outside lower center',ncol=3,frameon=False,fontsize=8)
    save(fig,'A05','无可行候选时的离散控制阶段','Full s23、无噪声、demo188：双方都未完成。新保护减少重复下降，但没有创造可行抓取。空白为其他控制阶段，CSV保留全部阶段。','附录','v6_infeasible')
    # Older v10 diagnostic: split 16-panel sheet into two readable figures.
    rr=c(V10+'/analysis/wall_edge_trajectories.csv')
    for suffix,fields,labels in [('a',['eef_z_m','can_z_m'],['末端高度（m）','物体高度（m）']),('b',['can_goal_xy_distance_m','can_axis_tilt_deg'],['物体到目标XY距离（m）','物体轴倾角（°）'])]:
        USED.add(V10+'/analysis/wall_edge_trajectories.csv');fig,axes=subplots(1,2,height=2.8)
        for ax,key,label in zip(axes,fields,labels):
            for v,col,ls in zip(['v6','v9','path','v10'],COLORS,['-','--',':','-.']):
                r=[r for r in rr if r['version']==v];line(ax,[int(r['step']) for r in r],[float(r[key]) for r in r],v,col,ls,key,False)
            ax.set(xlim=(0,400),xlabel='控制步',ylabel=label);grid(ax)
        axes[0].legend(frameon=False,ncol=2,fontsize=8)
        save(fig,'A06'+suffix,'v10 箱沿已知案例：'+('/'.join(labels)), 'demo6000005，BC k=2、噪声0.05；同起点同噪声。逐步观测，不平滑；v6成功后在实际结束步停止。','附录','v10_wall','轨迹复杂不是绘图插值；v6的完成来自BC接管，不应声称新恢复抓持。')
    rr=j(V11+'/analysis/development.json');fig,ax=subplots(height=3.35);a=np.array([[g['v6_success'],g['v11_success']] for g in rr['groups']]);ax.pcolormesh(np.arange(3)-.5,np.arange(9)-.5,a,cmap='Blues',vmin=0,vmax=30);ax.set_ylim(7.5,-.5)
    for (y,x),v in np.ndenumerate(a):ax.text(x,y,f'{v}/30',ha='center',va='center',color='white');mark(rr['groups'][y]['condition'],['v6','v11'][x],x,int(v),n=30)
    ax.set(yticks=range(8),yticklabels=[g['condition'] for g in rr['groups']],xticks=[0,1],xticklabels=['v6：236/240','v11：235/240'])
    save(fig,'A07','v11 开发集逐条件退步核对','30个相同起点、8执行条件；Full s41噪声组少1次成功，v11未达到采用门槛，未独立确认。','附录','v11_development','不能用颜色差或240执行次数夸大独立样本量。')
    # Every plotted v11 trace metric is exported, including previously missing target XY distance.
    for id,prefix,versions,title in [('A08','v11_edge_',['v10','axis','guard','v11'],'已知箱沿四组消融'),('A09','v11_regression_',['v6','v11'],'持物等待开发退步')]:
        traces={v:j('traces/'+prefix+v+'.json') for v in versions}
        initial=next(iter(traces.values()))[0]['state_before']
        for r in traces.values():np.testing.assert_array_equal(initial,r[0]['state_before'])
        for part,keys,labels in [('a',['eef_z','can_z'],['末端世界高度（m）','物体世界高度（m）']),('b',['goal_xy','gap' if id=='A08' else 'eef_can'],['物体到目标XY距离（m）','观测指间距（mm）' if id=='A08' else '末端与物体距离（mm）'])]:
            USED.update('traces/'+prefix+v+'.json' for v in versions);fig,axes=subplots(1,2,height=2.8)
            for ax,key,label in zip(axes,keys,labels):
                for v,col,ls in zip(versions,COLORS,['-','--',':','-.']):
                    r=traces[v];x=np.array([q['state_after'] for q in r]);t=[q['step'] for q in r]
                    yy={'eef_z':x[:,2],'can_z':x[:,18],'goal_xy':np.linalg.norm(x[:,16:18]-[.1975,.4025],axis=1),'gap':abs(x[:,7]-x[:,8])*1000,'eef_can':np.linalg.norm(x[:,:3]-x[:,16:19],axis=1)*1000}[key]
                    line(ax,t,yy,v,col,ls,key,False)
                ax.set(xlim=(0,400),xlabel='控制步（20 Hz，D=2）',ylabel=label);grid(ax)
            axes[0].legend(frameon=False,ncol=2,fontsize=8)
            save(fig,id+part,title+'：'+('/'.join(labels)), 'state_after原始每控制步数据，同起点验证通过，无平滑/补零/终点外推。'+('BC k=2、噪声0.05、demo6000005；仅v11在380步完成。' if id=='A08' else 'Full s41、噪声0.05、demo87；v6在358步成功，v11在400步失败；新箱沿模块未触发。'), '附录',id,'真实控制阶段/观测波动保留。逐点CSV补全了旧v11退步图未导出的目标XY距离。')

def main():
    global OUT
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=RUN/'figures');p.add_argument('--replace-generated',action='store_true');args=p.parse_args();OUT=args.output.resolve()
    if OUT.exists() and any(OUT.iterdir()) and not (args.replace_generated and OUT==(RUN/'figures').resolve() and (OUT/'CATALOG.json').is_file()):raise SystemExit('Use a new output directory; --replace-generated only repairs this new package\'s own generated figures.')
    OUT.mkdir(parents=True,exist_ok=True)
    available={f.name for f in font_manager.fontManager.ttflist};font=next((f for f in ['Microsoft YaHei','Noto Sans CJK SC','SimHei','SimSun'] if f in available),None)
    if not font:raise SystemExit('Install a Chinese font (Noto Sans CJK SC or Microsoft YaHei); do not export missing glyphs.')
    plt.rcParams.update({'font.family':[font,'DejaVu Sans'],'font.size':9,'axes.titlesize':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.6,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'path','axes.unicode_minus':False,'savefig.facecolor':'white'})
    import logging
    logging.getLogger('fontTools.subset').setLevel(logging.ERROR)
    method();training();rates_and_pairs();forecast_and_extensions();recovery();later_diagnostics()
    (OUT/'CATALOG.json').write_text(json.dumps({'font':font,'figures':CAT,'new_experiments':0},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'figure_groups':len(CAT),'formats_per_group':4,'output':str(OUT),'font':font,'new_experiments':0}))
if __name__=='__main__':main()
