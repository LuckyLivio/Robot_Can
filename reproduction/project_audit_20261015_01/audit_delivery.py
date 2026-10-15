"""Decode archived videos, check local transfer ZIPs and inspect portability."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import ast,json,hashlib,subprocess,shutil,zipfile,os
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(name,d):
    with (RUN/name).open('x',encoding='utf8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def main():
    before=json.loads((RUN/'before_manifest.json').read_text());videos=defaultdict(list)
    for p,h in before.items():
        if p.endswith('.mp4'):videos[h].append(p)
    def decode(ps):
        p=ROOT/ps[0];meta=subprocess.run([shutil.which('ffprobe'),'-v','error','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_frames:format=duration','-of','json',str(p)],capture_output=True,text=True)
        dec=subprocess.run([shutil.which('ffmpeg'),'-v','error','-threads','1','-i',str(p),'-f','null','-'],capture_output=True,text=True)
        return {'paths':ps,'passed':meta.returncode==0 and dec.returncode==0 and not dec.stderr.strip(),'metadata':json.loads(meta.stdout) if meta.returncode==0 else {},'decode_stderr':dec.stderr[:1500]}
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(decode,videos.values()))
    save('media_validation.json',{'passed':all(r['passed'] for r in results),'unique_videos':len(results),'tracked_video_paths':sum(len(r['paths']) for r in results),'files':results})
    zips=[]
    for p in ROOT.glob('THESIS_HANDOFF_*.zip'):
        expected=p.with_suffix(p.suffix+'.sha256').read_text().split()[0];actual=digest(p)
        with zipfile.ZipFile(p) as z:bad=z.testzip();n=len(z.infolist())
        zips.append({'path':p.name,'bytes':p.stat().st_size,'sha256':actual,'hash_matches':actual==expected,'crc_error':bad,'members':n})
    save('zip_validation.json',{'passed':all(x['hash_matches'] and x['crc_error'] is None for x in zips),'files':zips})
    literals=[]
    for rel in before:
        if not rel.endswith('.py') or rel.startswith('THESIS_HANDOFF_'):continue
        tree=ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                v=node.value
                if (len(v)>2 and v[0].isalpha() and v[1:3] in [':/',':\\']) or v.startswith(('/home/','/root/')):
                    literals.append({'file':rel,'line':node.lineno,'literal':v[:250]})
    save('portability_literals.json',literals)
    gitbytes=sum(p.stat().st_size for p in (ROOT/'.git').rglob('*') if p.is_file())
    stats={'git_directory_bytes':gitbytes,'root_python_scripts':len(list(ROOT.glob('*.py'))),'absolute_path_literal_occurrences':len(literals),
       'ci_workflows_present':(ROOT/'.github/workflows').is_dir(),'root_license_present':any((ROOT/n).exists() for n in ['LICENSE','LICENSE.md','LICENSE.txt']),
       'git_object_stats':subprocess.check_output(['git','count-objects','-v'],cwd=ROOT).decode()}
    save('portability_summary.json',stats)
    print(json.dumps({'media_passed':all(r['passed'] for r in results),'unique_videos':len(results),'zips':zips,'portability':stats},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
