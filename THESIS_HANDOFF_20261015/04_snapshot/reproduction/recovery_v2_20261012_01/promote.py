"""Enforce the predeclared gate before freezing or creating any fresh test start."""
import datetime,json
from setup_study import ROOT,RUN,digest,write

def main():
    s=json.loads((RUN/'analysis_dev_a/summary.json').read_text());plan=json.loads((RUN/'study_plan.json').read_text());gate=plan['promotion_gate'];rows=s['comparisons']
    count=lambda method,noise:sum(r['v2_successes'] for r in rows if r['method']==method and r['noise']==noise)
    tests={'total':s['v2_successes']>=gate['minimum_new_successes'],
        'bc_clean':count('bc_k2',0.)>=gate['bc_clean_minimum'],'bc_noise':count('bc_k2',.05)>=gate['bc_noise_minimum'],
        'full_clean':count('full',0.)>=gate['full_clean_minimum'],'full_noise':count('full',.05)>=gate['full_noise_minimum'],
        'paired_regressions':s['regressions_vs_v1']<=gate['maximum_paired_v1_regressions'],
        'per_job_regressions':max(r['regressed_vs_v1'] for r in rows)<=gate['maximum_per_job_v1_regressions']}
    passed=all(tests.values());write(RUN/'promotion.json',{'passed':passed,'checks':tests,'v2_successes':s['v2_successes'],'v1_successes':s['v1_successes'],
        'rescues':s['rescues_vs_v1'],'regressions':s['regressions_vs_v1'],'predeclared_plan_sha256':digest(RUN/'study_plan.json')})
    assert passed,tests
    sources=json.loads((RUN/'dev_a/started.json').read_text())['sha256']
    for name,sha in sources.items():assert digest(ROOT/name)==sha,name
    design={'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'n':60,
            'initialization_seeds':list(range(426101201,426101261)),
            'state_names':[f'demo_{3000000+i}' for i in range(60)],'noise_seeds':[3070000+i for i in range(60)],
            'selection':'All registered native reset seeds; no policy-outcome selection or filtering; no tuning after freeze',
            'source_sha256':sources,'promotion_sha256':digest(RUN/'promotion.json')}
    write(RUN/'freeze_before_states.json',design);print(json.dumps({'promoted':True,'successes':s['v2_successes'],'regressions':s['regressions_vs_v1']}))

if __name__=='__main__':main()
