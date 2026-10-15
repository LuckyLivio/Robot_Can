"""Reconcile final build pointers, validate active links, and freeze this delivery."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import ast
import json
import re
import shutil
import subprocess
from portable import digest, verify

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]


def main():
    frozen = json.loads((RUN / 'baseline.json').read_text())
    for p in [RUN / 'README.md', RUN / 'index.html', RUN / 'update_documents.py']:
        p.write_text(p.read_text(encoding='utf8').replace('release_01', 'release_02'), encoding='utf8')
    p = RUN / 'REPORT.md'
    p.write_text(p.read_text(encoding='utf8').replace('287,185,635', '287,185,453'), encoding='utf8')
    shutil.copy2(RUN / 'builds/release_02/BUILD_RECEIPT.json', RUN / 'BUILD_RECEIPT.json')
    shutil.copy2(RUN / 'validation/relocated/run_03/validation.json', RUN / 'package_validation.json')
    for kind, name in [('demo', 'CAN_LAB_DEMO'), ('writing', 'CAN_LAB_WRITING_ADDENDUM')]:
        verify(RUN / 'builds/release_02' / name)
        shutil.copy2(RUN / 'builds/release_02' / name / 'PACKAGE_MANIFEST.json', RUN / 'package_manifests' / (kind + '.json'))
    shutil.copy2(RUN / 'builds/TRANSFER_TO_NEW_DEVICE/TRANSFER_MANIFEST.json', RUN / 'package_manifests/transfer.json')
    transfer = json.loads((RUN / 'transfer_receipt.json').read_text(encoding='utf-8-sig'))
    old_zip = json.loads((ROOT / 'reproduction/project_audit_20261015_01/zip_validation.json').read_text())
    old_hash = next(r['sha256'] for r in old_zip['files'] if r['path'].endswith('_WRITING.zip'))
    if transfer['archives'][0]['sha256'] != old_hash:
        raise ValueError('Original writing ZIP differs')
    for row in transfer['archives']:
        if digest(RUN / 'builds/TRANSFER_TO_NEW_DEVICE' / row['path']) != row['sha256']:
            raise ValueError('Transfer copy differs')
    # Demo content is identical to the already browser-tested package; ZIP timestamps may differ.
    compared = json.loads((RUN / 'package_manifests/demo_browser_tested.json').read_text())
    final = json.loads((RUN / 'package_manifests/demo.json').read_text())
    if compared != final:
        raise ValueError('Final demo content changed after browser testing')
    browser = json.loads((RUN / 'browser_validation.json').read_text())
    browser['final_demo_manifest_sha256'] = digest(RUN / 'package_manifests/demo.json')
    browser['final_demo_matches_tested_content'] = True
    (RUN / 'browser_validation.json').write_text(json.dumps(browser, ensure_ascii=False, indent=2), encoding='utf8')
    files = [p for p in RUN.rglob('*') if p.is_file() and not any(x in p.relative_to(RUN).parts for x in ['builds', 'validation', 'outputs', '__pycache__'])]
    for p in files:
        if p.suffix == '.py':
            ast.parse(p.read_text(encoding='utf-8-sig'))
    links = []
    class Parser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            links.extend((self.file, v) for k, v in attrs if k in {'src', 'href', 'poster'} and v)
    active = [ROOT / p for p in frozen['authorized_documents']] + [RUN / n for n in ['README.md', 'REPORT.md', 'TARGET_DEVICE_CHECKLIST.md', 'index.html']]
    for p in active:
        text = p.read_text(encoding='utf-8-sig')
        if p.suffix == '.md':
            links.extend((p, link) for link in re.findall(r'\]\(([^)]+)\)', text))
        else:
            parser = Parser(); parser.file = p; parser.feed(text)
    count = 0
    for source, target in links:
        url = urlsplit(target)
        if url.scheme or not url.path:
            continue
        if not (source.parent / unquote(url.path)).exists():
            raise ValueError('Active link missing: ' + str(source) + ' -> ' + target)
        count += 1
    for p in (RUN / 'builds/release_02/CAN_LAB_DEMO').glob('*.js'):
        subprocess.run([shutil.which('node'), '--check', str(p)], capture_output=True, check=True)
    receipt = {'passed': True, 'active_local_links': count, 'new_python_files_parse': True,
               'demo_javascript_syntax_passed': True, 'old_writing_zip_unchanged': True,
               'final_build': 'release_02', 'new_simulation_episodes': 0,
               'actual_second_device_validated': False, 'v12_implemented': False}
    (RUN / 'completion_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    exclude = {'DELIVERY_MANIFEST.json', 'integrity_receipt.json'}
    current = {p.relative_to(ROOT).as_posix(): digest(p) for p in RUN.rglob('*')
               if p.is_file() and p.name not in exclude
               and not any(x in p.relative_to(RUN).parts for x in ['builds', 'validation', 'outputs', '__pycache__'])}
    current.update({rel: digest(ROOT / rel) for rel in frozen['authorized_documents']})
    (RUN / 'DELIVERY_MANIFEST.json').write_text(json.dumps({'files': current}, indent=2), encoding='utf8')
    print(json.dumps({**receipt, 'delivery_files': len(current)}))


if __name__ == '__main__':
    main()
