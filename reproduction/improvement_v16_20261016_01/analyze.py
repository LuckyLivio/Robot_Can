"""Paired descriptive outcome gates with actual v14/v15/budget reruns."""
from pathlib import Path
import argparse,csv,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
TARGETS={('known13_bc_k2_noise005_demo_13000021','demo_13000021'),
         ('known13_full_s41_noise005_demo_13000022','demo_13000022'),
         ('clearance_profile_6000005','demo_6000005')}
def read(path):return json.loads(path.read_text(encoding='utf8'))
def rows(folder,version):
    records={}
    for job in read(folder/'jobs.json'):
        if job['version']!=version:continue
        result=read(folder/job['id']/'result.json');assert result['status']=='complete' and result['job']==job
        assert [row['demo'] for row in result['records']]==job['demos']
        for row in result['records']:
            key=(job['id'].split('_',1)[1],row['demo']);assert key not in records
            records[key]=row
    return records
def references(jobs,version):
    records={};cache={}
    for job in jobs:
        path=job.get('baseline_result_'+version)
        if not path:continue
        if path not in cache:
            result=read(ROOT/path);assert result['status']=='complete'
            cache[path]={row['demo']:row for row in result['records']}
        for demo in job['demos']:
            key=(job['id'].split('_',1)[1],demo)
            if key in records:assert records[key]==cache[path][demo]
            records[key]=cache[path][demo]
    return records
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',required=True);parser.add_argument('--save',action='store_true');args=parser.parse_args()
    folder=RUN/args.stage;completed=read(folder/'completed.json');assert completed['source_unchanged']
    jobs=read(folder/'jobs.json');versions=list(dict.fromkeys(job['version'] for job in jobs));development=args.stage.startswith('dev')
    baselines=['v14','v15'] if development else ['v14','v15','budget']
    expected_versions={'v14','v15','v16'} if development else {'v14','v15','budget','ik','held','edge','v16'}
    assert set(versions)==expected_versions
    reference_names=['v6','v13']+baselines
    refs={version:references(jobs,version) for version in reference_names};baseline_checks={}
    for version in baselines:
        actual=rows(folder,version);historical=refs[version]
        consistent=all(row['success']==actual[key]['success'] and row['steps']==actual[key]['steps'] for key,row in historical.items())
        assert consistent,(version,'Actual rerun differs from saved baseline')
        baseline_checks[version]={'available_saved_cases':len(historical),'success_and_steps_equal':consistent}
        refs[version]=actual
    expected=set(refs['v14']);summary={};table=[]
    for version in versions:
        records=rows(folder,version);assert set(records)==expected,'Unequal paired profiles'
        result={'success':sum(row['success'] for row in records.values()),'episodes':len(records),'failures':[],
                'target_rescues':[],'rescued_vs_v14':[]}
        for ref in reference_names:
            result['regressed_vs_'+ref]=[];result['paired_reference_'+ref]=sum(key in refs[ref] for key in records)
        for key,row in records.items():
            original={ref:refs[ref].get(key) for ref in reference_names}
            for ref,before in original.items():
                if before and before['success'] and not row['success']:result['regressed_vs_'+ref].append(key)
            if not original['v14']['success'] and row['success']:
                result['rescued_vs_v14'].append(key)
                if key in TARGETS:result['target_rescues'].append(key)
            if not row['success']:result['failures'].append(key)
            table.append({'version':version,'condition':key[0],'demo':key[1],'success':row['success'],'steps':row['steps'],
                          **{ref+'_success':before['success'] if before else '' for ref,before in original.items()},
                          **{event:len(row.get(event,[])) for event in ['carry15_events','edge15_events','budget15_events','ik16_events','held16_events','edge16_events']}})
        summary[version]=result
    full=summary['v16'];no_regression=all(not full['regressed_vs_'+ref] for ref in reference_names)
    targets={tuple(key) for key in full['target_rescues']}==TARGETS
    executions=sum(result['episodes'] for result in summary.values());assert executions==completed['episodes']
    if development:
        gate=full['episodes']==240 and executions==720 and full['success']>=236 and no_regression and all(full['paired_reference_'+ref]==240 for ref in reference_names)
    elif args.stage.startswith('pilot'):
        gate=full['episodes']==94 and executions==658 and no_regression and targets and all(full['paired_reference_'+ref]==94 for ref in baselines) and full['paired_reference_v13']==94 and full['paired_reference_v6']==93
    elif args.stage.startswith('smoke'):
        gate=full['episodes']==9 and executions==63 and no_regression and targets and all(full['paired_reference_'+ref]==9 for ref in baselines) and full['paired_reference_v13']==9 and full['paired_reference_v6']==8
    else:raise ValueError('Unknown stage')
    output={'stage':args.stage,'variants':summary,'outcome_gate_passed':gate,'evaluated_executions':executions,
            'paired_conditions_per_version':len(expected),'actual_baselines':baselines,'historical_baseline_checks':baseline_checks,
            'all_three_targets_rescued':targets if not development else None,
            'note':'Known profiles, not independent starts. ik/held/edge each repair full v15; budget retains v15 C-only. Development is v14/v15/v16 each 240 = 720 actual runs. Physical and decision gates are separate.'}
    if args.save:
        paths=[RUN/'analysis'/f'{args.stage}.json',RUN/'analysis'/f'{args.stage}_pairs.csv']
        assert all(not path.exists() for path in paths)
        with paths[0].open('x',encoding='utf8') as stream:json.dump(output,stream,indent=2)
        with paths[1].open('x',newline='',encoding='utf8') as stream:
            writer=csv.DictWriter(stream,fieldnames=table[0]);writer.writeheader();writer.writerows(table)
    print(json.dumps(output,indent=2))
if __name__=='__main__':main()
