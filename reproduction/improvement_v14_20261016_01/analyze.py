"""Paired known-condition gates against actual parent rerun and saved references."""
from pathlib import Path
import argparse,csv,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
TARGETS={('known13_bc_k2_noise005_demo_13000021','demo_13000021'),
         ('known13_full_s41_noise005_demo_13000022','demo_13000022')}
def read(p):return json.loads(p.read_text(encoding='utf8'))
def rows(folder,prefix):
    out={}
    for j in read(folder/'jobs.json'):
        if j['version']!=prefix:continue
        d=read(folder/j['id']/'result.json');assert d['status']=='complete' and d['job']==j
        assert [r['demo'] for r in d['records']]==j['demos']
        for r in d['records']:
            key=(j['id'].split('_',1)[1],r['demo']);assert key not in out
            out[key]=r
    return out
def references(jobs,version):
    out={};cache={}
    for j in jobs:
        p=j.get('baseline_result_'+version)
        if not p:continue
        if p not in cache:
            d=read(ROOT/p);assert d['status']=='complete'
            cache[p]={r['demo']:r for r in d['records']}
        for n in j['demos']:
            key=(j['id'].split('_',1)[1],n)
            if key in out:assert out[key]==cache[p][n]
            out[key]=cache[p][n]
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--save',action='store_true');a=p.parse_args()
    stage=RUN/a.stage;assert read(stage/'completed.json')['source_unchanged']
    jobs=read(stage/'jobs.json');versions=list(dict.fromkeys(j['version'] for j in jobs));dev=a.stage.startswith('dev')
    reference6=references(jobs,'v6');reference13=references(jobs,'v13')
    rerun=rows(stage,'v13') if 'v13' in versions else {}
    parent_replay_consistent=all(r['success']==reference13[k]['success'] and r['steps']==reference13[k]['steps'] for k,r in rerun.items())
    assert parent_replay_consistent,'Parent rerun differs from its saved reference'
    reference13.update(rerun)
    table=[];summary={}
    expected_keys=None
    for v in versions:
        rs=rows(stage,v)
        if expected_keys is None:expected_keys=set(rs)
        else:assert set(rs)==expected_keys, 'Unequal paired case sets'
        s={'success':sum(r['success'] for r in rs.values()),'episodes':len(rs),'regressed_vs_v6':[],
           'regressed_vs_v13':[],'rescued_vs_v13':[],'target_rescues':[],'failures':[],
           'paired_reference_v6':sum(k in reference6 for k in rs),'paired_reference_v13':sum(k in reference13 for k in rs)}
        for key,r in rs.items():
            b=reference6.get(key);o=reference13.get(key)
            if b and b['success'] and not r['success']:s['regressed_vs_v6'].append(key)
            if o and o['success'] and not r['success']:s['regressed_vs_v13'].append(key)
            if o and not o['success'] and r['success']:s['rescued_vs_v13'].append(key)
            if key in TARGETS and o and not o['success'] and r['success']:s['target_rescues'].append(key)
            if not r['success']:s['failures'].append(key)
            table.append({'version':v,'condition':key[0],'demo':key[1],'success':r['success'],'steps':r['steps'],
                          'v6_success':b['success'] if b else '', 'v13_success':o['success'] if o else '',
                          'tracking_events':len(r.get('tracking14_events',[])),'clearance_events':len(r.get('clearance14_events',[]))})
        summary[v]=s
    s=summary['v14'];gate=None
    no_regression=not s['regressed_vs_v6'] and not s['regressed_vs_v13']
    targets_rescued={tuple(k) for k in s['target_rescues']}==TARGETS
    if dev:gate=s['episodes']==240 and s['success']>=236 and no_regression and s['paired_reference_v13']==240 and s['paired_reference_v6']==240
    elif a.stage.startswith('pilot'):gate=s['episodes']==93 and no_regression and targets_rescued
    elif a.stage.startswith('smoke'):gate=s['episodes']==8 and no_regression and targets_rescued
    out={'stage':a.stage,'variants':summary,'outcome_gate_passed':gate,'parent_rerun_consistent':parent_replay_consistent,
         'both_targets_rescued':targets_rescued if not dev else None,
         'note':'Known diagnostic/development conditions; not independent confirmation. Verification gates are separate.'}
    if a.save:
        with (RUN/'analysis'/f'{a.stage}.json').open('x',encoding='utf8') as f:json.dump(out,f,indent=2)
        with (RUN/'analysis'/f'{a.stage}_pairs.csv').open('x',newline='',encoding='utf8') as f:w=csv.DictWriter(f,fieldnames=table[0]);w.writeheader();w.writerows(table)
    print(json.dumps(out,indent=2))
