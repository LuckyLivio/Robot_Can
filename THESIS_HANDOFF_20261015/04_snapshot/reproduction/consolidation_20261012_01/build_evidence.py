"""Integrate existing records only. No policy/model/environment imports or runs."""
import collections,datetime,hashlib,json,os,re
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):
 with p.open('x',encoding='utf8') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stage(path):
 jobs=read(path/'jobs.json');results=[]
 for j in jobs:
  r=read(path/j['id']/'result.json');assert r['status']=='complete' and [x['demo'] for x in r['records']]==j['demos']
  assert all(x['steps']<=400 and (x['success'] or x['steps']==400) for x in r['records'])
  results.append((j,r['records']))
 return results
def factorial(name,enabled):
 src=ROOT/'reproduction'/name/'confirmation';runs=stage(src);data={}
 for j,r in runs:data[j['version'],j['method'],j['seed'],j['noise']]=r
 ids=[r['demo'] for r in data['disabled','bc_k2',None,0.]];n=len(ids);assert n==60
 def outcome(v,m,s,noise):
  rows=data[v,m,s,noise];assert [r['demo'] for r in rows]==ids
  return np.array([r['success'] for r in rows],float)
 cells=[];effects={};rng=np.random.default_rng(2026101207)
 for noise,label in [(0.,'clean'),(.05,'noise005')]:
  values={}
  for v in ['disabled',enabled]:
   bc=outcome(v,'bc_k2',None,noise);full=np.stack([outcome(v,'full',s,noise) for s in [17,23,41]]).mean(0)
   values[v+'_bc']=bc;values[v+'_full']=full
   cells.extend([{'recovery':v,'method':'BC k=2','noise':noise,'successes':int(bc.sum()),'executions':n,'rate':float(bc.mean()),'starts':n},
                 {'recovery':v,'method':'Full (three-seed mean)','noise':noise,'successes':int(sum(outcome(v,'full',s,noise).sum() for s in [17,23,41])),
                  'executions':3*n,'rate':float(full.mean()),'starts':n}])
  diffs={'world_model_without_recovery':values['disabled_full']-values['disabled_bc'],
   'world_model_with_recovery':values[enabled+'_full']-values[enabled+'_bc'],
   'recovery_for_bc':values[enabled+'_bc']-values['disabled_bc'],
   'recovery_for_full':values[enabled+'_full']-values['disabled_full']}
  diffs['interaction']=diffs['world_model_with_recovery']-diffs['world_model_without_recovery']
  idx=rng.integers(0,n,(20000,n))
  effects[label]={k:{'estimate':float(a.mean()),'ci95':np.quantile(a[idx].mean(1),[.025,.975]).tolist()} for k,a in diffs.items()}
 return {'source':src.relative_to(ROOT).as_posix(),'enabled_version':enabled,'unique_starts':n,'cells':cells,'effects':effects,
  'analysis_status':'New descriptive analysis of previously observed confirmation data. Not a new experiment or independent confirmation.',
  'statistics':'20000 paired-start percentile bootstrap draws, seed2026101207; Full averages three fixed seeds within each start. Pointwise intervals, no multiplicity adjustment or retraining uncertainty.'}
def trace(folder,demo):
 payload=read(folder/'result.json');record=next(r for r in payload['records'] if r['demo']==demo);rows=[]
 for line in (folder/'trace.jsonl').open(encoding='utf8'):
  r=json.loads(line)
  if r['demo']==demo:
   x=r['state_after'];rows.append({'step':r['step'],'eef':x[:3],'object':x[16:19],'phase':r['recovery']['mode'],
       'hold_observed':r['recovery']['stable_hold'],'gap':abs(x[7]-x[8])})
 assert len(rows)==record['steps']
 return {'job':payload['job']['id'],'success':record['success'],'steps':record['steps'],'events':record['events'],'samples':rows,
         'source':(folder/'trace.jsonl').relative_to(ROOT).as_posix(),'trace_sha256':digest(folder/'trace.jsonl')}
