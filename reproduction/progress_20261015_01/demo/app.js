'use strict';
// Data comes from frozen local evidence; no remote requests or result mutation.
const player = document.getElementById('player');
const conditionButtons = [...document.querySelectorAll('[data-condition]')];
const caseButtons = [...document.querySelectorAll('[data-case]')];
const methods = [ ['bc_k2','BC k=2','固定动作偏移'], ['full','Full','世界模型 · 种子 17'], ['plain','Plain','去排序 · 种子 17'] ];
let selectedCondition='clean', selectedCase='full_only_success';
const categoryLabel = c => c.id.includes('full_only') ? 'Full 独胜' : c.id.includes('failure') ? '共同未完成' : '共同成功';
const conditionLabel = c => c.condition==='clean' ? '干净执行' : '加入扰动';
function selectCase(){
  const c=DEMO_DATA.cases.find(c=>c.id===selectedCondition+'_'+selectedCase);
  if(!c) return;
  document.getElementById('demo-title').textContent=selectedCase==='full_only_success'?'这个起点，Full 完成了搬运。':selectedCase==='shared_failure'?'同一起点，仍有共同失败。':'同一起点，对照也能完成。';
  player.pause();
  player.src=c.video;player.poster=c.firstFrame;player.load();
  document.getElementById('media-error').hidden=true;
  conditionButtons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.condition===selectedCondition)));
  caseButtons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.case===selectedCase)));
  document.getElementById('scene-label').textContent=conditionLabel(c)+' / 同一起点 · 同一时间轴';
  document.getElementById('scene-number').textContent=String(DEMO_DATA.cases.indexOf(c)+1).padStart(2,'0')+' / 06';
  document.getElementById('case-info').textContent=c.state_name+' · '+categoryLabel(c)+' · '+c.duration_s.toFixed(1)+' 秒';
  document.getElementById('download').href=c.video;
  document.getElementById('download').setAttribute('download',c.id+'.mp4');
  document.getElementById('outcomes').replaceChildren(...methods.map(([id,name,description])=>{
    const result=c.results[id], box=document.createElement('article');box.className='outcome';
    const info=document.createElement('div'),h=document.createElement('h3'),p=document.createElement('p'),badge=document.createElement('span');
    h.textContent=name;p.textContent=description;info.append(h,p);
    badge.className='status'+(result.success?' success':'');badge.textContent=(result.success?'成功 · ':'未完成 · ')+result.steps+' 步';
    box.append(info,badge);return box;
  }));
  const explanations={shared_success:'三种方法都完成了任务。BC k=2 本身就是有竞争力的基线；这个案例说明，完成任务并不总是需要世界模型。',full_only_success:'从相同状态出发，Full 完成放置，BC 与 Plain 在 400 步内未完成。可以观察它们的动作差异；这是按结果类别选出的说明案例，不代表每个起点都有同样收益。',shared_failure:'三种方法均未在 400 步内完成任务。保留失败过程，才能看清候选选择和评分门限仍然存在的局限。'};
  document.getElementById('scene-description').textContent=explanations[selectedCase];
}
conditionButtons.forEach(b=>b.addEventListener('click',()=>{selectedCondition=b.dataset.condition;selectCase();}));
caseButtons.forEach(b=>b.addEventListener('click',()=>{selectedCase=b.dataset.case;selectCase();}));
document.getElementById('speed').addEventListener('change',e=>{player.playbackRate=Number(e.target.value);});
player.addEventListener('loadedmetadata',()=>{player.playbackRate=Number(document.getElementById('speed').value);});
const playButton=document.getElementById('play-button');
function playLabel(){playButton.innerHTML=player.paused?'播放演示 <span aria-hidden="true">▶</span>':'暂停演示 <span aria-hidden="true">Ⅱ</span>';}
player.addEventListener('play',playLabel);player.addEventListener('pause',playLabel);player.addEventListener('ended',playLabel);
player.addEventListener('error',()=>{document.getElementById('media-error').hidden=false;});
playButton.addEventListener('click',async()=>{if(player.paused){try{await player.play();}catch(e){document.getElementById('media-error').hidden=false;}}else player.pause();});
for(const c of DEMO_DATA.cases){const tr=document.createElement('tr');const values=[conditionLabel(c)+' / '+categoryLabel(c),c.state_name,...methods.map(([id])=>(c.results[id].success?'成功 ':'未完成 ')+c.results[id].steps+' 步')];for(const value of values){const td=document.createElement('td');td.textContent=value;tr.append(td);}document.getElementById('case-table').append(tr);}
for(const condition of ['clean','noise005']){
  const target=document.getElementById(condition==='clean'?'clean-bars':'noise-bars');
  for(const [method,label] of methods){
    const result=DEMO_DATA.statistics.find(r=>r.method===method&&r.condition===condition);
    const row=document.createElement('div');row.className='bar-row '+method;
    const header=document.createElement('div');header.className='bar-label';
    const name=document.createElement('span');name.textContent=label;
    const value=document.createElement('strong');value.textContent=result.rate.toFixed(1)+'%';header.append(name,value);
    const track=document.createElement('div');track.className='bar-track';track.setAttribute('aria-hidden','true');
    const fill=document.createElement('div');fill.className='bar-fill';fill.style.width=result.rate+'%';track.append(fill);
    const detail=document.createElement('p');detail.className='bar-details';detail.textContent=result.counts.join(' / ')+' 成功；'+(method==='bc_k2'?'分母 60':'每种子分母 60');row.append(header,track,detail);target.append(row);
  }
}
selectCase();
