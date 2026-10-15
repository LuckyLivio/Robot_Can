"""Create a self-contained plotting/writing supplement; no weights or simulation."""
from pathlib import Path
import hashlib,json,zipfile,subprocess,sys,tempfile,re
RUN=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    build=RUN/'builds';build.mkdir(exist_ok=True)
    names=['README.md','REPORT.md','CHECKLIST.md','CHECKLIST.csv','THESIS_OUTLINE_REVIEWED.md','CURVE_EXPLANATIONS.md','PLAN_AND_NEXT_STEPS.md','CLEANUP.md','FIGURE_CATALOG.md','FIGURE_INDEX.csv','PLOT_SOURCES.json','index.html','style.css','build_figures.py','verify.py',
        'statistics_validation.json','contracts.json','inventory_summary.json','result_validation.json','cleanup_inventory.json','media_hash_continuity.json','environment_and_inference.json','document_changes.json','validation/figure_validation.json','validation/visual_review.json','validation/document_validation.json','validation/browser_validation.json','validation/browser_curve_preview.jpg']
    names.append('DATA_DICTIONARY.md')
    paths=[RUN/n for n in names]
    paths+=sorted((RUN/'figures').rglob('*'));paths+=sorted((RUN/'inputs').rglob('*'));paths=[p for p in paths if p.is_file()]
    content={p.relative_to(RUN).as_posix():p.read_bytes() for p in paths}
    # Package navigation is self-contained; downloads are already unpacked.
    s=content['index.html'].decode('utf8');s=s.replace('<a href="builds/CAN_LAB_PAPER_FIGURES_20261015.zip" download>下载图表与提纲包</a>','<span>已解压：当前目录即图表与提纲包</span>');s=s.replace('PLOT_SOURCES.json / MANIFEST.json','PLOT_SOURCES.json / PACKAGE_MANIFEST.json');content['index.html']=s.encode('utf8')
    s=content['README.md'].decode('utf8');s=s.replace('[下载本轮图表与提纲ZIP](builds/CAN_LAB_PAPER_FIGURES_20261015.zip)','本目录即已解压的本轮图表与提纲包');content['README.md']=s.encode('utf8')
    s=content['REPORT.md'].decode('utf8').replace('[新包大小与哈希](PACKAGE_BUILD.json)','新包大小与SHA记录在仓库PACKAGE_BUILD.json及ZIP旁校验文件');content['REPORT.md']=s.encode('utf8')
    manifest={'purpose':'Paper figure/outline supplement, not full simulation reproduction','source_commit_before_changes':'f6acd284a423fe323f2cbd76c5f5724ec9f64eb1','new_experiments':0,'files':{p:hashlib.sha256(b).hexdigest() for p,b in content.items()}}
    content['PACKAGE_MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf8')
    target=build/'CAN_LAB_PAPER_FIGURES_20261015.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,b in sorted(content.items()):z.writestr('CAN_LAB_PAPER_FIGURES/'+p,b)
    with zipfile.ZipFile(target) as z:assert z.testzip() is None
    # Standard-library check from a fresh, Unicode/space-containing extraction.
    validation=build/'移位 验证';validation.mkdir(exist_ok=True)
    with zipfile.ZipFile(target) as z:z.extractall(validation)
    root=validation/'CAN_LAB_PAPER_FIGURES'
    result=subprocess.run([sys.executable,'-B',str(root/'verify.py'),'--package'],capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)['passed']
    receipt={'zip':target.relative_to(RUN).as_posix(),'bytes':target.stat().st_size,'sha256':sha(target),'members':len(content),'files_verified':len(manifest['files']),'crc_passed':True,'relocated_standard_library_verification':json.loads(result.stdout),'historical_packages_modified':False}
    (RUN/'PACKAGE_BUILD.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    target.with_suffix('.zip.sha256').write_text(receipt['sha256']+'  '+target.name+'\n',encoding='ascii')
    print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
