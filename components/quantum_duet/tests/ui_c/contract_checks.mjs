import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validateEnvelope,envelopeView,freezeJSON,arrangedPlayback,exportEnvelope,readEnvelope} from '../../web/run-contract.mjs';
import {midiBytes,DuetAudio,mountDuet} from '../../web/ui.mjs';
const original=fs.readFileSync(new URL('../../../../docs/team/fixtures/run-result.v1.json',import.meta.url),'utf8');
const fixture=JSON.parse(original),copy=()=>JSON.parse(original);
validateEnvelope(fixture);
const reordered=copy();reordered.execution.experiments.reverse();validateEnvelope(reordered);
const take=envelopeView(fixture);
assert.equal(take.excerpt.quantum.wins,fixture.rounds.filter(r=>r.quantum.win).length);
assert.equal(take.events.quantum.length,32);
assert.equal(fixture.execution.backend_run_calls_this_replay,0);
for(const mutate of [
 d=>d.contract_version='unknown', d=>d.events.quantum.pop(), d=>d.events.quantum[0].round_id='wrong',
 d=>d.events.quantum[0].velocity=0,d=>d.events.quantum[0].duration_beats=NaN,
 d=>d.events.quantum[0].pitch_midi=128,d=>d.events.quantum[1]={...d.events.quantum[0]},
 d=>d.execution.experiments[0].counts['10']=1.5,d=>d.statistics.total_independent_shots=5120,
 d=>d.models.qcbm_checkpoint_sha256='unknown',d=>d.rounds[0].quantum.displayed_ba='01',
 d=>d.execution.data_status='unknown',d=>d.rounds[0].quantum.win=true
]) {const bad=copy();mutate(bad);assert.throws(()=>validateEnvelope(bad));}
const failed={contract_version:'qm.run-result.v1',run_id:'failed-id',mode:'raw',status:'failed',errors:[{stage:'backend',code:'REJECTED',message:'No accepted job'}],fallback:{requested:false,used:false}};
validateEnvelope(failed);assert.throws(()=>envelopeView(failed),/backend\/REJECTED/);
assert.throws(()=>arrangedPlayback(fixture),/unavailable/);
const supplied=copy();
supplied.arranged={requested_backend:'rules',actual_backend:'rules',raw_source_sha256:fixture.raw_source.sha256,transformation_ids:['test-only-transpose'],errors:[],fallback:{requested:false,used:false},events:{}};
for(const m of ['quantum','classical'])supplied.arranged.events[m]=supplied.events[m].map(e=>({...e,event_id:e.event_id+'/arranged',pitch_midi:e.rest?null:e.pitch_midi+1,source_event_ids:[e.event_id]}));
const frozen=freezeJSON(supplied),rawBefore=JSON.stringify(frozen.events);
arrangedPlayback(frozen);assert.equal(JSON.stringify(frozen.events),rawBefore);
assert.throws(()=>{frozen.events.quantum[0].velocity=1;},TypeError);
const badArrange=JSON.parse(JSON.stringify(supplied));badArrange.arranged.events.quantum[0].source_event_ids=['unknown'];
assert.throws(()=>arrangedPlayback(badArrange),/lineage/);
const wrongSource=JSON.parse(JSON.stringify(supplied));wrongSource.arranged.raw_source_sha256='0'.repeat(64);
assert.throws(()=>arrangedPlayback(wrongSource),/provenance/);
const exportJSON=JSON.parse(exportEnvelope(original,fixture,{mode:'raw',tempo_bpm:90}));
assert.equal(exportJSON.raw_envelope_text,original);assert.deepEqual(exportJSON.run_result,fixture);
assert.equal(readEnvelope(JSON.stringify(exportJSON)).rawText,original);
const contradictory=JSON.parse(JSON.stringify(exportJSON));contradictory.run_result.run_id='contradiction';assert.throws(()=>readEnvelope(contradictory),/contradicts/);

