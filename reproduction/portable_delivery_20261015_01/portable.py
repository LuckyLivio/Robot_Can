"""Standard-library package verification and a loopback-only demo server."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse
import hashlib
import json
import sys
import webbrowser


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'PACKAGE_MANIFEST.json').read_text(encoding='utf8'))
    for item in manifest['files']:
        p = (root / item['path']).resolve()
        if not p.is_relative_to(root) or not p.is_file():
            raise ValueError('Missing or unsafe package path: ' + item['path'])
        if p.stat().st_size != item['bytes'] or digest(p) != item['sha256']:
            raise ValueError('Package content differs: ' + item['path'])
    return {'passed': True, 'profile': manifest['profile'],
            'files': len(manifest['files']), 'source_commit': manifest['source_commit']}


def serve(root, port, open_browser=False):
    root = Path(root).resolve()
    if not (root / 'index.html').is_file():
        raise ValueError('This directory has no index.html')
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    with ThreadingHTTPServer(('127.0.0.1', port), handler) as server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print('Open: ' + url + '\nPress Ctrl+C to stop.', flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command')
    sub.add_parser('verify', help='Hash all package files; no simulation.')
    server = sub.add_parser('serve', help='Serve this package on localhost.')
    server.add_argument('--port', type=int, default=8767)
    server.add_argument('--open', action='store_true')
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    root = Path(__file__).resolve().parent
    if args.command == 'verify':
        print(json.dumps(verify(root), ensure_ascii=False))
    else:
        verify(root)
        serve(root, args.port, args.open)


if __name__ == '__main__':
    main()
