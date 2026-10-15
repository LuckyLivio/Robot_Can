"""Paired outcomes; diagnostics are not independent confirmation evidence."""
from pathlib import Path
import argparse,json
RUN=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--save',action='store_true');a=p.parse_args()
    stage=RUN/a.stage;rows={v:{} for v in ['v9','height','path','v10']};incomplete=[]
    jobs=json.loads((stage/'jobs.json').read_text())
    for j in jobs:
        path=stage/j['id']/'result.json'
        if not path.exists():incomplete.append(j['id']);continue
        try:d=json.loads(path.read_text())
        except json.JSONDecodeError:incomplete.append(j['id']);continue
        if d['status']!='complete':incomplete.append(j['id'])
        for r in d['records']:rows[j['version']][(j['id'].split('_',1)[1],r['demo'])]=r
    baseline={}
    for f in (RUN.parents[1]/'reproduction/improvement_v9_20261015_01/pilot_b').glob('v6_*/result.json'):
        d=json.loads(f.read_text());j=d['job']
        for r in d['records']:baseline[(j['id'].split('_',1)[1],r['demo'])]=r
    summary={}
    for v,rs in rows.items():
        reg=[];rescue=[];fail=[]
        for k,r in rs.items():
            b=baseline.get(k)
            if b and b['success'] and not r['success']:reg.append(k)
            if b and not b['success'] and r['success']:rescue.append(k)
            if not r['success']:fail.append({'case':k,'phases':r['phases'],'events':[(e['step'],e['to'],e['reason']) for e in r['events']], 'guard_events':r.get('guard_events',[])})
        summary[v]={'success':sum(r['success'] for r in rs.values()),'episodes':len(rs),'rescues':rescue,'regressions':reg,'failures':fail}
    report={'stage':a.stage,'complete':not incomplete,'incomplete_jobs':incomplete,'variants':summary}
    if a.save:
        assert not incomplete
        with (RUN/'analysis'/f'{a.stage}.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
    print(json.dumps({v:{k:d[k] for k in ['success','episodes','rescues','regressions']} for v,d in summary.items()},indent=2))
    print('incomplete jobs',len(incomplete))
if __name__=='__main__':main()
