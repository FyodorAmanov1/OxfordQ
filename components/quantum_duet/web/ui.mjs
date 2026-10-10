const $ = id => document.getElementById(id);
const percent = x => (x * 100).toFixed(2) + '%';
const noteName = pitch => pitch === null ? 'rest' : ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'][pitch%12] + (Math.floor(pitch/12)-1);

export function parsePythonJSON(value) {
  const text = typeof value === 'string' ? value : value.toJs();
  if(typeof text !== 'string')throw Error('Expected validated Python JSON text');
  return JSON.parse(text);
}

export function assertTake(take) {
  if (take.schema_version !== 1 || take.execution.backend_run_calls !== 1 || take.statistics.total_independent_shots !== 4*take.execution.shots_per_circuit) throw Error('Invalid take allocation');
  if (take.base_melody.generated_now !== (take.execution.mode === 'five-live')) throw Error('Recorded/current melody mismatch');
  for (const name of ['quantum','classical']) if(take.rounds[name].length !== 16 || take.events[name].length !== 32) throw Error('Incomplete musical take');
  return take;
}

// Standard MIDI type 1, 480 ticks/beat, conductor and two separate voices.
export function midiBytes(events, bpm) {
  const u32 = n => [(n>>>24)&255,(n>>>16)&255,(n>>>8)&255,n&255];
  const vlq = n => { let b=[n&127]; while(n>>=7)b.unshift((n&127)|128); return b; };
  const chunk = (name, bytes) => [...Array.from(name,c=>c.charCodeAt(0)),...u32(bytes.length),...bytes];
  const tempo = Math.round(60000000/bpm);
  const conductor = [0,255,81,3,(tempo>>>16)&255,(tempo>>>8)&255,tempo&255,0,255,88,4,4,2,24,8,...vlq(7680),255,47,0];
  const tracks = [chunk('MTrk',conductor)];
  ['alice','bob'].forEach((voice,channel)=>{
    const label=Array.from(voice,c=>c.charCodeAt(0));
    let bytes=[0,255,3,label.length,...label,0,192+channel,channel?32:73], tick=0;
    const scheduled=[];
    for(const e of events.filter(e=>e.voice===voice&&!e.rest)) {
      const start=Math.round(e.onset_beats*480),end=start+Math.round(e.duration_beats*480);
      scheduled.push([start,[144+channel,e.pitch_midi,80]],[end,[128+channel,e.pitch_midi,0]]);
    }
    scheduled.sort((a,b)=>a[0]-b[0]);
    for(const [at,msg] of scheduled){bytes.push(...vlq(at-tick),...msg);tick=at;}
    bytes.push(...vlq(7680-tick),255,47,0); tracks.push(chunk('MTrk',bytes));
  });
  return new Uint8Array([...chunk('MThd',[0,1,0,3,1,224]),...tracks.flat()]);
}

export class DuetAudio {
  constructor(onFrame, onState, contextFactory = () => new AudioContext()) {
    this.onFrame=onFrame;this.onState=onState;this.contextFactory=contextFactory;
    this.context=null;this.nodes=[];this.voices={};this.generation=0;this.frame=null;
  }
  stop() {
    this.generation++;
    if(this.frame!==null)cancelAnimationFrame(this.frame);
    this.frame=null;
    for(const {osc,gain} of this.nodes){try{osc.stop();}catch{} osc.disconnect();gain.disconnect();}
    this.nodes=[];
    for(const gain of Object.values(this.voices))gain.disconnect();
    this.voices={};this.onState('Stopped',0);
  }
  mute(voice, muted){if(this.voices[voice])this.voices[voice].gain.setValueAtTime(muted?0:1,this.context.currentTime);}
  async play(events,bpm,mutes) {
    this.stop();const generation=this.generation;
    this.context ||= this.contextFactory();
    await this.context.resume();
    if(generation!==this.generation)return; // cancels races between repeated user gestures
    const ctx=this.context, beat=60/bpm, start=ctx.currentTime+.06;
    for(const voice of ['alice','bob']) {
      const gain=ctx.createGain();gain.gain.value=mutes[voice]?0:1;gain.connect(ctx.destination);this.voices[voice]=gain;
    }
    for(const e of events) {
      if(e.rest)continue;
      const osc=ctx.createOscillator(),gain=ctx.createGain(),real=new Float32Array(6),imag=new Float32Array(6);
      if(e.voice==='alice'){imag[1]=1/1.2;imag[2]=.2/1.2;}
      else{const scale=1+1/9+1/25;imag[1]=1/scale;imag[3]=-1/9/scale;imag[5]=1/25/scale;}
      osc.setPeriodicWave(ctx.createPeriodicWave(real,imag,{disableNormalization:true}));
      osc.frequency.value=440*2**((e.pitch_midi-69)/12);
      const at=start+e.onset_beats*beat,duration=e.duration_beats*beat;
      gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(.18,at+.01);
      gain.gain.setValueAtTime(.18,at+duration-.03);gain.gain.linearRampToValueAtTime(0,at+duration);
      osc.connect(gain);gain.connect(this.voices[e.voice]);osc.start(at);osc.stop(at+duration);
      this.nodes.push({osc,gain});
    }
    this.onState('Playing',this.nodes.length);
    const frame=()=>{
      if(generation!==this.generation)return;
      const position=Math.max(0,(ctx.currentTime-start)/beat);
      if(position>=16){this.stop();this.onFrame(0);return;}
      this.onFrame(position);this.frame=requestAnimationFrame(frame);
    };
    frame();
  }
}

