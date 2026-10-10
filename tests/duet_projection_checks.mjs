import assert from 'node:assert/strict';
import fs from 'node:fs';
import {webcrypto} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {playbackProjection,validateSource} from '../components/quantum_duet/web/playback-projection.mjs';
import {readEnvelope,exportEnvelope,envelopeView,validateEnvelope} from '../components/quantum_duet/web/run-contract.mjs';
import {midiBytes} from '../components/quantum_duet/web/ui.mjs';
global.crypto=webcrypto;
const py=process.argv[2]||'.venv-review/Scripts/python.exe';
const r=spawnSync(py,['-c',`
import json
from pathlib import Path
from unittest.mock import patch
from quantum_duet.browser_projection import arrange_browser,project,browser_bundle
from quantum_duet.orchestration_adapter import arrange_result,freeze_result
raw=Path('docs/team/fixtures/run-result.v1.json').read_bytes()
source=Path('components/quantum_duet/tests/fixtures/qollab-local-run.json').read_bytes()
with patch('qiskit.providers.basic_provider.BasicSimulator.run',side_effect=AssertionError('New job')):
    good=arrange_browser(raw,raw_source_bytes=source)
    frozen=freeze_result(json.loads(raw),raw_bytes=source)
    classical=arrange_result(frozen,policy='classical').to_dict()
    with patch('orchestrator.pipeline.orchestrate',side_effect=RuntimeError('test failure')):
        failed=arrange_result(frozen,policy='quantum').to_dict()
    failure=browser_bundle(raw,project(raw,dict(quantum=failed,classical=classical)),raw_source_bytes=source)
print(json.dumps(dict(good=good,failure=failure,failed_envelope=failed)))
`],{encoding:'utf8',maxBuffer:2_000_000});
assert.equal(r.status,0,r.stderr);
const {good,failure,failed_envelope}=JSON.parse(r.stdout),raw=good.run_result, before=JSON.stringify(raw);
await validateSource(raw,good.raw_source_text);
const projection=await playbackProjection(raw,good.raw_envelope_text,good.playback_projection);
assert.equal(projection.available,true);
const f=await playbackProjection(raw,failure.raw_envelope_text,failure.playback_projection);
assert.equal(f.available,false);assert.equal(f.events.quantum,null);assert.equal(f.events.classical.length,32);
validateEnvelope(failed_envelope);assert.equal(envelopeView(failed_envelope).events.quantum.length,32);
assert.equal(JSON.stringify(raw),before);
const exported=exportEnvelope(good.raw_envelope_text,raw,{mode:'arranged'},good.playback_projection,good.raw_source_text);
assert.deepEqual(readEnvelope(exported),{rawText:good.raw_envelope_text,result:raw,projection:good.playback_projection,sourceText:good.raw_source_text});
await assert.rejects(()=>validateSource(raw,good.raw_source_text+' '),/digest/);
for(const mutate of [
 p=>p.raw_envelope_sha256='0'.repeat(64),
 p=>p.policies.quantum.events[0].round_id='wrong',
 p=>p.policies.quantum.events[0].source_event_ids=['wrong'],
 p=>p.policies.quantum.events.find(e=>!e.rest).duration_beats=0.0001,
 p=>p.policies.quantum.actual_backend='other',
 p=>p.policies.quantum.events.pop(),
 p=>p.raw_source.sha256='0'.repeat(64),
 p=>p.available=false,
]){const p=JSON.parse(JSON.stringify(good.playback_projection));mutate(p);await assert.rejects(()=>playbackProjection(raw,good.raw_envelope_text,p));}
for(const mutate of [e=>e.pitch_midi=71,e=>e.event_id='wrong']){
 const changed=JSON.parse(before);mutate(changed.events.quantum.find(e=>!e.rest));assert.throws(()=>validateEnvelope(changed),/frozen/);
}
fs.mkdirSync('output-integration/midi',{recursive:true});
for(const method of ['quantum','classical'])for(const mode of ['raw','arranged']) {
 const events=mode==='raw'?raw.events[method]:projection.events[method];
 fs.writeFileSync(`output-integration/midi/browser-${mode}-${method}.mid`,midiBytes(events,120,{run_id:raw.run_id,method,mode,raw_source:raw.raw_source,round_ids:raw.rounds.map(r=>r.round_id)}));
}
fs.writeFileSync('output-integration/failure.json',JSON.stringify(failure));
fs.writeFileSync('output-integration/failed-envelope.json',JSON.stringify(failed_envelope));
// Reuse C's reviewed DOM/audio doubles, then exercise the production seam itself.
await import('../components/quantum_duet/tests/ui_c/contract_checks.mjs');
const {mountDuet}=await import('../components/quantum_duet/web/ui.mjs');
const get=id=>document.getElementById(id), listeners={};
window.addEventListener=(name,fn)=>listeners[name]=fn;
get('method').value='quantum';get('music-mode').value='raw';
let jobs=0,arrangements=0,returnedBundle=null;
const priorLog=console.log;console.log=()=>{};
const lifecycle=mountDuet(async()=>{jobs++;throw Error('Unexpected job');},'coordinator mock',{
 loadFixture:async()=>good,
 arrange:async()=>{arrangements++;if(returnedBundle)return returnedBundle;throw Error('Transport failure');}
});
await get('fixture').onclick();
get('music-mode').value='arranged';get('music-mode').onchange();
assert.match(get('music-provenance').textContent,/ARRANGED.*rules/);
get('method').value='classical';get('method').onchange();
assert.match(get('music-provenance').textContent,/classical/);
get('json').onclick();assert.equal(JSON.parse(get('export-payload').value).raw_envelope_text,good.raw_envelope_text);
await get('arrange').onclick();assert.equal(get('play').disabled,false);assert.match(get('music-provenance').textContent,/Transport failure.*RAW/);
returnedBundle={...good,raw_envelope_text:good.raw_envelope_text+' '};
await get('arrange').onclick();assert.equal(get('play').disabled,false);assert.match(get('music-provenance').textContent,/changed original evidence/);
get('json').onclick();assert.equal(JSON.parse(get('export-payload').value).raw_envelope_text,good.raw_envelope_text);
get('method').value='quantum';get('method').onchange();
get('import-payload').value=JSON.stringify(failure);await get('import-result').onclick();
assert.equal(get('play').disabled,false);assert.equal(get('music-mode').options[1].disabled,true);
assert.match(get('music-provenance').textContent,/quantum: arrangement/);
get('method').value='classical';get('method').onchange();assert.equal(get('music-mode').options[1].disabled,false);
get('music-mode').value='arranged';get('music-mode').onchange();assert.match(get('music-provenance').textContent,/ARRANGED.*rules/);
assert.equal(jobs,0);assert.equal(arrangements,2);listeners.pagehide();await lifecycle;console.log=priorLog;
console.log(JSON.stringify({status:'passed',timestamp_utc:new Date().toISOString(),checks:'real paired rules projection, byte/source digests, failure isolation, lineage, ticks, rest retention, no jobs, export roundtrip, raw mapping rejects corruption; 4 MIDI files'}));
