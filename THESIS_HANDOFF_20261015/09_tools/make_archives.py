"""Create full and writing ZIPs after package validation; never runs experiments."""
from pathlib import Path
import hashlib,json,zipfile
PACK=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    files=[p for p in sorted(PACK.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    report=[]
    for mode in ['WRITING','FULL']:
        target=PACK.parent/f'{PACK.name}_{mode}.zip'
        assert not target.exists(),target
        selected=[p for p in files if mode=='FULL' or '08_full_traces_gzip' not in p.relative_to(PACK).parts]
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
            for p in selected:
                z.write(p,f'{PACK.name}/{p.relative_to(PACK).as_posix()}',compress_type=zipfile.ZIP_STORED if p.suffix=='.gz' else zipfile.ZIP_DEFLATED)
        digest=sha(target);target.with_suffix(target.suffix+'.sha256').write_text(f'{digest}  {target.name}\n',encoding='ascii')
        with zipfile.ZipFile(target) as z:
            assert len(z.namelist())==len(selected)
            assert z.testzip() is None
        row={'mode':mode,'path':str(target),'files':len(selected),'bytes':target.stat().st_size,'sha256':digest,'zip_crc_passed':True}
        report.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    (PACK.parent/'.git/transfer_archive_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':main()
