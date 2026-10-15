from pathlib import Path
import json,sys
import numpy as np
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
from probe import snapshot
from recovery.recovery_controller import Config
from recovery.path_search import EdgeSearch
from reproduction.improvement_v8_20261015_01.recovery.geometry import CAN,support
if __name__=='__main__':
    c,x,q=snapshot();c.cfg=Config();s=EdgeSearch(c,x,q)
    while not s.advance(16):pass
    r=s.chosen['rotation'];world=CAN@Rotation.from_quat(x[19:23]).as_matrix().T
    span=float(np.ptp(world@r[:,1]));offset=s.chosen['goal']-x[16:19]
    # This is an envelope diagnostic, not a new candidate or a claim of execution success.
    p=RUN/'pilot_a/v10_regression_6000005/trace.jsonl';selected=[]
    for row in map(json.loads,p.open()):
        if row['step'] not in [280,287,288,289,295,320,350,400]:continue
        x=np.array(row['state_before']);d,why=support(x,.8)
        selected.append({'step_before':row['step'],'mode':row['recovery']['mode'],'can_position':x[16:19].tolist(),'eef_position':x[:3].tolist(),'support_reason':why,'observed_gap_m':abs(float(x[7]-x[8]))})
    out={'source':'pilot_a physical trace + separate physical contact replay; contact never used by controller',
        'static_candidate':{'closure_axis_world':r[:,1].tolist(),'can_hull_projected_span_m':span,'requested_gap_m':c.approach_gap,'closure_center_offset_m':float(offset@r[:,1])},
        'selected_states':selected,'conclusion':'The fixed-bin hand sweep omits can contact. Finger1 contacts the can before closing, after which the can changes support and replanning aborts the approach. Projected envelope is a diagnostic, not a full grasp feasibility test.'}
    with (RUN/'analysis/contact_diagnosis.json').open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps(out))
