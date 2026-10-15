"""Plot descriptive effects from existing paired-start outcomes only."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
RUN=Path(__file__).resolve().parent
def main():
 rows=json.loads((RUN/'factorial_analysis.json').read_text());fig,axes=plt.subplots(3,2,figsize=(13,11.2),sharex=True)
 labels=['Recovery effect, BC','Recovery effect, Full','Full - BC, no recovery','Full - BC, with recovery','Interaction']
 keys=['recovery_for_bc','recovery_for_full','world_model_without_recovery','world_model_with_recovery','interaction']
 titles=['v2 confirmation batch / v2 recovery','v3 confirmation batch / v2 recovery','v3 confirmation batch / v3 recovery']
 plt.rcParams.update({'font.size':10})
 for i,r in enumerate(rows):
  for j,cond in enumerate(['clean','noise005']):
   ax=axes[i,j]
   for y,key in enumerate(keys):
    d=r['effects'][cond][key];v=d['estimate']*100;lo,hi=np.array(d['ci95'])*100;color='#14836e' if y<2 else '#637c99'
    ax.errorbar(v,y,xerr=[[v-lo],[hi-v]],fmt='o',color=color,capsize=3,ms=6)
    ax.annotate(f'{v:+.2f} [{lo:+.2f}, {hi:+.2f}]',(v,y),xytext=(0,10),textcoords='offset points',ha='center',fontsize=7)
   ax.set_title(titles[i]+(' | Clean' if j==0 else ' | Noise 0.05'),fontsize=10)
   ax.set_yticks(range(5),labels if j==0 else ['']*5);ax.invert_yaxis();ax.set_ylim(4.6,-.7);ax.axvline(0,color='#888',ls='--',lw=1);ax.grid(axis='x',alpha=.15);ax.spines[['top','right']].set_visible(False)
 for ax in axes[-1]:ax.set_xlabel('Success difference (percentage points)')
 fig.suptitle('Existing factorial evidence | two 60-start batches | three descriptive contrasts\nFull averages 3 fixed seeds; paired-start pointwise 95% intervals; no new policy runs',fontsize=12)
 fig.tight_layout(rect=[0,0,1,.94])
 out=RUN/'figures';out.mkdir(exist_ok=False)
 for ext in ['png','svg','pdf']:fig.savefig(out/f'factorial_effects.{ext}',dpi=300)
 plt.close(fig)
 report=RUN/'FACTORIAL_REVIEW.md';text=report.read_text(encoding='utf8').replace('-0.00','+0.00')
 text=text.replace('上述轮次分别使用不同的60个起点，不能按成功率挑最好轮次。','v2与v3轮次使用不同的60个起点；上面后两节共用同一批v3起点，不是三批独立数据。不能按成功率挑最好轮次。')
 report.write_text(text+'\n![已有四组效应图](figures/factorial_effects.png)\n',encoding='utf8')
 print('Saved PNG/SVG/PDF; existing policy outcomes unchanged.')
if __name__=='__main__':main()
