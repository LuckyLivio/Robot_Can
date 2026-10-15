"""Archive source snapshots and verify that all earlier project files survive."""
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
analysis=json.loads((RUN/'analysis/analysis.json').read_text())
assert analysis['status']=='complete' and analysis['verification']['completed_evaluation_jobs']==60
sources=RUN/'sources';sources.mkdir(exist_ok=False)
for file in RUN.glob('*.py'):shutil.copyfile(file,sources/file.name)
if (RUN/'rerun.ps1').exists():shutil.copyfile(RUN/'rerun.ps1',sources/'rerun.ps1')
(sources/'original_runtime').mkdir()
for name in ('common.py','world_model.py','collect_branches.py','evaluate_delay.py','calibrate_score_head.py'):
    shutil.copyfile(ROOT/name,sources/'original_runtime'/name)
before=json.loads((RUN/'before_manifest.json').read_text(encoding='utf-8-sig'))
changed=[];missing=[]
for name,digest in before.items():
    path=ROOT/name
    if not path.is_file():missing.append(name)
    elif sha(path)!=digest:changed.append(name)
assert not changed and not missing,(changed,missing)
added={p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('*')
       if p.is_file() and not any(part in p.parts for part in ('.venv','__pycache__','.git','.idea'))
       and p.relative_to(ROOT).as_posix() not in before}
result={'status':'complete','preexisting_files_checked':len(before),'modified':changed,'deleted':missing,
        'all_preexisting_files_unchanged':True,'added_files_before_manifest':added}
with (RUN/'change_manifest.json').open('x',encoding='utf-8') as file:json.dump(result,file,indent=2)
print(json.dumps({'preserved_files':len(before),'changed':changed,'deleted':missing,'added_files':len(added)}))
