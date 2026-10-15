"""Portable, read-only file/hash/provenance validation. Standard library only."""
from pathlib import Path
import argparse,concurrent.futures,csv,gzip,hashlib,json,subprocess,sys
PACK=Path(__file__).resolve().parents[1]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mode',choices=['writing','full'],default='writing');args=parser.parse_args()
    manifest=json.loads((PACK/'07_provenance/PACKAGE_MANIFEST.json').read_text(encoding='utf8'))
    files=[r for r in manifest['files'] if args.mode=='full' or not r['path'].startswith('08_full_traces_gzip/')]
    def check(r):
        p=(PACK/r['path']).resolve();assert p.is_relative_to(PACK.resolve()),p
        assert p.is_file() and p.stat().st_size==r['bytes'],r['path']
        assert digest(p)==r['sha256'],r['path']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(check,files))
    assets=rows(PACK/'07_provenance/SOURCE_ASSETS.csv')
    assert len(assets)==3946
    for r in assets:
        p=PACK/r['package_path']
        if r['storage']=='copy':assert digest(p)==r['original_sha256'],r['source_repo_path']
    trace_count=0
    if args.mode=='full':
        def trace(r):
            h=hashlib.sha256();count=0;n=0
            with gzip.open(PACK/r['package_path'],'rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk);count+=chunk.count(b'\n');n+=len(chunk)
            assert h.hexdigest()==r['original_sha256'] and n==int(r['original_bytes']) and count==int(r['jsonl_line_count']),r['source_repo_path']
        compressed=[r for r in assets if r['storage']=='gzip']
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(trace,compressed))
        trace_count=len(compressed)
    provenance=rows(PACK/'02_tables/PROVENANCE.csv')
    for r in provenance:
        assert digest(PACK/'04_snapshot'/r['source_repo_path'])==r['source_sha256'],r['source_repo_path']
        assert digest(PACK/'02_tables'/r['derived_table'])==r['derived_sha256'],r['derived_table']
    checks=rows(PACK/'02_tables/VALIDATION_CHECKS.csv');assert all(r['passed']=='True' for r in checks)
    tables=json.loads((PACK/'02_tables/table_catalog.json').read_text(encoding='utf8'))['tables']
    for r in tables:assert len(rows(PACK/'02_tables'/r['table']))==r['rows'],r['table']
    figure=subprocess.run([sys.executable,str(PACK/'03_figures/verify_figures.py')],cwd=PACK,capture_output=True,text=True,encoding='utf8',check=True)
    figures=json.loads(figure.stdout);assert figures['passed']
    print(json.dumps({'passed':True,'mode':args.mode,'package_files_hashed':len(files),
        'frozen_project_files_indexed':len(assets),'compressed_traces_decompressed_and_sha_verified':trace_count,
        'table_count':len(tables),'existing_numeric_checks_passed':len(checks),
        'figure_groups':figures['figure_groups'],'figure_files':figures['figure_files'],
        'source_commit':manifest['source_commit'],'new_training_steps':0,'new_model_inference':0,
        'new_simulation_episodes':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
