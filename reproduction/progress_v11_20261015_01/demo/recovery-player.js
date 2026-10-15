'use strict';
const recoveryPlayer=document.getElementById('recovery-player');
const recoverySelect=document.getElementById('recovery-case');
const recoveryPlay=document.getElementById('recovery-play');
for(const c of RECOVERY_MEDIA){const option=document.createElement('option');option.value=c.id;option.textContent=c.label+' · '+c.demo;recoverySelect.append(option);}
function chooseRecovery(){
  const c=RECOVERY_MEDIA.find(c=>c.id===recoverySelect.value);recoveryPlayer.pause();
  recoveryPlayer.src=c.video;recoveryPlayer.poster=c.poster;recoveryPlayer.load();
  document.getElementById('recovery-case-description').textContent=c.label+' / '+c.demo+'。'+['v6','v8'].map(v=>`${v}：${c.results[v].success?'成功':'未完成'}，${c.results[v].steps} 步`).join('；')+'。';
  document.getElementById('recovery-sources').replaceChildren(...c.sources.map((source,i)=>{const a=document.createElement('a');a.href='../../../'+source;a.textContent=(i===0?'v6':'v8')+' 原始结果 ↗';return a;}));
  document.getElementById('recovery-download').href=c.video;
  document.getElementById('recovery-media-error').hidden=true;
}
recoverySelect.addEventListener('change',chooseRecovery);
recoveryPlayer.addEventListener('error',()=>{document.getElementById('recovery-media-error').hidden=false;});
recoveryPlay.addEventListener('click',async()=>{if(recoveryPlayer.paused){try{await recoveryPlayer.play();}catch(e){document.getElementById('recovery-media-error').hidden=false;}}else recoveryPlayer.pause();});
for(const event of ['play','pause','ended'])recoveryPlayer.addEventListener(event,()=>{recoveryPlay.textContent=recoveryPlayer.paused?'播放对比 ▶':'暂停对比 Ⅱ';});
chooseRecovery();
