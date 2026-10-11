import { renderAudio } from './audio.mjs';

export async function mountComposer(generate, loadPiano) {
  const $=id=>document.getElementById(id);
  const urls=[];
  function download(id,data,type,name){
    const url=URL.createObjectURL(new Blob([data],{type}));urls.push(url);
    $(id).href=url;$(id).download=name;
  }
  const bankPromise=loadPiano().then(text=>JSON.parse(text));
  bankPromise.catch(()=>{}); // Report a failed bank load in the generation action.
  $('controls').addEventListener('submit',async event=>{
    event.preventDefault();if(!$('controls').reportValidity())return;
    $('error').hidden=true;$('generate').disabled=true;
    const parameters={seed:Number($('seed').value),bars:Number($('bars').value),
      bpm:Number($('bpm').value),shots:Number($('shots').value),interaction:Number($('interaction').value)};
    const controls=[...$('controls').querySelectorAll('input,select')];controls.forEach(e=>e.disabled=true);
    $('status').textContent='Running one musical quantum-walk job, then evolving the persistent ideal state…';
    try{
      const bank=await bankPromise; // Check audio assets before consuming a backend job.
      const score=JSON.parse(await generate(parameters));
      $('status').textContent='Quantum composition complete. Rendering the sampled piano and accompaniment…';
      // Let the new status paint before the audio renderer allocates its buffers.
      await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
      const audio=await renderAudio(score,bank);
      download('wav',audio.wav,'audio/wav','quantum-graph-composition.wav');
      $('player').src=$('wav').href;
      const midi=Uint8Array.from(atob(score.midi_base64),c=>c.charCodeAt(0));
      download('midi',midi,'audio/midi','quantum-graph-composition.mid');
      const exported={...score};delete exported.midi_base64;
      $('export-text').value=JSON.stringify(score);
      download('score',JSON.stringify(exported,null,2),'application/json','quantum-graph-composition.json');
      $('summary').textContent=`${score.metadata.key} · ${score.metadata.bars} bars · ${score.metadata.bpm} BPM · ${Math.floor(audio.seconds/60)}:${String(Math.round(audio.seconds%60)).padStart(2,'0')} · seed ${score.metadata.seed}`;
      $('theme').replaceChildren();
      const names=['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'];
      score.theme.forEach((bar,i)=>{
        const div=document.createElement('div'),title=document.createElement('strong'),notes=document.createElement('span'),rhythm=document.createElement('span');
        title.textContent=`Theme bar ${i+1}`;
        notes.textContent=bar.lead_pitches.map(p=>names[p%12]+(Math.floor(p/12)-1)).join(' · ');
        rhythm.textContent='Offsets (beats): '+bar.onsets.join(', ');
        div.append(title,notes,rhythm);$('theme').append(div);
      });
      const e=score.metadata.execution;
      $('execution').textContent=`Selected backend: ${e.backend_name}; ${e.qubits} qubits, ${e.shots} shots, ${e.backend_run_calls} job. Continuation: ${score.metadata.qubits}-qubit ideal Qiskit Statevector with ${score.metadata.steps} evolution substeps per bar. These are separate execution stages.`;
      const contours=new Set(score.decisions.map(d=>d.node.contour)).size;
      const rhythms=new Set(score.decisions.map(d=>d.node.rhythm)).size;
      const harmonies=new Set(score.decisions.map(d=>d.node.harmony)).size;
      $('decisions').textContent=`This piece selected ${contours} melodic contours, ${rhythms} attack rhythms and ${harmonies} harmonic nodes. The JSON download records every quantum-derived gesture, its answering gesture, theme distance, and musical constraint. State norm error: ${score.metadata.maximum_state_norm_error.toExponential(2)}.`;
      $('result').hidden=false;$('status').textContent='Ready to listen. Use Play below; download WAV or MIDI to keep the piece. Stop → Run starts another composition.';
      $('generate').textContent='Composition complete';
      console.log(JSON.stringify({event:'composition-complete',metadata:score.metadata,audio:{seconds:audio.seconds,peak:audio.peak,bytes:audio.wav.byteLength}}));
    }catch(error){
      $('error').textContent=`Generation stopped: ${error.message}. No simulator was substituted. Use Stop → Run to try again.`;
      $('error').hidden=false;$('status').textContent='No completed composition. The error above identifies the failure.';
      $('generate').textContent='Restart with Stop → Run';
      console.error(error);
    }
  });
  window.addEventListener('pagehide',()=>{ $('player').pause();urls.forEach(url=>URL.revokeObjectURL(url)); },{once:true});
}
