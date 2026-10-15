"""Validate links, script syntax, media metadata and source-derived summaries."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import ast,hashlib,json,shutil,subprocess,urllib.request
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];DEMO=RUN/'demo'

def main():
    links=[];ids=[]
    class Parser(HTMLParser):
        def handle_starttag(self,tag,attrs):
            for k,v in attrs:
                if k=='id':ids.append(v)
                if k in ['src','href'] and v:links.append(v)
    parser=Parser();parser.feed((DEMO/'index.html').read_text(encoding='utf8'));assert len(ids)==len(set(ids))
    local=[]
    for link in links:
        parts=urlsplit(link)
        if parts.scheme or link.startswith('#'):continue
        p=DEMO/unquote(parts.path);assert p.exists(),link;local.append(link)
    scripts=list(DEMO.glob('*.js'))
    for p in scripts:subprocess.run([shutil.which('node'),'--check',str(p)],check=True,capture_output=True)
    for p in list(RUN.glob('*.py'))+list((ROOT/'reproduction/improvement_v8_20261015_01').glob('*.py')):ast.parse(p.read_text(encoding='utf-8-sig'))
    originals=json.loads((RUN/'original_20fps_validation.json').read_text());candidates=json.loads((RUN/'candidate_replay_validation.json').read_text())
    assert originals['passed'] and candidates['passed'];media=originals['media']+candidates['cases'];checks=[]
    for m in media:
        p=DEMO/m['video'];assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']
        probe=json.loads(subprocess.check_output([shutil.which('ffprobe'),'-v','error','-select_streams','v:0','-show_entries','stream=avg_frame_rate,nb_frames,width,height','-of','json',str(p)]))['streams'][0]
        assert probe['avg_frame_rate']=='20/1' and int(probe['nb_frames'])==m['frames']
        url='http://127.0.0.1:8766/'+p.relative_to(ROOT).as_posix()
        with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=5) as response:assert response.status==200
        checks.append({'file':p.relative_to(ROOT).as_posix(),**probe})
    status=json.loads((DEMO/'progress.json').read_text(encoding='utf8'));assert not status['v8']['adopted'] and not status['v8']['dev_240_launched']
    assert status['v8']['pilot']['variants']['v8']['success']==30
    browser=json.loads((RUN/'browser_validation.json').read_text())
    for rel,h in browser['source_sha256'].items():assert hashlib.sha256((RUN/rel).read_bytes()).hexdigest()==h,rel
    report={'passed':True,'local_links_checked':len(local),'unique_ids':len(ids),'javascript_syntax_checked':len(scripts),'videos_checked':checks,
            'browser_checks':browser['checks'],'browser_note':'Separate interactive receipt matches these assets. This script does not itself launch browser tests.'}
    with (RUN/'frontend_validation_final.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k!='videos_checked'}),flush=True)
if __name__=='__main__':main()
