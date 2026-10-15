"""Verify active guides/new report/navigation and existing demo, without old snapshot links."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import ast,json,re,subprocess,shutil,urllib.request
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def main():
    changes=json.loads((RUN/'document_changes.json').read_text())['updated_or_added'];paths=[ROOT/p for p in changes if p.endswith('.md')]
    paths+=list(RUN.glob('*.md'));missing=[];checked=0
    for p in paths:
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
            u=urlsplit(link.strip('<>'))
            if u.scheme or not u.path:continue
            checked+=1
            if not (p.parent/unquote(u.path)).exists():missing.append({'source':p.relative_to(ROOT).as_posix(),'link':link})
    htmls=[ROOT/'index.html',ROOT/'WORKSPACE/index.html',RUN/'index.html',ROOT/'reproduction/progress_v11_20261015_01/demo/index.html']
    class Parser(HTMLParser):
        def __init__(self):super().__init__();self.links=[];self.ids=[]
        def handle_starttag(self,tag,attrs):
            for k,v in attrs:
                if k=='id':self.ids.append(v)
                if k in ['src','href','srcset','poster'] and v:self.links.append(v)
    htmlchecked=0
    for p in htmls:
        parser=Parser();parser.feed(p.read_text(encoding='utf8'));assert len(parser.ids)==len(set(parser.ids)),p
        for link in parser.links:
            u=urlsplit(link)
            if u.scheme or not u.path:continue
            htmlchecked+=1
            if not (p.parent/unquote(u.path)).exists():missing.append({'source':p.relative_to(ROOT).as_posix(),'link':link})
    assert not missing,missing
    before=json.loads((RUN/'before_manifest.json').read_text());scripts=[ROOT/p for p in before if Path(p).suffix in ['.js','.cjs']]
    for p in scripts:subprocess.run([shutil.which('node'),'--check',str(p)],capture_output=True,check=True)
    for p in RUN.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
    for p in [*htmls,RUN/'CHECKLIST.csv',RUN/'REPORT.md',ROOT/'THESIS_HANDOFF_LATEST.md']:
        url='http://127.0.0.1:8766/'+p.relative_to(ROOT).as_posix()
        with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=5) as r:assert r.status==200
    result={'passed':True,'active_markdown_documents':len(paths),'local_markdown_links':checked,'active_html_pages':len(htmls),'html_local_links':htmlchecked,'javascript_syntax_files':len(scripts),'missing_active_links':missing,'note':'629 preexisting relative links in frozen backup/snapshot/source-copy Markdown remain intentionally unchanged; not missing original assets.'}
    with (RUN/'active_document_validation.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
if __name__=='__main__':main()
