import * as inference from 'quantum_harmony.inference';
const $ = id => document.getElementById(id);
let result = null, selectedStep = 0, audio = null, playGeneration = 0;
const parsePythonJSON = value => JSON.parse(typeof value === 'string' ? value : value.toJs());
const pct = x => `${(100*x).toFixed(1)}%`;
function randomSeed(){const a=new Uint32Array(2);crypto.getRandomValues(a);return Number((BigInt(a[0])<<21n)^BigInt(a[1]&0x1fffff));}

function renderTimeline(){
  const lane=$('timeline');lane.replaceChildren();
  result.chords.forEach((chord,i)=>{
    const b=document.createElement('button');b.className='chord'+(i===selectedStep?' selected':'');
    b.innerHTML=`<span class="bar-no">${i+1}</span><strong>${chord.symbol}</strong><small>${chord.label}</small>`;
    b.onclick=()=>{selectedStep=i;renderTimeline();renderInspector();};lane.append(b);
  });
}
function probabilityRows(labels,raw,effective,sampledIndex){
  const wrap=document.createElement('div');wrap.className='probability-list';
  labels.forEach((label,i)=>{const row=document.createElement('div');row.className='prob-row'+(i===sampledIndex?' sampled':'');
    const rawText=raw&&Math.abs(raw[i]-effective[i])>1e-9?`<small>measured ${pct(raw[i])}</small>`:'';
    row.innerHTML=`<span class="prob-label">${label}</span><div class="prob-track"><div class="prob-fill" style="width:${100*effective[i]}%"></div></div><span class="prob-value">${pct(effective[i])}${rawText}</span>`;wrap.append(row);});
  return wrap;
}
function renderInspector(){
  const panel=$('inspector-body');panel.replaceChildren();
  if(!result){panel.innerHTML='<p class="muted">Generate harmony, then click any chord to inspect its quantum provenance.</p>';return;}
  if(selectedStep===0){panel.innerHTML=`<div class="inspector-start"><span class="tag">START STATE</span><h3>${result.chords[0].symbol}</h3><p>The sequence begins at tonic <b>I</b>. Quantum inference starts when choosing bar 2.</p></div>`;return;}
  const step=result.steps[selectedStep-1];const title=document.createElement('div');title.className='inspector-title';
  title.innerHTML=`<div><span class="tag">TRANSITION ${selectedStep}</span><h3>${step.previous_coarse} → ${step.resolved_label}</h3></div><div class="inspector-outcome">${result.chords[selectedStep].symbol}</div>`;panel.append(title);
  const note=document.createElement('p');note.className='small';note.textContent=result.controls.harmonic_colour_note;panel.append(note);
  const h=document.createElement('h4');h.textContent=`3-qubit coarse PQC · sampled ${step.sampled_coarse}`;panel.append(h);
  panel.append(probabilityRows(step.coarse.labels,step.coarse.probabilities,step.effective_coarse_probabilities,step.sampled_coarse_index));
  if(step.resolver){const a=document.createElement('div');a.className='resolver-arrow';a.textContent='OTHER ↓ 4-qubit chromatic resolver';panel.append(a);panel.append(probabilityRows(step.resolver.labels,step.resolver.probabilities,step.resolver.probabilities,step.sampled_resolver_index));}
  if(step.fallback){const f=document.createElement('p');f.className='warning';f.textContent=`Rare-class fallback: ${step.fallback}`;panel.append(f);}
  const m=document.createElement('div');m.className='inspector-meta';m.innerHTML=`<span>${step.coarse.qubits}q coarse</span><span>${step.coarse.shots} shots</span><span>${step.coarse.backend_name||step.coarse.backend_class}</span><span>job ${step.coarse.job_id||'not reported'}</span>`;panel.append(m);
}
function renderResult(){
  $('empty-state').hidden=true;$('workspace').hidden=false;$('key-display').textContent=result.key;$('sequence-display').textContent=result.chords.map(c=>c.symbol).join('  →  ');
  $('backend').textContent=result.execution.backend_name||result.execution.backend_class;$('jobs').textContent=`${result.execution.new_quantum_jobs} new · ${result.execution.cache_hits} cached`;$('seed-used').textContent=String(result.seed);$('model-summary').textContent=`${result.model.coarse} + ${result.model.resolver}`;selectedStep=0;renderTimeline();renderInspector();
}
async function generate(useRandomSeed=false){
  const seedField=$('seed');if(useRandomSeed||!seedField.value.trim())seedField.value=String(randomSeed());
  const key=$('key').value,bars=Number($('bars').value),colour=$('colour').value,shots=Number($('shots').value),seed=Number(seedField.value);
  if(!Number.isInteger(shots)||shots<16||shots>4096){$('status').textContent='Shots must be an integer from 16 to 4096.';return;}
  stopPlayback();for(const id of ['generate','variation'])$(id).disabled=true;$('status').textContent='Generating harmony · measured quantum distributions are cached by context…';
  try{const proxy=await inference.generate_progression.callPromising(backend,key,bars,colour,shots,seed);result=parsePythonJSON(proxy);renderResult();$('status').textContent=`Ready · ${result.execution.new_quantum_jobs} new quantum job(s), ${result.execution.cache_hits} cache hit(s).`;for(const id of ['play','stop','variation','export'])$(id).disabled=false;}
  catch(error){$('status').textContent=`Generation failed: ${error.message}. No backend fallback was used.`;}
  finally{$('generate').disabled=false;if(result)$('variation').disabled=false;}
}
const noteFrequency=midi=>440*Math.pow(2,(midi-69)/12);
function voiceEnvelope(ctx,master,midi,start,duration,sound,gainScale=1){
  const osc=ctx.createOscillator(),gain=ctx.createGain();
  if(sound==='strings'){osc.type='sawtooth';gain.gain.setValueAtTime(0,start);gain.gain.linearRampToValueAtTime(.045*gainScale,start+Math.min(.18,duration*.2));gain.gain.setValueAtTime(.04*gainScale,Math.max(start+.2,start+duration-.18));gain.gain.linearRampToValueAtTime(0,start+duration);}
  else if(sound==='synth'){osc.type='square';gain.gain.setValueAtTime(0,start);gain.gain.linearRampToValueAtTime(.035*gainScale,start+.015);gain.gain.exponentialRampToValueAtTime(.008*gainScale,start+Math.max(.04,duration-.05));gain.gain.linearRampToValueAtTime(0,start+duration);}
  else{osc.type='triangle';gain.gain.setValueAtTime(0,start);gain.gain.linearRampToValueAtTime(.07*gainScale,start+.008);gain.gain.exponentialRampToValueAtTime(.012*gainScale,start+Math.max(.04,duration*.72));gain.gain.linearRampToValueAtTime(0,start+duration);}
  osc.frequency.value=noteFrequency(midi);osc.connect(gain);gain.connect(master);osc.start(start);osc.stop(start+duration+.02);return{osc,gain};
}
function scheduleChord(ctx,master,chord,at,beat,pattern,sound){
  const nodes=[],notes=chord.midi,add=(midi,start,duration,scale=1)=>nodes.push(voiceEnvelope(ctx,master,midi,start,duration,sound,scale));add(chord.bass_midi,at,Math.max(.25,3.6*beat),.9);
  if(pattern==='arpeggio'){[0,1,2,1,0,1,2,1].forEach((idx,n)=>add(notes[idx%notes.length],at+n*.5*beat,.42*beat,1));}
  else if(pattern==='pulse'){for(let b=0;b<4;b++)notes.forEach(midi=>add(midi,at+b*beat,.72*beat,.72));}
  else notes.forEach(midi=>add(midi,at,3.65*beat,1));return nodes;
}
async function play(){
  if(!result)return;stopPlayback();const generation=++playGeneration;audio=new AudioContext();await audio.resume();const bpm=Number($('tempo').value),beat=60/bpm,sound=$('sound').value,pattern=$('pattern').value,master=audio.createGain();master.gain.value=.75;master.connect(audio.destination);const start=audio.currentTime+.08;
  result.chords.forEach((chord,i)=>scheduleChord(audio,master,chord,start+i*4*beat,beat,pattern,sound));$('playback-status').textContent=`Playing ${result.chords.length} generated chords · ${bpm} BPM · ${sound} · ${pattern}`;
  const timer=()=>{if(generation!==playGeneration||!audio)return;const bar=Math.floor((audio.currentTime-start)/(4*beat));if(bar>=0&&bar<result.chords.length&&bar!==selectedStep){selectedStep=bar;renderTimeline();renderInspector();}if(bar>=result.chords.length){stopPlayback();return;}requestAnimationFrame(timer);};requestAnimationFrame(timer);
}
function stopPlayback(){playGeneration++;if(audio){try{audio.close();}catch{}audio=null;}$('playback-status').textContent='Stopped';}
function exportJSON(){if(!result)return;const payload=JSON.stringify({...result,playback:{tempo_bpm:Number($('tempo').value),sound:$('sound').value,pattern:$('pattern').value,quantum_shots_unchanged:true}},null,2);$('export-panel').hidden=false;$('export-payload').value=payload;console.log(JSON.stringify({event:'quantum-harmony-export',encoding:'utf-8',payload}));}
$('generate').onclick=()=>generate(false);$('variation').onclick=()=>generate(true);$('play').onclick=play;$('stop').onclick=stopPlayback;$('export').onclick=exportJSON;$('tempo').oninput=()=>$('tempo-value').textContent=`${$('tempo').value} BPM`;window.addEventListener('pagehide',stopPlayback);renderInspector();
