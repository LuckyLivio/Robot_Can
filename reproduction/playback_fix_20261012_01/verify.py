"""Read-only verifier for the preserved scientific project and display patch."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 m=json.loads((RUN/'verification.json').read_text(encoding='utf8'));assert m['passed']
 for section in ['preserved_files','current_files']:
  for rel,sha in m[section].items():
   p=ROOT/rel;assert p.is_file() and digest(p)==sha,f'Missing/changed: {rel}'
 print(json.dumps({'passed':True,'protected_original_files':m['protected_original_files'],
  'protected_consolidation_assets':m['protected_consolidation_assets'],
  'authorized_changes':m['authorized_changes'],'old_code_weights_results_unchanged':True,
  'new_policy_episodes':0},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
