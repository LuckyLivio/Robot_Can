"""Publication-size categorical figures from complete saved outcomes only."""
from pathlib import Path
import argparse,csv,hashlib,json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];OUT=RUN/'figures'
LABELS={'v6':'v6 参考','v13':'v13 父版本','track':'仅跟踪 T','clearance':'仅间隙 C','v14':'组合 v14'}
COLORS={'v6':'#737D89','v13':'#4B5663','track':'#C68A16','clearance':'#009E73','v14':'#0072B2'}
ORDER=['v6','v13','track','clearance','v14'];catalog=[];previous={}
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,
                     'legend.fontsize':8,'pdf.fonttype':42,'svg.fonttype':'path','axes.spines.top':False,'axes.spines.right':False,
                     'axes.titleweight':'medium','axes.titlesize':11,'axes.titlepad':13,'savefig.dpi':600,'figure.facecolor':'white'})
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(fig,name,caption,rows,sources,stage):
    assert rows
    sources=sorted(set(sources));hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
    dimensions=(np.asarray(fig.get_size_inches())*25.4).tolist()
    item={'id':name,'stage':stage,'caption':caption,'width_mm':dimensions[0],'height_mm':dimensions[1],'dpi':600,
          'no_smoothing':True,'categorical_conditions_not_connected':True,'rows':len(rows),'sources':hashes}
    outputs=[OUT/f'{name}.{ext}' for ext in ['png','pdf','svg','csv']]
    if any(p.exists() for p in outputs):
        assert all(p.is_file() for p in outputs),f'Incomplete previous figure: {name}'
        old=previous.get(name);assert old and old['sources']==hashes and old['rows']==len(rows),f'Would replace changed historical figure: {name}'
        assert all(sha(OUT/f'{name}.{ext}')==digest for ext,digest in old['outputs_sha256'].items())
        plt.close(fig);catalog.append(old);return
    for ext in ['png','pdf','svg']:fig.savefig(OUT/f'{name}.{ext}',dpi=600,facecolor='white')
    plt.close(fig)
    with (OUT/f'{name}.csv').open('x',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    item['outputs_sha256']={ext:sha(OUT/f'{name}.{ext}') for ext in ['png','pdf','svg','csv']};catalog.append(item)
def basic_bar(stage,data,sources,caption):
    versions=[v for v in ORDER if v in data];fig,ax=plt.subplots(figsize=(7.1,3.35),layout='constrained');rows=[]
    for i,v in enumerate(versions):
        s=data[v];n=s['episodes'];success=s['success'];rate=100*success/n
        ax.barh(i,rate,color=COLORS[v],height=.56,zorder=2)
        inside=rate>=85;x=rate-1.5 if inside else rate+1.5
        ax.text(x,i,f'{success}/{n}  ({rate:.1f}%)',ha='right' if inside else 'left',va='center',color='white' if inside else '#202C36',fontsize=9)
        rows.append({'stage':stage,'version':v,'success':success,'executions':n,'success_percent':rate})
    title={'smoke':'已知小测试','pilot':'已知条件消融','dev':'开发对照'}.get(stage.split('_')[0],stage)
    ax.set(xlim=(0,100),yticks=range(len(versions)),yticklabels=[LABELS[v] for v in versions],xlabel='成功率（%）',title=f'{title} · {stage} · 各版本 {data[versions[0]]["episodes"]} 次执行')
    ax.invert_yaxis();ax.grid(axis='x',alpha=.18,zorder=0);ax.set_axisbelow(True)
    save(fig,'V14_'+stage+'_outcomes',caption,rows,sources,stage)
def development(stage,d,p):
    jobs=read(RUN/stage/'jobs.json');totals={v:{'success':0,'episodes':0} for v in ['v6','v13','v14']};per=[];sources=[p,RUN/stage/'jobs.json']
    for j in jobs:
        assert j['version']=='v14'
        suffix=j['id'].split('_',1)[1]
        for v in ['v6','v13','v14']:
            path=RUN/stage/j['id']/'result.json' if v=='v14' else ROOT/j['baseline_result_'+v]
            raw=read(path);assert raw['status']=='complete';sources.append(path)
            records={r['demo']:r for r in raw['records']};rr=[records[n] for n in j['demos']]
            n=len(rr);success=sum(r['success'] for r in rr);totals[v]['success']+=success;totals[v]['episodes']+=n
            per.append({'condition':suffix,'version':v,'success':success,'executions':n,'success_percent':100*success/n})
    assert totals['v14']['success']==d['variants']['v14']['success'] and totals['v14']['episodes']==240
    basic_bar(stage,totals,sources,'开发数据：30 个共同起点 × 八个固定条件，共 240 次/版本。v6、v13 为历史同起点同噪声参照，v14 为本轮执行；开发只用于筛选，不是独立确认。')
    condition_plot(stage,per,sources,'开发对照 · 同起点、同噪声、八个固定条件','30 个开发起点在八条件下重复使用；条件是类别，不相连为趋势线。显示每条件成功数与成功率，无独立泛化区间。')
def condition_plot(stage,rows,sources,title,caption):
    conditions=list(dict.fromkeys(r['condition'] for r in rows));versions=[v for v in ['v6','v13','v14'] if any(r['version']==v for r in rows)]
    fig,(ax,countax)=plt.subplots(1,2,figsize=(7.1,4.5),layout='constrained',gridspec_kw={'width_ratios':[4.2,1.7]},sharey=True)
    offsets=np.linspace(-.19,.19,len(versions));markers=['s','^','o']
    for ci,c in enumerate(conditions):
        parts=[]
        for k,(v,delta) in enumerate(zip(versions,offsets)):
            r=next(r for r in rows if r['condition']==c and r['version']==v)
            ax.scatter(r['success_percent'],ci+delta,c=COLORS[v],marker=markers[k],s=22,label=LABELS[v] if ci==0 else None,zorder=3,clip_on=False)
            parts.append(f'{r["success"]}/{r["executions"]}')
        countax.text(.02,ci,' · '.join(parts),ha='left',va='center',fontsize=8)
    labels=[c.replace('bc_k2','BC k=2').replace('full_s','Full s').replace('_clean',' / 干净').replace('_noise005',' / 噪声0.05') for c in conditions]
    ax.set(yticks=range(len(conditions)),yticklabels=labels,xlim=(0,100),xlabel='成功率（%）',ylim=(len(conditions)-.6,-.6))
    ax.grid(axis='x',alpha=.18);ax.legend(frameon=False,loc='lower left',fontsize=8);countax.set_xlim(0,1);countax.axis('off')
    countax.set_title(' / '.join(versions)+'\n成功数 / 执行数',fontsize=8,pad=10);fig.suptitle(title,fontsize=11)
    save(fig,'V14_'+stage+'_conditions',caption,rows,sources,stage)
def confirmation(stage,d,p):
    fig,(absolute,effects)=plt.subplots(1,2,figsize=(7.1,3.45),layout='constrained',gridspec_kw={'width_ratios':[1,1.25]});rows=[]
    for i,v in enumerate(['v6','v13','v14']):
        s=d['statistics'][v];mean=s['estimate_percent'];lo,hi=s['ci95_percent']
        absolute.errorbar(mean,i,xerr=[[max(0,mean-lo)],[max(0,hi-mean)]],fmt='o',color=COLORS[v],capsize=3)
        rows.append({'quantity':v,'estimate_percent_or_pp':mean,'ci_low':lo,'ci_high':hi,'unit':'percent','independent_starts':60})
    absolute.set(yticks=range(3),yticklabels=['v6','v13','v14'],xlim=(0,100),ylim=(2.45,-.65),xlabel='成功率（%）',title='各版本 480 次执行')
    endpoints=[]
    for i,ref in enumerate(['v6','v13']):
        s=d['statistics']['v14_minus_'+ref];mean=s['estimate_percent'];lo,hi=s['ci95_percent'];endpoints.extend([lo,hi,0])
        effects.errorbar(mean,i,xerr=[[max(0,mean-lo)],[max(0,hi-mean)]],fmt='o',color=COLORS['v14'] if i==0 else COLORS['clearance'],capsize=3)
        effects.text(mean,i+.19,f'{mean:+.2f} [{lo:.2f}, {hi:.2f}]',ha='center',va='top',fontsize=8)
        rows.append({'quantity':'v14_minus_'+ref,'estimate_percent_or_pp':mean,'ci_low':lo,'ci_high':hi,'unit':'percentage_point','independent_starts':60})
    spread=max(max(endpoints)-min(endpoints),2);effects.set(xlim=(min(endpoints)-.35*spread,max(endpoints)+.35*spread),yticks=range(2),yticklabels=['v14 − v6','v14 − v13'],ylim=(1.6,-.6),xlabel='配对成功率差（百分点）',title='主要 / 次要配对效果')
    effects.axvline(0,c='#67727d',lw=.9,ls='--');absolute.grid(axis='x',alpha=.18);effects.grid(axis='x',alpha=.18)
    fig.suptitle('独立确认 · 60 个全新起点 · 95% 配对起点 bootstrap 区间',fontsize=10)
    caption='每个起点的八个固定条件一起重采样，60 个独立起点、20000 次 bootstrap；各版本 480 次执行不是 480 个独立起点。主比较 v14−v6，次比较 v14−v13；95% 百分位区间未做多重比较校正。采用门槛与正区间提升主张分开判断。'
    save(fig,'V14_confirmation_effects',caption,rows,[p],stage)
    per=[{'condition':r['condition'],'version':v,'success':r[v+'_success'],'executions':r['episodes'],'success_percent':100*r[v+'_success']/r['episodes']} for r in d['conditions'] for v in ['v6','v13','v14']]
    condition_plot(stage,per,[p],'独立确认 · 八条件逐项对照','同一批 60 个全新起点下的八个固定条件。散点仅用于分项描述，不将类别连线，不把条件当作独立重训练。右列按 v6 / v13 / v14 顺序列出原始计数。')
def main():
    global previous
    parser=argparse.ArgumentParser();parser.add_argument('--stage',help='Optional single complete stage; existing figures are retained');args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    previous={r['id']:r for r in read(OUT/'CATALOG.json')} if (OUT/'CATALOG.json').exists() else {}
    paths=[]
    for p in (RUN/'analysis').glob('*.json'):
        if not re.fullmatch(r'(?:smoke|pilot|dev)_[a-z0-9]+|confirmation',p.stem):continue
        if args.stage and p.stem!=args.stage:continue
        d=read(p)
        if 'variants' not in d or not (RUN/p.stem/'completed.json').exists():continue
        paths.append(p)
    if args.stage:assert paths, 'Requested stage has no complete outcome analysis'
    for p in sorted(paths):
        stage=p.stem;d=read(p);assert d['stage']==stage
        if stage=='confirmation':confirmation(stage,d,p)
        elif stage.startswith('dev_'):development(stage,d,p)
        else:
            n=d['variants']['v14']['episodes'];purpose='小测试' if stage.startswith('smoke_') else '消融'
            caption=f'{stage}：{purpose}已知条件，每组 {n} 次执行。v13 为父版本，T 为路径跟踪组件，C 为下降间隙组件，v14 为 T+C。起点与策略/噪声可能重复关联；这是描述统计，不给独立推断区间。负结果与失败修订保留，不合并不同阶段分母。'
            basic_bar(stage,d['variants'],[p],caption)
    merged={**previous,**{r['id']:r for r in catalog}}
    (OUT/'CATALOG.json').write_text(json.dumps([merged[k] for k in sorted(merged)],ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'figures_this_call':len(catalog),'figures_total':len(merged),'stages':[p.stem for p in paths]},ensure_ascii=False))
if __name__=='__main__':main()
