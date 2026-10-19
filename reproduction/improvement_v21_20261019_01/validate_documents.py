"""Check changed v21 delivery documents and local links without rewriting history."""
from pathlib import Path
from urllib.parse import unquote,urlsplit
import argparse,hashlib,json,re
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
EXPECTED={'README.md','index.html','STATUS.md','DEMO_GUIDE.md','RESULTS.md','EVIDENCE_INDEX.md','PROJECT_NAVIGATION.md','THESIS_HANDOFF_LATEST.md','PROGRAM_GUIDE.md'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',default='documents');args=p.parse_args()
    assert Path(args.name).name==args.name and args.name not in ['.','..']
    output=RUN/'validation'/(args.name+'.json');output.parent.mkdir(exist_ok=True)
    assert not output.exists(),('Receipt exists; use a new --name',output)
    changes=RUN/'document_changes.json';changed=json.loads(changes.read_text(encoding='utf8'))['updated']
    assert set(changed)==EXPECTED and len(changed)==len(EXPECTED),'Root documentation update inventory differs from registered nine files'
    paths=list(dict.fromkeys([ROOT/name for name in changed if name.endswith('.md')]+[RUN/'README.md',RUN/'REPORT.md',RUN/'protocols/PLAN.md']))
    checked=[];missing=[]
    for path in paths:
        assert path.is_file(),path
        text=path.read_text(encoding='utf8')
        # Ignore fenced commands; inspect ordinary Markdown links and images.
        text=re.sub(r'```.*?```','',text,flags=re.S)
        for raw in re.findall(r'!?\[[^\]]*\]\(([^)\n]+)\)',text):
            target=raw.strip()
            if target.startswith('<'):target=target[1:target.index('>')]
            else:target=re.split(r'\s+[\"\']',target,maxsplit=1)[0]
            parsed=urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:continue
            decoded=unquote(parsed.path)
            actual=(ROOT/decoded.lstrip('/') if decoded.startswith('/') else path.parent/decoded).resolve()
            actual.relative_to(ROOT)
            item={'document':path.relative_to(ROOT).as_posix(),'target':target};checked.append(item)
            if not actual.exists():missing.append(item)
    redirect='reproduction/improvement_v21_20261019_01/index.html'
    assert redirect in (ROOT/'index.html').read_text(encoding='utf8'),'Root redirect is not v21'
    sources=paths+[ROOT/'index.html',changes,Path(__file__).resolve()]
    result={'passed':not missing,'documents':len(paths),'root_files_declared_updated':len(changed),
            'local_links_checked':len(checked),'missing':missing,'root_redirect_targets_v21':True,
            'source_sha256':{path.relative_to(ROOT).as_posix():sha(path) for path in sources},
            'note':'Document inventory, local links and redirect checks only. Scientific conclusions and browser appearance require separate review.'}
    with output.open('x',encoding='utf8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False));assert not missing,missing
if __name__=='__main__':main()
