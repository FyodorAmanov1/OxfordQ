// Optional independent recording player. No generator or backend is imported.
const check = (ok, message) => { if (!ok) throw Error(message); };
export function validateShowcase(bundle) {
  check(bundle?.schema === 'oxfordq.composition-showcase.v1' && bundle.data_status === 'PRE-GENERATED'
    && bundle.backend_jobs_this_playback === 0, 'Invalid composition playback provenance');
  check(bundle.freeze?.accepted_commit === '2801ba46ed5acdc7fbf0d3cca635f50aa8a2b88c', 'Unaccepted composition version');
  const trace = JSON.parse(bundle.trace_text), raw = JSON.parse(bundle.raw_samples_text);
  check(trace.data_status === 'PRE-GENERATED' && trace.bars === 16 && trace.seconds === 32 && trace.tempo_bpm === 120
    && ['backend_jobs','sampling_calls','training_steps','statevector_evaluations'].every(k => trace[k] === 0), 'Invalid frozen composition trace');
  check(raw.seed === 20261011 && raw.motifs?.length === 16 && raw.motifs.flatMap(m => m.tokens).length === 64
    && trace.source.raw_samples_sha256 === bundle.freeze.files['raw-samples.json'].sha256, 'Invalid composition source');
  check(Object.keys(bundle.media).sort().join() === ['improved-arranged.mid','improved-arranged.wav','improved-melody.mid','improved-melody.wav'].join(), 'Incomplete frozen media');
  return {schema:'oxfordq.composition-provenance.v1', data_status:'PRE-GENERATED', backend_jobs_this_playback:0,
    freeze:bundle.freeze, raw_samples_text:bundle.raw_samples_text, trace_text:bundle.trace_text};
}
export const mediaBytes = encoded => Uint8Array.from(atob(encoded), c => c.charCodeAt(0));

export function mountComposition(loadShowcase) {
  const $ = id => document.getElementById(id), player = $('composition-audio');
  let bundle = null, provenance = null, pending = null, closed = false, generation = 0, url = null;
  const pause = () => { generation++; player.pause(); };
  const texture = () => $('composition-texture').value;
  const installAudio = () => {
    pause(); if (url) URL.revokeObjectURL(url);
    url = URL.createObjectURL(new Blob([mediaBytes(bundle.media[`improved-${texture()}.wav`])], {type:'audio/wav'}));
    player.src = url; player.load();
  };
  const exportFile = (filename, encoding, payload, type, body) => {
    $('composition-export-panel').hidden = false;
    $('composition-export-description').textContent = `${filename} · ${encoding} · PRE-GENERATED. Copy this lossless payload or use Qollab Console output; direct downloads may be blocked. No backend submissions.`;
    $('composition-export-payload').value = payload;
    console.log(JSON.stringify({event:'composition-export',filename,encoding,payload}));
    const link = document.createElement('a'), href = URL.createObjectURL(new Blob([body],{type}));
    link.href = href; link.download = filename; document.body.append(link); link.click(); link.remove();
    window.setTimeout(() => URL.revokeObjectURL(href),10000);
  };
  $('composition-texture').onchange = () => { if (bundle) installAudio(); $('composition-export-panel').hidden=true; };
  $('composition-midi').onclick = () => {
    const data=bundle.media[`improved-${texture()}.mid`];
    exportFile(`oxfordq-composition-${texture()}.mid`,'base64',data,'audio/midi',mediaBytes(data));
  };
  $('composition-json').onclick = () => {
    const text=JSON.stringify(provenance);
    exportFile('oxfordq-composition-provenance.json','utf-8',text,'application/json',text);
  };
  player.addEventListener('play', () => {
    if ($('app-mode').value !== 'composition') pause(); else $('stop').click();
  });
  player.addEventListener('error', () => {
    $('composition-status').textContent='Composition audio failed. Experiment mode remains available; no fallback or backend request.';
  });
  $('app-mode').onchange = async () => {
    pause(); $('stop').click();
    const selected=$('app-mode').value==='composition', current=generation;
    $('duet-app').hidden=selected; $('composition-app').hidden=!selected;
    if (!selected || closed) return;
    if (bundle) return;
    $('composition-status').textContent='Loading frozen PRE-GENERATED assets · zero backend submissions…';
    try {
      pending ||= Promise.resolve().then(loadShowcase);
      const loaded=await pending, verified=validateShowcase(loaded);
      if (closed) return;
      bundle=loaded; provenance=verified;
      $('composition-provenance').textContent=JSON.stringify(provenance,null,2);
      for (const id of ['composition-midi','composition-json']) $(id).disabled=false;
      installAudio();
      if (current !== generation-1 || $('app-mode').value !== 'composition') pause();
      $('composition-status').textContent='PRE-GENERATED · accepted PR #9 recording · 16 bars / 32 seconds · zero backend submissions';
    } catch (error) {
      pending=null; $('composition-status').textContent=`Composition unavailable: ${error.message}. Experiment mode remains available. No fallback or backend request.`;
    }
  };
  window.addEventListener('pagehide', () => { closed=true; pause(); if(url) URL.revokeObjectURL(url); });
}
