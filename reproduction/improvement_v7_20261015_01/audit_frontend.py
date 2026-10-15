"""Read-only provenance, timing, and recorded-motion audit of the old frontend."""
from pathlib import Path
import hashlib,json,subprocess,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
def main():
    demo=ROOT/'reproduction/release_20261012_01/demo';page=ROOT/'reproduction/consolidation_20261012_01/demo'
    manifest=json.loads((demo/'media_manifest.json').read_text());videos=[];motion=[]
    for case in manifest:
        video=demo/case['video'];same=hashlib.sha256(video.read_bytes()).hexdigest()==case['sha256'];assert same
        probe=None
        if shutil.which('ffprobe'):
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=avg_frame_rate,r_frame_rate,nb_frames,width,height,duration','-of','json',str(video)]))['streams'][0]
        videos.append({'case':case['id'],'sha256_matches_frozen_manifest':same,'declared_fps':case['fps'],'probe':probe})
        for method in ['bc_k2','full','plain']:
            folder=demo/'traces'/f"{method}_{case['condition']}";info=json.loads((folder/'results.json').read_text())
            path=folder/info['trace_files'][case['state_name']];rows=[json.loads(l) for l in path.open()]
            xyz=np.array([rows[0]['state_before'][:3]]+[r['state_after'][:3] for r in rows]);delta=np.diff(xyz,axis=0)
            length=np.linalg.norm(delta,axis=1);norm=length[1:]*length[:-1]
            cos=np.divide(np.sum(delta[1:]*delta[:-1],axis=1),norm,out=np.ones_like(norm),where=norm>1e-15)
            reversal=(length[1:]>.0005)&(length[:-1]>.0005)&(cos<-.5)
            gap=np.array([abs(r['state_before'][7]-r['state_before'][8]) for r in rows])*1000
            motion.append({'case':case['id'],'method':method,'steps':len(rows),'success':rows[-1]['success_after'],
                'eef_path_length_m':float(length.sum()),'eef_step_mm_p95':float(np.quantile(length*1000,.95)),
                'large_direction_reversals':int(reversal.sum()),'gap_min_mm':float(gap.min()),'gap_max_mm':float(gap.max()),
                'source':path.relative_to(ROOT).as_posix()})
    # Parse the data file; do not execute its JavaScript.
    raw=(page/'evidence.js').read_text(encoding='utf8').strip();evidence=json.loads(raw[raw.index('=')+1:].rstrip(';'))
    trajectories=[{'kind':c['kind'],'demo':c['demo'],'series':[{'label':s['label'],'source':s['source']} for s in c['series']]} for c in evidence['trajectory_cases']]
    report={'video_provenance':'Old BC/Full/Plain seed17 comparison, no recovery v6/v7 controller.',
      'video_sampling':'20 Hz physics control, every two steps sampled, encoded at 10 fps; success panel freezes at its terminal state; final 1 s hold.',
      'trajectory_animation':'Canvas advances whole control steps at 20 Hz with requestAnimationFrame; no interpolation between samples.',
      'frontend_versions':trajectories,'videos':videos,'motion':motion,
      'metric_definition':'Large direction reversal: adjacent EEF increments both >0.5 mm and angle >120 degrees. Descriptive proxy only, not a standardized stability/safety threshold.',
      'browser_dropped_frames':'Not measured. Asset inspection does not exclude machine/browser playback stutter.',
      'result_integrity':'Frozen video hashes match; visual timing does not alter stored simulation success. Real trajectory reversals and grip oscillations must not be hidden by presentation smoothing.'}
    with (RUN/'analysis/frontend_motion_audit.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
    print(json.dumps({'video_count':len(videos),'actual_fps':[v['probe']['avg_frame_rate'] if v['probe'] else None for v in videos],
                      'default_case_motion':[r for r in motion if r['case']=='clean_full_only_success'],'trajectory_sources':trajectories},indent=2))
if __name__=='__main__':main()
