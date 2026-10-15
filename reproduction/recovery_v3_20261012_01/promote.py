"""Do not create fresh test states unless the preregistered dev gate passes."""
import json,datetime,argparse
from setup_study import ROOT,RUN,write,digest
def main(stage):
    s=json.loads((RUN/f'analysis_{stage}/summary.json').read_text());plan=json.loads((RUN/'study_plan.json').read_text());g=plan['dev_gate'];rows=s['comparisons']
    count=lambda method,noise:sum(r['v3_successes'] for r in rows if r['method']==method and r['noise']==noise)
    checks={'total':s['v3_successes']>=g['min_success'],'regressions':s['regressions_vs_v2']<=g['max_regressions'],
      'bc_clean':count('bc_k2',0.)>=g['min_bc_clean'],'bc_noise':count('bc_k2',.05)>=g['min_bc_noise'],
      'full_clean':count('full',0.)>=g['min_full_clean'],'full_noise':count('full',.05)>=g['min_full_noise']}
    passed=all(checks.values());receipt={'passed':passed,'stage':stage,'checks':checks,'v3_successes':s['v3_successes'],
      'v2_successes':s['v2_successes'],'rescues':s['rescues_vs_v2'],'regressions':s['regressions_vs_v2'],'study_plan_sha256':digest(RUN/'study_plan.json')}
    write(RUN/f'promotion_{stage}.json',receipt)
    print(json.dumps({'passed':passed,'checks':checks,'successes':s['v3_successes']}),flush=True)
    if not passed:return
    assert json.loads((RUN/f'validation_{stage}.json').read_text())['passed']
    write(RUN/'promotion.json',receipt)
    sources=json.loads((RUN/stage/'started.json').read_text())['sha256']
    for name,sha in sources.items():assert digest(ROOT/name)==sha,name
    for p in [*RUN.glob('*.py'),RUN/'study_plan.json',RUN/'DEVELOPMENT_NOTES.md']:sources[p.relative_to(ROOT).as_posix()]=digest(p)
    conf=plan['confirmation_if_pass']
    write(RUN/'freeze_before_states.json',{'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'initialization_seeds':conf['native_seeds'],'state_names':[f'demo_{i}' for i in conf['demo_ids']],
      'noise_seeds':[70000+i for i in conf['demo_ids']],'source_sha256':sources,'promotion_sha256':digest(RUN/'promotion.json'),
      'selection':'Every registered seed retained; no policy outcome filtering; no tuning after freeze.'})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();main(a.stage)
