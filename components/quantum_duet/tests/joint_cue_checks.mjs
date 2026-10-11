import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {webcrypto} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {validateJoint} from '../web/joint-cue-contract.mjs';
import {midiBytes,mountDuet} from '../web/ui.mjs';
globalThis.crypto??=webcrypto;
for(const name of ['diagnostic-32','application-32']){
 const captured=JSON.parse(readFileSync(new URL(`../evidence/joint-cue/${name}.json`,import.meta.url),'utf8'));
 await validateJoint(captured); // Real returned results; validation performs zero jobs.
}
const python=process.argv[2];if(!python)throw Error('Pass the verified Python executable');
const generated=spawnSync(python,['-c',`import json;from quantum_duet.joint_cue import generate_joint;from qiskit.providers.basic_provider import BasicSimulator;print(generate_joint(BasicSimulator(),32,20261011,asset_dir='components/quantum_duet/src/quantum_duet/data'))`],{encoding:'utf8'});
assert.equal(generated.status,0,generated.stderr);
const take=JSON.parse(generated.stdout);await validateJoint(take);
const source=JSON.stringify(take);
for(const method of ['quantum','classical']){
 const midi=midiBytes(take.events[method],120,{run_id:take.run_id,contract_version:take.contract_version,histogram_sha256:take.histogram_sha256,method,mode:'raw'});
 assert.equal(new TextDecoder().decode(midi.slice(0,4)),'MThd');assert(midi.length>1000);
}
assert.equal(JSON.stringify(take),source);
for(const change of [t=>t.execution.circuit_count=4,t=>t.statistics.expected_success=.9,t=>t.rounds.quantum[0].x^=1,t=>t.events.quantum[0].event_id='other',t=>t.execution.simulator_verified=false,t=>t.joint_histogram_yxba['0000']=999,t=>t.events.classical[0].pitch_midi=80,t=>t.randomness.cue_redraws=1]){
 const mutated=JSON.parse(JSON.stringify(take));change(mutated);
 // Backend classification is not trusted from a selector; simulator_verified is mandatory.
 if(JSON.stringify(mutated)===source)mutated.execution.simulator_verified=false;
 await assert.rejects(()=>validateJoint(mutated));
}
// Exercise the installed interface, not only its contract validator.
class Node {
 constructor(){this.value='';this.checked=false;this.disabled=false;this.dataset={};this.style={};this.children=[];this.options=[{},{}];this.classList={toggle(){}};}
 replaceChildren(){this.children=[];}append(child){this.children.push(child);}remove(){}
 setAttribute(){}click(){}querySelector(){return {style:{}};}querySelectorAll(){return this.children.filter(c=>c.className?.includes('note'));}
}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);};
global.document={getElementById:get,createElement:()=>new Node(),body:new Node()};
const listeners={};global.window={addEventListener:(name,fn)=>listeners[name]=fn,setTimeout(){}};
global.Blob=class {};URL.createObjectURL=()=> 'blob:mock';URL.revokeObjectURL=()=>{};
global.requestAnimationFrame=()=>1;global.cancelAnimationFrame=()=>{};global.btoa=s=>Buffer.from(s,'binary').toString('base64');
get('method').value='quantum';get('music-mode').value='raw';get('shots').value='32';get('batch').value='joint-cue-recorded';
let calls=0;const savedLog=console.log;console.log=()=>{};
const lifecycle=mountDuet(async()=>{calls++;return source;},'mock test');
await get('generate').onclick();await get('generate').onclick();assert.equal(calls,1);assert.equal(get('play').disabled,false);
assert.match(get('status').textContent,/one circuit \/ one job/);assert.match(get('melody-origin').textContent,/RECORDED/);
get('json').onclick();assert.equal(JSON.parse(get('export-payload').value).raw_envelope_text,source);
get('midi').onclick();assert.equal(Buffer.from(get('export-payload').value,'base64').slice(0,4).toString(),'MThd');
const zeroGenerated=spawnSync(python,['-c',`import json,sys;from quantum_duet.joint_cue import assemble_joint,prepare_presentation,load_assets; t=json.loads(sys.stdin.read()); a,m,r=load_assets('components/quantum_duet/src/quantum_duet/data'); print(json.dumps(assemble_joint({'0000':32},t['execution'],a,m,r,prepare_presentation(20261011))))`],{encoding:'utf8',input:source});
assert.equal(zeroGenerated.status,0,zeroGenerated.stderr);
get('import-payload').value=zeroGenerated.stdout;await get('import-result').onclick();assert.equal(get('play').disabled,false);assert.equal(get('estimate').textContent,'Unavailable');assert.match(get('interval').textContent,/empty|zero/);
get('method').value='classical';get('method').onchange();get('midi').onclick();assert.equal(calls,1);
listeners.pagehide();await lifecycle;console.log=savedLog;
console.log('Joint-cue contract + mounted UI: paired MIDI/JSON, source identity, zero-group playback and single-job lifecycle passed');
