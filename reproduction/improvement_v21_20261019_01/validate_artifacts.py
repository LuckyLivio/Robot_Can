"""Validate actual v21 figures and local web resources; no new videos required.

This is delivery validation, never an experiment or a demonstration replay.
Run only after REPORT.md, index.html and figures/CATALOG.json exist.
"""
from pathlib import Path
import argparse,ast,csv,hashlib,json,shutil,subprocess
from html.parser import HTMLParser
from urllib.parse import quote,unquote,urlsplit
from urllib.request import urlopen
import xml.etree.ElementTree as ET
from PIL import Image

RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args):
    return subprocess.run(list(map(str,args)),check=True,capture_output=True,text=True,encoding='utf8',errors='replace').stdout
def pdf_tool(name,*args):
    executable=shutil.which(name)
    if not executable:
        renderer=shutil.which('pdftoppm')
        candidate=Path(renderer).parent/(name+'.exe') if renderer else None
        if candidate and candidate.is_file():executable=str(candidate)
    assert executable,('Required installed PDF tool unavailable',name)
    return command([executable,*args])
def local_path(parent,raw):
    target=(ROOT/raw.lstrip('/') if raw.startswith('/') else parent/raw).resolve()
    target.relative_to(ROOT)
    return target

def raw_records(stage):
    folder=RUN/stage
    jobs=json.loads((folder/'jobs.json').read_text(encoding='utf8'))
    records=[]
    for job in jobs:
        path=folder/job['id']/'result.json'
        result=json.loads(path.read_text(encoding='utf8'))
        assert result['status']=='complete' and result['job']==job
        for record in result['records']:
            records.append({'stage':stage,'version':job['version'],'condition':job['id'].split('_',1)[1],
                'demo':record['demo'],'comparison_profile':job.get('comparison_profile','standard'),
                'success':record['success'],'steps':record['steps'],'result':path.relative_to(RUN).as_posix()})
    return records

