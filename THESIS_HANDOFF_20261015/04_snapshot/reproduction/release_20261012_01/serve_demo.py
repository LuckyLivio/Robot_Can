"""Serve the local demonstration; no external network exposure or file writes."""
import argparse,functools
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);args=p.parse_args()
    assert (RUN/'demo/index.html').is_file(),'Generate the demo before starting its server.'
    handler=functools.partial(SimpleHTTPRequestHandler,directory=str(ROOT))
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler)
    print(f'Open http://127.0.0.1:{args.port}/reproduction/{RUN.name}/demo/index.html',flush=True)
    print('Local only. Press Ctrl+C to stop.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
