// Separate private test surface; does not import or overwrite the shared UI.
import * as fresh from 'quantum_duet.fresh_qcbm';
import * as rules from 'quantum_duet.fresh_music_bridge';
const $=id=>document.getElementById(id);
const text=v=>typeof v==='string'?v:v.toJs();
let attempted=false,sourceText=null,score=null,ctx=null,nodes=[],generation=0;
function stop(){generation++;for(const n of nodes){try{n.osc.stop();}catch{}n.osc.disconnect();n.gain.disconnect();}nodes=[];$('playback').textContent='Stopped · no additional jobs';}
function exportFile(name,mime,bytes,payload){$('export').value=payload;const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([bytes],{type:mime}));link.download=name;link.click();URL.revokeObjectURL(link.href);console.log(JSON.stringify({event:'fresh-music-export',filename:name,payload}));}
$('generate').onclick=async()=>{
 if(attempted)return;attempted=true;$('generate').disabled=true;
 $('status').textContent='Submitting one 12-qubit circuit to the supplied simulator; no CHSH job.';
 try{
  sourceText=text(await fresh.generate_fresh.callPromising(backend,32,20261011));
  const s=JSON.parse(sourceText);$('provenance').textContent=sourceText;
  $('status').textContent=`LIVE supplied ${s.execution.backend_name} / ${s.execution.backend_class} / noise ${s.execution.noise_model} / job ${s.execution.job_id} / ${s.execution.returned_shots} returned shots / one circuit / one call. Fresh QCBM source; arrangement not yet performed.`;
  $('compose').disabled=false;console.log(JSON.stringify({event:'fresh-qcbm-source',raw_source_text:sourceText}));
 }catch(error){$('status').textContent=`Generation failed: ${error.message}. No retry, fallback or fabricated source.`;console.error('fresh-qcbm generation failed');}
};
$('compose').onclick=async()=>{
 if(!sourceText)return;stop();$('compose').disabled=true;
 try{
  const resultText=text(await rules.compose_result.callPromising(sourceText));score=JSON.parse(resultText);
  if(score.schema_version!=='qm.five-part-composition.v1'||score.source_json_text!==sourceText||score.tracks.length!==5||score.duration_seconds!==32)throw Error('Invalid composition/source identity');
  $('provenance').textContent=resultText;
  $('status').textContent+=` / CLASSICAL arrangement completed: 16 bars, 32 seconds, Flute / Clarinet / Violin / Cello / Piano; zero additional jobs.`;
  for(const id of ['play','stop','midi','json'])$(id).disabled=false;
  console.log(JSON.stringify({event:'fresh-music-composed',job_id:score.execution.job_id,source_json_sha256:score.source_json_sha256,midi_sha256:score.export.midi_sha256,additional_jobs:0}));
 }catch(error){$('status').textContent+=` / Arrangement failed: ${error.message}. Measured source retained.`;}
};
$('play').onclick=async()=>{
 if(!score)return;stop();const token=generation;ctx??=new AudioContext();await ctx.resume();if(token!==generation)return;
 const start=ctx.currentTime+.08;
 for(const track of score.tracks)for(const event of track.events){
  if(event.rest||event.muted)continue;
  const osc=ctx.createOscillator(),gain=ctx.createGain();
  osc.type={flute:'sine',clarinet:'triangle',violin:'sawtooth',cello:'triangle',piano:'sine'}[track.instrument_id];
  osc.frequency.value=440*2**((event.pitch_midi-69)/12);
  const at=start+event.onset_beats*.5,duration=event.duration_beats*.5,level=.08*event.velocity/127;
  gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(level,at+.008);
  gain.gain.setValueAtTime(level,at+Math.max(.008,duration-.025));gain.gain.linearRampToValueAtTime(0,at+duration);
  osc.connect(gain);gain.connect(ctx.destination);osc.start(at);osc.stop(at+duration);nodes.push({osc,gain});
 }
 $('playback').textContent=`Playing ${nodes.length} scheduled notes across five parts · 32-second score · zero additional jobs`;
};
$('stop').onclick=stop;
$('midi').onclick=()=>{if(!score)return;const b64=score.export.midi_base64;exportFile('fresh-five-part-composition.mid','audio/midi',Uint8Array.from(atob(b64),c=>c.charCodeAt(0)),b64);};
$('json').onclick=()=>{if(!score)return;const body=JSON.stringify(score);exportFile('fresh-five-part-composition.json','application/json',body,body);};
await new Promise(resolve=>window.addEventListener('pagehide',()=>{stop();resolve();},{once:true}));
