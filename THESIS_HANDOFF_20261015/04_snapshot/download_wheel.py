"""Parallel HTTP-range download, verified against publisher-provided SHA256."""
import argparse
import concurrent.futures
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import unquote

import requests

ROOT=Path(__file__).resolve().parent


def main(args):
    if args.torch:
        index='https://download.pytorch.org/whl/cu126/torch/'
        body=requests.get(index,timeout=30).text
        links=re.findall(r'href="([^"]+)"',body)
        link=next(x for x in links if 'torch-2.6.0%2Bcu126-cp310-cp310-win_amd64.whl' in x)
        url,expected=link.split('#sha256=')
        filename=unquote(url.rsplit('/',1)[-1])
        probe=requests.get(url,headers={'Range':'bytes=0-0'},timeout=30)
        probe.raise_for_status()
        size=int(probe.headers['Content-Range'].split('/')[-1])
    else:
        meta=requests.get(f'https://pypi.org/pypi/{args.package}/{args.version}/json',timeout=30).json()
        item=next(x for x in meta['urls'] if x['filename'].endswith('py3-none-any.whl'))
        url=item['url']; expected=item['digests']['sha256']; size=item['size'];filename=item['filename']
    out=ROOT.parents[1]/'tmp/robot_bootstrap'/filename
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists() and hashlib.sha256(out.read_bytes()).hexdigest()==expected:
        print('cached',out,flush=True);return
    partial=out.with_suffix('.partial')
    with partial.open('wb') as f:
        f.truncate(size)
    chunk=8*1024*1024
    jobs=[(start,min(start+chunk,size)-1) for start in range(0,size,chunk)]
    def fetch(job):
        start,end=job
        for attempt in range(4):
            try:
                r=requests.get(url,headers={'Range':f'bytes={start}-{end}'},timeout=(30,90))
                r.raise_for_status()
                if r.status_code!=206 or len(r.content)!=end-start+1:
                    raise RuntimeError('Range response mismatch')
                with partial.open('r+b') as f:
                    f.seek(start);f.write(r.content)
                return len(r.content)
            except Exception:
                if attempt==3:raise
                time.sleep(1+attempt)
    completed=0;started=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for fut in concurrent.futures.as_completed([pool.submit(fetch,job) for job in jobs]):
            completed+=fut.result()
            print(f'{filename}: {completed/size:.0%} {completed/1024**2:.0f} MiB, {time.perf_counter()-started:.1f}s',flush=True)
    h=hashlib.sha256()
    with partial.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    if h.hexdigest()!=expected:raise RuntimeError('Publisher SHA256 mismatch')
    partial.replace(out)
    out.with_suffix('.manifest.json').write_text(json.dumps({'url':url,'sha256':expected,'bytes':size},indent=2),encoding='utf-8')
    print('verified',out,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--package',default='robosuite');p.add_argument('--version',default='1.5.1')
    p.add_argument('--workers',type=int,default=8);p.add_argument('--torch',action='store_true')
    main(p.parse_args())
