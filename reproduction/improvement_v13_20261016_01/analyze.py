from pathlib import Path
import argparse,csv,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def rows(folder,prefix):
    out={}
    for p in folder.glob(prefix+'_*/result.json'):
        d=json.loads(p.read_text());assert d['status']=='complete'
        for r in d['records']:out[(d['job']['id'].split('_',1)[1],r['demo'])]=r
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--save',action='store_true');a=p.parse_args()
    stage=RUN/a.stage;jobs=json.loads((stage/'jobs.json').read_text());versions=list(dict.fromkeys(j['version'] for j in jobs));dev=a.stage.startswith('dev')
    reference6=rows(ROOT/('reproduction/improvement_v6_20261015_01/dev_a' if dev else 'reproduction/improvement_v9_20261015_01/pilot_b'),'v6')
    reference12=rows(ROOT/'reproduction/improvement_v12_20261015_01'/('dev_a' if dev else 'pilot_a'),'v12')
    if not dev:
        old=rows(ROOT/'reproduction/improvement_v12_20261015_01/confirmation','v6')
        for j in jobs:
            suffix=j['id'].split('_',1)[1]
            if suffix.startswith('known_') and '_demo_120' in suffix:
                condition=suffix[6:].split('_demo_')[0]
                for demo in j['demos']:reference6[(suffix,demo)]=old[(condition,demo)]
        reference12.update(rows(stage,'v12'))
    table=[];summary={}
    for v in versions:
        rs=rows(stage,v);s={'success':sum(r['success'] for r in rs.values()),'episodes':len(rs),'regressed_vs_v6':[],
                           'regressed_vs_v12':[],'rescued_vs_v12':[],'new_case_rescues':[],'failures':[]}
        for key,r in rs.items():
            b=reference6.get(key);o=reference12.get(key)
            if b and b['success'] and not r['success']:s['regressed_vs_v6'].append(key)
            if o and o['success'] and not r['success']:s['regressed_vs_v12'].append(key)
            if o and not o['success'] and r['success']:
                s['rescued_vs_v12'].append(key)
                if key[1].startswith('demo_120'):s['new_case_rescues'].append(key)
            if not r['success']:s['failures'].append(key)
            table.append({'version':v,'condition':key[0],'demo':key[1],'success':r['success'],'steps':r['steps'],
                          'v6_success':b['success'] if b else '', 'v12_success':o['success'] if o else '',
                          'support_events':len(r.get('support13_events',[])),'escape_events':len(r.get('escape_events',[]))})
        summary[v]=s
    s=summary['v13'];gate=None
    no_regression=not s['regressed_vs_v6'] and not s['regressed_vs_v12']
    if dev:gate=s['episodes']==240 and s['success']>=236 and no_regression
    elif a.stage.startswith('pilot'):gate=s['episodes']==50 and no_regression and bool(s['new_case_rescues'])
    out={'stage':a.stage,'variants':summary,'outcome_gate_passed':gate,'note':'Known diagnostic/development conditions; not independent confirmation. Verification gates are separate.'}
    if a.save:
        with (RUN/'analysis'/f'{a.stage}.json').open('x') as f:json.dump(out,f,indent=2)
        with (RUN/'analysis'/f'{a.stage}_pairs.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=table[0]);w.writeheader();w.writerows(table)
    print(json.dumps(out,indent=2))
