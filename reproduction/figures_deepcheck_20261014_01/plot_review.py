"""Alternative figures exposing uncertainty and fixed-dataset checkpoint metrics."""
from pathlib import Path
import sys,json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
ROOT=Path(__file__).resolve().parents[2]; RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import make_figures as old
OUT=RUN/'figures';OUT.mkdir(exist_ok=True)
D=json.loads((RUN/'diagnostics.json').read_text(encoding='utf8'))
F=json.loads((ROOT/'figures/figure_data.json').read_text(encoding='utf8'))['figures']
plt.rcParams.update({'font.size':10,'axes.titlesize':12})
def save(fig,name,note):
    fig.text(.5,.015,note,ha='center',fontsize=9,color='#475569')
    fig.tight_layout(rect=(0,.09,1,.94))
    fig.savefig(OUT/f'{name}.png',dpi=220)
    fig.savefig(OUT/f'{name}.pdf')
    plt.close(fig)
def rows(path):
    with path.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def rate_plot(development=False):
    methods=['bc_k2','full','plain','direct','prediction_only','no_risk_score','no_gate'] if development else ['bc_k2','full','plain']
    labels={'bc_k2':'BC k=2','full':'Full','plain':'Plain（无排序）','direct':'Direct','prediction_only':'仅预测 + 物理代价','no_risk_score':'Full 去风险评分','no_gate':'Full 去门控'}
    run=old.DEV if development else old.CONF
    table=rows(ROOT/run/'analysis/summary.csv')
    fig,axes=plt.subplots(1,2,figsize=(12,6 if development else 4.8),sharex=True)
    for ax,cond,title in zip(axes,['clean','noise005'],['无噪声','动作噪声 σ=0.05']):
        for i,m in enumerate(methods):
            r=next(r for r in table if r['method']==m and (('clean' if float(r['noise'])==0 else 'noise005') if development else r['condition'])==cond)
            prefix='crossed_bootstrap_ci_' if development else 'paired_crossed_bootstrap_'
            v=float(r['mean_success_percent']);lo=float(r[prefix+'low_percent']);hi=float(r[prefix+'high_percent'])
            ax.errorbar(v,i,xerr=[[v-lo],[hi-v]],fmt='o',color='#2563eb' if m=='full' else '#475569',capsize=4,ms=6)
            ax.text(103,i,f'{v:.1f}%',va='center',fontsize=10)
        ax.set(yticks=range(len(methods)),yticklabels=[labels[m] for m in methods],xlim=(0,119),xticks=range(0,101,20),xlabel='成功率（%）',title=title)
        ax.set_ylim(len(methods)-.5,-.6);ax.grid(axis='x',alpha=.15)
    n=30 if development else 60
    fig.suptitle(('开发集消融 · 不能作为独立确认' if development else '独立确认 · 成功率与不确定性'),fontsize=15)
    save(fig,'figure_ablation' if development else 'figure_success_rate',f'点 = 均值；线 = 原分析的 95% 交叉 bootstrap 区间。每条件 {n} 个起点；BC 固定权重，其他方法 3 个训练种子。\n区间反映样本不确定性，不是三个种子的极差；方法间结论应看配对差值区间。')

def pairs():
    for cond in ['clean','noise005']:
        data=F['figure_paired_'+cond];a=np.array([r['counts'] for r in data])
        fig,ax=plt.subplots(figsize=(9.2,4.1))
        ax.imshow(a,cmap='Blues',vmin=0,vmax=60,aspect='auto')
        for (i,j),v in np.ndenumerate(a):ax.text(j,i,str(v),ha='center',va='center',fontsize=16,color='white' if v>30 else '#0f172a')
        ax.set(xticks=range(4),xticklabels=['双方成功','仅 Full 成功','仅 BC 成功','双方失败'],yticks=range(3),yticklabels=['Full s17','Full s23','Full s41'])
        fig.suptitle(f"独立确认 · 相同起点配对计数 · {'无噪声' if cond=='clean' else '噪声 0.05'}",fontsize=15)
        save(fig,'figure_paired_'+cond,'每行共 60 个相同起点；三行共用起点。计数相同不表示模型或轨迹相同。BC 均为固定 k=2。')

def steps():
    fig,axes=plt.subplots(1,2,figsize=(11,5),sharex=True,sharey=True)
    for ax,c,title in zip(axes,['clean','noise005'],['无噪声','动作噪声 σ=0.05']):
        for s,col in zip(old.SEEDS,old.COLORS):
            a=np.array([r['difference'] for r in F['figure_success_steps'] if r['condition']==c and r['seed']==s])
            x=np.unique(a);y=[100*np.mean(a<=v) for v in x]
            ax.step(np.r_[x[0]-1,x],np.r_[0,y],where='post',color=col,label=f's{s} · n={len(a)}')
        ax.axvline(0,color='#94a3b8',ls='--',lw=1);ax.set(title=title,xlabel='配对步数差：Full − BC k=2',ylabel='累计回合比例（%）',ylim=(0,103))
        ax.grid(alpha=.15);ax.legend(frameon=False)
    fig.suptitle('双方均成功的回合 · 配对步数差完整分布',fontsize=15)
    save(fig,'figure_success_steps','负值 = Full 更快；零点的跳跃表示步数相同。只包含双方成功交集，不代表全体回合效率。\n阶梯来自离散整数步数；没有散点横向偏移、平滑或隐藏离群点。')

