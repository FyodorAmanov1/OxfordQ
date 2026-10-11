import {playbackProjection,validateSource} from './playback-projection.mjs';
import {freezeJSON, envelopeView, arrangedPlayback, exportEnvelope, readEnvelope} from './run-contract.mjs';
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
export function midiBytes(events, bpm, identity = null) {
  if(!Number.isFinite(bpm)||bpm<=0||bpm>400||Math.round(60000000/bpm)>0xffffff)throw Error('Invalid MIDI tempo');
  const u32 = n => [(n>>>24)&255,(n>>>16)&255,(n>>>8)&255,n&255];
  const vlq = n => { let b=[n&127]; while(n>>=7)b.unshift((n&127)|128); return b; };
  const chunk = (name, bytes) => [...Array.from(name,c=>c.charCodeAt(0)),...u32(bytes.length),...bytes];
  const metadata = value => {const bytes=Array.from(new TextEncoder().encode(value));return [0,255,1,...vlq(bytes.length),...bytes];};
  const tempo = Math.round(60000000/bpm);
  const conductor = [...(identity?metadata(JSON.stringify(identity)):[]),0,255,81,3,(tempo>>>16)&255,(tempo>>>8)&255,tempo&255,0,255,88,4,4,2,24,8,...vlq(7680),255,47,0];
  const tracks = [chunk('MTrk',conductor)];
  ['alice','bob'].forEach((voice,channel)=>{
    const label=Array.from(voice,c=>c.charCodeAt(0));
    let bytes=[0,255,3,label.length,...label,0,192+channel,channel?41:73], tick=0;
    const scheduled=[];
    for(const e of events.filter(e=>e.voice===voice&&!e.rest)) {
      if(!Number.isInteger(e.pitch_midi)||e.pitch_midi<0||e.pitch_midi>127||!Number.isFinite(e.onset_beats)||e.onset_beats<0||!Number.isFinite(e.duration_beats)||e.duration_beats<=0||e.onset_beats+e.duration_beats>16)throw Error('Invalid MIDI event');
      const velocity=e.velocity??80;
      if(!Number.isInteger(velocity)||velocity<1||velocity>127)throw Error('Invalid MIDI velocity');
      const start=Math.round(e.onset_beats*480),end=start+Math.round(e.duration_beats*480);
      if(end<=start||end>7680)throw Error('Invalid MIDI tick timing');
      if(identity)bytes.push(...metadata(JSON.stringify({event_id:e.event_id,round_id:e.round_id,voice:e.voice,pitch_midi:e.pitch_midi,velocity,start_tick:start,end_tick:end,source_event_ids:e.source_event_ids})));
      scheduled.push([start,[144+channel,e.pitch_midi,velocity]],[end,[128+channel,e.pitch_midi,0]]);
    }
    scheduled.sort((a,b)=>a[0]-b[0] || a[1][0]-b[1][0]);
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
      const level=.18*(e.velocity??80)/80,attack=Math.min(.01,duration/4),release=Math.min(.03,duration/4);
      gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(level,at+attack);
      gain.gain.setValueAtTime(level,at+duration-release);gain.gain.linearRampToValueAtTime(0,at+duration);
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

export function mountDuet(run, environment, options = {}) {
  let take=null,requested=false,envelope=null,rawText=null,arranged=null,projection=null,sourceText=null,loading=false,closed=false;
  let finish, updateMusicMode=()=>{};
  const generated = new Promise(resolve => { finish = resolve; });
  const method=()=>$('method').value;
  const events=()=> $('music-mode').value === 'arranged' ? arranged[method()] : take.events[method()];
  const tempo=()=>{const n=Number($('tempo').value);if(!Number.isFinite(n)||n<=0||n>400)throw Error('Tempo must be greater than 0 and at most 400 BPM');return n;};
  const frame=position=>{
    if(!take)return;
    const i=Math.min(15,Math.floor(position)),r=take.rounds[method()][i];
    for(const voice of ['alice','bob']) {
      const lane=$(voice+'-lane');
      lane.querySelector('.playhead').style.left=(100*position/16)+'%';
      lane.querySelectorAll('.note').forEach(node=>node.classList.toggle('active',Number(node.dataset.round)===i));
    }
    const a=take.events[method()].find(e=>e.round===i&&e.voice==='alice'),b=take.events[method()].find(e=>e.round===i&&e.voice==='bob');
    $('round').textContent=`${r.round_id || 'Legacy round '+(i+1)} · x=${r.x}, y=${r.y}, a=${r.a}, b=${r.b} · required parity ${r.required_parity} · ${r.win?'rule satisfied':'rule not satisfied'} | Raw Alice ${noteName(a.pitch_midi)} @ ${a.onset_beats.toFixed(1)} beats · Bob ${noteName(b.pitch_midi)} @ ${b.onset_beats.toFixed(1)} beats`;
  };
  const audio=new DuetAudio(frame,(state,n)=>{
    $('playback-status').textContent=`${state} · ${n} scheduled voice notes · existing take replay`;
    $('playback-status').dataset.activeNodes=String(n);
  });
  const draw=()=>{
    if(!take)return;
    for(const voice of ['alice','bob']) {
      const lane=$(voice+'-lane');lane.replaceChildren();
      for(const e of events().filter(e=>e.voice===voice)){
        const cell=document.createElement('span');cell.className='note'+(e.rest?' rest':'');
        cell.dataset.round=String(e.round??envelope.rounds.findIndex(r=>r.round_id===e.round_id));
        cell.textContent=noteName(e.pitch_midi);cell.title=`${e.round_id || 'Round '+(e.round+1)}: token ${e.base_token??'arranged'}, output ${e.local_output??'arranged'}, ${e.onset_beats} beats`;
        cell.style.gridColumn=String(Number(cell.dataset.round)+1);
        cell.style.transform=`translateY(${e.rest?0:(voice==='alice'?78:54)-e.pitch_midi}px)`;lane.append(cell);
      }
      const head=document.createElement('span');head.className='playhead';lane.append(head);
      lane.setAttribute('aria-label',`${voice} notes: `+events().filter(e=>e.voice===voice).map(e=>`${e.round_id || e.round+1} ${noteName(e.pitch_midi)}`).join(', '));
    }
    const q=take.excerpt.quantum,c=take.excerpt.classical;
    $('excerpt').textContent=`16-round excerpt: quantum ${q.wins}/16, local classical ${c.wins}/16. Every round retained, including rests. These scores are not the full batch estimate.`;
    frame(0);
  };
  $('environment').textContent=environment;
  const controls = enabled => {for(const id of ['play','stop','midi','json'])$(id).disabled=!enabled;};
  const reportError = error => {
    audio.stop();take=null;envelope=null;arranged=null;rawText=null;controls(false);
    $('music-mode').value='raw';$('music-mode').options[1].disabled=true;
    $('status').dataset.error='true';$('status').textContent=`Result failed: ${error.message}. No fallback or automatic retry.`;
    for(const id of ['alice-lane','bob-lane'])$(id).replaceChildren();
    $('estimate').textContent='—';$('interval').textContent='No successful result';$('evidence-origin').textContent='Failed / unavailable';
    $('allocation').textContent='No successful counts displayed';$('melody-origin').textContent='Unavailable';$('round').textContent='No playable result';
    $('provenance').textContent=error.message;$('music-provenance').textContent='Raw / arranged playback unavailable';$('export-panel').hidden=true;
  };
  const install = async (value, fixtureLabel = '') => {
    audio.stop();const supplied=readEnvelope(value);rawText=supplied.rawText;
    const parsed=supplied.result;envelope=null;arranged=null;projection=supplied.projection;sourceText=supplied.sourceText;
    if(parsed.contract_version!==undefined) {
      take=envelopeView(parsed);envelope=freezeJSON(parsed);await validateSource(envelope,sourceText);
    } else {
      take=assertTake(parsed);freezeJSON(take);
    }
    $('music-mode').value='raw';const option=$('music-mode').options[1];option.disabled=true;option.textContent='Arranged · unavailable';
    let arrangedMessage=envelope?.status==='failed'?`Arrangement failed: ${envelope.errors.map(e=>`${e.stage}/${e.code}: ${e.message}`).join('; ')}`:'Arranged unavailable: no supplied output.';
    if(projection) {
      try {const validated=await playbackProjection(envelope,rawText,projection);arranged=validated.events;freezeJSON(projection);option.disabled=!validated.available;option.textContent='Arranged · local rules (per policy)';arrangedMessage=validated.errors.length?validated.errors.join('; '):'Separate creative rules output · zero new shots. Plan retained in projection provenance.';}
      catch(error){arranged=null;arrangedMessage=error.message;}
    } else if(envelope?.arranged) {
      try {arranged=arrangedPlayback(envelope);option.disabled=false;option.textContent='Arranged · supplied output';arrangedMessage='Arranged supplied and validated for paired playback.';}
      catch(error){arrangedMessage+=` ${error.message}`;}
    }
    const stats=take.statistics,execution=take.execution;
    $('tempo').value=String(envelope?.tempo_bpm??120);
    $('estimate').textContent=percent(stats.expected_success);
    $('quantum-reference').textContent=percent(take.references.quantum_exact);
    $('interval').textContent=`${stats.interval_method}: ${percent(stats.success_interval[0])}–${percent(stats.success_interval[1])}`;
    const origin=envelope?execution.data_status.toUpperCase():'LIVE legacy take';
    $('allocation').textContent=`${stats.total_independent_shots.toLocaleString()} ${envelope?.execution.data_status==='recorded'?'historical':'returned'} CHSH shots · ${stats.shots_per_setting} per setting. QCBM/excerpt excluded. Conditional independence assumed; not hardware-certified.`;
    $('evidence-origin').textContent=`${origin} · all CHSH counts`;
    $('melody-origin').textContent=envelope?`${origin} · ${execution.mode}`:take.base_melody.generated_now?'Current-run QCBM melody':'Recorded M3A QCBM melody';
    $('angles').textContent='Trained angles [A0, A1, B0, B1] in radians: '+take.models.bell_angles_radians.map(x=>x.toFixed(6)).join(', ');
    $('status').dataset.error='false';
    $('status').textContent=envelope?`${origin} ${fixtureLabel} · ${execution.backend_name} · run ${envelope.run_id} · ${execution.backend_run_calls_this_replay} backend calls this replay / zero new shots from loading. Historical/original calls ${execution.backend_run_calls}. Counts order reconstructed.`:`LIVE legacy take · ${execution.backend_name} · ${execution.execution_mode} · ${execution.circuit_count} circuits / one job. Job ${execution.job_id}. Run/round envelope integration pending.`;
    $('provenance').textContent=JSON.stringify(envelope?{run_id:envelope.run_id,execution:{...execution,experiments:undefined},models:envelope.models,raw_source:envelope.raw_source,errors:envelope.errors,fallback:envelope.fallback,playback_projection:projection,arranged:envelope.arranged?{...envelope.arranged,events:undefined}:null}:{execution,models:take.models,identity:'Legacy bridge has no shared envelope; original JSON retained'},null,2);
    const provenance=()=>{
      if($('music-mode').value==='raw') {
        $('music-provenance').textContent=`RAW · direct local mapping, central arranger bypassed. ${arrangedMessage}`;
      } else {
        const a=projection?.policies[method()]??envelope.arranged;
        const transforms=projection?a.transformation_ids.length:a.transformation_ids.join(', ');
        $('music-provenance').textContent=`ARRANGED · ${a.actual_backend} · ${method()} · transforms ${transforms} · ${a.creative_plan?.key??'supplied creative plan'} · immutable raw source ${envelope.raw_source.sha256}. CHSH evidence refers to raw source.`;
      }
    };
    updateMusicMode=()=>{
      option.disabled=!arranged?.[method()];
      if(option.disabled)$('music-mode').value='raw';
      provenance();
    };
    $('music-mode').onchange=()=>{audio.stop();updateMusicMode();draw();};updateMusicMode();
    $('export-panel').hidden=true;controls(true);if($('arrange'))$('arrange').disabled=!options.arrange||!envelope||envelope.status!=='completed';draw();
    console.log(JSON.stringify({event:'take-loaded',run_id:envelope?.run_id,execution:execution,statistics:stats}));
  };
  const load=async (loader, label='')=>{
    if(loading||closed)return;
    loading=true;audio.stop();controls(false);$('fixture').disabled=true;$('import-result').disabled=true;
    const generateDisabled=$('generate').disabled;$('generate').disabled=true;
    try{const value=await loader();if(!closed)await install(value,label);}catch(error){if(!closed)reportError(error);}
    finally{loading=false;$('fixture').disabled=false;$('import-result').disabled=false;$('generate').disabled=generateDisabled;}
  };
  if($('arrange')) {
    $('arrange').textContent=`Arrange locally · ${options.arrangementBackend || 'rules'} · zero quantum shots`;
    $('arrange').disabled=true;
    $('arrange').onclick=async()=>{
      if(loading||closed||!envelope||!options.arrange)return;
      loading=true;audio.stop();$('arrange').disabled=true;controls(false);$('fixture').disabled=true;$('import-result').disabled=true;
      const previousGenerate=$('generate').disabled;$('generate').disabled=true;
      try {
        const bundle=await options.arrange(rawText,sourceText), returned=readEnvelope(bundle);
        if(returned.rawText!==rawText || returned.sourceText!==sourceText)throw Error('Arrangement response changed original evidence');
        if(!closed)await install(bundle);
      }
      catch(error){controls(true);$('music-provenance').textContent=`Arrangement failed: ${error.message}. Existing RAW playback remains available.`;}
      finally{loading=false;$('arrange').disabled=false;$('fixture').disabled=false;$('import-result').disabled=false;$('generate').disabled=previousGenerate;}
    };
  }
  $('fixture').onclick=()=>load(()=>{
    if(!options.loadFixture)throw Error(options.fixtureUnavailable||'Recorded fixture loader unavailable');
    return options.loadFixture();
  },'Qollab built-in simulator fixture');
  $('import-result').onclick=()=>load(()=>{
    const text=$('import-payload').value;
    if(!readEnvelope(text).result.contract_version)throw Error('A qm.run-result envelope is required');
    return text;
  });
  $('generate').onclick=async()=>{
    if(requested||loading||closed)return;
    const shots=Number($('shots').value);
    if(!Number.isInteger(shots)||shots<16||shots>4096){$('status').textContent='Shots must be an integer from 16 to 4096.';return;}
    requested=true;
    loading=true;audio.stop();controls(false);$('fixture').disabled=true;$('import-result').disabled=true;
    for(const id of ['generate','batch','shots','execution-type'])$(id).disabled=true;
    $('status').textContent='Running one inference job…';
    try {
      const value=await run({shots,mode:$('batch').value,executionType:$('execution-type').value});
      if(!closed)await install(value);
    } catch(error) {
      reportError(error);
      console.error($('status').textContent);
    } finally {loading=false;$('fixture').disabled=false;$('import-result').disabled=false;}
  };
  $('play').onclick=async()=>{
    if(!take)return;
    try{await audio.play(events(),tempo(),{alice:$('mute-alice').checked,bob:$('mute-bob').checked});}
    catch(error){audio.stop();$('playback-status').textContent='Audio failed: '+error.message;}
  };
  $('stop').onclick=()=>{audio.stop();frame(0);};
  $('method').onchange=()=>{audio.stop();updateMusicMode();draw();};
  $('tempo').onchange=()=>{audio.stop();frame(0);};
  for(const voice of ['alice','bob'])$('mute-'+voice).onchange=()=>audio.mute(voice,$('mute-'+voice).checked);
  $('midi').onclick=()=>{try{download(`quantum-duet-${$('music-mode').value}-${method()}.mid`,'audio/midi',midiBytes(events(),tempo(),envelope?{run_id:envelope.run_id,method:method(),mode:$('music-mode').value,raw_source:envelope.raw_source,round_ids:envelope.rounds.map(r=>r.round_id),transformation_ids:$('music-mode').value==='arranged'?(projection?.policies[method()].transformation_ids??envelope.arranged.transformation_ids):[]}:null));}catch(error){$('playback-status').textContent=error.message;}};
  $('json').onclick=()=>download('quantum-duet-run.json','application/json',exportEnvelope(rawText,envelope||take,{method:method(),mode:$('music-mode').value,tempo_bpm:Number($('tempo').value),mute_alice:$('mute-alice').checked,mute_bob:$('mute-bob').checked},projection,sourceText));
  window.addEventListener('pagehide',()=>{closed=true;audio.stop();finish();});
  // Keep Qollab's Run alive for playback/export console messages until Stop.
  // The requested guard still permits exactly one backend call on this page.
  return generated;
}
