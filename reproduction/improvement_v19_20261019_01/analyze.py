"""Paired descriptive gates: actual v17/v18/budget, available saved v16/v15/v14/v13/v6."""
from pathlib import Path
import argparse,csv,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
TARGETS={('known13_bc_k2_noise005_demo_13000021','demo_13000021'),
         ('known13_full_s41_noise005_demo_13000022','demo_13000022'),
         ('clearance_profile_6000005','demo_6000005')}
EVENTS=['carry15_events','edge15_events','budget15_events','ik16_events','held16_events','edge16_events','route17_events','edge17_events','held17_events','handoff18_events','route18_events','transition19_events','budget19_events','settling19_events']
def read(path):return json.loads(path.read_text(encoding='utf8'))
def suffix(job):
    prefix=job['version']+'_';assert job['id'].startswith(prefix)
    return job['id'][len(prefix):]
def rows(folder,version):
    records={}
    for job in read(folder/'jobs.json'):
        if job['version']!=version:continue
        result=read(folder/job['id']/'result.json');assert result['status']=='complete' and result['job']==job
        assert [row['demo'] for row in result['records']]==job['demos']
        for row in result['records']:
            key=(suffix(job),row['demo']);assert key not in records
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
            key=(suffix(job),demo)
            if key in records:assert records[key]==cache[path][demo]
            records[key]=cache[path][demo]
    return records
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',required=True);parser.add_argument('--save',action='store_true');args=parser.parse_args()
    folder=RUN/args.stage;completed=read(folder/'completed.json');assert completed['source_unchanged']
    jobs=read(folder/'jobs.json');versions=list(dict.fromkeys(job['version'] for job in jobs));development=args.stage.startswith('dev')
    baselines=['v17','v18'] if development else ['v17','v18','budget']
    expected_versions={'v17','v18','v19'} if development else {'v17','v18','budget','transition','candidate','settling','ab','v19'}
    assert set(versions)==expected_versions
    reference_names=['v6','v13','v14','v15','v16']+baselines
    refs={version:references(jobs,version) for version in reference_names};baseline_checks={}
    for version in baselines:
        actual=rows(folder,version);historical=refs[version]
        consistent=all(row['success']==actual[key]['success'] and row['steps']==actual[key]['steps'] for key,row in historical.items())
        assert consistent,(version,'Actual rerun differs from saved baseline')
        baseline_checks[version]={'available_saved_cases':len(historical),'success_and_steps_equal':consistent}
        refs[version]=actual
    expected=set(refs['v18']);summary={};table=[]
    for version in versions:
        records=rows(folder,version);assert set(records)==expected,'Unequal paired profiles'
        result={'success':sum(row['success'] for row in records.values()),'episodes':len(records),'failures':[],
                'target_successes':[],'target_rescues':[],'rescued_vs_v18':[]}
        for ref in reference_names:
            result['regressed_vs_'+ref]=[];result['paired_reference_'+ref]=sum(key in refs[ref] for key in records)
        for key,row in records.items():
            original={ref:refs[ref].get(key) for ref in reference_names}
            for ref,before in original.items():
                if before and before['success'] and not row['success']:result['regressed_vs_'+ref].append(key)
            if not original['v18']['success'] and row['success']:result['rescued_vs_v18'].append(key)
            if row['success'] and key in TARGETS:
                result['target_successes'].append(key)
                # These remain the original v14 failure targets, not necessarily
                # new rescues relative to v15 (the clearance profile already won).
                before=original.get('v14')
                if before is not None and not before['success']:result['target_rescues'].append(key)
            if not row['success']:result['failures'].append(key)
            table.append({'version':version,'condition':key[0],'demo':key[1],'success':row['success'],'steps':row['steps'],
                          **{ref+'_success':before['success'] if before else '' for ref,before in original.items()},
                          **{event:len(row.get(event,[])) for event in EVENTS}})
        summary[version]=result
    full=summary['v19'];no_regression=all(not full['regressed_vs_'+ref] for ref in reference_names)
    targets={tuple(key) for key in full['target_successes']}==TARGETS
    executions=sum(result['episodes'] for result in summary.values());assert executions==completed['episodes']
    registered_coverage={ref:len(references(jobs,ref)) for ref in reference_names if ref not in baselines}
    historical_coverage_complete=all(full['paired_reference_'+ref]==count for ref,count in registered_coverage.items())
    if development:
        gate=(full['episodes']==240 and executions==720 and full['success']>=236 and no_regression
              and all(full['paired_reference_'+ref]==240 for ref in baselines+['v6','v13']) and historical_coverage_complete)
    elif args.stage.startswith('pilot'):
        gate=(full['episodes']==94 and executions==752 and no_regression and targets
              and all(full['paired_reference_'+ref]==94 for ref in baselines) and historical_coverage_complete
              and full['paired_reference_v13']==94 and full['paired_reference_v6']==93)
    elif args.stage.startswith('smoke'):
        gate=(full['episodes']==9 and executions==72 and no_regression and targets
              and all(full['paired_reference_'+ref]==9 for ref in baselines) and historical_coverage_complete
              and full['paired_reference_v13']==9 and full['paired_reference_v6']==8)
    else:raise ValueError('Unknown stage')
    output={'stage':args.stage,'variants':summary,'outcome_gate_passed':gate,'evaluated_executions':executions,
            'paired_conditions_per_version':len(expected),'actual_baselines':baselines,'historical_baseline_checks':baseline_checks,
            'all_three_targets_successful':targets if not development else None,
            'all_three_targets_rescued':{tuple(key) for key in full['target_rescues']}==TARGETS if not development else None,
            'registered_historical_reference_coverage':registered_coverage,
            'target_rescue_reference':'Original v14 targets; clearance6000005 is already successful under v15, not a new v15 rescue.',
            'note':'Known profiles, not independent starts. A/B/C/AB each repair full actual v18; AC and BC are absent, so this is not a full three-factor interaction design; budget retains v15 C-only with different protection and is only a success-count comparator, not an adoptable substitute. Nine profiles reuse eight starts. Development is v17/v18/v19 each 240 = 720 actual runs. Historical coverage is only the registered existing matches. Physical and decision gates are separate.'}
    if args.save:
        paths=[RUN/'analysis'/f'{args.stage}.json',RUN/'analysis'/f'{args.stage}_pairs.csv']
        assert all(not path.exists() for path in paths)
        with paths[0].open('x',encoding='utf8') as stream:json.dump(output,stream,indent=2)
        with paths[1].open('x',newline='',encoding='utf8') as stream:
            writer=csv.DictWriter(stream,fieldnames=table[0]);writer.writeheader();writer.writerows(table)
    print(json.dumps(output,indent=2))
if __name__=='__main__':main()
