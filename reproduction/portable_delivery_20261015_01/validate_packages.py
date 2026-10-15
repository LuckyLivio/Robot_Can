"""Extract into a new Unicode/space path and test with a clean stdlib-only venv."""
from pathlib import Path
from html.parser import HTMLParser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit, unquote, quote
import argparse
import importlib.util
import json
import subprocess
import sys
import urllib.request
import zipfile
from portable import digest, verify
import launcher

RUN = Path(__file__).resolve().parent


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        self.links.extend(v for k, v in attrs if k in {'src', 'href', 'poster'} and v)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    build = args.build.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    relocated = out / '新设备 验证'
    relocated.mkdir()
    env = relocated / 'fresh_stdlib_env'
    subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(env)], check=True)
    py = env / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    no_torch = subprocess.check_output([str(py), '-c', "import importlib.util; print(importlib.util.find_spec('torch') is None)"], text=True).strip()
    if no_torch != 'True':
        raise ValueError('The presentation test environment is not isolated')
    records = []
    for archive in sorted(build.glob('*.zip')):
        sidecar = archive.with_suffix('.zip.sha256').read_text().split()[0]
        if digest(archive) != sidecar:
            raise ValueError('Archive SHA mismatch')
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                if not (relocated / member.filename).resolve().is_relative_to(relocated):
                    raise ValueError('Unsafe ZIP member')
            if z.testzip():
                raise ValueError('ZIP CRC mismatch')
            z.extractall(relocated)
        package = relocated / archive.stem
        cp = subprocess.run([str(py), '-B', str(package / 'portable.py'), 'verify'],
                            cwd=out, text=True, capture_output=True, check=True)
        receipt = json.loads(cp.stdout)
        local_links = set()
        for file in package.rglob('*.html'):
            parser = Links()
            parser.feed(file.read_text(encoding='utf8'))
            for link in parser.links:
                u = urlsplit(link)
                if u.scheme or not u.path:
                    continue
                target = (file.parent / unquote(u.path)).resolve()
                if not target.is_relative_to(package) or not target.is_file():
                    raise ValueError('Broken local HTML link: ' + str(file) + ' -> ' + link)
                local_links.add(target.relative_to(package).as_posix())
        media = []
        js = package / 'media-data.js'
        if js.exists():
            cases = json.loads(js.read_text(encoding='utf8').split('=', 1)[1].rstrip(';'))
            for c in cases:
                for k in ['video', 'poster']:
                    target = package / c[k]
                    if not target.is_file():
                        raise ValueError('Missing dynamic media')
                    local_links.add(c[k])
                media.append(c['video'])
        handler = partial(QuietHandler, directory=str(package))
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for rel in ['index.html', *sorted(local_links)]:
                req = urllib.request.Request(f'http://127.0.0.1:{server.server_port}/' + quote(rel), method='HEAD')
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status != 200:
                        raise ValueError('HTTP asset failed')
        finally:
            server.shutdown(); server.server_close(); thread.join()
        # Detect a corrupted byte; restore only the disposable extracted copy.
        sample = package / 'README.md'
        before = sample.read_bytes()
        sample.write_bytes(before + b'\nTAMPER_TEST\n')
        rejected = False
        try:
            verify(package)
        except ValueError:
            rejected = True
        finally:
            sample.write_bytes(before)
        if not rejected:
            raise ValueError('Tamper detection failed')
        verify(package)
        records.append({**receipt, 'zip_sha256': digest(archive), 'local_html_links': len(local_links),
                        'dynamic_videos': len(media), 'http_head_passed': True,
                        'tamper_detection_passed': rejected, 'relocated_package': str(package)})
    # Test default commands and rerun planning without ever calling a simulator.
    cp = subprocess.run([sys.executable, '-B', str(RUN / 'launcher.py')], capture_output=True, text=True, check=True)
    if 'usage:' not in cp.stdout:
        raise ValueError('Default must show help')
    plans = []
    for name in launcher.EXPERIMENTS:
        dest = RUN / 'outputs' / ('selftest_' + name)
        result = launcher.plan(name, dest)
        if dest.exists() or any(c[0] != sys.executable for c in result['commands']):
            raise ValueError('Dry-run mutated output or used another interpreter')
        plans.append({'experiment': name, 'episodes': result['episodes'], 'jobs': len(result['jobs']), 'output_created': False})
    rejected = []
    for label, destination, job in [('existing', out, None), ('protected_repo', launcher.ROOT / 'models/new_attempt', None),
                                   ('invalid_job', RUN / 'outputs/invalid_job', 'missing_job')]:
        try:
            launcher.plan('v11-development', destination, job)
        except (ValueError, FileExistsError):
            rejected.append(label)
    if len(rejected) != 3:
        raise ValueError('Rerun path/job guards failed')
    receipt = {'passed': True, 'packages': records, 'clean_stdlib_environment_has_no_torch': True,
               'plans': plans, 'rejected_invalid_requests': rejected, 'simulation_episodes': 0,
               'actual_second_device_tested': False,
               'scope': 'Same-machine clean stdlib venv and relocated paths; HTTP availability, hashes and launcher dry-run. Browser playback is separate.'}
    (out / 'validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
