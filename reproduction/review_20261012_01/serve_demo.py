"""Serve the current presentation locally; no writes or public binding."""
import argparse,functools
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);args=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),functools.partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
    print(f'Open http://127.0.0.1:{args.port}/reproduction/{RUN.name}/demo/index.html',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
