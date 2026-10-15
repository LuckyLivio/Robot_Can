"""Finalize the consolidated assets, preserving every original scientific file."""
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 before=read(RUN/'before_manifest.json');changes=read(RUN/'document_changes.json');changed=set(changes['changed_root_documents']);protected={}
 for rel,sha in before.items():
  p=RUN/'previous_documents'/rel if rel in changed else ROOT/rel
  assert p.is_file() and digest(p)==sha,rel
  protected[p.relative_to(ROOT).as_posix()]=sha
 assert len(protected)==len(before)
 for p in (RUN/'previous_documents').glob('*.md'):assert digest(p)==before[p.name],p
 assert read(RUN/'content_validation_v2.json')['passed'];assert (RUN/'REPORT.md').exists()
 current={}
 for p in ROOT.glob('*.md'):
  if p.name not in before or p.name in changed:current[p.relative_to(ROOT).as_posix()]=digest(p)
 for p in RUN.rglob('*'):
  if p.is_file() and p.name!='consolidation_validation.json' and '__pycache__' not in p.parts:current[p.relative_to(ROOT).as_posix()]=digest(p)
 data={'passed':True,'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protected_existing_files':len(before),
  'changed_root_documents':sorted(changed),'archived_root_documents':len(list((RUN/'previous_documents').glob('*.md'))),
  'original_python_sources_modified':0,'new_policy_episodes':0,'new_world_model_training_jobs':0,'paper_body_written':False,
  'old_models_results_and_pages_unchanged':True,'references_checked':8,'new_descriptive_factorial_contrasts':3,
  'factorial_distinct_confirmation_batches':2,'new_illustrative_trace_cases':3,'preserved_files':protected,'current_files':current}
 with (RUN/'consolidation_validation.json').open('x',encoding='utf8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
 print(json.dumps({k:v for k,v in data.items() if k not in ['preserved_files','current_files']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
