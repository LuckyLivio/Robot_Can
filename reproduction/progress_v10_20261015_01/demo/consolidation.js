'use strict';
const versions=[['v2','v2'],['v4','v4'],['timing_only','仅时间安排'],['side_only','仅侧倒间隙'],['v5','v5 组合']];
const rowCells=(values)=>{const tr=document.createElement('tr');for(const v of values){const td=document.createElement('td');td.textContent=v;tr.append(td);}return tr;};
for(const [v,label] of versions){const m=EVIDENCE.v5_matrix[v],t=EVIDENCE.v5_totals[v];const tr=rowCells([label,m.bc_clean,m.bc_noise,m.full_clean,m.full_noise,`${t.successes} (${(100*t.successes/t.episodes).toFixed(2)}%)`]);if(v==='v5')tr.className='best';document.getElementById('recovery-table').append(tr);}
for(const [v,label] of versions){const g=EVIDENCE.geometry[v];const tr=rowCells([label,g.source_far_alignment.successes,g.destination_corner.successes,g.sideways_source.successes,g.sideways_destination.successes,g.all.successes]);if(v==='v5')tr.className='best';document.getElementById('geometry-table').append(tr);}

const slider=document.getElementById('trace-step'),tracePlay=document.getElementById('trace-play');
const phaseNames={NORMAL:'基础策略',RETRACT:'退回高位',ALIGN:'高位对齐',DESCEND:'下降抓取',CLOSE:'闭合',TEST_LIFT:'试抬确认',LIFT:'抬升',CARRY:'搬运',PLACE:'放置',RELEASE:'释放',RETREAT:'退出',EXHAUSTED:'尝试耗尽'};
const explanations={timing:'同一BC干净起点：v4到400步仍未满足成功条件；v5在384步完成。前段相同，剩余预算下的抬升与搬运安排为释放留下时间。',side:'同一Full s41干净起点：v4两次下降后失败；v5在274步完成。侧倒间隙候选帮助了这一例，并不代表所有窄格都可抓取。',loss:'目标箱侧倒压力起点：v5第171步确认抬升，却在188步失抓；第二次无可行候选，最终仍失败。短暂抓起不等于任务完成。'};
let traceKind='timing',controlStep=1,playing=false,lastTime=null,accumulator=0,animationFrame=null;
tracePlay.dataset.playbackState='paused';tracePlay.setAttribute('aria-pressed','false');
let traceCase=EVIDENCE.trajectory_cases.find(c=>c.kind===traceKind);
const COLORS=['#9298a1','#087fa0'];
function cursorSample(series,key){
  const enabled=document.getElementById('trace-interpolation').checked;
  const t=Math.min(series.steps,controlStep+(playing&&enabled?accumulator:0));
  const i=Math.max(0,Math.floor(t)-1),j=Math.min(series.samples.length-1,i+1),f=t-Math.floor(t);
  return {point:series.samples[i][key].map((v,k)=>v+(series.samples[j][key][k]-v)*f),step:t};
}

