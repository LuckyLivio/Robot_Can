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
    stage=RUN/a.stage;jobs=json.loads((stage/'jobs.json').read_text());versions=list(dict.fromkeys(j['version'] for j in jobs))
    dev=a.stage.startswith('dev');ref=rows(ROOT/('reproduction/improvement_v6_20261015_01/dev_a' if dev else 'reproduction/improvement_v9_20261015_01/pilot_b'),'v6')
    old=rows(ROOT/'reproduction/improvement_v11_20261015_01'/('dev_a' if dev else 'pilot_a'),'v11')
    allrows={v:rows(stage,v) for v in versions};table=[];summary={}
    for v,rs in allrows.items():
        rescued=[];regressed=[];old_regressed=[];fails=[]
        for k,r in rs.items():
            b=ref.get(k);o=old.get(k)
            if b and b['success'] and not r['success']:regressed.append(k)
            if b and not b['success'] and r['success']:rescued.append(k)
            if o and o['success'] and not r['success']:old_regressed.append(k)
            if not r['success']:fails.append(k)
            table.append({'variant':v,'condition':k[0],'demo':k[1],'success':r['success'],'steps':r['steps'],
                          'v6_success':b['success'] if b else '', 'v11_success':o['success'] if o else '',
                          'wait_transfers':sum(e.get('evidence') is not None for e in r.get('wait_hold_events',[]))})
        summary[v]={'success':sum(r['success'] for r in rs.values()),'episodes':len(rs),
                    'rescued_vs_v6':rescued,'regressed_vs_v6':regressed,'regressed_vs_v11':old_regressed,'failures':fails,
                    'wait_transfers':sum(t['wait_transfers'] for t in table if t['variant']==v)}
    gate=None
    if 'v12' in allrows:
        rs=allrows['v12'];s=summary['v12']
        if dev:gate=len(rs)==240 and s['success']>=236 and not s['regressed_vs_v6']
        elif a.stage.startswith('pilot'):
            core={k:r for k,r in rs.items() if k[0]!='held_wait_demo87'}
            gate=len(core)==37 and sum(r['success'] for r in core.values())>=31 and not s['regressed_vs_v6'] and not s['regressed_vs_v11'] and rs[('held_wait_demo87','demo_87')]['success']
    out={'stage':a.stage,'variants':summary,'outcome_gate_passed':gate,'note':'Known/development cases, not independent confirmation. Validation gates recorded separately.'}
    if a.save:
        with (RUN/'analysis'/f'{a.stage}.json').open('x') as f:json.dump(out,f,indent=2)
        with (RUN/'analysis'/f'{a.stage}_pairs.csv').open('x',newline='') as f:
            w=csv.DictWriter(f,fieldnames=table[0]);w.writeheader();w.writerows(table)
    print(json.dumps(out,indent=2))
