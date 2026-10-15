"""Audit existing results, source syntax, document links and frozen display data."""
import ast,collections,hashlib,json,math,re,subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
CONSOL=ROOT/'reproduction/consolidation_20261012_01'

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.ids=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if a.get('id'):self.ids.append(a['id'])
  self.links.extend(a[k] for k in ['href','src','srcset'] if a.get(k))

def check_link(p,link):
 s=urlsplit(link)
 if s.scheme or s.netloc:return False
 if not s.path:
  if p.suffix=='.html' and s.fragment:
   parser=Links();parser.feed(p.read_text(encoding='utf8'));assert s.fragment in parser.ids,link
  return False
 q=(p.parent/unquote(s.path)).resolve()
 if q in [RUN/'verification.json',RUN/'audit.json'] and not q.exists():return False
 assert q.exists(),f'Missing local link: {p.relative_to(ROOT)} -> {link}'
 return True

def records(path,expected=None):
 d=read(path);assert d['status']=='complete',path
 rows=d['records'];assert rows
 if expected is not None:assert [r['demo'] for r in rows]==expected,path
 for r in rows:assert isinstance(r['success'],bool) and 1<=r['steps']<=400,path
 return rows

def main():
 stages=[]
 multi=ROOT/'reproduction/multiseed_20261012_01';jobs=read(multi/'jobs.json');trains=0;evals=0;episodes=0;completion_hashes=0
 for j in jobs:
  receipt=read(multi/'completed'/f'{j["id"]}.json');assert receipt['status']=='complete'
  for rel,sha in receipt['output_sha256'].items():assert digest(ROOT/rel)==sha,rel;completion_hashes+=1
  assert all((ROOT/rel).is_file() for rel in j['outputs'])
  if j['phase']=='train':trains+=1
  else:evals+=1;episodes+=len(records(ROOT/j['outputs'][0]))
 stages.append({'stage':'multiseed','training_jobs':trains,'evaluation_jobs':evals,'existing_evaluation_episodes':episodes})
 core=[]
 for j in read(ROOT/'reproduction/confirmation_20261012_01/jobs.json'):
  rows=records(ROOT/j['outputs'][0]);assert len(rows)==60
  core.append({'method':j['method'],'seed':j['seed'],'noise':j['noise'],'successes':sum(r['success'] for r in rows),'episodes':60})
 stages.append({'stage':'original_confirmation','evaluation_jobs':len(core),'existing_evaluation_episodes':sum(r['episodes'] for r in core)})
 ext=ROOT/'reproduction/extensions_20261012_01';ejobs=read(ext/'jobs.json');ne=0
 for j in ejobs:
  ne+=len(records(ext/'evaluations'/j['id']/'result.json',j['demos']))
  receipt=read(ext/'completed'/f'{j["id"]}.json');assert receipt['status']=='complete'
  for rel,sha in receipt['outputs'].items():assert digest(ROOT/rel)==sha,rel;completion_hashes+=1
 stages.append({'stage':'extensions','evaluation_jobs':len(ejobs),'existing_evaluation_episodes':ne})
 matrix={};totals={}
 for version,stage_names in [('v2',['dev_a','confirmation','geometry_confirmation']),('v3',['dev_a','dev_b','dev_c','confirmation','geometry_confirmation']),('v4',['dev_a']),('v5',['dev_a','confirmation','geometry_confirmation'])]:
  for stage_name in stage_names:
   stage=ROOT/'reproduction'/f'recovery_{version}_20261012_01'/stage_name;jobs=read(stage/'jobs.json');nr=0
   for j in jobs:
    rows=records(stage/j['id']/'result.json',j['demos']);nr+=len(rows)
    if version=='v5' and stage_name=='confirmation':
     v=j['version'];g=totals.setdefault(v,{'successes':0,'episodes':0});g['successes']+=sum(r['success'] for r in rows);g['episodes']+=len(rows)
     m=matrix.setdefault(v,{'bc_clean':0,'bc_noise':0,'full_clean':0,'full_noise':0})
     m[('bc' if j['method']=='bc_k2' else 'full')+('_clean' if j['noise']==0 else '_noise')]+=sum(r['success'] for r in rows)
   stages.append({'stage':f'{version}/{stage_name}','evaluation_jobs':len(jobs),'existing_evaluation_episodes':nr})
 # V1 uses its original evaluation layout; verify every completed result file.
 v1=ROOT/'reproduction/recovery_20261012_01'
 v1jobs=read(v1/'formal_jobs.json');v1results=[];v1episodes=0
 for j in v1jobs:
  p=v1/'formal'/j['id']/'result.json';v1results.append(p);v1episodes+=len(records(p,j['demos']))
 stages.append({'stage':'v1/formal','evaluation_jobs':len(v1jobs),'existing_evaluation_episodes':v1episodes})
 e=read(CONSOL/'evidence.json');assert e['core']==core and e['v5_totals']==totals and e['v5_matrix']==matrix
 parsed=json.loads((CONSOL/'demo/evidence.js').read_text(encoding='utf8').strip().removeprefix('const EVIDENCE = ').removesuffix(';'));assert parsed==e
 for case in e['trajectory_cases']:
  for series in case['series']:
   p=ROOT/series['source'];assert digest(p)==series['trace_sha256']
   raw=[json.loads(line) for line in p.open(encoding='utf8') if f'"{case["demo"]}"' in line]
   raw=[r for r in raw if r['demo']==case['demo']];assert len(raw)==len(series['samples'])==series['steps']
   for a,b in zip(raw,series['samples']):
    assert a['step']==b['step'] and a['state_after'][:3]==b['eef'] and a['state_after'][16:19]==b['object']
    assert a['recovery']['mode']==b['phase'] and a['recovery']['stable_hold']==b['hold_observed']
    assert all(math.isfinite(x) for k in ['eef','object'] for x in b[k]) and 1<=b['step']<=400
 demo=json.loads((CONSOL/'demo/data.js').read_text(encoding='utf8').strip().removeprefix('const DEMO_DATA = ').removesuffix(';'))
 for c in demo['cases']:
  assert digest((CONSOL/'demo'/c['video']).resolve())==c['sha256']
 wm=read(CONSOL/'world_model_view.json');assert digest(ROOT/wm['source'])==wm['source_sha256'] and digest(ROOT/wm['confirmation_source'])==wm['confirmation_source_sha256']
 source=read(ROOT/wm['source'])
 for r in wm['rows']:
  matched=[x for x in source['rows'] if x['method']==r['method']]
  for k in ['normalized_state_mse','eef_position_rmse_m','object_position_rmse_m']:assert r[k]==sum(x[k] for x in matched)/len(matched)
 full=next(r for r in wm['rows'] if r['method']=='full');weak=next(r for r in wm['rows'] if r['method']=='persistence')
 assert wm['object_rmse_reduction_percent']==100*(1-full['object_position_rmse_m']/weak['object_position_rmse_m'])
 assert wm['confirmation_joint_effect'] in read(ROOT/wm['confirmation_source'])['paired']
 refs=read(CONSOL/'references_metadata.json');bib=(CONSOL/'references_verified.bib').read_text(encoding='utf8');assert len(refs)==8
 for r in refs:assert r['key'] in bib and r['title'] in bib and r['url'] in bib
 links=0
 docs=list(ROOT.glob('*.md'))+[p for base in [CONSOL,RUN] for p in base.rglob('*.md') if 'before' not in p.parts and 'previous_documents' not in p.parts]
 for p in docs:
  for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):links+=check_link(p,link)
 p=CONSOL/'demo/index.html';parser=Links();parser.feed(p.read_text(encoding='utf8'));assert len(parser.ids)==len(set(parser.ids))
 for link in parser.links:links+=check_link(p,link)
 syntax=subprocess.check_output(['rg','--files','-g','*.py','-g','!.venv/**'],cwd=ROOT,text=True,encoding='utf8').splitlines()
 for rel in syntax:ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'),filename=rel)
 result={'passed':True,'stages':stages,'completed_output_hashes_checked':completion_hashes,'v1_result_files':len(v1results),
  'python_source_files_parsed':len(syntax),'local_links_checked':links,'videos_verified':6,'trace_cases_verified':3,'references_checked':8,
  'v5_confirmation_totals':totals,'policy_or_physics_runs':0,'new_training_jobs':0,
  'scope':'File, syntax, recorded-result and local document audit. Completed experiments were not rerun; conditional stopped pilots are preserved.'}
 write(RUN/'audit.json',result);print(json.dumps({k:v for k,v in result.items() if k!='stages'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
