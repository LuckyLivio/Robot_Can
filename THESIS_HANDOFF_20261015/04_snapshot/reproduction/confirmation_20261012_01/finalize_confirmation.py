"""Archive sources and verify preservation of every pre-existing project file."""
import datetime,hashlib,importlib.metadata,json,platform,shutil,sys
from pathlib import Path
import torch
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(RUN))
from prepare_states import write
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    validation=json.loads((RUN/'analysis/result_validation.json').read_text());assert validation['passed']
    before=json.loads((RUN/'before_manifest.json').read_text());changed=[];missing=[]
    for relative,sha in before.items():
        p=ROOT/relative
        if not p.exists():missing.append(relative)
        elif digest(p)!=sha:changed.append(relative)
    assert not changed and not missing,{'changed':changed,'missing':missing}
    lock=json.loads((RUN/'lock.json').read_text())
    for relative,sha in lock['input_sha256'].items():assert digest(ROOT/relative)==sha,relative
    for p in list(RUN.glob('*.py'))+[ROOT/n for n in ('common.py','world_model.py','collect_branches.py','collect_rollout_branches.py','evaluate_delay.py')]:
        target=RUN/'sources'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():raise FileExistsError(target)
        shutil.copyfile(p,target)
    env={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
         'packages':{n:importlib.metadata.version(n) for n in ('torch','numpy','robosuite','mujoco','h5py','matplotlib')},
         'cuda_available':torch.cuda.is_available(),'torch_cuda':torch.version.cuda,
         'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
         'evaluation_device':'CPU, two torch threads per worker; three concurrent local workers',
         'no_training_in_this_confirmation':True}
    write(RUN/'environment.json',env)
    files={p.relative_to(ROOT).as_posix():digest(p) for p in RUN.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    manifest={'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'complete','preexisting_files_verified_unchanged':len(before),
        'changed_existing':changed,'deleted_existing':missing,'preserved_all_previous_weights_and_results':True,
        'new_files_sha256':files,'manifest_excludes_itself':True,
        'root_code_and_documents_unchanged':True,'confirmation_validation':validation}
    write(RUN/'change_manifest.json',manifest)
    print(json.dumps({'status':'complete','preexisting_files_unchanged':len(before),'new_files_before_manifest':len(files)}),flush=True)

if __name__=='__main__':main()
