"""Verify preserved historical files and the complete supplemental release."""
import argparse, ast, datetime, json, subprocess, sys
from pathlib import Path
from register import ROOT,RUN,digest


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def check(mapping):
    for rel,sha in mapping.items():
        path=ROOT/rel
        assert path.is_file(),f'Missing: {rel}'
        assert digest(path)==sha,f'Changed: {rel}'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true');args=parser.parse_args()
    final=RUN/'final_validation.json'
    if args.freeze:
        assert not final.exists()
        before=read(RUN/'before_manifest.json');check(before);check(read(RUN/'frozen_inputs.json'))
        audit=read(RUN/'analysis/run_verification.json')
        assert audit['passed'] and audit['new_jobs']==88 and audit['new_episodes']==900
        assert read(RUN/'snapshot_validation.json')['passed'] and read(RUN/'evaluator_validation.json')['passed']
        code=[]
        for p in RUN.glob('*.py'):
            ast.parse(p.read_text(encoding='utf-8'));code.append(p.name)
        previous=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'reproduction/review_20261012_01/verify_project.py')],cwd=ROOT,text=True,encoding='utf-8',capture_output=True,check=True)
        previous_json=json.loads(previous.stdout);assert previous_json['passed']
        with (RUN/'historical_verification.json').open('x',encoding='utf-8') as f:json.dump(previous_json,f,indent=2)
        files=[p for p in RUN.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        files.append(ROOT/'SUPPLEMENTAL_RESULTS.md')
        current={p.relative_to(ROOT).as_posix():digest(p) for p in files}
        value={'passed':True,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'preserved_files':before,'current_files':current,'deleted_existing_files':[],
               'changed_existing_files':[],'python_syntax_verified':code,
               'new_jobs':88,'new_episodes':900,'trace_steps':audit['new_trace_steps'],
               'oracle_decisions':audit['oracle_decisions'],'weights_and_historical_results_unchanged':True,
               'previous_review_verifier_passed':True,'no_manuscript_written':True}
        with final.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,ensure_ascii=False)
    value=read(final);assert value['passed'];check(value['preserved_files']);check(value['current_files'])
    print(json.dumps({'passed':True,'preserved_files':len(value['preserved_files']),
                      'verified_new_files':len(value['current_files']),'new_jobs':value['new_jobs'],
                      'new_episodes':value['new_episodes'],'changed_existing_files':value['changed_existing_files'],
                      'deleted_existing_files':value['deleted_existing_files']},indent=2))


if __name__=='__main__':main()