def training():
    fig,axes=plt.subplots(3,3,figsize=(12,9.8),sharex=True,sharey='row')
    metrics=[('total_loss','全量固定集总损失'),('prediction_mse','全量固定集归一化状态 MSE'),('object_error_mm','物体位置误差（mm）')]
    for j,s in enumerate(old.SEEDS):
        chosen=next(r['selected_step'] for r in F['figure_training_curves'] if r['seed']==s)
        for i,(field,label) in enumerate(metrics):
            ax=axes[i,j]
            for split,col,style in [('train','#2563eb','-'),('dev','#c56a22','--')]:
                r=[r for r in D['checkpoint_metrics'] if r['seed']==s and r['split']==split]
                ax.plot([r['step'] for r in r],[r[field] for r in r],color=col,ls=style,marker='o',ms=3,label='训练集' if split=='train' else '开发集')
            ax.axvline(chosen,color='#94a3b8',lw=.8,ls=':')
            if i==0:ax.set_title(f's{s} · 原选择 step {chosen}')
            if j==0:ax.set_ylabel(label)
            if i==2:ax.set_xlabel('已完成的优化器更新次数')
            ax.set_xticks([250,1500,3000]);ax.grid(alpha=.15)
    axes[0,0].legend(frameon=False)
    fig.suptitle('36 个已存 checkpoint 的固定数据集复算（没有重新训练）',fontsize=15)
    save(fig,'figure_training_curves','训练集：160 组 / 20 条父轨迹；开发集：64 组 / 8 条父轨迹。每个点都评估对应完整固定集。\n损失在更新后的权重上计算；不等于日志中更新前的随机批次损失。虚线标记原选中权重，未重新选择。')

def regret():
    fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    for s,col in zip(old.SEEDS,old.COLORS):
        r=[r for r in D['checkpoint_metrics'] if r['seed']==s and r['split']=='dev']
        axes[0].plot([v['step'] for v in r],[v['mean_regret'] for v in r],color=col,marker='o',label=f's{s}',ms=3)
    r=[r for r in D['checkpoint_metrics'] if r['seed']==23 and r['split']=='dev']
    axes[1].plot([v['step'] for v in r],[v['mean_regret'] for v in r],label='整体平均 regret',marker='o',ms=3)
    detail=[r for r in D['dev_group_details'] if r['seed']==23]
    axes[1].plot([v['step'] for v in detail],[v['regret'][5]/64 for v in detail],label='单个组 5 对均值的贡献',ls='--',marker='s',ms=3)
    for ax in axes:ax.set(xlabel='更新次数',ylabel='开发集 regret');ax.grid(alpha=.15);ax.legend(frameon=False)
    axes[0].set_title('三个种子的复算结果');axes[1].set_title('s23 突跳追踪：demo_105 的第 5 号组')
    fig.suptitle('评分曲线为何跳变：一个候选选择改变就能明显改变均值',fontsize=14)
    save(fig,'figure_regret_diagnostic','固定开发集仅 64 个候选组，来自 8 条父轨迹；组编号从 0 开始。此指标不是闭环成功率。')

def method():
    fig,ax=plt.subplots(figsize=(12,6));ax.axis('off');ax.set(xlim=(0,12),ylim=(0,6))
    boxes=[(.2,4.1,'观测状态 x_t\n23 维特权状态'),(4.25,4.1,'固定 BC\n提供 k=0,1,2,3 候选'),(8.3,4.1,'真实 FIFO 前缀\n+ 重复候选动作 · H=8'),
           (.2,1.7,'GRU 未来状态预测\n输入 x_t 与候选想象序列'),(4.25,1.7,'未来状态 → 进展 / 失抓评分\n最高分候选与 k=2 比较\n差值不足 0.02 则回退 k=2'),(8.3,1.7,'提交一个动作到 D=2 队列\n执行队首动作\n环境返回新的观测')]
    for x,y,t in boxes:
        ax.add_patch(FancyBboxPatch((x,y),3.45,1.15,boxstyle='round,pad=.08',fc='#eef4fa',ec='#94a3b8'))
        ax.text(x+1.725,y+.575,t,ha='center',va='center',fontsize=9.5)
    def arrow(a,b,connection='arc3'):
        ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'#475569','connectionstyle':connection,'lw':1.4})
    arrow((3.8,4.675),(4.1,4.675));arrow((7.85,4.675),(8.15,4.675))
    arrow((1.925,4),(1.925,3))
    ax.plot([10,10,3],[4,3.5,3.5],color='#475569',lw=1.4);arrow((3,3.5),(3,3))
    arrow((3.8,2.275),(4.1,2.275));arrow((7.85,2.275),(8.15,2.275))
    ax.plot([10,.05,.05,1],[1.2,1.2,5.65,5.65],color='#94a3b8',lw=1)
    arrow((10,1.6),(10,1.2));arrow((1,5.65),(1,5.4))
    ax.text(6,.9,'执行后重新观测，再进行下一次选择',ha='center',fontsize=9,color='#64748b')
    ax.text(6,.35,'S = p(H) + 0.5 mean(p) − 0.5 max(r)；r 对应失抓标签，不是通用失败概率。',ha='center',fontsize=10)
    fig.suptitle('世界模型候选选择流程 · 明确状态与动作序列两路输入',fontsize=15)
    save(fig,'figure_method_diagram','示意独立确认时的模型选择模块；不包含后续恢复控制。执行只提交一个动作，想象中的重复动作不会一次全部执行。')

if __name__=='__main__':
    rate_plot();rate_plot(True);pairs();steps();training();regret();method()
    print('Saved eight figure groups in',OUT)
