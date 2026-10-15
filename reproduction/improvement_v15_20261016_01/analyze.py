"""Known-condition paired gates; v14 reference is rerun on every new condition."""
from pathlib import Path
import argparse,csv,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
TARGETS={('known13_bc_k2_noise005_demo_13000021','demo_13000021'),
         ('known13_full_s41_noise005_demo_13000022','demo_13000022'),
         ('clearance_profile_6000005','demo_6000005')}
REFERENCES=['v6','v13','v14']
def read(p):return json.loads(p.read_text(encoding='utf8'))
def rows(folder,version):
    out={}
    for j in read(folder/'jobs.json'):
        if j['version']!=version:continue
        d=read(folder/j['id']/'result.json');assert d['status']=='complete' and d['job']==j
        assert [r['demo'] for r in d['records']]==j['demos']
        for r in d['records']:
            key=(j['id'].split('_',1)[1],r['demo']);assert key not in out
            out[key]=r
    return out
def references(jobs,version):
    out={};cache={}
    for j in jobs:
        path=j.get('baseline_result_'+version)
        if not path:continue
        if path not in cache:
            d=read(ROOT/path);assert d['status']=='complete';cache[path]={r['demo']:r for r in d['records']}
        for name in j['demos']:
            key=(j['id'].split('_',1)[1],name)
            if key in out:assert out[key]==cache[path][name]
            out[key]=cache[path][name]
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--save',action='store_true');a=p.parse_args()
    stage=RUN/a.stage;completed=read(stage/'completed.json');assert completed['source_unchanged']
    jobs=read(stage/'jobs.json');versions=list(dict.fromkeys(j['version'] for j in jobs));dev=a.stage.startswith('dev')
    assert 'v14' in versions and 'v15' in versions
    if dev:assert set(versions)=={'v14','v15'}
    else:assert set(versions)=={'v14','carry','edge','budget','v15'}
    refs={v:references(jobs,v) for v in REFERENCES};parent=rows(stage,'v14')
    historical=refs['v14'];consistent=all(r['success']==parent[k]['success'] and r['steps']==parent[k]['steps'] for k,r in historical.items())
    assert consistent,'v14 rerun disagrees with available saved B reference'
    refs['v14']=parent;summary={};table=[];expected=set(parent)
    for version in versions:
        records=rows(stage,version);assert set(records)==expected,'Unequal paired case sets'
        s={'success':sum(r['success'] for r in records.values()),'episodes':len(records),'failures':[],
           'target_rescues':[],'rescued_vs_v14':[]}
        for ref in REFERENCES:s['regressed_vs_'+ref]=[];s['paired_reference_'+ref]=sum(k in refs[ref] for k in records)
        for key,r in records.items():
            originals={v:refs[v].get(key) for v in REFERENCES};original=originals['v14']
            for ref,b in originals.items():
                if b and b['success'] and not r['success']:s['regressed_vs_'+ref].append(key)
            if not original['success'] and r['success']:
                s['rescued_vs_v14'].append(key)
                if key in TARGETS:s['target_rescues'].append(key)
            if not r['success']:s['failures'].append(key)
            table.append({'version':version,'condition':key[0],'demo':key[1],'success':r['success'],'steps':r['steps'],
                          **{v+'_success':b['success'] if b else '' for v,b in originals.items()},
                          'carry_events':len(r.get('carry15_events',[])),'edge15_events':len(r.get('edge15_events',[])),
                          'budget_events':len(r.get('budget15_events',[]))})
        summary[version]=s
    s=summary['v15'];no_regression=all(not s['regressed_vs_'+ref] for ref in REFERENCES)
    all_targets={tuple(k) for k in s['target_rescues']}==TARGETS
    count=sum(t['episodes'] for t in summary.values());assert count==completed['episodes']
    if dev:
        gate=s['episodes']==240 and count==480 and s['success']>=236 and no_regression and all(s['paired_reference_'+v]==240 for v in REFERENCES)
    elif a.stage.startswith('pilot'):gate=s['episodes']==94 and count==470 and no_regression and all_targets and s['paired_reference_v14']==94
    elif a.stage.startswith('smoke'):gate=s['episodes']==9 and count==45 and no_regression and all_targets and s['paired_reference_v14']==9
    else:raise ValueError('Unknown stage')
    out={'stage':a.stage,'variants':summary,'outcome_gate_passed':gate,'evaluated_executions':count,
         'paired_conditions_per_version':len(expected),'parent_reference':'actual v14 rerun on every condition',
         'parent_historical_checks':len(historical),'parent_rerun_consistent_where_available':consistent,
         'all_three_targets_rescued':all_targets if not dev else None,
         'note':'Known diagnostic/development cases; profile variants are not distinct independent starts. Development comprises v14 240 + v15 240 = 480 executions. Verification gates are separate.'}
    if a.save:
        with (RUN/'analysis'/f'{a.stage}.json').open('x',encoding='utf8') as f:json.dump(out,f,indent=2)
        with (RUN/'analysis'/f'{a.stage}_pairs.csv').open('x',newline='',encoding='utf8') as f:w=csv.DictWriter(f,fieldnames=table[0]);w.writeheader();w.writerows(table)
    print(json.dumps(out,indent=2))
