"""Read-only assertions on the completed page; writes one exclusive receipt."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import ast,hashlib,json,shutil,subprocess,urllib.request,re
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];DEMO=RUN/'demo'
STUDY=ROOT/'reproduction/improvement_v11_20261015_01'

def main():
    links=[];ids=[]
    class Parser(HTMLParser):
        def handle_starttag(self,tag,attrs):
            for k,v in attrs:
                if k=='id':ids.append(v)
                if k in ['src','href','srcset','poster'] and v:links.append(v)
    p=Parser();p.feed((DEMO/'index.html').read_text(encoding='utf8'));assert len(ids)==len(set(ids))
    local=[]
    for link in links:
        part=urlsplit(link)
        if part.scheme or not part.path:continue
        f=DEMO/unquote(part.path);assert f.is_file(),link;local.append(link)
        if f.suffix in ['.css','.js']:assert part.query=='v='+hashlib.sha256(f.read_bytes()).hexdigest()[:12]
    for doc in [STUDY/'REPORT.md',RUN/'README.md',ROOT/'README.md']:
        for link in re.findall(r'\]\(([^)]+)\)',doc.read_text(encoding='utf8')):
            part=urlsplit(link)
            if not part.scheme and part.path:assert (doc.parent/unquote(part.path)).is_file(),(doc,link)
    scripts=list(DEMO.glob('*.js'))
    for p in scripts:subprocess.run([shutil.which('node'),'--check',str(p)],capture_output=True,check=True)
    for folder in [RUN,STUDY]:
        for p in folder.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    old=ROOT/'reproduction/progress_20261015_01';media=[]
    for file,key in [('original_20fps_validation.json','media'),('candidate_replay_validation.json','cases')]:
        record=json.loads((old/file).read_text());assert record['passed']
        for m in record[key]:
            p=old/'demo'/m['video'];assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']
            media.append(p.relative_to(ROOT).as_posix())
    replay=json.loads((RUN/'edge_replay_validation.json').read_text());assert replay['passed']
    newvideo=RUN/replay['video'];assert hashlib.sha256(newvideo.read_bytes()).hexdigest()==replay['sha256']
    assert replay['frames']==421 and replay['fps']==20 and replay['same_initial_state']
    for p in [DEMO/'index.html',DEMO/'progress.json',newvideo,*(ROOT/f for f in media)]:
        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8766/'+p.relative_to(ROOT).as_posix(),method='HEAD'),timeout=5) as r:assert r.status==200
    data=json.loads((DEMO/'progress.json').read_text())['v11'];receipt=json.loads((STUDY/'analysis/final_receipt.json').read_text())
    for key in ['variants','timing','development','actual_executions_total']:assert data[key]==receipt[key],key
    assert data['stage']=='pilot_a' and not data['adopted'] and data['dev_240_launched']
    assert data['actual_executions_total']==397 and data['development']['v11_success']==235
    report={'passed':True,'links':len(local),'unique_ids':len(ids),'javascript_files':len(scripts),'historical_videos_unchanged':len(media),
            'new_video_sha256':replay['sha256'],'status_and_timing_match':True,
            'source_sha256':{p.relative_to(RUN).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [DEMO/'index.html',*scripts,*DEMO.glob('*.css')]},
            'scope':'Syntax, local HTML/Markdown links, HTTP, asset hashes and data checks. Interactive browser results are recorded separately.'}
    with (RUN/'frontend_validation.json').open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'}))
if __name__=='__main__':main()
