'use strict';
async function refreshProgress(){
  try {
    const r=await fetch('progress.json',{cache:'no-store'});if(!r.ok)throw new Error('status unavailable');
    const d=await r.json();document.getElementById('progress-time').textContent='更新于 '+d.updated;
    document.getElementById('v9-state').textContent=d.v9.status;
    const rows=[['v6 · 历史已知诊断','31 / 37','参考基线'],['v8 · 历史合用','30 / 37','未采用 · 1例退步']];
    if(d.v9.variants)for(const [v,s] of Object.entries(d.v9.variants))rows.push([v+' · '+d.v9.stage,`${s.success} / ${s.episodes}`,s.regressions?`${s.rescues.length} 救回 / ${s.regressions.length} 退步`:'仅统计已完成回合']);
    document.getElementById('progress-table').replaceChildren(...rows.map(cells=>{const tr=document.createElement('tr');for(const s of cells){const td=document.createElement('td');td.textContent=s;tr.append(td);}return tr;}));
    document.getElementById('progress-error').hidden=true;
  }catch(e){document.getElementById('progress-error').hidden=false;}
}
refreshProgress();setInterval(refreshProgress,30000);