// Parse the actual MIDI, including deltas/metadata, rather than only its header.
function parseMidi(bytes) {
 let p=14,tracks=[];const u32=()=>{const n=bytes[p]*2**24+bytes[p+1]*2**16+bytes[p+2]*256+bytes[p+3];p+=4;return n;};
 const vlq=()=>{let n=0,b;do{b=bytes[p++];n=(n<<7)+(b&127);}while(b&128);return n;};
 while(p<bytes.length){assert.equal(Buffer.from(bytes.slice(p,p+4)).toString(),'MTrk');p+=4;const end=p+4+u32(),events=[];let tick=0;
  while(p<end){tick+=vlq();const status=bytes[p++];
   if(status===255){const type=bytes[p++],length=vlq(),data=bytes.slice(p,p+length);p+=length;events.push({tick,type,data});}
   else {const size=(status&240)===192?1:2,data=bytes.slice(p,p+size);p+=size;events.push({tick,status,data});}
  }tracks.push(events);
 }return tracks;
}
for(const m of ['quantum','classical']) {
 const events=copy().events[m];events.find(e=>!e.rest).velocity=57;
 const midi=midiBytes(events,120,{run_id:fixture.run_id,raw_source:fixture.raw_source,round_ids:fixture.rounds.map(r=>r.round_id)}),tracks=parseMidi(midi);
 assert.equal(tracks.length,3);
 assert.deepEqual(Array.from(midi.slice(8,14)),[0,1,0,3,1,224]);
 assert.equal(Buffer.from(tracks[0][0].data).toString().includes(fixture.run_id),true);
 assert.deepEqual(Array.from(tracks[0].find(e=>e.type===81).data),[7,161,32]);
 for(const [i,voice] of ['alice','bob'].entries()) {
  const notes=events.filter(e=>e.voice===voice&&!e.rest),ons=tracks[i+1].filter(e=>(e.status&240)===144),offs=tracks[i+1].filter(e=>(e.status&240)===128);
  assert.equal(tracks[i+1].find(e=>(e.status&240)===192).data[0],i?41:73);
  assert.equal(ons.length,notes.length);assert.equal(offs.length,notes.length);
  notes.forEach((e,j)=>{assert.equal(ons[j].tick,Math.round(e.onset_beats*480));assert.equal(offs[j].tick-ons[j].tick,192);assert.equal(ons[j].data[1],e.velocity);});
  assert.equal(tracks[i+1].at(-1).tick,7680);
  assert.equal(tracks[i+1].filter(e=>e.type===1).length,notes.length);
  tracks[i+1].filter(e=>e.type===1).forEach((meta,j)=>{const source=JSON.parse(Buffer.from(meta.data).toString());assert.equal(source.event_id,notes[j].event_id);assert.equal(source.start_tick,ons[j].tick);assert.equal(source.end_tick,offs[j].tick);});
 }
}
assert.throws(()=>midiBytes(fixture.events.quantum,NaN),/tempo/);

