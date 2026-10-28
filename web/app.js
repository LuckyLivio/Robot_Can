/* CAN LAB: buildless, offline-capable presentation of frozen research evidence. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const data = window.CANLAB_DATA;
  const esc = value => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const fixed = (n, digits = 2) => Number.isFinite(Number(n)) ? Number(n).toFixed(digits) : "—";
  const signed = n => `${Number(n) > 0 ? "+" : ""}${fixed(n)}`;
  let toastTimer;
  function toast(message) {
    $("toast").textContent = message;
    $("toast").classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $("toast").classList.remove("show"), 2600);
  }
  if (!data || !Array.isArray(data.cells) || !data.cases.length) {
    $("heroSuccessDetail").textContent = "数据未能载入，请确认web/data.js存在并刷新页面。";
    $("caseTitle").textContent = "未找到回放数据";
    $("playButton").disabled = true;
    return;
  }
  const state = {policy:"full", noise:"joint", metric:"success", showCandidate:false, caseId:data.meta.default_case, runIndex:0, frame:0, playing:false};
  const policyLabel = p => p === "full" ? "Full" : "BC";
  const controlLabel = c => ({none:"无恢复",v5:"v5恢复",queue_budget:"预算候选"}[c] || c);
  const noiseLabel = n => n === "joint" ? "两条件等权" : Number(n) === 0 ? "干净环境" : "噪声0.05";
  function aggregate(policy, controller) {
    const cells = data.cells.filter(c => c.policy === policy && c.controller === controller && (state.noise === "joint" || c.noise === Number(state.noise)));
    return cells.reduce((a,c) => ({successes:a.successes+c.successes,total:a.total+c.total,stable:a.stable+c.stable}), {successes:0,total:0,stable:0});
  }
  function rate(cell, metric = state.metric) { return 100 * (metric === "success" ? cell.successes : cell.stable) / cell.total; }
  function getEffect(contrast, method, comparison) {
    const noise = state.noise === "joint" ? "equal_noise_joint" : Number(state.noise);
    return data.effects.find(e => e.contrast === contrast && e.method === method && e.noise === noise && e.metric === (state.metric === "success" ? "success" : "stable") && (!comparison || e.comparison === comparison));
  }
  function renderResults() {
    const selected = aggregate(state.policy,"v5");
    const successRate = rate(selected,"success");
    $("heroSuccess").innerHTML = `${fixed(successRate)}<small>%</small>`;
    $("metricConfig").textContent = `${policyLabel(state.policy)} + v5 · ${noiseLabel(state.noise)}`;
    $("heroSuccessDetail").textContent = `${selected.successes} / ${selected.total}次执行 · 60个独立起点`;
    $("horizonTitle").textContent = state.policy === "full" ? "世界模型预测时域" : "BC输出动作块";
    $("horizonDetail").textContent = state.policy === "full" ? "4条候选 · 每周期只提交1条命令" : "固定索引2 · 世界模型未启用";
    document.querySelectorAll("[data-policy]").forEach(b => {
      const active = b.dataset.policy === state.policy;
      b.setAttribute("aria-pressed", String(active));
      b.querySelector("i").textContent = active ? "当前展示" : "切换查看";
    });
    document.querySelectorAll("[data-noise]").forEach(b => b.setAttribute("aria-pressed",String(b.dataset.noise === state.noise)));
    $("chartTitle").textContent = state.metric === "success" ? "任务成功率" : "稳定成功 / 全部执行";
    $("conditionLabel").textContent = noiseLabel(state.noise);
    const configs = [["bc","none"],["full","none"],["bc","v5"],["full","v5"]];
    if (state.showCandidate) configs.push(["bc","queue_budget"],["full","queue_budget"]);
    $("comparisonBars").innerHTML = configs.map(([p,c]) => {
      const a = aggregate(p,c), r = rate(a), n = state.metric === "success" ? a.successes : a.stable;
      return `<div class="comparison-row${p === state.policy && c === "v5" ? " selected" : ""}${c === "queue_budget" ? " candidate" : ""}"><div class="bar-label">${policyLabel(p)}${c === "v5" ? " + v5" : c === "queue_budget" ? " + 预算候选" : ""}<small>${c === "v5" ? "冻结共享恢复" : c === "none" ? "策略直接控制" : "尚未采用"}</small></div><div class="bar-track" role="img" aria-label="${esc(policyLabel(p)+" "+controlLabel(c))}：${fixed(r)}%，${n}/${a.total}"><span class="bar-fill" style="width:${r}%"></span></div><div class="bar-value">${fixed(r)}%<small>${n} / ${a.total}</small></div></div>`;
    }).join("");
    $("selectedConfig").textContent = `${policyLabel(state.policy)} + v5`;
    $("selectedRate").innerHTML = `${fixed(rate(selected))}<small>%</small>`;
    $("selectedCount").textContent = `${state.metric === "success" ? selected.successes : selected.stable} / ${selected.total}次${state.metric === "success" ? "任务成功" : "稳定成功"}`;
    $("selectedStable").textContent = `${selected.stable}/${selected.total} · ${fixed(rate(selected,"stability"))}%`;
    const timing = data.timing.entries.find(t => t.policy === state.policy && t.noise === (state.noise === "joint" ? "joint" : Number(state.noise)));
    $("selectedLatency").textContent = timing ? `${fixed(timing.p95_ms)} ms` : "—";
    const effect = getEffect("recovery_effect",state.policy,"v5 - none");
    const world = getEffect("world_model_effect","v5");
    const metricName = state.metric === "success" ? "任务成功率" : "稳定成功率";
    $("effectSummary").textContent = effect && world
      ? `v5使${policyLabel(state.policy)}的${metricName}变化${signed(effect.effect)}个百分点（95%区间 ${fixed(effect.ci95_low)}～${fixed(effect.ci95_high)}）。相同v5下，Full相对BC为${signed(world.effect)}个百分点（${fixed(world.ci95_low)}～${fixed(world.ci95_high)}）。`
      : "当前条件的配对区间请查看完整配对结果。";
    $("resultTable").innerHTML = data.cells.filter(c => state.noise === "joint" || c.noise === Number(state.noise)).map(c => `<tr><td>${policyLabel(c.policy)} · ${controlLabel(c.controller)}</td><td>${noiseLabel(c.noise)}</td><td>${c.successes}/${c.total} · ${fixed(c.success_rate*100)}%</td><td>${c.stable}/${c.total} · ${fixed(c.stable_rate*100)}%</td><td>${c.controller === "queue_budget" ? "未采用候选" : "正式对照"}</td></tr>`).join("");
  }
  document.querySelectorAll("[data-policy]").forEach(b => b.addEventListener("click",() => {state.policy=b.dataset.policy;renderResults();}));
  document.querySelectorAll("[data-noise]").forEach(b => b.addEventListener("click",() => {state.noise=b.dataset.noise;renderResults();}));
  $("outcomeSelect").addEventListener("change",e => {state.metric=e.target.value;renderResults();});
  $("showCandidate").addEventListener("change",e => {state.showCandidate=e.target.checked;renderResults();});

  const phaseNames = {NORMAL:"正常监测",RETRACT:"回撤",ALIGN:"对齐",DESCEND:"下降",CLOSE:"闭爪",TEST_LIFT:"试抬确认",LIFT:"抬升",CARRY:"搬运",PLACE:"放置",RELEASE:"释放",RETREAT:"退出",EXHAUSTED:"停止恢复覆盖"};
  const phaseColors = {NORMAL:"#c3d1b7",RETRACT:"#8da67b",ALIGN:"#74966a",DESCEND:"#5b865c",CLOSE:"#3b7350",TEST_LIFT:"#275f43",LIFT:"#3e7e70",CARRY:"#5d9b87",PLACE:"#89af91",RELEASE:"#c2a16c",RETREAT:"#9c996e",EXHAUSTED:"#b48765"};
  const currentCase = () => data.cases.find(c => c.id === state.caseId) || data.cases[0];
  const currentRun = () => currentCase().runs[state.runIndex];
  const currentFrame = () => currentRun().frames[state.frame];
  const actionText = a => `[${a.slice(0,3).map(n => fixed(n,2)).join(", ")}]`;
  let raf=0, lastTick=0, playhead=0;
  function pause() {
    state.playing=false;cancelAnimationFrame(raf);
    $("playButton").textContent="▶";$("playButton").setAttribute("aria-label","播放轨迹");
  }
  function seek(index) {
    state.frame=Math.min(Math.max(Math.round(index),0),currentRun().frames.length-1);
    playhead=state.frame;renderFrame();
  }
  function tick(now) {
    if (!state.playing) return;
    playhead += Math.min(now-lastTick,150) / 1000 * data.meta.control_hz * Number($("playbackSpeed").value);
    lastTick=now;
    state.frame=Math.min(Math.floor(playhead),currentRun().frames.length-1);
    renderFrame();
    if (state.frame === currentRun().frames.length-1) pause();
    else raf=requestAnimationFrame(tick);
  }
  function play() {
    if (state.frame===currentRun().frames.length-1) seek(0);
    state.playing=true;playhead=state.frame;lastTick=performance.now();
    $("playButton").textContent="Ⅱ";$("playButton").setAttribute("aria-label","暂停轨迹");
    raf=requestAnimationFrame(tick);
  }
  function renderTimeline() {
    const frames=currentRun().frames, segments=[];
    frames.forEach((f,i) => {
      const phase=f.nextPhase;
      const last=segments[segments.length-1];
      if (last && last.phase===phase) last.end=i;
      else segments.push({phase,start:i,end:i});
    });
    $("phaseTimeline").innerHTML=segments.map(s => `<button data-frame="${s.start}" style="flex-grow:${s.end-s.start+1};background:${phaseColors[s.phase]||"#9fae92"}" title="${esc(phaseNames[s.phase]||s.phase)}：第${s.start+1}～${s.end+1}步" aria-label="跳到${esc(phaseNames[s.phase]||s.phase)}，第${s.start+1}步"></button>`).join("");
  }
  function selectCase(id) {
    pause();state.caseId=id;state.runIndex=0;state.frame=0;playhead=0;
    const c=currentCase();
    document.querySelectorAll("[data-case]").forEach(b => b.setAttribute("aria-pressed",String(b.dataset.case===c.id)));
    $("runSelect").innerHTML=c.runs.map((r,i) => `<option value="${i}">${esc(r.label)}</option>`).join("");
    $("caseTitle").textContent=c.title;$("caseDescription").textContent=c.description;
    $("caseKind").textContent="Full · seed17";
    selectRun(0);
  }
  function selectRun(index) {
    pause();state.runIndex=index;state.frame=0;playhead=0;
    const r=currentRun(), c=currentCase();
    $("frameSlider").max=r.frames.length-1;$("frameSlider").value=0;
    $("caseMeta").textContent=`${c.demo} · ${noiseLabel(c.noise)} · ${r.steps}步 · ${r.label}`;
    $("runOutcome").textContent=r.success ? "回合成功" : "回合未完成";
    $("runOutcome").classList.toggle("failure",!r.success);
    $("rawTraceLink").href=r.source;
    renderTimeline();renderFrame();
  }
  function renderFrame() {
    const f=currentFrame(),r=currentRun(),phase=f.nextPhase;
    $("frameSlider").value=state.frame;
    $("stepLabel").textContent=`${f.step} / ${r.frames.length}步`;
    const name=r.controller==="none" ? "无恢复 · 策略执行" : phaseNames[phase] || phase;
    $("phaseBadge").textContent=`${phase} / ${name}`;
    $("inspectorPhase").textContent=name;
    $("frameTime").textContent=`${f.step} / ${fixed((f.step-1)/data.meta.control_hz)} s`;
    $("frameHolding").textContent=f.holding ? "已确认抓持" : "未确认抓持";
    $("frameAttempts").textContent=`${f.attempts} / 2次`;
    $("frameHeight").textContent=`${fixed(f.object[2],3)} m`;
    $("candidateIndex").textContent=`k = ${f.selected}`;
    $("candidateScores").innerHTML=Array.isArray(f.scores) ? f.scores.map((s,i) => `<div class="score-block${i===f.selected?" selected":""}"><small>候选 ${i}</small>${fixed(s,3)}</div>`).join("") : '<span class="no-score">当前方法不使用候选评分</span>';
    $("pendingZero").textContent=actionText(f.queue[0]);$("pendingOne").textContent=actionText(f.queue[1]);
    $("submittedAction").textContent=actionText(f.submitted);$("executedAction").textContent=actionText(f.executed);
    drawTrajectory();
  }
  const canvas=$("trajectoryCanvas"),ctx=canvas.getContext("2d");
  function drawTrajectory() {
    if (!ctx) return;
    const width=canvas.clientWidth, height=canvas.clientHeight;
    if (!width || !height) return;
    const dpr=Math.min(window.devicePixelRatio||1,2);
    if (canvas.width!==Math.round(width*dpr)||canvas.height!==Math.round(height*dpr)) {canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);}
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);
    const frames=currentRun().frames, f=currentFrame();
    const all=currentCase().runs.flatMap(r => r.frames.flatMap(v => [v.eef,v.object]));
    const xmin=Math.min(-.24,...all.map(p=>p[0]))-.02,xmax=Math.max(.4,...all.map(p=>p[0]))+.02;
    const ymin=Math.min(-.55,...all.map(p=>p[1]))-.02,ymax=Math.max(.55,...all.map(p=>p[1]))+.02;
    const pad={left:41,right:55,top:42,bottom:37};
    const w=width-pad.left-pad.right,h=height-pad.top-pad.bottom;
    const x=v=>pad.left+(v-xmin)/(xmax-xmin)*w,y=v=>pad.top+(ymax-v)/(ymax-ymin)*h;
    ctx.font='9px "Segoe UI","Microsoft YaHei",sans-serif';ctx.textBaseline="middle";
    ctx.strokeStyle="#dce5d2";ctx.lineWidth=1;
    for (const value of [-.2,0,.2,.4]) {const p=x(value);ctx.beginPath();ctx.moveTo(p,pad.top);ctx.lineTo(p,height-pad.bottom);ctx.stroke();ctx.fillStyle="#9dab90";ctx.textAlign="center";ctx.fillText(fixed(value,1),p,height-pad.bottom+13);}
    for (const value of [-.5,-.25,0,.25,.5]) {const p=y(value);ctx.beginPath();ctx.moveTo(pad.left,p);ctx.lineTo(width-pad.right,p);ctx.stroke();ctx.fillStyle="#9dab90";ctx.textAlign="right";ctx.fillText(fixed(value,2),pad.left-8,p);}
    function area(x0,y0,x1,y1,label){ctx.fillStyle="#e5ecda80";ctx.fillRect(x(x0),y(y1),x(x1)-x(x0),y(y0)-y(y1));ctx.strokeStyle="#c9d8b9";ctx.setLineDash([4,4]);ctx.strokeRect(x(x0),y(y1),x(x1)-x(x0),y(y0)-y(y1));ctx.setLineDash([]);ctx.fillStyle="#a2b292";ctx.textAlign="right";ctx.fillText(label,x(x1)-6,y(y1)+11);}
    area(-.095,-.495,.295,-.005,"抓取箱参考区域");area(-.095,.035,.295,.525,"放置箱参考区域");
    function trail(key,end,color,alpha,lineWidth){ctx.save();ctx.globalAlpha=alpha;ctx.strokeStyle=color;ctx.lineWidth=lineWidth;ctx.lineJoin="round";ctx.lineCap="round";ctx.beginPath();frames.slice(0,end+1).forEach((v,i)=>i?ctx.lineTo(x(v[key][0]),y(v[key][1])):ctx.moveTo(x(v[key][0]),y(v[key][1])));ctx.stroke();ctx.restore();}
    trail("eef",frames.length-1,"#356b47",.16,1.3);trail("object",frames.length-1,"#b78042",.19,1.3);
    trail("eef",state.frame,"#214b39",.9,2);trail("object",state.frame,"#b67b3f",1,2.4);
    const ex=x(f.eef[0]),ey=y(f.eef[1]),ox=x(f.object[0]),oy=y(f.object[1]);
    ctx.strokeStyle="#214b39";ctx.lineWidth=1.8;ctx.beginPath();ctx.arc(ex,ey,7,0,Math.PI*2);ctx.stroke();ctx.beginPath();ctx.moveTo(ex-11,ey);ctx.lineTo(ex+11,ey);ctx.moveTo(ex,ey-11);ctx.lineTo(ex,ey+11);ctx.stroke();
    ctx.fillStyle="#b67b3f";ctx.beginPath();ctx.arc(ox,oy,5.5,0,Math.PI*2);ctx.fill();ctx.strokeStyle="#fffcf3";ctx.lineWidth=2;ctx.stroke();
    const zX=width-24,zTop=60,zBottom=height-46,z=Math.max(0,Math.min(1,(f.object[2]-.8)/.45));
    ctx.fillStyle="#e0e8d6";ctx.fillRect(zX-3,zTop,6,zBottom-zTop);ctx.fillStyle="#b68a53";ctx.fillRect(zX-3,zBottom-z*(zBottom-zTop),6,z*(zBottom-zTop));
    ctx.textAlign="center";ctx.fillStyle="#94a582";ctx.font='8px "Segoe UI",sans-serif';ctx.fillText("Z(m)",zX,zTop-14);ctx.fillText(fixed(f.object[2],2),zX,zBottom+12);
    ctx.textAlign="right";ctx.fillText("X(m)",width-pad.right+13,height-pad.bottom+13);
  }
  $("caseTabs").innerHTML=data.cases.map(c=>`<button data-case="${esc(c.id)}" aria-pressed="false">${esc({recovered:"恢复救回",success:"常规成功",failure:"保留失败"}[c.kind])}<span>${esc(noiseLabel(c.noise))} · Full seed17</span></button>`).join("");
  $("caseTabs").addEventListener("click",e=>{const b=e.target.closest("[data-case]");if(b)selectCase(b.dataset.case);});
  $("runSelect").addEventListener("change",e=>selectRun(Number(e.target.value)));
  $("playButton").addEventListener("click",()=>state.playing?pause():play());
  $("prevFrame").addEventListener("click",()=>{pause();seek(state.frame-1);});
  $("nextFrame").addEventListener("click",()=>{pause();seek(state.frame+1);});
  $("frameSlider").addEventListener("input",e=>seek(Number(e.target.value)));
  $("phaseTimeline").addEventListener("click",e=>{const b=e.target.closest("[data-frame]");if(b){pause();seek(Number(b.dataset.frame));}});
  $("downloadCase").addEventListener("click",()=>{
    const run=currentRun(),c=currentCase();
    const blob=new Blob([JSON.stringify({kind:"display_quantized_trace",note:data.meta.case_scope,case:c.id,...run},null,2)],{type:"application/json"});
    const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=`${run.job}_${c.demo}_display.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast("已导出当前回合；原始全精度日志另有链接。");
  });
  const modules={
    state:{eyebrow:"OBSERVATION CONTRACT",title:"在同一时刻，组织状态与坐标关系。",description:"读取末端位姿、夹爪关节量、物体相对位姿与世界位姿，组成23维输入。正式冻结策略使用legacy兼容语义；新canonical入口用于匹配重训与几何一致性研究。",tags:["23维状态","xyzw四元数","匹配观测语义"],input:"仿真器观测 / 位姿与关节量",output:"xₜ ∈ R²³",boundary:"当前使用含物体真值的低维仿真状态；展示画面没有作为视觉输入。"},
    bc:{eyebrow:"BEHAVIOR CLONING",title:"从示范中学习，生成下一段动作。",description:"三层512宽度MLP配合5分量混合密度输出，生成8步七维动作块。部署确定性选择混合权重最大的分量均值，从前四条命令中构造有限候选。",tags:["3 × 512 MLP","5分量MDN","8 × 7动作块"],input:"当前状态 xₜ",output:"动作块 Aₜ ∈ R⁸ˣ⁷",boundary:"BC是本项目的强基线。关闭世界模型时固定选择动作块索引2，与D2补偿规则保持一致。"},
    world:{eyebrow:"ACTION-CONDITIONED WORLD MODEL",title:"以动作作为条件，预测未来状态。",description:"128宽度GRU以标准化状态递推，预测动作带来的短期变化。每个候选保留相同的两条真实在途命令，后接重复候选；用进展与失持读出比较8步后果，仅提交一条新命令。",tags:["87,321个参数","4候选 × 8步","冻结权重 / future_only"],input:"23维状态 + D2队列 + 候选命令",output:"未来状态 / 进展与失持logits",boundary:"分数提升不足0.02时保守回退索引2。主确认日志保存候选分数，未保存完整预测轨迹。"},
    recovery:{eyebrow:"INDEPENDENT RECOVERY SUPERVISOR",title:"根据观测历史，把异常转为有界恢复。",description:"冻结v5独立检测抓持丢失、停滞与时间压力，按回撤、对齐、闭爪、试抬、抬升、搬运和释放等阶段恢复。最多发起两次尝试，第二次仍可继续完成。",tags:["5帧抓持确认","最多2次尝试","400步回合预算"],input:"状态 + 建议动作 + 上次实际动作",output:"提交命令 + 控制阶段诊断",boundary:"不接收世界模型评分、奖励或成功标签。EXHAUSTED表示停止覆盖并透传策略，不代表紧急停机。"},
    queue:{eyebrow:"DELAYED CLOSED-LOOP EXECUTION",title:"把在途命令，纳入每次闭环决策。",description:"真实先进先出队列保存两条已提交命令，当前周期执行队首、新命令进入队尾。出队后仅对平移前三维加入配置噪声，再限幅并推进环境；随后重新观测和决策。",tags:["20 Hz控制","D2 / 100 ms","出队后加噪"],input:"队列 [q₀, q₁] + 本步提交 uₜ",output:"实际动作 aₜ / 下一帧观测",boundary:"新提交与实际执行相隔两个控制周期。控制计算计时不包含物理推进、文件写入或真机通信。"}
  };
  function selectModule(key){const m=modules[key];document.querySelectorAll("[data-module]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.module===key)));$("moduleEyebrow").textContent=m.eyebrow;$("moduleTitle").textContent=m.title;$("moduleDescription").textContent=m.description;$("moduleInput").textContent=m.input;$("moduleOutput").textContent=m.output;$("moduleBoundary").textContent=m.boundary;$("moduleTags").innerHTML=m.tags.map(t=>`<span>${esc(t)}</span>`).join("");}
  document.querySelectorAll("[data-module]").forEach(b=>b.addEventListener("click",()=>selectModule(b.dataset.module)));
  $("presentationToggle").addEventListener("click",e=>{const active=document.body.classList.toggle("presentation");e.currentTarget.setAttribute("aria-pressed",String(active));drawTrajectory();});
  $("copyCommand").addEventListener("click",async()=>{
    const text=$("serverCommand").textContent;
    try{await navigator.clipboard.writeText(text);toast("启动命令已复制");}
    catch{const selection=window.getSelection(),range=document.createRange();range.selectNodeContents($("serverCommand"));selection.removeAllRanges();selection.addRange(range);toast("请使用Ctrl+C复制已选中的命令");}
  });
  $("openHistory").addEventListener("click",()=>{$("historyDialog").showModal();$("historyVideo").load();});
  $("closeHistory").addEventListener("click",()=>$("historyDialog").close());
  $("historyDialog").addEventListener("close",()=>$("historyVideo").pause());
  $("historyDialog").addEventListener("click",e=>{if(e.target===$("historyDialog")){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
  const sections=Array.from(document.querySelectorAll(".section-anchor"));
  let navFrame=0;
  function updateNavigation(){
    navFrame=0;let active=sections[0];const line=Math.min(innerHeight*.25,180);
    for(const section of sections)if(section.getBoundingClientRect().top<=line)active=section;
    document.querySelectorAll(".side-nav a").forEach(a=>a.classList.toggle("active",a.hash===`#${active.id}`));
  }
  window.addEventListener("scroll",()=>{if(!navFrame)navFrame=requestAnimationFrame(updateNavigation);},{passive:true});
  window.addEventListener("resize",updateNavigation);
  document.addEventListener("visibilitychange",()=>{if(document.hidden)pause();});
  new ResizeObserver(()=>drawTrajectory()).observe(canvas);
  renderResults();selectCase(state.caseId);selectModule("world");updateNavigation();
})();
