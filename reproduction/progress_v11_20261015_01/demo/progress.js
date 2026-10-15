'use strict';
async function refreshProgress(){
  try {
    const r=await fetch('progress.json',{cache:'no-store'});if(!r.ok)throw new Error('status unavailable');
    const d=await r.json();document.getElementById('progress-time').textContent='更新于 '+d.updated;
    document.getElementById('v11-state').textContent=d.v11.status;
    const rows=[['v6 · 历史已知诊断','31 / 37','参考基线'],['v10 · 历史合用','30 / 37','未采用 · 1例退步']];
    if(d.v11.variants)for(const [v,s] of Object.entries(d.v11.variants))rows.push([v+' · '+d.v11.stage,`${s.success} / ${s.episodes}`,s.regressions?`${s.rescues.length} 救回 / ${s.regressions.length} 退步`:'仅统计已完成回合']);
    document.getElementById('progress-table').replaceChildren(...rows.map(cells=>{const tr=document.createElement('tr');for(const s of cells){const td=document.createElement('td');td.textContent=s;tr.append(td);}return tr;}));
    if(d.v11.summary) document.getElementById('progress-metrics').textContent=d.v11.summary;
    if(d.v11.development){
      const dev=d.v11.development;
      const groups=dev.groups.map(g=>[g.condition,`${g.v6_success} / ${g.episodes}`,`${g.v11_success} / ${g.episodes}`]);
      groups.push(['合计',`${dev.v6_success} / ${dev.episodes}`,`${dev.v11_success} / ${dev.episodes}`]);
      document.getElementById('development-table').replaceChildren(...groups.map(cells=>{const tr=document.createElement('tr');for(const s of cells){const td=document.createElement('td');td.textContent=s;tr.append(td);}return tr;}));
    }
    document.getElementById('progress-error').hidden=true;
  }catch(e){document.getElementById('progress-error').hidden=false;}
}
refreshProgress();setInterval(refreshProgress,30000);
const edgePlayer=document.getElementById('edge-player');
const edgePlay=document.getElementById('edge-play');
const edgeError=document.getElementById('edge-error');
edgePlay.addEventListener('click',async()=>{
  if(!edgePlayer.paused){edgePlayer.pause();return;}
  try{await edgePlayer.play();edgeError.hidden=true;}catch(e){edgeError.hidden=false;}
});
edgePlayer.addEventListener('play',()=>{edgePlay.textContent='暂停箱沿对比 ⏸';});
edgePlayer.addEventListener('pause',()=>{edgePlay.textContent='播放箱沿对比 ▶';});
edgePlayer.addEventListener('error',()=>{edgeError.hidden=false;});
