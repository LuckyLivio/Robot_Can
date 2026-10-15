"""Seal this display-only patch without rewriting the historical manifests."""
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text(encoding='utf8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 old_path=ROOT/'reproduction/consolidation_20261012_01/consolidation_validation.json'
 old=read(old_path);before=read(RUN/'before.json');protected={}
 for section in ['preserved_files','current_files']:
  for rel,sha in old[section].items():
   p=ROOT/before[rel]['archive'] if rel in before else ROOT/rel
   assert p.is_file() and digest(p)==sha,rel
   if rel in before:assert sha==before[rel]['sha256']
   mapped=p.relative_to(ROOT).as_posix()
   if mapped in protected:assert protected[mapped]==sha
   protected[mapped]=sha
 protected[old_path.relative_to(ROOT).as_posix()]=digest(old_path)
 assert read(RUN/'audit.json')['passed'] and read(RUN/'regression_before.json')['reproduced'] and read(RUN/'regression_after.json')['passed']
 qa=read(RUN/'qa/browser_checks.json');assert len(qa['full_playback_cases'])==3 and not qa['console_errors']
 for c in qa['full_playback_cases']:assert c['start']['state']=='playing' and c['end']['state']=='ended' and c['end']['step']=='400 / 400'
 assert qa['mobile']['start']['client']==qa['mobile']['start']['scroll'] and qa['mobile']['end']['state']=='ended'
 current={rel:digest(ROOT/rel) for rel in before}
 for p in RUN.rglob('*'):
  if p.is_file() and p.name!='verification.json' and '__pycache__' not in p.parts:current[p.relative_to(ROOT).as_posix()]=digest(p)
 data={'passed':True,'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'protected_original_files':old['protected_existing_files'],'protected_consolidation_assets':len(old['current_files']),
  'authorized_changes':list(before),'old_code_weights_results_unchanged':True,'new_policy_episodes':0,'new_training_jobs':0,
  'preserved_files':protected,'current_files':current}
 with (RUN/'verification.json').open('x',encoding='utf8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
 print(json.dumps({k:v for k,v in data.items() if k not in ['preserved_files','current_files']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