def compare_csv_to_raw(name,rows,records):
    if name.endswith('_profiles'):
        expected={(r['version'],r['comparison_profile']) for r in records}
        assert {(r['version'],r['comparison_profile']) for r in rows}==expected
        for row in rows:
            matched=[r for r in records if r['version']==row['version'] and r['comparison_profile']==row['comparison_profile']]
            assert int(row['success'])==sum(r['success'] for r in matched)
            assert int(row['executions'])==len(matched)
            if row['steps_if_single_profile']:
                assert len(matched)==1 and int(row['steps_if_single_profile'])==matched[0]['steps']
    elif name.endswith('_targets'):
        assert len(rows)==18 and len({(r['version'],r['condition'],r['demo']) for r in rows})==18
        for row in rows:
            matched=[r for r in records if all(r[key]==row[key] for key in ['version','condition','demo','comparison_profile'])]
            assert len(matched)==1
            assert row['success'] in ['True','False'] and (row['success']=='True')==matched[0]['success']
            assert int(row['steps'])==matched[0]['steps'] and row['result']==matched[0]['result']
    else:
        raise AssertionError(('Unknown figure data contract',name))
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ['href','src','poster'] and value:self.links.append(value)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='artifacts');parser.add_argument('--base-url',default='http://127.0.0.1:8766');args=parser.parse_args()
    assert Path(args.name).name==args.name and args.name not in ['.','..']
    server=urlsplit(args.base_url)
    assert server.scheme=='http' and server.hostname in ['127.0.0.1','localhost','::1'],'Local HTTP server required'
    out=RUN/'validation';out.mkdir(exist_ok=True);receipt=out/(args.name+'.json')
    assert not receipt.exists(),('Receipt exists; use a new --name',receipt)
    for path in [RUN/'REPORT.md',RUN/'index.html',RUN/'figures/CATALOG.json']:assert path.is_file(),path
    code=list(RUN.glob('*.py'))+list((RUN/'recovery').glob('*.py'))+list((RUN/'figure_qa').glob('*.py'))
    for path in code:ast.parse(path.read_text(encoding='utf8'),filename=str(path))
    catalog=json.loads((RUN/'figures/CATALOG.json').read_text(encoding='utf8'))
    assert catalog and len({g['id'] for g in catalog})==len(catalog)
    previews=out/(args.name+'_previews');previews.mkdir(exist_ok=False)
    figures=[]
    for entry in catalog:
        name=entry['id'];assert Path(name).name==name
        base=RUN/'figures'/name;source_hashes=entry['sources'];assert source_hashes
        for rel,digest in source_hashes.items():assert sha(local_path(ROOT,rel))==digest,(name,rel,'Source hash')
        outputs=entry['outputs_sha256'];assert all(ext in outputs for ext in ['png','pdf','svg','csv'])
        for ext in ['png','pdf','svg','csv']:assert sha(base.with_suffix('.'+ext))==outputs[ext],(name,ext,'Output hash')
        with Image.open(base.with_suffix('.png')) as picture:
            dpi=picture.info.get('dpi',(0,0));assert min(dpi)>=599
            size=picture.size;picture.verify()
        expected_size=[entry['width_mm']/25.4*dpi[0],entry['height_mm']/25.4*dpi[1]]
        assert all(abs(actual-expected)<=2 for actual,expected in zip(size,expected_size)),(name,'Physical figure size')
        layout_entry=entry.get('alignment_qa');assert layout_entry,(name,'Rendered layout receipt missing')
        layout_path=RUN/'figures'/layout_entry['receipt'];layout= json.loads(layout_path.read_text(encoding='utf8'))
        assert sha(layout_path)==layout_entry['sha256'] and layout['passed']
        assert layout['tolerance_pt']==1.5,(name,'Layout tolerance changed')
        assert layout['minimum_visible_font_size_pt']>=8.,(name,'Font floor changed')
        formal=layout['formal_audit'];formal_path=RUN/'figures'/formal['path']
        assert sha(formal_path)==formal['sha256'],(name,'Formal alignment audit hash')
        formal_report=json.loads(formal_path.read_text(encoding='utf8'))
        assert formal_report['summary']['fail']==0,(name,'Formal panel alignment failure')
        assert formal_report['verdict'] in ['PASS','NOT APPLICABLE'],(name,'Alignment not validated')
        with base.with_suffix('.csv').open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
        assert len(rows)==entry['rows'] and rows,(name,'CSV row count')
        records=raw_records(entry['stage'])
        compare_csv_to_raw(name,rows,records)
        svg=ET.parse(base.with_suffix('.svg')).getroot()
        assert svg.tag.endswith('}svg') and not any(e.tag.endswith('}image') for e in svg.iter())
        listing=pdf_tool('pdfimages','-list',base.with_suffix('.pdf'))
        assert len(listing.strip().splitlines())==2,(name,'Embedded raster PDF')
        font_listing=pdf_tool('pdffonts',base.with_suffix('.pdf'));fonts=font_listing.strip().splitlines()[2:]
        assert fonts and 'Type 3' not in font_listing and all(row.split()[-5]=='yes' for row in fonts),(name,'PDF fonts')
        pdf_tool('pdftoppm','-r','100','-singlefile','-png',base.with_suffix('.pdf'),previews/name)
        with Image.open(previews/(name+'.png')) as picture:picture.verify()
        figures.append({'id':name,'pdf_rendered':True,'embedded_fonts':True,'vector_only':True,'png_dpi':list(dpi),
                        'png_size':list(size),'csv_rows':len(rows),'source_hashes_match':True,'output_hashes_match':True,
                        'physical_dimensions_match':True,'rendered_layout_receipt_verified':True,
                        'csv_values_recomputed_from_raw_results':True,'raw_source_executions':len(records),
                        'pdf_preview':(previews/(name+'.png')).relative_to(ROOT).as_posix()})
    # v21 did not register a fresh demonstration; historical v14 links are allowed.
    own_videos=sorted((RUN/'demo').glob('*/comparison.mp4'))
    assert not own_videos,'Unexpected new videos need a separate explicit physical-replay receipt'
    page=Links();page.feed((RUN/'index.html').read_text(encoding='utf8'));local=[]
    for value in page.links:
        parsed=urlsplit(value)
        if parsed.scheme or parsed.netloc or not parsed.path:continue
        target=local_path(RUN,unquote(parsed.path));assert target.exists(),value
        rel=target.relative_to(ROOT).as_posix()
        url=args.base_url.rstrip('/')+'/'+quote(rel,safe='/')
        with urlopen(url,timeout=15) as response:assert response.status==200,(value,response.status)
        local.append(rel)
    result={'passed':True,'python_parsed':len(code),'figures':figures,'videos':[],
            'new_videos_required':0,'new_videos_present':0,'historical_video_links':[p for p in local if p.endswith('.mp4')],
            'html_local_resources_http200':len(local),'local_resources':local,
            'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in [RUN/'index.html',RUN/'REPORT.md',RUN/'figures/CATALOG.json',Path(__file__).resolve()]},
            'note':'Local delivery checks only; no new evaluation samples. Historical video links are not new v21 demonstrations. Browser interaction and visual review are separate.'}
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
