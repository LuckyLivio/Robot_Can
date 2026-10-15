"""Embed frozen media metadata and extract truthful first-frame posters."""
import csv,json,hashlib
from pathlib import Path
import cv2
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
OLD=ROOT/'reproduction/release_20261012_01/demo';OUT=RUN/'demo'
def main():
    cases=json.loads((OLD/'media_manifest.json').read_text(encoding='utf-8'))
    (OUT/'posters').mkdir(exist_ok=True)
    for c in cases:
        video=OLD/c['video'];assert hashlib.sha256(video.read_bytes()).hexdigest()==c['sha256']
        cap=cv2.VideoCapture(str(video));ok,frame=cap.read();cap.release();assert ok
        poster=OUT/'posters'/f"{c['id']}_first.jpg"
        assert cv2.imwrite(str(poster),frame,[cv2.IMWRITE_JPEG_QUALITY,94])
        c['video']='../../release_20261012_01/demo/'+c['video']
        c['poster']='../../release_20261012_01/demo/'+c['poster']
        c['firstFrame']='posters/'+poster.name
    with (ROOT/'reproduction/confirmation_20261012_01/analysis/summary.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    stats=[{'method':r['method'],'condition':r['condition'],'rate':float(r['mean_success_percent']),
            'counts':[int(r[k]) for k in ('success_s17_or_fixed_bc','success_s23','success_s41') if r[k]]}
           for r in rows if r['condition']!='joint_equal_weight']
    (OUT/'data.js').write_text('const DEMO_DATA = '+json.dumps({'cases':cases,'statistics':stats},ensure_ascii=False,indent=2)+';\n',encoding='utf-8')
    print(json.dumps({'unchanged_videos':len(cases),'first_frame_posters':len(cases),'statistics_rows':len(stats)}))
if __name__=='__main__':main()
