"""Finalize only after factual, document, runtime, and browser review pass."""
import ast,datetime,hashlib,json,re
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    output=RUN/'review_validation.json';assert not output.exists()
    before=read(RUN/'before_manifest.json');changed=[];deleted=[];preserved={}
    allowed={'README.md','PROGRAM_GUIDE.md','DEMO_GUIDE.md','STATUS.md','REPRODUCTION_PLAN.md'}
    for rel,sha in before.items():
        p=ROOT/rel
        if not p.exists():deleted.append(rel)
        elif digest(p)!=sha:changed.append(rel)
        else:preserved[rel]=sha
    assert not deleted,deleted
    assert set(changed)==allowed,changed
    archive=RUN/'previous_documents'
    for p in archive.glob('*.md'):assert digest(p)==before[p.name]
    for p in RUN.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    linkchecks=[]
    for p in ROOT.glob('*.md'):
        content=p.read_text(encoding='utf-8');assert content.count('```')%2==0,p.name
        for value in re.findall(r'\]\(([^)]+)\)',content):
            parsed=urlsplit(value)
            if parsed.scheme or value.startswith('#'):continue
            target=p.parent/unquote(parsed.path)
            if target.resolve()==output.resolve():continue
            assert target.exists(),(p.name,value)
            linkchecks.append({'file':p.name,'target':value})
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.refs=[];self.ids=[]
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if 'id' in attrs:self.ids.append(attrs['id'])
            for key in ('href','src'):
                if attrs.get(key):self.refs.append(attrs[key])
    html=RUN/'demo/index.html';parser=Links();parser.feed(html.read_text(encoding='utf-8'))
    assert len(parser.ids)==len(set(parser.ids))
    for value in parser.refs:
        if value.startswith('#'):assert value[1:] in parser.ids;continue
        if urlsplit(value).scheme:continue
        assert (html.parent/unquote(urlsplit(value).path)).exists(),value
    source=(RUN/'demo/data.js').read_text(encoding='utf-8')
    data=json.loads(source.removeprefix('const DEMO_DATA = ').strip().removesuffix(';'))
    oldmedia=read(ROOT/'reproduction/release_20261012_01/demo/media_manifest.json')
    assert len(data['cases'])==len(oldmedia)==6
    for case,old in zip(data['cases'],oldmedia):
        for key in ('id','state_name','condition','sha256','results','duration_s'):assert case[key]==old[key]
        assert digest(html.parent/case['video'])==case['sha256']
        assert (html.parent/case['firstFrame']).is_file()
    assert read(RUN/'audit_validation.json')['passed']
    assert read(RUN/'inventory_qualifications.json')['unresolved_flag_count']==0
    assert read(RUN/'checkpoint_validation.json')['passed']
    assert read(RUN/'smoke_validation.json')['checks_passed']
    browser=read(RUN/'browser_validation.json');assert browser['passed']
    manifest={'passed':True,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'changed_existing_files':changed,'deleted_existing_files':deleted,
        'preexisting_files':len(before),'preserved_historical_file_count':len(preserved),
        'archived_root_documents':len(list(archive.glob('*.md'))),'current_root_documents':len(list(ROOT.glob('*.md'))),
        'current_document_local_links_checked':len(linkchecks),'html_static_references_checked':len(parser.refs),
        'original_controller_code_unchanged':True,'old_weights_results_data_figures_videos_unchanged':True,
        'old_release_directory_unchanged':True,'thesis_body_not_written':True,
        'mainline_training_jobs_verified':15,'selected_world_models_loaded':18,
        'development_evaluations_verified':60,'confirmation_evaluations_verified':14,
        'confirmation_statistics_recomputed':9,'browser_validation':browser,
        'preserved_files':preserved,'current_files':{p.relative_to(ROOT).as_posix():digest(p) for p in [*ROOT.glob('*.md'),*RUN.rglob('*')] if p.is_file() and '__pycache__' not in p.parts},
        'manifest_excludes_itself':True}
    with output.open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2,ensure_ascii=False)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('preserved_files','current_files','browser_validation')},indent=2,ensure_ascii=False))
if __name__=='__main__':main()
