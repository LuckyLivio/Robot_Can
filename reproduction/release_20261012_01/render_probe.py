"""Check local offscreen rendering on a QA-only state, without policy changes."""
import sys,json,hashlib,shutil,subprocess
from pathlib import Path
import h5py,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from common import make_env,restore_demo
from collect_rollout_branches import signature
from robosuite.utils.binding_utils import MjRenderContextOffscreen

env=make_env(False)
with h5py.File(ROOT/'reproduction/confirmation_20261012_01/qa_starts.hdf5') as f:
    restore_demo(env,f['data/demo_2000000'])
    before=signature(env)
    warmstart=env.sim.data.qacc_warmstart.copy()
    context=MjRenderContextOffscreen(env.sim,device_id=0)
    context.vopt.geomgroup[0]=0;context.vopt.geomgroup[1]=1
    frame=env.sim.render(width=480,height=480,camera_name='agentview')[::-1].copy()
    env.sim.data.qacc_warmstart[:]=warmstart
    err=float(np.max(np.abs(before-signature(env))))
    print('render_error',err,'pixel_std',float(frame.std()),'changed_indices',np.flatnonzero(before!=signature(env)).tolist(),flush=True)
    assert err==0 and frame.std()>10
    Image.fromarray(frame).save(RUN/'render_probe_visual.png')
    ffmpeg=shutil.which('ffmpeg');assert ffmpeg
    version=subprocess.run([ffmpeg,'-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    with (RUN/'render_validation.json').open('x',encoding='utf-8') as out:json.dump({'passed':True,'physics_controller_change_after_warmstart_restore':err,'shape':list(frame.shape),'ffmpeg':ffmpeg,'ffmpeg_version':version,'note':'Renderer updates qacc_warmstart by ~1e-11; copy and restore that auxiliary array so visualization leaves the recorded physics/controller signature exactly unchanged. Collision geoms disabled in camera view.'},out,indent=2)
env.close();print('render_probe_passed',flush=True)
