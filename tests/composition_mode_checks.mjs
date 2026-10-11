import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validateShowcase,mediaBytes,mountComposition} from '../components/quantum_duet/web/composition-mode.mjs';
const root=new URL('../components/quantum_duet/composition/',import.meta.url);
const bundle={schema:'oxfordq.composition-showcase.v1',data_status:'PRE-GENERATED',backend_jobs_this_playback:0,
 freeze:JSON.parse(fs.readFileSync(new URL('freeze.json',root))),
 raw_samples_text:fs.readFileSync(new URL('raw-samples.json',root),'utf8'),trace_text:fs.readFileSync(new URL('trace.json',root),'utf8'),media:{}};
for(const texture of ['melody','arranged'])for(const ext of ['mid','wav']){
 const name=`improved-${texture}.${ext}`;bundle.media[name]=fs.readFileSync(new URL(name,root)).toString('base64');
}
global.atob=s=>Buffer.from(s,'base64').toString('binary');
validateShowcase(bundle);
for(const mutate of [b=>b.data_status='LIVE',b=>b.backend_jobs_this_playback=1,b=>b.freeze.accepted_commit='changed',b=>delete b.media['improved-melody.wav'],b=>b.raw_samples_text='{"seed":1,"motifs":[]}']){
 const b=JSON.parse(JSON.stringify(bundle));mutate(b);assert.throws(()=>validateShowcase(b));
}
class Node{
 constructor(){this.value='';this.hidden=false;this.disabled=false;this.listeners={};this.paused=true;this.children=[];this.textContent='';}
 addEventListener(name,fn){this.listeners[name]=fn;}pause(){this.paused=true;}load(){}click(){this.onclick?.();}append(n){this.children.push(n);}remove(){}
}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);};
global.document={getElementById:get,createElement:()=>new Node(),body:new Node()};
let urls=0,revoked=[];URL.createObjectURL=()=>`blob:mock-${++urls}`;URL.revokeObjectURL=u=>revoked.push(u);
global.Blob=class{};const listeners={};global.window={addEventListener:(n,f)=>listeners[n]=f,setTimeout(){}};
get('app-mode').value='experiment';get('composition-texture').value='melody';
let stopped=0,loads=0;get('stop').onclick=()=>stopped++;
const logs=[],old=console.log;console.log=s=>logs.push(JSON.parse(s));
mountComposition(async()=>{loads++;return bundle;});
get('app-mode').value='composition';await get('app-mode').onchange();
assert.equal(loads,1);assert.equal(get('duet-app').hidden,true);assert.equal(get('composition-app').hidden,false);
assert.match(get('composition-status').textContent,/PRE-GENERATED.*zero backend/);
const audio=get('composition-audio');audio.paused=false;audio.listeners.play();assert.ok(stopped>0);
get('composition-midi').onclick();assert.equal(logs.at(-1).filename,'oxfordq-composition-melody.mid');
assert.deepEqual(Buffer.from(mediaBytes(logs.at(-1).payload)),fs.readFileSync(new URL('improved-melody.mid',root)));
get('composition-texture').value='arranged';get('composition-texture').onchange();assert.equal(audio.paused,true);
get('composition-midi').onclick();assert.equal(logs.at(-1).filename,'oxfordq-composition-arranged.mid');
assert.deepEqual(Buffer.from(mediaBytes(logs.at(-1).payload)),fs.readFileSync(new URL('improved-arranged.mid',root)));
get('composition-json').onclick();const provenance=JSON.parse(logs.at(-1).payload);
assert.equal(provenance.raw_samples_text,bundle.raw_samples_text);assert.equal(provenance.trace_text,bundle.trace_text);
get('app-mode').value='experiment';await get('app-mode').onchange();assert.equal(audio.paused,true);assert.equal(get('duet-app').hidden,false);
get('app-mode').value='composition';await get('app-mode').onchange();assert.equal(loads,1);
listeners.pagehide();assert.equal(audio.paused,true);assert.ok(revoked.length>=2);
// Failed optional loader leaves the Experiment usable and submits no replacement job.
mountComposition(async()=>{throw Error('missing frozen asset');});
await get('app-mode').onchange();assert.match(get('composition-status').textContent,/unavailable.*Experiment mode remains available/);
get('app-mode').value='experiment';await get('app-mode').onchange();assert.equal(get('duet-app').hidden,false);
console.log=old;
console.log(JSON.stringify({status:'passed',timestamp_utc:new Date().toISOString(),scope:'Node mocked DOM/media, exact frozen exports and optional failure isolation; actual browser separate'}));
