'use strict';
// Run the real display script with a deterministic clock and minimal canvas DOM.
// This is a software regression test; it does not launch a browser or simulator.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const run=__dirname,root=path.resolve(run,'../..');
const legacy=process.argv.includes('--expect-bug');
const source=legacy?path.join(run,'before/consolidation.js'):path.join(root,'reproduction/consolidation_20261012_01/demo/consolidation.js');
const data=JSON.parse(fs.readFileSync(path.join(root,'reproduction/consolidation_20261012_01/evidence.json'),'utf8'));
const elements=new Map();
class Element{
 constructor(){this.listeners={};this.dataset={};this.attrs={};this.style={};this.textContent='';this.value='1';this.width=1000;this.height=650;}
 addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);}
 emit(name){for(const fn of this.listeners[name]??[])fn({target:this});}
 append(){} replaceChildren(){}
 setAttribute(k,v){this.attrs[k]=v;}
 getContext(){return new Proxy({},{get:(o,k)=>o[k]??(()=>{}),set:(o,k,v)=>(o[k]=v,true)});}
}
const get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
const caseButtons=['timing','side','loss'].map(kind=>{const e=new Element();e.dataset.traceCase=kind;return e;});
let nextId=1;const frames=new Map();
const doc={getElementById:get,createElement:()=>new Element(),querySelectorAll:()=>caseButtons,addEventListener:()=>{},hidden:false};
const context=vm.createContext({document:doc,EVIDENCE:data,performance:{now:()=>1000},
 requestAnimationFrame:fn=>{const id=nextId++;frames.set(id,fn);return id;},cancelAnimationFrame:id=>frames.delete(id)});
vm.runInContext(fs.readFileSync(source,'utf8'),context,{filename:source});
const frame=now=>{const pending=[...frames.values()];frames.clear();for(const fn of pending)fn(now);};
const number=()=>Number(get('trace-step-label').textContent.split(' / ')[0]);
const select=kind=>caseButtons.find(b=>b.dataset.traceCase===kind).emit('click');
if(legacy){
 select('loss');get('trace-play').emit('click');let error;
 try{frame(999);}catch(e){error=e.message;}
 assert.equal(number(),0);assert.ok(error?.includes('undefined'));
 const result={reproduced:true,case:'loss',clock_start_ms:1000,first_frame_ms:999,invalid_step:number(),error};
 fs.writeFileSync(path.join(run,'regression_before.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}else{
 const results=[];
 for(const kind of ['timing','side','loss']){
  select(kind);assert.equal(number(),1);get('trace-play').emit('click');assert.equal(frames.size,1);
  frame(999);assert.equal(number(),1);frame(998);assert.equal(number(),1);
  frame(1049);assert.equal(number(),2);
  for(let i=1;i<=398;i++){frame(1049+i*50);assert.ok(number()>=1&&number()<=400);}
  assert.equal(number(),400);assert.equal(frames.size,0);assert.equal(get('trace-play').dataset.playbackState,'ended');
  get('trace-play').emit('click');assert.equal(number(),1);assert.equal(frames.size,1);frame(100);assert.equal(number(),1);
  get('trace-play').emit('click');assert.equal(frames.size,0);assert.equal(get('trace-play').attrs['aria-pressed'],'false');
  results.push({case:kind,all_400_steps:true,early_frame_guard:true,backward_clock_guard:true,automatic_end:true,replay:true,pause_cancels_frame:true});
 }
 select('timing');get('trace-play').emit('click');select('side');assert.equal(frames.size,0);get('trace-play').emit('click');assert.equal(frames.size,1);
 frame(999);frame(1049);assert.equal(number(),2);
 get('trace-step').value='188';get('trace-step').emit('input');assert.equal(number(),188);assert.equal(frames.size,0);
 get('trace-play').emit('click');frame(50000);assert.equal(number(),188);frame(50050);assert.equal(number(),189);
 select('loss');assert.equal(frames.size,0);get('trace-end').emit('click');assert.equal(number(),400);
 const result={passed:true,cases:results,switch_cancels_stale_loop:true,scrub_pauses:true,resume_rebases_clock:true};
 fs.writeFileSync(path.join(run,'regression_after.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}
