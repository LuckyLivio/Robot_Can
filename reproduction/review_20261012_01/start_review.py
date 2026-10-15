"""Create an exclusive pre-review snapshot without altering historical results."""
import datetime, hashlib, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    target=RUN/'before_manifest.json'
    if target.exists():raise FileExistsError(target)
    before={p.relative_to(ROOT).as_posix():digest(p) for p in ROOT.rglob('*')
            if p.is_file() and RUN not in p.parents and not any(x in p.parts for x in ('.venv','__pycache__','.idea','.git'))}
    with target.open('x',encoding='utf-8') as f:json.dump(before,f,indent=2)
    archive=RUN/'previous_documents';archive.mkdir()
    for p in ROOT.glob('*.md'):shutil.copy2(p,archive/p.name)
    with (RUN/'scope.json').open('x',encoding='utf-8') as f:
        json.dump({'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'scope':'Read-only experimental audit, documentation corrections, new presentation frontend; no thesis body or training.',
            'old_release_verified_before_review':True,
            'preserve':'All pre-existing non-root-Markdown files, including all previous releases, code, data, weights, figures and results.',
            'preexisting_files':len(before),'archived_root_documents':len(list(archive.glob('*.md')))},f,indent=2)
    print(json.dumps({'snapshot_files':len(before),'archive_documents':len(list(archive.glob('*.md')))}))
if __name__=='__main__':main()
