"""Paired frozen-development comparison; no tuning or test-set selection."""
from pathlib import Path
import argparse,csv,json,hashlib
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--save',action='store_true');a=p.parse_args()
    jobs=json.loads((RUN/'dev_a/jobs.json').read_text());groups=[];rows=[];failures=[];incomplete=[]
    for j in jobs:
        new=RUN/'dev_a'/j['id']/'result.json';old=ROOT/'reproduction/recovery_v5_20261012_01/dev_a'/('v5'+j['id'][2:])/'result.json'
        if not new.exists():incomplete.append(j['id']);continue
        try:d=json.loads(new.read_text())
        except json.JSONDecodeError:incomplete.append(j['id']);continue
        if d['status']!='complete':incomplete.append(j['id'])
        base={r['demo']:r for r in json.loads(old.read_text())['records']};paired=[]
        for r in d['records']:
            b=base[r['demo']]
            row={'job':j['id'],'method':j['method'],'seed':j['seed'],'noise':j['noise'],'demo':r['demo'],
                 'v5_success':b['success'],'v6_success':r['success'],'v5_steps':b['steps'],'v6_steps':r['steps'],
                 'v5_attempts':b['attempts'],'v6_attempts':r['attempts'],
                 'v5_failed_attempts':b['failed_attempts'],'v6_failed_attempts':r['failed_attempts'],
                 'v5_source':str(old.relative_to(ROOT)),'v6_source':str(new.relative_to(ROOT))}
            rows.append(row);paired.append(row)
            if not r['success']:
                failures.append({'job':j['id'],'demo':r['demo'],'baseline_success':b['success'],
                    'events':r['events'],'guard_events':r.get('guard_events',[]),'phases':r['phases']})
        groups.append({'job':j['id'],'n':len(paired),'v5':sum(r['v5_success'] for r in paired),
                       'v6':sum(r['v6_success'] for r in paired),
                       'rescues':sum(not r['v5_success'] and r['v6_success'] for r in paired),
                       'regressions':sum(r['v5_success'] and not r['v6_success'] for r in paired)})
    rescue=[r for r in rows if not r['v5_success'] and r['v6_success']];reg=[r for r in rows if r['v5_success'] and not r['v6_success']]
    v5=sum(r['v5_success'] for r in rows);v6=sum(r['v6_success'] for r in rows)
    gate=json.loads((RUN/'protocols/study_plan.json').read_text())['dev_gate']
    distinct=sorted(set(r['demo'] for r in rescue));complete=not incomplete
    passed=(complete and len(rows)==gate['episodes'] and v6-v5>=gate['net_success_vs_v5_min'] and
            len(distinct)>=gate['distinct_rescued_starts_min'] and len(reg)<=gate['new_regressions_max'])
    result={'complete':complete,'episodes':len(rows),'unique_starts':len(set(r['demo'] for r in rows)),
            'v5_successes':v5,'v6_successes':v6,'net_success_change':v6-v5,'rescues':rescue,'regressions':reg,
            'distinct_rescued_starts':distinct,'groups':groups,'dev_gate_passed':passed,'gate':gate,
            'mean_steps_all_v5':sum(r['v5_steps'] for r in rows)/max(1,len(rows)),
            'mean_steps_all_v6':sum(r['v6_steps'] for r in rows)/max(1,len(rows)),
            'failures':failures,'note':'30 known starts x 4 policy/model settings x 2 noise conditions, not 240 independent starts.'}
    if a.save:
        assert complete and (RUN/'dev_a/completed.json').exists()
        lock=json.loads((RUN/'protocols/dev_lock.json').read_text())
        assert all(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h for rel,h in lock['sha256'].items())
        result['frozen_inputs_unchanged']=True
        with (RUN/'analysis/dev_comparison.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
        with (RUN/'analysis/dev_pairs.csv').open('x',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({k:v for k,v in result.items() if k not in ['failures','rescues','regressions']},indent=2))
    print('incomplete',incomplete)
if __name__=='__main__':main()
