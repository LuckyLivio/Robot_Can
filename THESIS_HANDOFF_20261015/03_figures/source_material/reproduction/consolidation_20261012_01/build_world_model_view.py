"""Build presentation data and figures from frozen measurements, without policy runs."""
import hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
RUN=Path(__file__).resolve().parent

def main():
 source=ROOT/'reproduction/extensions_20261012_01/offline_metrics.json'
 raw=json.loads(source.read_text(encoding='utf8'))
 rows=[]
 for method in ['persistence','plain','full']:
  selected=[r for r in raw['rows'] if r['method']==method]
  assert len(selected)==3
  rows.append({'method':method,'training_seeds':[r['seed'] for r in selected],
   **{k:sum(r[k] for r in selected)/len(selected) for k in ['normalized_state_mse','eef_position_rmse_m','object_position_rmse_m']}})
 full=next(r for r in rows if r['method']=='full');weak=next(r for r in rows if r['method']=='persistence')
 confirmation_source=ROOT/'reproduction/confirmation_20261012_01/analysis/analysis.json'
 confirmation=json.loads(confirmation_source.read_text(encoding='utf8'))
 joint=next(r for r in confirmation['paired'] if r['left']=='full' and r['right']=='bc_k2' and r['condition']=='joint_equal_weight')
 data={'source':source.relative_to(ROOT).as_posix(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
  'confirmation_source':confirmation_source.relative_to(ROOT).as_posix(),'confirmation_source_sha256':hashlib.sha256(confirmation_source.read_bytes()).hexdigest(),
  'confirmation_joint_effect':joint,
  'groups':raw['groups'],'independent_parents':raw['independent_parents'],'scope':raw['caution'],'rows':rows,
  'object_rmse_reduction_percent':100*(1-full['object_position_rmse_m']/weak['object_position_rmse_m']),
  'eef_rmse_reduction_percent':100*(1-full['eef_position_rmse_m']/weak['eef_position_rmse_m'])}
 (RUN/'world_model_view.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 (RUN/'demo/world-model-data.js').write_text('const WORLD_MODEL_VIEW = '+json.dumps(data,ensure_ascii=False)+';\n',encoding='utf8')
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','axes.edgecolor':'#d8dce3','axes.labelcolor':'#565d69','text.color':'#242830'})
 fig,axes=plt.subplots(1,2,figsize=(10,3.5),layout='constrained')
 colors=['#a6abb5','#515966','#0677df'];labels=['Persistence','Plain','Full']
 for ax,key,title in zip(axes,['eef_position_rmse_m','object_position_rmse_m'],['Robot end-effector','Object position']):
  values=[r[key]*1000 for r in rows]
  ax.barh(labels,values,color=colors,height=.5)
  ax.invert_yaxis();ax.set_xlim(0,70);ax.set_xlabel('Position RMSE (mm; lower is better)');ax.set_title(title,loc='left',fontweight='bold',pad=12)
  ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0);ax.grid(axis='x',color='#eceff4',linewidth=.6);ax.set_axisbelow(True)
  for i,v in enumerate(values):ax.text(v+1,i,f'{v:.2f}',va='center',fontsize=11,color=colors[i])
 fig.suptitle('Development diagnosis: 64 branch groups / 8 reused parents',fontsize=11,color='#565d69')
 for ext in ['svg','png','pdf']:fig.savefig(RUN/'figures'/f'prediction_rmse.{ext}',dpi=300,bbox_inches='tight')
 plt.close(fig)
 fig,axes=plt.subplots(2,1,figsize=(6,5.6),layout='constrained')
 for ax,key,title in zip(axes,['eef_position_rmse_m','object_position_rmse_m'],['Robot end-effector','Object position']):
  values=[r[key]*1000 for r in rows]
  ax.barh(labels,values,color=colors,height=.5);ax.invert_yaxis();ax.set_xlim(0,70)
  ax.set_xlabel('Position RMSE (mm; lower is better)');ax.set_title(title,loc='left',fontweight='bold',pad=12)
  ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0);ax.grid(axis='x',color='#eceff4',linewidth=.6);ax.set_axisbelow(True)
  for i,v in enumerate(values):ax.text(v+1,i,f'{v:.2f}',va='center',fontsize=11,color=colors[i])
 fig.savefig(RUN/'figures/prediction_rmse_mobile.svg',bbox_inches='tight');plt.close(fig)
 print(json.dumps({'groups':data['groups'],'parents':data['independent_parents'],'object_reduction_percent':data['object_rmse_reduction_percent'],'new_policy_episodes':0}))

if __name__=='__main__':main()
