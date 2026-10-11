import * as inference from 'quantum_harmony.inference';
const $ = id => document.getElementById(id);
let result = null, selectedStep = 0, audio = null, playGeneration = 0, masterGain = null;
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
  const spec={piano:{attack:.004,decay:.65,release:.13,struck:true,type:'triangle',level:.07},
    strings:{attack:.015,decay:.08,sustain:.88,release:.12,swell:.10,type:'sawtooth',level:.04},
    flute:{attack:.075,decay:.09,sustain:.84,release:.075,swell:.20,type:'sine',level:.07},
    percussion:{attack:.002,decay:.16,release:.05,struck:true,type:'sine',level:.08},
    synth:{attack:.025,decay:.15,sustain:.65,release:.08,swell:.08,type:'triangle',level:.05}}[sound];
  const attack=Math.min(spec.attack,duration*.22),decay=Math.min(spec.decay,duration*.22),release=Math.min(spec.release,Math.max(.008,duration*.4)),level=spec.level*gainScale;
  osc.type=spec.type;gain.gain.setValueAtTime(0,start);
  const amplitude=time=>{
    if(time<attack)return .5-.5*Math.cos(Math.PI*time/attack);
    if(spec.struck)return Math.exp(-(time-attack)/(spec.decay*2**((60-midi)/48)));
    const phase=Math.max(0,Math.min(1,(time-attack-decay)/Math.max(.001,duration-attack-decay)));
    return (1-(1-spec.sustain)*Math.min(1,(time-attack)/decay))*(1+spec.swell*Math.sin(Math.PI*phase))*(1-.22*phase**3);
  };
  for(const time of [...new Set([attack,...Array.from({length:48},(_,i)=>duration*(i+1)/48)])].sort((a,b)=>a-b))gain.gain.linearRampToValueAtTime(level*amplitude(time),start+time);
  for(let i=1;i<=8;i++)gain.gain.linearRampToValueAtTime(level*amplitude(duration)*(.5+.5*Math.cos(Math.PI*i/8)),start+duration+release*i/8);
  osc.frequency.value=noteFrequency(midi);osc.connect(gain);gain.connect(master);osc.start(start);osc.stop(start+duration+release);return{osc,gain};
}
function scheduleChord(ctx,master,chord,at,beat,pattern,sound){
  const nodes=[],notes=chord.midi,add=(midi,start,duration,scale=1)=>nodes.push(voiceEnvelope(ctx,master,midi,start,duration,sound,scale));add(chord.bass_midi,at,Math.max(.25,3.6*beat),.9);
  if(pattern==='arpeggio'){[0,1,2,1,0,1,2,1].forEach((idx,n)=>add(notes[idx%notes.length],at+n*.5*beat,.42*beat,1));}
  else if(pattern==='pulse'){for(let b=0;b<4;b++)notes.forEach(midi=>add(midi,at+b*beat,.72*beat,.72));}
  else notes.forEach(midi=>add(midi,at,3.65*beat,1));return nodes;
}
async function play(){
  if(!result)return;stopPlayback();const generation=++playGeneration;audio=new AudioContext();await audio.resume();if(generation!==playGeneration||!audio)return;const bpm=Number($('tempo').value),beat=60/bpm,sound=$('sound').value,pattern=$('pattern').value,master=audio.createGain();masterGain=master;master.gain.value=Number($('volume').value)/100;master.connect(audio.destination);const start=audio.currentTime+.08;
  result.chords.forEach((chord,i)=>scheduleChord(audio,master,chord,start+i*4*beat,beat,pattern,sound));$('playback-status').textContent=`Playing ${result.chords.length} generated chords · ${bpm} BPM · ${sound} · ${pattern}`;
  const timer=()=>{if(generation!==playGeneration||!audio)return;const bar=Math.floor((audio.currentTime-start)/(4*beat));if(bar>=0&&bar<result.chords.length&&bar!==selectedStep){selectedStep=bar;renderTimeline();renderInspector();}if(bar>=result.chords.length){stopPlayback();return;}requestAnimationFrame(timer);};requestAnimationFrame(timer);
}
function stopPlayback(){playGeneration++;masterGain=null;if(audio){try{audio.close();}catch{}audio=null;}$('playback-status').textContent='Stopped';}
function exportJSON(){if(!result)return;const payload=JSON.stringify({...result,playback:{tempo_bpm:Number($('tempo').value),sound:$('sound').value,pattern:$('pattern').value,volume:Number($('volume').value)/100,quantum_shots_unchanged:true}},null,2);$('export-panel').hidden=false;$('export-payload').value=payload;console.log(JSON.stringify({event:'quantum-harmony-export',encoding:'utf-8',payload}));}
$('generate').onclick=()=>generate(false);$('variation').onclick=()=>generate(true);$('play').onclick=play;$('stop').onclick=stopPlayback;$('export').onclick=exportJSON;$('tempo').oninput=()=>$('tempo-value').textContent=`${$('tempo').value} BPM`;window.addEventListener('pagehide',stopPlayback);renderInspector();
$('volume').oninput=()=>{const value=Number($('volume').value)/100;$('volume-value').textContent=$('volume').value+'%';if(masterGain&&audio){masterGain.gain.cancelScheduledValues(audio.currentTime);masterGain.gain.setValueAtTime(masterGain.gain.value,audio.currentTime);masterGain.gain.linearRampToValueAtTime(value,audio.currentTime+.025);}};
