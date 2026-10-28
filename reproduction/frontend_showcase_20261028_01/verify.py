"""Verify the static showcase and evidence provenance without running research."""
import csv,hashlib,json,re,subprocess
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASELINE='30cf534292432979e0fd5e3591e5d164649e0351'
NODE=Path('C:/Users/Livio/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
errors=[]
def check(ok,message):
    if not ok:errors.append(message)
def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()
class Page(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.urls=[];self.h1=0
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        for key in ('src','href','poster'):
            if attrs.get(key):self.urls.append(attrs[key])
        if tag=='h1':self.h1+=1
page=Page();page.feed((ROOT/'index.html').read_text(encoding='utf-8'))
check(len(page.ids)==len(set(page.ids)),'Duplicate DOM IDs')
check(page.h1==1,'Single page heading')
local=[]
for url in page.urls:
    parts=urlsplit(url)
    if parts.scheme or parts.netloc:continue
    if not parts.path:
        check(not parts.fragment or parts.fragment in page.ids,'Missing section: '+url);continue
    path=(ROOT/unquote(parts.path)).resolve();local.append(path)
    check(path.is_relative_to(ROOT) and path.is_file(),'Broken local link: '+url)
manifest=json.loads((ROOT/'web/data_manifest.json').read_text(encoding='utf-8'))
for name,record in {**manifest['inputs'],**manifest['outputs']}.items():
    check(sha(ROOT/name)==record['sha256'],'Source/output digest changed: '+name)
check((ROOT/'web/data.js').stat().st_size<500*1024,'Display data budget exceeded')
node=NODE if NODE.is_file() else 'node'
subprocess.run([str(node),'--check',str(ROOT/'web/app.js')],check=True,capture_output=True)
javascript='''const fs=require('fs'),vm=require('vm'),c={window:{}};vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),c);const d=c.window.CANLAB_DATA;for(const q of d.cases){for(const r of q.runs){if(r.method!=='full'||r.seed!==17||r.frames.length!==r.steps)throw Error('Case identity');r.frames.forEach((f,i)=>{if(f.step!==i+1||f.eef.length!==3||f.object.length!==3||f.queue.length!==2||f.queue.some(a=>a.length!==7)||f.executed.length!==7||f.submitted.length!==7)throw Error('Frame contract')});}}console.log(JSON.stringify({cells:d.cells.length,effects:d.effects.length,cases:d.cases.length,runs:d.cases.reduce((n,c)=>n+c.runs.length,0),frames:d.cases.reduce((n,c)=>n+c.runs.reduce((m,r)=>m+r.frames.length,0),0),independent_starts:d.meta.independent_starts,full:d.cells.filter(c=>c.policy==='full'&&c.controller==='v5').reduce((n,c)=>n+c.successes,0),bc:d.cells.filter(c=>c.policy==='bc'&&c.controller==='v5').reduce((n,c)=>n+c.successes,0)}));'''
counts=json.loads(subprocess.check_output([str(node),'-e',javascript,str(ROOT/'web/data.js')],encoding='utf-8'))
check(counts=={'cells':12,'effects':117,'cases':3,'runs':6,'frames':1672,'independent_starts':60,'full':352,'bc':119},'Evidence totals mismatch')
for name in ('index.html','README.md'):
    prior=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT)
    check((HERE/'before'/name).read_bytes()==prior,'Before snapshot differs: '+name)
changed=subprocess.check_output(['git','diff','--name-only','-z',BASELINE],cwd=ROOT).decode('utf-8').split('\0')
outside=[p for p in changed if p and p not in ('index.html','README.md') and not p.startswith(('web/','reproduction/frontend_showcase_20261028_01/'))]
check(not outside,'Unrelated tracked changes')
for name in ('desktop.png','replay.png','mobile.png'):check((HERE/'validation'/name).is_file(),'Missing browser proof: '+name)
receipt=json.loads((HERE/'validation/browser_checks.json').read_text(encoding='utf-8'))
ui_checks=receipt['statistics_ui_checks']
check(len(ui_checks)==12,'Browser statistics coverage')
with (ROOT/'reproduction/graduation_repairs_20261022_01/analysis/confirmation/cells.csv').open(encoding='utf-8',newline='') as f:
    original_cells=list(csv.DictReader(f))
for item in ui_checks:
    rows=[c for c in original_cells if c['method']==item['policy'] and c['controller']=='v5'
          and (item['noise']=='joint' or float(c['noise'])==float(item['noise']))]
    key='successes' if item['metric']=='success' else 'stable_successes'
    expected=f"{100*sum(int(c[key]) for c in rows)/sum(int(c['executions']) for c in rows):.2f}%"
    check(item['rate']==expected,'Browser displayed rate differs from source CSV')
media=['reproduction/release_20261012_01/render_probe_visual.png',
       'reproduction/progress_20261015_01/demo/videos20/clean_full_only_success.mp4',
       'reproduction/progress_20261015_01/demo/videos20/clean_full_only_success.png']
report={'passed':not errors,'errors':errors,'verified_utc':datetime.now(timezone.utc).isoformat(),'baseline':BASELINE,
        'scope':'Static presentation frontend only; no training or simulation','local_asset_links_checked':len(local),
        'unique_dom_ids':len(page.ids),'data_input_digests_checked':len(manifest['inputs']),'data_output_digests_checked':len(manifest['outputs']),
        'evidence_counts':counts,'data_js_bytes':(ROOT/'web/data.js').stat().st_size,
        'browser_test_receipt':'validation/browser_checks.json','browser_statistics_combinations_checked':len(ui_checks),
        'browser_console_errors':receipt['console_errors'],'browser_console_warnings':receipt['console_warnings'],
        'media_source_sha256':{name:sha(ROOT/name) for name in media},
        'research_changes_outside_frontend':outside,'offline_file_protocol':'Not tested: browser security policy allows HTTP/HTTPS only; no workaround attempted',
        'final_outputs_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in [ROOT/'index.html',ROOT/'web/styles.css',ROOT/'web/app.js',ROOT/'web/data.js']}}
(HERE/'quality_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':not errors,'errors':errors,'links':len(local),'source_hashes':len(manifest['inputs']),**counts},ensure_ascii=False))
raise SystemExit(1 if errors else 0)
