"""Read-only validation of frozen experiments and the current release."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    frozen=json.loads((RUN/'frozen_results.json').read_text(encoding='utf-8'))
    for relative,sha in frozen['protected_sha256'].items():
        assert (ROOT/relative).is_file(),f'Missing frozen file: {relative}'
        assert digest(ROOT/relative)==sha,f'Changed frozen file: {relative}'
    release=RUN/'release_validation.json'
    if not release.exists():
        print(f"Frozen experiments verified: {len(frozen['protected_sha256'])} files. Release is not finalized yet.")
        return
    manifest=json.loads(release.read_text(encoding='utf-8'));assert manifest['passed']
    for relative,sha in manifest['release_sha256'].items():assert digest(ROOT/relative)==sha,relative
    print(json.dumps({'passed':True,'frozen_experiment_files':len(frozen['protected_sha256']),
        'verified_release_files':len(manifest['release_sha256']),'changed_existing_files':manifest['changed_existing_files'],
        'deleted_existing_files':manifest['deleted_existing_files'],'video_count':6},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
