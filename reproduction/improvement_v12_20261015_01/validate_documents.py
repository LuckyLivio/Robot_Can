"""Check local links in the active documents and v12 reports without editing."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json, re

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]

if __name__ == '__main__':
    changed = json.loads((RUN / 'document_changes.json').read_text())['updated']
    paths = [ROOT / p for p in changed if p.endswith('.md')]
    paths += [RUN / 'README.md', RUN / 'REPORT.md', RUN / 'protocols/PLAN.md']
    checked, missing = [], []
    for p in paths:
        for target in re.findall(r'!?\[[^\]]*\]\(([^)\n]+)\)', p.read_text(encoding='utf8')):
            target = target.strip().strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme or not parsed.path:
                continue
            item = {'document': p.relative_to(ROOT).as_posix(), 'target': target}
            checked.append(item)
            if not (p.parent / unquote(parsed.path)).exists():
                missing.append(item)
    root_index = (ROOT / 'index.html').read_text(encoding='utf8')
    assert 'reproduction/improvement_v12_20261015_01/index.html' in root_index
    result = {'passed': not missing, 'documents': len(paths),
              'local_links_checked': len(checked), 'missing': missing,
              'root_redirect_targets_v12': True}
    (RUN / 'validation/documents.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(result))
    assert not missing, missing
