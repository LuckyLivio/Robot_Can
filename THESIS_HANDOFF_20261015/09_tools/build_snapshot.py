"""Copy the frozen Git snapshot and gzip existing step logs. No experiments."""
from pathlib import Path
import concurrent.futures,csv,gzip,hashlib,json,shutil,subprocess,time
PACK=Path(__file__).resolve().parents[1]
ROOT=PACK.parent
BASE='c8bbe86d0bd760524afb946a2c9220641a0872f0'
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    tree=subprocess.check_output(['git','ls-tree','-r','-z',BASE],cwd=ROOT)
    files=[]
    for entry in tree.split(b'\0'):
        if entry:
            meta,rel=entry.split(b'\t',1)
            files.append((rel.decode('utf8'),meta.decode().split()[2]))
    def one(item):
        rel,blob=item; src=ROOT/rel; istrace=rel.endswith('.jsonl')
        target=PACK/('08_full_traces_gzip' if istrace else '04_snapshot')/(rel+'.gz' if istrace else rel)
        target.parent.mkdir(parents=True,exist_ok=True)
        assert not target.exists(),target
        h=hashlib.sha256();lines=0
        if istrace:
            with src.open('rb') as source,target.open('xb') as stored:
                with gzip.GzipFile(filename='',fileobj=stored,mode='wb',compresslevel=6,mtime=0) as zipped:
                    for chunk in iter(lambda:source.read(1024*1024),b''):
                        h.update(chunk);lines+=chunk.count(b'\n');zipped.write(chunk)
        else:
            shutil.copy2(src,target);h.update(src.read_bytes())
        return {'source_repo_path':rel,'git_blob_sha1':blob,'original_sha256':h.hexdigest(),
                'original_bytes':src.stat().st_size,'storage':'gzip' if istrace else 'copy',
                'package_path':target.relative_to(PACK).as_posix(),'stored_bytes':target.stat().st_size,
                'stored_sha256':digest(target),'jsonl_line_count':lines if istrace else ''}
    result=[];start=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for i,row in enumerate(pool.map(one,files),1):
            result.append(row)
            if i%250==0:print(f'Copied/compressed {i}/{len(files)} frozen files',flush=True)
    out=PACK/'07_provenance';out.mkdir(exist_ok=True)
    with (out/'SOURCE_ASSETS.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
    info={'source_repository':'https://github.com/LuckyLivio/Robot_can','source_commit':BASE,
          'frozen_files':len(result),'copied_files':sum(r['storage']=='copy' for r in result),
          'gzip_trace_files':sum(r['storage']=='gzip' for r in result),
          'original_bytes':sum(r['original_bytes'] for r in result),'stored_bytes':sum(r['stored_bytes'] for r in result),
          'scope':'Original tracked project files copied byte-for-byte; JSONL losslessly gzip-compressed. No training or rollout.',
          'new_training_steps':0,'new_simulation_episodes':0,'elapsed_seconds':time.perf_counter()-start}
    (out/'SOURCE_SNAPSHOT.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(info,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