function download(name,type,body) {
  // Qollab's preview sandbox permits scripts but not direct downloads. Keep a
  // visible, lossless export and a console envelope for its Download output UI.
  const encoding=typeof body==='string'?'utf-8':'base64';
  const payload=encoding==='utf-8'?body:btoa(String.fromCharCode(...body));
  $('export-panel').hidden=false;
  $('export-description').textContent=`${name} · ${encoding}. Direct download is attempted. In Qollab, use Console → Download output, then the supplied extract_duet_exports.py utility; or copy this payload. Export adds no backend shots.`;
  $('export-payload').value=payload;
  console.log(JSON.stringify({event:'duet-export',filename:name,encoding,payload}));
  const url=URL.createObjectURL(new Blob([body],{type}));
  const anchor=document.createElement('a');anchor.href=url;anchor.download=name;document.body.append(anchor);anchor.click();anchor.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),10000);
}

export function mountDuet(run, environment) {
  let take=null,requested=false;
  let finish;
  const generated = new Promise(resolve => { finish = resolve; });
  const method=()=>$('method').value;
  const tempo=()=>{const n=Number($('tempo').value);if(!Number.isFinite(n)||n<60||n>180)throw Error('Tempo must be 60..180 BPM');return n;};
  const frame=position=>{
    if(!take)return;
    const i=Math.min(15,Math.floor(position)),r=take.rounds[method()][i];
    for(const voice of ['alice','bob']) {
      const lane=$(voice+'-lane');
      lane.querySelector('.playhead').style.left=(100*position/16)+'%';
      lane.querySelectorAll('.note').forEach((node,j)=>node.classList.toggle('active',j===i));
    }
    const a=take.events[method()].find(e=>e.round===i&&e.voice==='alice'),b=take.events[method()].find(e=>e.round===i&&e.voice==='bob');
    $('round').textContent=`Round ${i+1}/16 · x=${r.x}, y=${r.y}, a=${r.a}, b=${r.b} · required parity ${r.required_parity} · ${r.win?'rule satisfied':'rule not satisfied'} | Alice ${noteName(a.pitch_midi)} @ ${a.onset_beats.toFixed(1)} beats · Bob ${noteName(b.pitch_midi)} @ ${b.onset_beats.toFixed(1)} beats`;
  };
  const audio=new DuetAudio(frame,(state,n)=>{
    $('playback-status').textContent=`${state} · ${n} scheduled voice notes · existing take replay`;
    $('playback-status').dataset.activeNodes=String(n);
  });
  const draw=()=>{
    if(!take)return;
    for(const voice of ['alice','bob']) {
      const lane=$(voice+'-lane');lane.replaceChildren();
      for(const e of take.events[method()].filter(e=>e.voice===voice)){
        const cell=document.createElement('span');cell.className='note'+(e.rest?' rest':'');
        cell.textContent=noteName(e.pitch_midi);cell.title=`Round ${e.round+1}: token ${e.base_token}, output ${e.local_output}, ${e.onset_beats} beats`;
        cell.style.transform=`translateY(${e.rest?0:(voice==='alice'?78:54)-e.pitch_midi}px)`;lane.append(cell);
      }
      const head=document.createElement('span');head.className='playhead';lane.append(head);
      lane.setAttribute('aria-label',`${voice} notes: `+take.events[method()].filter(e=>e.voice===voice).map(e=>`${e.round+1} ${noteName(e.pitch_midi)}`).join(', '));
    }
    const q=take.excerpt.quantum,c=take.excerpt.classical;
    $('excerpt').textContent=`16-round excerpt: quantum ${q.wins}/16, local classical ${c.wins}/16. Every round retained, including rests. These scores are not the full batch estimate.`;
    frame(0);
  };
  $('environment').textContent=environment;
  $('generate').onclick=async()=>{
    if(requested)return;
    const shots=Number($('shots').value);
    if(!Number.isInteger(shots)||shots<16||shots>4096){$('status').textContent='Shots must be an integer from 16 to 4096.';return;}
    requested=true;
    for(const id of ['generate','batch','shots','execution-type'])$(id).disabled=true;
    $('status').textContent='Running one inference job…';
    try {
      take=assertTake(await run({shots,mode:$('batch').value,executionType:$('execution-type').value}));
      const stats=take.statistics;
      $('estimate').textContent=percent(stats.expected_success);
      $('quantum-reference').textContent=percent(take.references.quantum_exact);
      $('interval').textContent=`95% Hoeffding: ${percent(stats.success_interval[0])}–${percent(stats.success_interval[1])}`;
      $('allocation').textContent=`${stats.total_independent_shots.toLocaleString()} CHSH shots · ${stats.shots_per_setting} per setting · fixed equal allocation. Conditional independence assumed; not hardware-certified.`;
      $('melody-origin').textContent=take.base_melody.generated_now?'Current-run QCBM melody':'Recorded M3A QCBM melody';
      $('angles').textContent='Trained angles [A0, A1, B0, B1] in radians: '+take.models.bell_angles_radians.map(x=>x.toFixed(6)).join(', ');
      $('status').textContent=`Take loaded · ${take.execution.backend_name} · ${take.execution.execution_mode} · ${take.execution.circuit_count} circuits / one job. Playback order reconstructed from counts. Job ${take.execution.job_id}`;
      for(const id of ['play','stop','midi','json'])$(id).disabled=false;
      draw();console.log(JSON.stringify({event:'take-loaded',execution:take.execution,statistics:stats}));
    } catch(error) {
      take=null;$('status').textContent=`Backend failed: ${error.message}. No fallback or second job. Use Qollab Stop → Run for an explicitly selected new run.`;
      console.error($('status').textContent);
    }
  };
  $('play').onclick=async()=>{
    if(!take)return;
    try{await audio.play(take.events[method()],tempo(),{alice:$('mute-alice').checked,bob:$('mute-bob').checked});}
    catch(error){audio.stop();$('playback-status').textContent='Audio failed: '+error.message;}
  };
  $('stop').onclick=()=>{audio.stop();frame(0);};
  $('method').onchange=()=>{audio.stop();draw();};
  $('tempo').onchange=()=>{audio.stop();frame(0);};
  for(const voice of ['alice','bob'])$('mute-'+voice).onchange=()=>audio.mute(voice,$('mute-'+voice).checked);
  $('midi').onclick=()=>{try{download(`quantum-duet-${method()}.mid`,'audio/midi',midiBytes(take.events[method()],tempo()));}catch(error){$('playback-status').textContent=error.message;}};
  $('json').onclick=()=>download('quantum-duet-run.json','application/json',JSON.stringify({ ...take,
    export_view:{method:method(),tempo_bpm:Number($('tempo').value),mute_alice:$('mute-alice').checked,mute_bob:$('mute-bob').checked,experimental_shots_unchanged:true}},null,2));
  window.addEventListener('pagehide',()=>{audio.stop();finish();});
  // Keep Qollab's Run alive for playback/export console messages until Stop.
  // The requested guard still permits exactly one backend call on this page.
  return generated;
}
