'use strict';
async function refreshProgress(){
  try {
    const r=await fetch('progress.json',{cache:'no-store'});if(!r.ok)throw new Error('status unavailable');
    const d=await r.json();document.getElementById('progress-time').textContent='更新于 '+d.updated;
    document.getElementById('v8-state').textContent=d.v8.status;
    const rows=[['v6 · 已知诊断','31 / 37','参考基线'],['v7 · 仅姿态重规划','31 / 37','无新增成功'],['v7 · 合用','30 / 37','未采用 · 1 例退步']];
    if(d.v8.pilot)for(const [v,s] of Object.entries(d.v8.pilot.variants))rows.push([v+' · 本轮诊断',`${s.success} / ${s.episodes}`,`${s.rescues.length} 救回 / ${s.regressions.length} 退步`]);
    document.getElementById('progress-table').replaceChildren(...rows.map(cells=>{const tr=document.createElement('tr');for(const s of cells){const td=document.createElement('td');td.textContent=s;tr.append(td);}return tr;}));
    document.getElementById('progress-error').hidden=true;
  }catch(e){document.getElementById('progress-error').hidden=false;}
}
refreshProgress();setInterval(refreshProgress,30000);
