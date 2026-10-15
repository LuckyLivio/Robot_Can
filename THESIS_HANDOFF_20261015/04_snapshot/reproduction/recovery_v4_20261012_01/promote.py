"""Apply the prospective gate to all three candidates; never select on confirmation."""
import json,datetime,argparse
from setup_study import ROOT,RUN,write,digest
def main(stage):
    s=json.loads((RUN/f'analysis_{stage}/summary.json').read_text());plan=json.loads((RUN/'study_plan.json').read_text());g=plan['dev_gate']
    assert json.loads((RUN/f'validation_{stage}.json').read_text())['passed']
    candidates={}
    for v in ['align_only','region_only','v4']:
        total=s['totals'][v];rows=[r for r in s['comparisons'] if r['version']==v]
        count=lambda m,n:sum(r['successes'] for r in rows if r['method']==m and r['noise']==n)
        checks={'total':total['successes']>=g['min_success'],'regressions':total['regressions_vs_v2']<=g['max_regressions'],
            'bc_clean':count('bc_k2',0.)>=g['min_bc_clean'],'bc_noise':count('bc_k2',.05)>=g['min_bc_noise'],
            'full_clean':count('full',0.)>=g['min_full_clean'],'full_noise':count('full',.05)>=g['min_full_noise']}
        candidates[v]={'passed':all(checks.values()),'checks':checks,**total}
    passing=[v for v,c in candidates.items() if c['passed']]
    selected=min(passing,key=lambda v:(-candidates[v]['successes'],candidates[v]['regressions_vs_v2'],2 if v=='v4' else 1,0 if v=='align_only' else 1)) if passing else None
    receipt={'passed':bool(passing),'selected_variant':selected,'stage':stage,'candidates':candidates,'study_plan_sha256':digest(RUN/'study_plan.json')}
    write(RUN/f'promotion_{stage}.json',receipt);print(json.dumps(receipt,indent=2),flush=True)
    if not passing:return
    write(RUN/'promotion.json',receipt)
    sources=json.loads((RUN/stage/'started.json').read_text())['sha256']
    for name,sha in sources.items():assert digest(ROOT/name)==sha,name
    for p in [*RUN.glob('*.py'),RUN/'study_plan.json',RUN/'DEVELOPMENT_NOTES.md']:sources[p.relative_to(ROOT).as_posix()]=digest(p)
    c=plan['confirmation_if_pass']
    write(RUN/'freeze_before_states.json',{'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'selected_variant':selected,'initialization_seeds':c['native_seeds'],'state_names':[f'demo_{i}' for i in c['demo_ids']],
        'noise_seeds':[70000+i for i in c['demo_ids']],'source_sha256':sources,'promotion_sha256':digest(RUN/'promotion.json'),
        'selection':'All registered starts retained; no outcomes used for selection; all four variants frozen before state generation.'})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();main(a.stage)
