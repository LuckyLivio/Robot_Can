"""Raw, un-smoothed trajectories. Stop successful traces at their actual terminal step."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];OUT=RUN/'analysis';allrows=[]
files={v:ROOT/f'reproduction/improvement_v9_20261015_01/pilot_b/{v}_regression_6000005/trace.jsonl' for v in ['v6']}
files.update({v:RUN/f'pilot_a/{v}_regression_6000005/trace.jsonl' for v in ['v9','path','v10']})
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(4,4,figsize=(14,10),sharex=True,sharey='row',layout='constrained');initial=None
phase_names=['NORMAL','RETRACT','PLAN_WAIT','POSE_WAIT','ALIGN','EDGE_ROTATE','EDGE_APPROACH','APERTURE','DESCEND','CLOSE','TEST_LIFT','LIFT','CARRY','PLACE','RELEASE','RETREAT','POSE_BLOCKED','EXHAUSTED']
for col,(v,f) in enumerate(files.items()):
    rows=[json.loads(l) for l in f.open()];x=np.array([r['state_after'] for r in rows]);t=np.array([r['step'] for r in rows])
    if initial is None:initial=rows[0]['state_before']
    else:np.testing.assert_array_equal(initial,rows[0]['state_before'])
    angle=np.rad2deg(np.arccos(np.clip(abs(Rotation.from_quat(x[:,19:23]).as_matrix()[:,2,2]),0,1)))
    distance=np.linalg.norm(x[:,16:18]-np.array([.1975,.4025]),axis=1)
    phases=[phase_names.index(r['recovery']['mode']) for r in rows]
    axs[0,col].plot(t,x[:,2],label='End effector',color='#3575ad',lw=1.3);axs[0,col].plot(t,x[:,18],label='Can',color='#e09b36',lw=1.3)
    axs[0,col].axhline(.9,ls=':',color='#9aa5b1',lw=1);axs[1,col].plot(t,distance,color='#3575ad',lw=1.3)
    axs[2,col].plot(t,angle,color='#7652a3',lw=1.3);axs[3,col].scatter(t,phases,s=3,marker='s',color='#526574',linewidths=0)
    axs[0,col].set_title(f"{v} | {'success' if rows[-1]['success_after'] else 'failed'} | {len(rows)} steps",fontweight='bold')
    axs[3,col].set_xlabel('Control step (20 Hz)')
    for ax in axs[:,col]:ax.grid(alpha=.15);ax.set_xlim(0,400)
    for i,r in enumerate(rows):
        allrows.append({'version':v,'step':r['step'],'eef_z_m':x[i,2],'can_z_m':x[i,18],'can_goal_xy_distance_m':distance[i],'can_axis_tilt_deg':angle[i],'phase':r['recovery']['mode'],'success_after':r['success_after']})
axs[0,0].legend(frameon=False);axs[0,0].set_ylabel('World height (m)');axs[1,0].set_ylabel('Can to target XY (m)');axs[2,0].set_ylabel('Can-axis tilt (deg)')
axs[3,0].set_yticks(range(len(phase_names)),phase_names,fontsize=6);axs[3,0].set_ylabel('Control phase')
fig.suptitle('Known wall-edge case: BC k=2, noise 0.05, demo_6000005\nSame initial state and noise seed; raw saved trajectories; no new confirmation',fontsize=13)
fig.savefig(OUT/'wall_edge_comparison.png',dpi=160);fig.savefig(OUT/'wall_edge_comparison.svg');plt.close(fig)
with (OUT/'wall_edge_trajectories.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
print('figure and raw CSV',len(allrows),'rows')
