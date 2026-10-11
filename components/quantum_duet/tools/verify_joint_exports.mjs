// Offline verification of three decoded browser exports. Never submits a job.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {webcrypto,createHash} from 'node:crypto';
import {validateJoint} from '../web/joint-cue-contract.mjs';
import {midiBytes} from '../web/ui.mjs';
globalThis.crypto??=webcrypto;
const [jsonFile,quantumMidi,classicalMidi]=process.argv.slice(2);
if(!jsonFile||!quantumMidi||!classicalMidi)throw Error('Usage: node verify_joint_exports.mjs run.json quantum.mid classical.mid');
const bundle=JSON.parse(fs.readFileSync(jsonFile,'utf8')),take=JSON.parse(bundle.raw_envelope_text);
assert.deepEqual(take,bundle.run_result);await validateJoint(take);
const hashes={};
for(const [method,file] of [['quantum',quantumMidi],['classical',classicalMidi]]){
 const identity={run_id:take.run_id,contract_version:take.contract_version,job_id:take.execution.job_id,histogram_sha256:take.histogram_sha256,method,mode:'raw',round_ids:take.rounds[method].map(r=>r.round_id)};
 const actual=fs.readFileSync(file),expected=Buffer.from(midiBytes(take.events[method],bundle.export_view.tempo_bpm,identity));
 assert.deepEqual(actual,expected,`${method} MIDI changed on export/decoding`);
 hashes[method]=createHash('sha256').update(actual).digest('hex');
}
console.log(JSON.stringify({status:'passed',verified_utc:new Date().toISOString(),job_id:take.execution.job_id,
 source_bytes_sha256:createHash('sha256').update(bundle.raw_envelope_text).digest('hex'),
 histogram_sha256:take.histogram_sha256,midi_sha256:hashes,backend_jobs_this_verification:0},null,2));