// Minimal DOM plus deferred AudioContext exercises UI lifecycle without a browser.
class Node {
 constructor(){this.value='';this.checked=false;this.disabled=false;this.dataset={};this.style={};this.children=[];this.options=[{},{}];this.classList={toggle(){}};}
 replaceChildren(){this.children=[];}append(child){this.children.push(child);}remove(){}
 setAttribute(){}click(){}querySelector(){return {style:{}};}querySelectorAll(){return this.children.filter(c=>c.className?.includes('note'));}
}
const nodes=new Map();global.document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);},createElement:()=>new Node(),body:new Node()};
const get=id=>document.getElementById(id);get('method').value='quantum';get('music-mode').value='raw';get('shots').value='1024';get('batch').value='five-live';
const listeners={};global.window={addEventListener:(name,fn)=>listeners[name]=fn,setTimeout(){}};
global.Blob=class {};URL.createObjectURL=()=> 'blob:mock';URL.revokeObjectURL=()=>{};
global.requestAnimationFrame=()=>1;global.cancelAnimationFrame=()=>{};global.btoa=s=>Buffer.from(s,'binary').toString('base64');
class Context {
 constructor(){this.currentTime=0;this.destination={};this.pending=[];this.oscs=[];}
 resume(){return new Promise(resolve=>this.pending.push(resolve));}
 createGain(){return {gain:{setValueAtTime(){},linearRampToValueAtTime(){}},connect(){},disconnect(){}};}
 createPeriodicWave(){return {};}
 createOscillator(){const o={active:false,frequency:{},connect(){},disconnect(){this.active=false;},setPeriodicWave(){},start(){this.active=true;},stop(at){if(at===undefined)this.active=false;}};this.oscs.push(o);return o;}
}
let ctx;global.AudioContext=class extends Context {constructor(){super();ctx=this;}};
let calls=0;const logs=[],saveLog=console.log;console.log=value=>logs.push(value);
const lifecycle=mountDuet(async()=>{calls++;return fixture;},'mock test',{loadFixture:async()=>original});
await get('fixture').onclick();assert.match(get('status').textContent,/RECORDED Qollab/);assert.equal(get('music-mode').options[1].disabled,true);
const play=get('play').onclick();get('stop').onclick();ctx.pending.splice(0).forEach(r=>r());await play;assert.equal(ctx.oscs.length,0);
for(let i=0;i<2;i++){const p=get('play').onclick();ctx.pending.splice(0).forEach(r=>r());await p;}
assert.equal(ctx.oscs.filter(o=>o.active).length,30);
get('method').value='classical';get('method').onchange();assert.equal(ctx.oscs.filter(o=>o.active).length,0);
get('tempo').value='90';get('tempo').onchange();get('mute-alice').checked=true;get('mute-alice').onchange();
get('json').onclick();assert.equal(JSON.parse(get('export-payload').value).raw_envelope_text,original);
get('import-payload').value=get('export-payload').value;await get('import-result').onclick();assert.equal(get('play').disabled,false);
get('midi').onclick();assert.equal(Buffer.from(get('export-payload').value,'base64').slice(0,4).toString(),'MThd');assert.equal(calls,0);
get('import-payload').value=JSON.stringify(supplied);await get('import-result').onclick();assert.equal(get('music-mode').options[1].disabled,false);
get('music-mode').value='arranged';get('music-mode').onchange();assert.match(get('music-provenance').textContent,/test-only-transpose/);
get('music-mode').value='raw';get('music-mode').onchange();get('json').onclick();assert.deepEqual(JSON.parse(get('export-payload').value).run_result.events,fixture.events);
get('import-payload').value=JSON.stringify(badArrange);await get('import-result').onclick();assert.equal(get('music-mode').options[1].disabled,true);assert.equal(get('play').disabled,false);
get('import-payload').value=JSON.stringify(failed);await get('import-result').onclick();assert.match(get('status').textContent,/REJECTED/);assert.equal(get('play').disabled,true);
get('import-payload').value='{"contract_version":"unknown"}';await get('import-result').onclick();assert.match(get('status').textContent,/Unknown/);
await get('generate').onclick();await get('generate').onclick();assert.equal(calls,1);assert.equal(get('generate').disabled,true);
listeners.pagehide();await lifecycle;console.log=saveLog;
assert.equal(JSON.stringify(fixture),JSON.stringify(JSON.parse(original)));
console.log(JSON.stringify({status:'passed',timestamp_utc:new Date().toISOString(),scope:'Node contract/MIDI parser and mocked DOM/AudioContext; no real browser claims',checks:['schema/errors','paired identities and integer histograms','immutable raw/arranged provenance','MIDI beats/velocity/meta identity','no backend calls on replay/import/export/switch','single live lifecycle','Stop/resume/repeat cleanup']},null,2));