function setupCanvas(id){const canvas=document.getElementById(id),ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);ctx.font='22px -apple-system,Segoe UI,Microsoft YaHei,sans-serif';return {canvas,ctx,w:canvas.width,h:canvas.height};}
function axes(ctx,w,h,xmin,xmax,ymin,ymax,xLabel,yLabel){
  const pad={left:90,right:28,top:32,bottom:65},pw=w-pad.left-pad.right,ph=h-pad.top-pad.bottom;
  const px=x=>pad.left+(x-xmin)/(xmax-xmin)*pw,py=y=>pad.top+(ymax-y)/(ymax-ymin)*ph;
  ctx.strokeStyle='#e9e9ee';ctx.lineWidth=1;ctx.fillStyle='#7b7b83';ctx.font='20px sans-serif';ctx.textAlign='center';
  for(let i=0;i<=4;i++){const xv=xmin+(xmax-xmin)*i/4,yv=ymin+(ymax-ymin)*i/4;ctx.beginPath();ctx.moveTo(px(xv),pad.top);ctx.lineTo(px(xv),h-pad.bottom);ctx.stroke();ctx.fillText(xv.toFixed(xmax>5?0:2),px(xv),h-pad.bottom+29);ctx.beginPath();ctx.moveTo(pad.left,py(yv));ctx.lineTo(w-pad.right,py(yv));ctx.stroke();ctx.textAlign='right';ctx.fillText(yv.toFixed(2),pad.left-14,py(yv)+6);ctx.textAlign='center';}
  ctx.fillText(xLabel,pad.left+pw/2,h-12);ctx.save();ctx.translate(23,pad.top+ph/2);ctx.rotate(-Math.PI/2);ctx.fillText(yLabel,0,0);ctx.restore();return {px,py,pad};
}
function drawXY(){
  const {ctx,w,h}=setupCanvas('xy-chart'),{px,py,pad}=axes(ctx,w,h,-.12,.36,-.55,.55,'X / m','Y / m');
  ctx.save();ctx.beginPath();ctx.rect(pad.left,pad.top,w-pad.left-pad.right,h-pad.top-pad.bottom);ctx.clip();
  ctx.fillStyle='#f8f8fa';ctx.strokeStyle='#d8d8df';ctx.lineWidth=2;
  for(const [a,b,c,d] of [[-.09,.29,-.49,-.01],[-.09,.09,.04,.27],[.11,.29,.04,.27],[-.09,.09,.29,.52],[.11,.29,.29,.52]]){ctx.fillRect(px(a),py(d),px(b)-px(a),py(c)-py(d));ctx.strokeRect(px(a),py(d),px(b)-px(a),py(c)-py(d));}
  traceCase.series.forEach((s,i)=>{const samples=s.samples.slice(0,Math.min(controlStep,s.steps));for(const key of ['eef','object']){ctx.beginPath();ctx.strokeStyle=COLORS[i];ctx.globalAlpha=key==='eef'?.55:1;ctx.lineWidth=key==='eef'?3:5;ctx.setLineDash(key==='eef'?[7,7]:[]);samples.forEach((r,j)=>{const [x,y]=r[key];if(j===0)ctx.moveTo(px(x),py(y));else ctx.lineTo(px(x),py(y));});ctx.stroke();ctx.setLineDash([]);const last=samples[samples.length-1];if(last){ctx.fillStyle=COLORS[i];const [x,y]=cursorSample(s,key).point;if(key==='object'){ctx.beginPath();ctx.arc(px(x),py(y),9,0,2*Math.PI);ctx.fill();}else ctx.fillRect(px(x)-5,py(y)-5,10,10);}}});ctx.globalAlpha=1;ctx.restore();
}
function drawHeight(){
  const {ctx,w,h}=setupCanvas('height-chart');const all=traceCase.series.flatMap(s=>s.samples.map(r=>r.object[2]));
  const {px,py,pad}=axes(ctx,w,h,0,400,Math.min(.8,...all)-.025,Math.max(1.14,...all)+.025,'控制步','罐体 Z / m');
  ctx.setLineDash([7,7]);ctx.strokeStyle='#c4c4cc';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(px(0),py(.8));ctx.lineTo(px(400),py(.8));ctx.stroke();ctx.setLineDash([]);
  traceCase.series.forEach((s,i)=>{const samples=s.samples.slice(0,Math.min(controlStep,s.steps));ctx.beginPath();ctx.strokeStyle=COLORS[i];ctx.lineWidth=4;samples.forEach((r,j)=>{if(j===0)ctx.moveTo(px(r.step),py(r.object[2]));else ctx.lineTo(px(r.step),py(r.object[2]));});ctx.stroke();const last=samples[samples.length-1];if(last){ctx.fillStyle=COLORS[i];ctx.beginPath();const cursor=cursorSample(s,'object');ctx.arc(px(cursor.step),py(cursor.point[2]),7,0,2*Math.PI);ctx.fill();}});
  ctx.strokeStyle='#72727b';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(px(controlStep),pad.top);ctx.lineTo(px(controlStep),h-pad.bottom);ctx.stroke();
}
function renderTrace(){
  slider.value=String(controlStep);document.getElementById('trace-step-label').textContent=`${controlStep} / 400`;
  document.getElementById('trace-title').textContent=`${traceCase.demo} · ${traceCase.title}`;document.getElementById('trace-explanation').textContent=explanations[traceKind];
  document.getElementById('trace-status').replaceChildren(...traceCase.series.map((s,i)=>{const r=s.samples[Math.min(controlStep,s.steps)-1],div=document.createElement('div'),strong=document.createElement('strong');const ended=controlStep>=s.steps;strong.textContent=`${s.label} · ${ended?(s.success?'成功，已结束':'400步未完成'):phaseNames[r.phase]||r.phase}`;strong.style.color=COLORS[i];const p=document.createElement('span');p.textContent=`　罐体高度 ${r.object[2].toFixed(3)} m · 指间距 ${(r.gap*1000).toFixed(1)} mm · ${ended?s.steps+'步':controlStep+'步'}`;div.append(strong,p);return div;}));
  document.querySelectorAll('[data-trace-case]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.traceCase===traceKind)));drawXY();drawHeight();
}
function pauseTrace(state='paused'){
  playing=false;
  if(animationFrame!==null)cancelAnimationFrame(animationFrame);
  animationFrame=null;lastTime=null;accumulator=0;
  tracePlay.dataset.playbackState=state;tracePlay.setAttribute('aria-pressed','false');
  tracePlay.textContent=state==='ended'?'重新播放 ↻':'播放轨迹 ▶';
}
document.querySelectorAll('[data-trace-case]').forEach(b=>b.addEventListener('click',()=>{pauseTrace();traceKind=b.dataset.traceCase;traceCase=EVIDENCE.trajectory_cases.find(c=>c.kind===traceKind);controlStep=1;renderTrace();}));
slider.addEventListener('input',()=>{pauseTrace();controlStep=Number(slider.value);renderTrace();});
document.getElementById('trace-end').addEventListener('click',()=>{pauseTrace();controlStep=400;renderTrace();});
tracePlay.addEventListener('click',()=>{
  if(playing){pauseTrace();return;}
  if(controlStep===400)controlStep=1;
  renderTrace();playing=true;lastTime=null;accumulator=0;
  tracePlay.dataset.playbackState='playing';tracePlay.setAttribute('aria-pressed','true');tracePlay.textContent='暂停轨迹 Ⅱ';
  animationFrame=requestAnimationFrame(tick);
});
function tick(now){
  animationFrame=null;if(!playing)return;
  // Use the animation frame's own clock. Its first timestamp can precede the
  // click's performance.now(), which used to turn floor(-epsilon) into -1.
  if(lastTime===null)lastTime=now;
  accumulator+=Math.max(0,now-lastTime)*.02;lastTime=now;
  const increment=Math.floor(accumulator);
  if(increment>0){accumulator-=increment;controlStep=Math.min(400,Math.max(1,controlStep+increment));renderTrace();}
  if(increment===0 && document.getElementById('trace-interpolation').checked){drawXY();drawHeight();}
  if(controlStep===400)pauseTrace('ended');else animationFrame=requestAnimationFrame(tick);
}
document.addEventListener('visibilitychange',()=>{if(document.hidden)pauseTrace();});
renderTrace();

document.getElementById('trace-interpolation').addEventListener('change',()=>{drawXY();drawHeight();});
