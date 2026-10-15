"""Verify that the failed smoke result really blocks development freezing."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='development_gate');args=parser.parse_args()
    output=RUN/'validation'/f'{args.name}.json';assert not output.exists()
    gate=RUN/'analysis/smoke_a.json';assert not json.loads(gate.read_text())['outcome_gate_passed']
    blocked_paths=[RUN/'protocols'/n for n in ['development_freeze.json','dev_jobs.json','confirmation_lock.json']]
    assert not any(p.exists() for p in blocked_paths)
    command=[sys.executable,'-X','utf8','-B',str(RUN/'freeze_development.py'),'--smoke','smoke_a','--mechanisms','mechanisms_c','--components','components_a']
    completed=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf8')
    assert completed.returncode!=0 and 'AssertionError: smoke_a' in completed.stderr
    assert not any(p.exists() for p in blocked_paths)
    out={'passed':True,'scope':'Failed outcome gate blocks development before jobs or freeze are written',
         'expected_exit_code':completed.returncode,'smoke_outcome_gate_passed':False,'new_experiments':0,
         'analysis_sha256':hashlib.sha256(gate.read_bytes()).hexdigest(),'freeze_script_sha256':hashlib.sha256((RUN/'freeze_development.py').read_bytes()).hexdigest(),
         'output':completed.stdout+completed.stderr,'development_and_confirmation_not_created':True}
    output.write_text(json.dumps(out,indent=2),encoding='utf8');print('Development correctly refused at smoke_a gate; no later jobs or states created.')
