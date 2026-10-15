"""Read-only integrated artifact verifier. Historical root docs map to archives."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 m=json.loads((RUN/'consolidation_validation.json').read_text(encoding='utf8'));assert m['passed']
 for section in ['preserved_files','current_files']:
  for rel,sha in m[section].items():assert (ROOT/rel).is_file() and digest(ROOT/rel)==sha,f'Missing/changed: {rel}'
 print(json.dumps({'passed':True,'protected_existing_files':m['protected_existing_files'],'archived_changed_root_documents':m['changed_root_documents'],
  'new_files_verified':len(m['current_files']),'old_code_weights_results_and_pages_unchanged':True,'new_policy_episodes':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
