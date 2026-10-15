"""Check active local links and current deliverables; frozen backups excluded."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import ast,json,re,urllib.request
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k=='id':self.ids.append(v)
            if k in ['href','src','poster'] and v:self.links.append(v)
            if k=='srcset' and v:self.links.extend(x.strip().split()[0] for x in v.split(','))
def main():
    md=[*ROOT.glob('*.md'),*ROOT.glob('WORKSPACE/**/*.md'),*RUN.glob('*.md')];count=0;missing=[]
    def check(p,target):
        nonlocal count
        u=urlsplit(target.strip('<>'))
        if u.scheme or not u.path or '{' in target:return
        count+=1
        q=(p.parent/unquote(u.path)).resolve()
        if not q.exists():missing.append({'file':p.relative_to(ROOT).as_posix(),'target':target})
    for p in md:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):check(p,target)
    htmls=[ROOT/'index.html',ROOT/'WORKSPACE/index.html',RUN/'index.html',ROOT/'reproduction/progress_v11_20261015_01/demo/index.html',ROOT/'reproduction/portable_delivery_20261015_01/index.html']
    for p in htmls:
        parser=Links();parser.feed(p.read_text(encoding='utf8'));assert len(set(parser.ids))==len(parser.ids)
        for target in parser.links:check(p,target)
    assert not missing,missing
    for p in RUN.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
    resources=[RUN/'index.html',RUN/'REPORT.md',RUN/'THESIS_OUTLINE_REVIEWED.md',RUN/'builds/CAN_LAB_PAPER_FIGURES_20261015.zip',ROOT/'reproduction/progress_v11_20261015_01/demo/index.html']
    resources+=list((RUN/'figures').glob('*.svg'))
    for p in resources:
        url='http://127.0.0.1:8766/'+p.relative_to(ROOT).as_posix()
        with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as r:assert r.status==200
    # Entire extracted supplement should have working local links as well.
    pack=RUN/'builds/移位 验证/CAN_LAB_PAPER_FIGURES';package_missing=[];pc=0
    for p in [*pack.glob('*.md'),pack/'index.html']:
        text=p.read_text(encoding='utf8')
        if p.suffix=='.html':parser=Links();parser.feed(text);targets=parser.links
        else:targets=re.findall(r'\]\(([^)]+)\)',text)
        for target in targets:
            u=urlsplit(target.strip('<>'))
            if u.scheme or not u.path:continue
            pc+=1
            if not (p.parent/unquote(u.path)).exists():package_missing.append((p.name,target))
    assert not package_missing,package_missing
    result={'passed':True,'active_markdown_documents':len(md),'active_html_pages':len(htmls),'local_links':count,'http_resources':len(resources),'package_local_links':pc,'missing':missing,'package_missing':package_missing,'scope':'Current guides and pages; frozen snapshot-relative links intentionally excluded.'}
    (RUN/'validation/document_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
