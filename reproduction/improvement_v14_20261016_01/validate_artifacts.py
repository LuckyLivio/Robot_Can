"""Source-backed paper figures, actual PDF rendering, video decode and links."""
from pathlib import Path
import ast,csv,hashlib,json,shutil,subprocess,sys
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
from urllib.request import urlopen
from PIL import Image
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];OUT=RUN/'validation';OUT.mkdir(exist_ok=True)
def command(args):return subprocess.run(list(map(str,args)),check=True,capture_output=True,text=True,encoding='utf8',errors='replace').stdout
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,t,attrs):
        for k,v in attrs:
            if k in ['href','src','poster'] and v:self.links.append(v)
if __name__=='__main__':
    code=list(RUN.glob('*.py'))+list((RUN/'recovery').glob('*.py'))
    for p in code:ast.parse(p.read_text(encoding='utf8'))
    cat=json.loads((RUN/'figures/CATALOG.json').read_text(encoding='utf8'));figures=[]
    poppler=Path(shutil.which('pdftoppm')).parent
    def pdf_tool(n,*args):
        exe=poppler/(n+'.exe')
        if not exe.is_file():exe=Path(shutil.which(n))
        return command([exe,*args])
    for g in cat:
        name=g['id'];base=RUN/'figures'/name
        for rel,h in g['sources'].items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h
        with Image.open(base.with_suffix('.png')) as im:assert min(im.info['dpi'])>599;im.verify()
        with base.with_suffix('.csv').open(encoding='utf-8-sig') as f:assert len(list(csv.DictReader(f)))==g['rows']
        listing=pdf_tool('pdfimages','-list',base.with_suffix('.pdf'));assert len(listing.strip().splitlines())==2
        fonts=pdf_tool('pdffonts',base.with_suffix('.pdf'));assert 'Type 3' not in fonts and all('yes' in l for l in fonts.strip().splitlines()[2:])
        pdf_tool('pdftoppm','-r','100','-singlefile','-png',base.with_suffix('.pdf'),OUT/name)
        figures.append({'id':name,'pdf_rendered':True,'embedded_fonts':True,'vector_only':True,'png_dpi':600,'source_hashes_match':True})
    videos=[]
    for video in sorted((RUN/'demo').glob('*/comparison.mp4')):
        probe=json.loads(command(['ffprobe','-v','error','-show_streams','-show_format','-of','json',video]))
        stream=next(s for s in probe['streams'] if s['codec_type']=='video');assert stream['r_frame_rate']=='20/1' and int(stream['nb_frames'])==421
        command(['ffmpeg','-v','error','-i',video,'-f','null','-'])
        receipt=json.loads((RUN/'analysis'/('demo_replay_'+video.parent.name+'.json')).read_text())
        assert receipt['passed'] and hashlib.sha256(video.read_bytes()).hexdigest()==receipt['video_sha256']
        videos.append({'case':video.parent.name,'fps':20,'frames':421,'duration_s':21.05,'full_decode_passed':True,'physical_replay_verified':True})
    assert len(videos)==2
    parser=Links();parser.feed((RUN/'index.html').read_text(encoding='utf8'));local=[]
    for s in parser.links:
        u=urlsplit(s)
        if u.scheme or not u.path:continue
        target=(RUN/unquote(u.path)).resolve();assert target.exists(),s
        path=target.relative_to(ROOT).as_posix()
        with urlopen('http://127.0.0.1:8766/'+path,timeout=15) as response:assert response.status==200
        local.append(path)
    out={'passed':True,'python_parsed':len(code),'figures':figures,'videos':videos,
         'html_local_resources_http200':len(local),'note':'Browser interaction and visual inspection recorded separately.'}
    (OUT/'artifacts.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out))
