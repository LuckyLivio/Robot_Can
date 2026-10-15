"""Inspect known pilot corner false rejections; no rollout or success oracle."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
import numpy as np
from recovery.recovery_controller import RecoveryController
from recovery.clearance_guard import candidates,goal_for,clearance_margin,vertical_margin
def main():
    out=[]
    for group,names in [('new_geometry',['demo_6100002','demo_6100003']),('known_pressure',['demo_11000006'])]:
        for line in (RUN/'pilot_a'/('v5_'+group)/'trace.jsonl').open():
            r=json.loads(line)
            if r['demo'] not in names or r['step']!=80:continue
            x=np.array(r['state_before'],np.float32);c=RecoveryController([.1975,.4025,.8],.8,x);c.plan_grasp(x)
            opts,scope=candidates(c,x);entries=[]
            for o in opts:
                goal=goal_for(c,x,o)
                for gap in [.052,.056,.060]:
                    # Closing direction clearance for the actual can footprint.
                    closure=o['rotation'][:2,1];required=.05+2*abs(float(o['grasp_offset']@closure))+.002
                    for height in [0.,.004,.008]:
                        g=goal.copy();g[2]+=height
                        entries.append({'nominal_gap':gap,'required_gap':required,'height_delta':height,
                          'yaw':float(np.arctan2(o['rotation'][1,0],o['rotation'][0,0])),
                          'margin_nominal':clearance_margin(g,o['rotation'],o['cell'],.8,gap),
                          'margin_envelope':vertical_margin(g,o['rotation'],o['cell'],.8,gap+.0055)})
            out.append({'demo':r['demo'],'position':x[16:19].tolist(),'candidates':entries})
    with (RUN/'analysis/pilot_a_corner_diagnosis.json').open('x',encoding='utf8') as f:json.dump(out,f,indent=2)
    for r in out:
        print(r['demo'],r['position'])
        for v in r['candidates']:
            if v['height_delta']==0:print(v)
if __name__=='__main__':main()