def main():
 core=[];root=ROOT/'reproduction/confirmation_20261012_01'
 for j in read(root/'jobs.json'):
  d=read(ROOT/j['outputs'][0]);assert d['status']=='complete' and len(d['records'])==60
  core.append({'method':j['method'],'seed':j['seed'],'noise':j['noise'],'successes':sum(r['success'] for r in d['records']),'episodes':60})
 latest=ROOT/'reproduction/recovery_v5_20261012_01';groups={};matrix={}
 for j,rows in stage(latest/'confirmation'):
  v=j['version'];g=groups.setdefault(v,{'successes':0,'episodes':0});g['successes']+=sum(r['success'] for r in rows);g['episodes']+=len(rows)
  m=matrix.setdefault(v,{'bc_clean':0,'bc_noise':0,'full_clean':0,'full_noise':0})
  m[('bc' if j['method']=='bc_k2' else 'full')+('_clean' if not j['noise'] else '_noise')]+=sum(r['success'] for r in rows)
 factorials=[factorial('recovery_v2_20261012_01','v2'),factorial('recovery_v3_20261012_01','v2'),factorial('recovery_v3_20261012_01','v3')]
 save(RUN/'factorial_analysis.json',factorials)
 cases=[]
 for kind,title,folder1,folder2,demo in [
  ('timing','时间安排：留出释放与退出的预算','confirmation/v4_bc_k2_clean','confirmation/v5_bc_k2_clean','demo_10000029'),
  ('side','侧倒间隙：一个成功救回的新起点','confirmation/v4_full_s41_clean','confirmation/v5_full_s41_clean','demo_10000012'),
  ('loss','失败边界：抓起后失抓仍未恢复','geometry_confirmation/v4_geometry','geometry_confirmation/v5_geometry','demo_11000013')]:
  cases.append({'kind':kind,'title':title,'demo':demo,'series':[{'label':'v4',**trace(latest/folder1,demo)},{'label':'v5',**trace(latest/folder2,demo)}]})
 (RUN/'demo').mkdir(exist_ok=False)
 old=ROOT/'reproduction/review_20261012_01/demo'
 raw=(old/'data.js').read_text(encoding='utf8').strip();demo= json.loads(raw.removeprefix('const DEMO_DATA = ').removesuffix(';'))
 for c in demo['cases']:
  for k in ['video','poster','firstFrame']:
   if c.get(k):c[k]=os.path.relpath((old/c[k]).resolve(),RUN/'demo').replace('\\','/')
 (RUN/'demo/data.js').write_text('const DEMO_DATA = '+json.dumps(demo,ensure_ascii=False,indent=2)+';\n',encoding='utf8')
 for n in ['app.js','styles.css']:(RUN/'demo'/n).write_bytes((old/n).read_bytes())
 evidence={'built_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'core':core,'v5_totals':groups,'v5_matrix':matrix,
  'v5_effect':read(latest/'analysis_confirmation/summary.json')['statistics']['overall_execution_mix']['v5_minus_v4'],
  'geometry':read(latest/'analysis_geometry_confirmation/summary.json')['totals'],
  'v5_failure_summary':{k:v for k,v in read(latest/'posthoc_failure_review.json').items() if k in ['v5_failure_executions','v5_failure_distinct_starts','v5_failure_categories','common_failed_executions_all_five']},
  'factorial':factorials,'trajectory_cases':cases,'display_scope':'All new trajectory visuals read existing logs. No new robot simulation/video/policy run. Cases selected after outcomes; illustrative only.'}
 save(RUN/'evidence.json',evidence)
 (RUN/'demo/evidence.js').write_text('const EVIDENCE = '+json.dumps(evidence,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf8')
 text=['# 有无世界模型与有无恢复：已有同起点证据复核','',
  '本页是对 v2/v3 已有确认结果的新描述性分析，没有新策略回合。它修正了“整个项目缺少四组对照”的笼统说法：旧轮次已具备；最新 v5 的 60 个新起点没有关闭恢复的对应组。不能把旧轮次拼接成 v5 同起点对照。','']
 for f in factorials:
  text.extend(['## '+f['source']+' / '+f['enabled_version'],'','| 恢复 | 方法 | 条件 | 成功执行 | 成功率 |','|---|---|---|---:|---:|'])
  for c in f['cells']:text.append(f"| {c['recovery']} | {c['method']} | {'干净' if not c['noise'] else '噪声0.05'} | {c['successes']}/{c['executions']} | {100*c['rate']:.2f}% |")
  text.extend(['','| 配对差值 | 干净：百分点 [95%区间] | 噪声：百分点 [95%区间] |','|---|---|---|'])
  names={'world_model_without_recovery':'Full−BC，无恢复','world_model_with_recovery':'Full−BC，有恢复','recovery_for_bc':'恢复−关闭恢复，BC','recovery_for_full':'恢复−关闭恢复，Full','interaction':'交互：恢复对Full的增益−恢复对BC的增益'}
  for k,label in names.items():
   vals=[]
   for n in ['clean','noise005']:
    r=f['effects'][n][k];vals.append(f"{r['estimate']*100:+.2f} [{r['ci95'][0]*100:+.2f}, {r['ci95'][1]*100:+.2f}]")
   text.append('| '+label+' | '+' | '.join(vals)+' |')
  text.extend(['','每个条件共60个配对起点。Full三种子先在起点内平均；20,000次起点bootstrap，随机种子2026101207。区间逐项、未校正多重比较，不包含重新训练的不确定性。',''])
 text.extend(['## 如何使用这些结果','','恢复层同时帮助BC和Full；当前数据不支持把所有恢复收益归为世界模型贡献。交互项描述两者改善幅度的差别，不是普遍因果或安全保证。上述轮次分别使用不同的60个起点，不能按成功率挑最好轮次。','',
  '如果后续只做交付整理，已有四组对照足以支持这项有边界的分析。只有需要专门评价最终v5的交互作用时，才另立同起点四组实验；当前这批v5起点已查看，复用只能称补充分析。'])
 (RUN/'FACTORIAL_REVIEW.md').write_text('\n'.join(text)+'\n',encoding='utf8')
 print(json.dumps({'core_jobs':len(core),'v5_totals':groups,'factorial_analyses':len(factorials),'illustrative_trace_cases':len(cases),'new_policy_episodes':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
