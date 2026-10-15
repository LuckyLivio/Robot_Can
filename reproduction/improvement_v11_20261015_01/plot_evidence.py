from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];OUT=RUN/'analysis'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
def trace(path,demo):return [r for r in map(json.loads,path.open()) if r['demo']==demo]
if __name__=='__main__':
    fig,axes=plt.subplots(3,4,figsize=(14,8),sharex=True,sharey='row',layout='constrained');csvrows=[];first=None
    for col,v in enumerate(['v10','axis','guard','v11']):
        rows=trace(RUN/f'pilot_a/{v}_regression_6000005/trace.jsonl','demo_6000005');x=np.array([r['state_after'] for r in rows]);t=np.array([r['step'] for r in rows])
        if first is None:first=rows[0]['state_before']
        else:np.testing.assert_array_equal(first,rows[0]['state_before'])
        dist=np.linalg.norm(x[:,16:18]-[.1975,.4025],axis=1);gap=np.abs(x[:,7]-x[:,8])*1000
        axes[0,col].plot(t,x[:,2],label='End effector',lw=1.3,color='#3575ad');axes[0,col].plot(t,x[:,18],label='Can',lw=1.3,color='#df9b36')
        axes[1,col].plot(t,dist,color='#3575ad',lw=1.3);axes[2,col].plot(t,gap,color='#7652a3',lw=1.3)
        axes[0,col].set_title(f"{v}: {'success' if rows[-1]['success_after'] else 'failed'}, {len(rows)} steps",fontweight='bold');axes[2,col].set_xlabel('Control step (20 Hz)')
        for ax in axes[:,col]:ax.grid(alpha=.15);ax.set_xlim(0,400)
        for i,r in enumerate(rows):csvrows.append({'version':v,'step':r['step'],'eef_z_m':x[i,2],'can_z_m':x[i,18],'can_to_goal_xy_m':dist[i],'gap_mm':gap[i],'mode':r['recovery']['mode'],'success_after':r['success_after']})
    for ax,label in zip(axes[:,0],['World height (m)','Can to target XY (m)','Observed aperture (mm)']):ax.set_ylabel(label)
    axes[0,0].legend(frameon=False);fig.suptitle('Known wall-edge diagnostic | BC k=2, noise 0.05, demo_6000005\nSame start and noise seed; raw every-step traces, no smoothing or terminal extrapolation',fontsize=13)
    fig.savefig(OUT/'wall_edge_comparison.png',dpi=160);fig.savefig(OUT/'wall_edge_comparison.svg');plt.close(fig)
    with (OUT/'wall_edge_trajectories.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
    fig,axes=plt.subplots(3,2,figsize=(11,8),sharex=True,sharey='row',layout='constrained');csvrows=[]
    for col,v in enumerate(['v6','v11']):
        base=ROOT/'reproduction/improvement_v6_20261015_01' if v=='v6' else RUN
        rows=trace(base/f'dev_a/{v}_full_s41_noise005/trace.jsonl','demo_87');x=np.array([r['state_after'] for r in rows]);t=np.array([r['step'] for r in rows]);dist=np.linalg.norm(x[:,:3]-x[:,16:19],axis=1)*1000
        axes[0,col].plot(t,x[:,2],label='End effector',color='#3575ad');axes[0,col].plot(t,x[:,18],label='Can',color='#df9b36');axes[1,col].plot(t,dist,color='#7652a3');axes[2,col].plot(t,np.linalg.norm(x[:,16:18]-[.1975,.4025],axis=1),color='#3575ad')
        axes[0,col].set_title(f"{v}: {'success' if rows[-1]['success_after'] else 'failed'}, {len(rows)} steps",fontweight='bold');axes[2,col].set_xlabel('Control step (20 Hz)')
        for ax in axes[:,col]:ax.grid(alpha=.15);ax.set_xlim(0,400)
        for i,r in enumerate(rows):csvrows.append({'version':v,'step':r['step'],'eef_z_m':x[i,2],'can_z_m':x[i,18],'eef_can_distance_mm':dist[i],'mode':r['recovery']['mode'],'success_after':r['success_after']})
    for ax,label in zip(axes[:,0],['World height (m)','End effector to can (mm)','Can to target XY (m)']):ax.set_ylabel(label)
    axes[0,0].legend(frameon=False);fig.suptitle('Development regression | Full seed41, noise 0.05, demo_87\nNew edge module never triggered; frozen v10 reproduces every v11 action',fontsize=13)
    fig.savefig(OUT/'development_regression.png',dpi=160);fig.savefig(OUT/'development_regression.svg');plt.close(fig)
    with (OUT/'development_regression_trajectory.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
    print('two raw-trace figures and CSVs written')
