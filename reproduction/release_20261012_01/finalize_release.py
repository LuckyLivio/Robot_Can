"""Check links, evidence, video decoding, and preservation; finalize once."""
import ast,datetime,hashlib,json,re,shutil,subprocess
from pathlib import Path
from urllib.parse import unquote,urlsplit
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not (RUN/'release_validation.json').exists()
    before=read(RUN/'before_manifest.json');protected=read(RUN/'frozen_results.json')['protected_sha256']
    changed=[];deleted=[]
    allowed={p.name for p in (RUN/'previous_documents').glob('*.md')}
    for relative,sha in before.items():
        p=ROOT/relative
        if not p.exists():deleted.append(relative)
        elif digest(p)!=sha:changed.append(relative)
    assert not deleted,deleted
    assert set(changed).issubset(allowed),changed
    for relative,sha in protected.items():assert digest(ROOT/relative)==sha,relative
    for p in (RUN/'previous_documents').glob('*.md'):assert digest(p)==before[p.name]
    for p in RUN.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    documents=sorted(ROOT.glob('*.md'));links=0
    for p in documents:
        content=p.read_text(encoding='utf-8');assert content.count('```')%2==0,p.name
        for url in re.findall(r'\]\(([^)]+)\)',content):
            parsed=urlsplit(url)
            if parsed.scheme or url.startswith('#'):continue
            target=p.parent/unquote(parsed.path)
            if target==RUN/'release_validation.json':continue
            assert target.exists(),(p.name,url)
            links+=1
    assert read(RUN/'demo/trace_validation.json')['passed']
    replay=read(RUN/'demo/replay_validation.json');assert replay['passed']
    assert replay['render_source_sha256']==digest(RUN/'make_demo.py')
    media=read(RUN/'demo/media_manifest.json');assert len(media)==6
    video_checks=[]
    for item in media:
        p=RUN/'demo'/item['video'];assert digest(p)==item['sha256']
        cap=cv2.VideoCapture(str(p));assert cap.isOpened(),p
        count=0;minstd=[float('inf')]*3;minmean=[float('inf')]*3
        while True:
            ok,frame=cap.read()
            if not ok:break
            assert frame.shape==(660,1440,3),frame.shape
            for i in range(3):
                pixels=frame[160:580,i*480:(i+1)*480]
                std=float(pixels.std());mean=float(pixels.mean())
                assert std>10 and mean>10,(item['id'],count,i,'Black/invalid panel')
                minstd[i]=min(minstd[i],std);minmean[i]=min(minmean[i],mean)
            count+=1
        cap.release();assert count==item['frames'],(item['id'],count,item['frames'])
        probe=shutil.which('ffprobe');assert probe
        info=json.loads(subprocess.run([probe,'-v','error','-show_entries','stream=codec_name,width,height,r_frame_rate:format=duration','-of','json',str(p)],capture_output=True,text=True,check=True).stdout)
        assert info['streams'][0]['codec_name']=='h264'
        assert abs(float(info['format']['duration'])-count/10)<.01
        video_checks.append({'id':item['id'],'decoded_frames':count,'codec':'h264','dimensions':[1440,660],
            'all_three_panels_nonblack_at_every_frame':True,'minimum_panel_std':minstd,'minimum_panel_mean':minmean})
    browser=read(RUN/'browser_validation.json');assert browser['passed']
    qa=read(RUN/'visual_review.json');assert qa['passed']
    manifest={'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,
        'preexisting_files':len(before),'changed_existing_files':changed,'deleted_existing_files':deleted,
        'preserved_frozen_experiment_files':len(protected),'archived_original_documents':len(allowed),
        'current_documents':len(documents),'local_document_links_checked':links,
        'original_controller_code_unchanged':True,'weights_results_data_and_old_figures_unchanged':True,
        'demonstration_episode_replays':len(replay['checks']),'replayed_steps':replay['total_replayed_control_steps'],
        'video_checks':video_checks,'browser_validation':browser,'visual_review':qa,
        'release_sha256':{p.relative_to(ROOT).as_posix():digest(p) for p in [*documents,*RUN.rglob('*')] if p.is_file() and '__pycache__' not in p.parts},
        'manifest_excludes_itself':True}
    with (RUN/'release_validation.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2,ensure_ascii=False)
    print(json.dumps({k:manifest[k] for k in ('passed','preexisting_files','changed_existing_files','deleted_existing_files','preserved_frozen_experiment_files','current_documents','local_document_links_checked','demonstration_episode_replays','replayed_steps')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
