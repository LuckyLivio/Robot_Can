'use strict';
// Display existing measurements; the mechanism diagram is explicitly conceptual.
const modelSteps=[
 '读取23维仿真状态，固定BC提出k=0/1/2/3四个动作候选。k=2指动作块的第三项，并不是预测两步后的真实状态。',
 '将实际FIFO中待执行的两条命令作为每个候选共同的预测前缀，再接入候选动作。预测考虑命令延迟，不能从空队列假设起算。',
 'GRU动力学模型向前展开H=8步。学习评分结合任务进展与失抓风险比较候选；8步包含前面两步等待命令，不是8步全由新动作驱动。',
 '候选评分优势超过0.02才替换BC k=2；否则回退。每次只提交一个动作，在下一次观测后重新规划。门限不是经过校准的安全保证。'
];
const stepButtons=[...document.querySelectorAll('[data-model-step]')];
function showModelStep(index){
 stepButtons.forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.modelStep)===index)));
 document.getElementById('model-step-detail').textContent=modelSteps[index];
 document.getElementById('visual-stage').textContent=['读取状态','还原延迟','预测候选','执行再规划'][index];
}
stepButtons.forEach(b=>b.addEventListener('click',()=>showModelStep(Number(b.dataset.modelStep))));showModelStep(0);
const gain=WORLD_MODEL_VIEW.object_rmse_reduction_percent.toFixed(1);
document.querySelectorAll('[data-object-gain]').forEach(el=>el.textContent=gain);
const clean=DEMO_DATA.statistics.find(r=>r.method==='full'&&r.condition==='clean');
document.getElementById('headline-success').textContent=clean.rate.toFixed(0);
document.getElementById('headline-effect').textContent='+'+WORLD_MODEL_VIEW.confirmation_joint_effect.mean_difference_pp.toFixed(2);
for(const r of WORLD_MODEL_VIEW.rows){
 const tr=document.createElement('tr');
 const label={full:'Full（世界模型）',plain:'Plain（去排序）',persistence:'持续性（状态保持）'}[r.method];
 [label,(r.eef_position_rmse_m*1000).toFixed(2),(r.object_position_rmse_m*1000).toFixed(2),r.normalized_state_mse.toFixed(4)].forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td);});
 document.getElementById('prediction-table').append(tr);
}
