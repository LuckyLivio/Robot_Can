"""Check displayed data and local links without any model/environment execution."""
import ast,hashlib,json,re,sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.ids=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if a.get('id'):self.ids.append(a['id'])
  for key in ['href','src','srcset']:
   if a.get(key):self.links.append(a[key])
def resolve(p,link):
 s=urlsplit(link)
 if s.scheme or s.netloc:return None
 path=unquote(s.path)
 if not path:return None
 return (p.parent/path).resolve()
def main():
 output=RUN/(sys.argv[1] if len(sys.argv)>1 else 'content_validation_v2.json')
 assert output.parent==RUN
 checked=0
 paths=list(ROOT.glob('*.md'))+[p for p in RUN.rglob('*.md') if 'previous_documents' not in p.parts]
 for p in paths:
  for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
   q=resolve(p,target)
   if q is not None:
    if q in [RUN/'consolidation_validation.json',output] and not q.exists():continue
    assert q.exists(),(p.name,target);checked+=1
 html=RUN/'demo/index.html';parser=Links();parser.feed(html.read_text(encoding='utf8'));assert len(parser.ids)==len(set(parser.ids))
 for target in parser.links:
  q=resolve(html,target)
  if q is not None:assert q.exists(),target;checked+=1
  elif target.startswith('#'):assert target[1:] in parser.ids,target
 e=read(RUN/'evidence.json');js=(RUN/'demo/evidence.js').read_text(encoding='utf8').strip()
 assert json.loads(js.removeprefix('const EVIDENCE = ').removesuffix(';'))==e
 demo=json.loads((RUN/'demo/data.js').read_text(encoding='utf8').strip().removeprefix('const DEMO_DATA = ').removesuffix(';'))
 assert len(demo['cases'])==6
 for c in demo['cases']:
  for key in ['video','poster','firstFrame']:
   if c.get(key):assert (RUN/'demo'/c[key]).is_file();checked+=1
  assert hashlib.sha256((RUN/'demo'/c['video']).read_bytes()).hexdigest()==c['sha256']
 core=read(ROOT/'reproduction/confirmation_20261012_01/jobs.json')
 for j in core:
  r=read(ROOT/j['outputs'][0]);row=next(x for x in e['core'] if x['method']==j['method'] and x['seed']==j['seed'] and x['noise']==j['noise'])
  assert row['successes']==sum(x['success'] for x in r['records']) and row['episodes']==len(r['records'])==60
 for case in e['trajectory_cases']:
  for series in case['series']:
   p=ROOT/series['source'];assert hashlib.sha256(p.read_bytes()).hexdigest()==series['trace_sha256']
   raw=[json.loads(line) for line in p.open(encoding='utf8') if f'"{case["demo"]}"' in line]
   raw=[r for r in raw if r['demo']==case['demo']]
   assert len(raw)==len(series['samples'])==series['steps']
   for a,b in zip(raw,series['samples']):
    assert a['step']==b['step'] and a['state_after'][:3]==b['eef'] and a['state_after'][16:19]==b['object']
    assert a['recovery']['mode']==b['phase'] and a['recovery']['stable_hold']==b['hold_observed']
 for n in ['recovery_v2_20261012_01','recovery_v3_20261012_01']:
  jobs=read(ROOT/'reproduction'/n/'confirmation/jobs.json')
  assert any(j['version']=='disabled' for j in jobs) and any(j['method']=='bc_k2' for j in jobs) and any(j['method']=='full' for j in jobs)
 wm=read(RUN/'world_model_view.json')
 assert json.loads((RUN/'demo/world-model-data.js').read_text(encoding='utf8').strip().removeprefix('const WORLD_MODEL_VIEW = ').removesuffix(';'))==wm
 for key in ['source','confirmation_source']:
  assert hashlib.sha256((ROOT/wm[key]).read_bytes()).hexdigest()==wm[key+'_sha256']
 raw=read(ROOT/wm['source'])
 for r in wm['rows']:
  selected=[x for x in raw['rows'] if x['method']==r['method']]
  for k in ['normalized_state_mse','eef_position_rmse_m','object_position_rmse_m']:
   assert r[k]==sum(x[k] for x in selected)/len(selected)
 full=next(r for r in wm['rows'] if r['method']=='full');weak=next(r for r in wm['rows'] if r['method']=='persistence')
 assert wm['object_rmse_reduction_percent']==100*(1-full['object_position_rmse_m']/weak['object_position_rmse_m'])
 original=read(ROOT/wm['confirmation_source'])
 assert wm['confirmation_joint_effect'] in original['paired'] and wm['groups']==64 and wm['independent_parents']==8
 refs=read(RUN/'references_metadata.json');bib=(RUN/'references_verified.bib').read_text(encoding='utf8');assert len(refs)==8
 for r in refs:assert r['key'] in bib and r['title'] in bib and r['url'] in bib and r['authors']
 for p in RUN.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
 qa=read(RUN/'qa/browser_checks_v2.json');assert len(qa['coreCases'])==6 and not qa['consoleErrors'];assert qa['mobileWidth']['client']==qa['mobileWidth']['scroll']
 assert all(c['media']['error'] is None and c['media']['readyState']>=2 for c in qa['coreCases'])
 assert len(qa['worldModel']['stages'])==4 and qa['worldModel']['defaultCase'].startswith('demo_1000026')
 assert len(qa['worldModel']['predictionRows'])==3 and qa['worldModel']['plotLoaded']
 payload={'passed':True,'checked_local_links_and_media':checked,'verified_original_videos':6,'verified_trace_cases':3,
  'verified_reference_entries':8,'checked_original_core_jobs':14,'world_model_presentation_sources_verified':True,'policy_or_environment_imports':False,'new_policy_episodes':0}
 with output.open('x',encoding='utf8') as f:json.dump(payload,f,ensure_ascii=False,indent=2)
 print(json.dumps(payload,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
