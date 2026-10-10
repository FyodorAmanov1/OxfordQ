// Coordinator-owned browser sidecar; authoritative raw events never change.
const check = (ok, message) => { if (!ok) throw Error(message); };
const stable = v => JSON.stringify(v && typeof v === 'object' ? Array.isArray(v) ? v.map(x=>JSON.parse(stable(x))) : Object.fromEntries(Object.keys(v).sort().map(k=>[k,JSON.parse(stable(v[k]))])) : v);
const digest = async text => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))), b=>b.toString(16).padStart(2,'0')).join('');

export async function validateSource(raw, sourceText) {
  if (sourceText != null) check(await digest(sourceText) === raw.raw_source.sha256, 'Original raw source byte digest mismatch');
}

export async function playbackProjection(raw, rawText, projection) {
  const p=projection;
  check(p?.projection_version==='qm.browser-playback.v1' && p.run_id===raw.run_id, 'Playback projection identity mismatch');
  check(await digest(rawText)===p.raw_envelope_sha256, 'Original envelope byte digest mismatch');
  check(typeof p.raw_envelope_canonical_json_text==='string' && stable(JSON.parse(p.raw_envelope_canonical_json_text))===stable(raw) && await digest(p.raw_envelope_canonical_json_text)===p.raw_envelope_canonical_json_sha256, 'Canonical envelope identity mismatch');
  check(stable(p.raw_source)===stable(raw.raw_source) && p.ppq===raw.ppq && p.tempo_bpm===raw.tempo_bpm, 'Projection source/metre mismatch');
  check(Object.keys(p.policies||{}).sort().join(',')==='classical,quantum', 'Both policy outcomes required');
  const events={}, errors=[];
  for(const method of ['quantum','classical']) {
    const a=p.policies[method];
    check(Array.isArray(a.errors) && a.fallback?.used===false && a.requested_backend==='rules', 'Invalid arrangement error/backend report');
    if(a.status==='failed') {
      check(a.errors.length>0 && a.events?.length===0 && a.lineage?.length===0, 'Failed arrangement contains invented playback');
      errors.push(...a.errors.map(e=>`${method}: ${e.stage}/${e.code}: ${e.message}`));
      events[method]=null;continue;
    }
    check(a.status==='completed' && a.actual_backend==='rules' && a.errors.length===0 && /^[a-f0-9]{64}$/.test(a.arrangement_result_sha256), 'Invalid successful arrangement provenance');
    check(a.events?.length===32 && Array.isArray(a.lineage) && Array.isArray(a.transformation_ids), 'Incomplete arranged events/lineage');
    const sources=new Map(raw.events[method].map(e=>[e.event_id,e])), seen=new Set(), ids=new Set(), transforms=new Set(a.transformation_ids), lines=new Map(a.lineage.map(l=>[l.output_id,l]));
    check(lines.size===a.lineage.length && transforms.size===lines.size && transforms.size===a.transformation_ids.length, 'Duplicate arrangement lineage');
    for(const e of a.events) {
      check(e.source_event_ids?.length===1 && sources.has(e.source_event_ids[0]), 'Unknown arranged source event');
      const s=sources.get(e.source_event_ids[0]), l=lines.get(e.output_id);
      check(!seen.has(s.event_id) && e.run_id===raw.run_id && e.round_id===s.round_id && e.round===s.round && e.voice===s.voice && typeof e.event_id==='string' && !ids.has(e.event_id) && e.event_id!==s.event_id, 'Invalid arranged run/round/event lineage');
      seen.add(s.event_id);ids.add(e.event_id);
      check(typeof e.rest==='boolean' && typeof e.muted==='boolean' && (e.rest?e.pitch_midi===null:Number.isInteger(e.pitch_midi)&&e.pitch_midi>=0&&e.pitch_midi<=127) && Number.isInteger(e.velocity)&&e.velocity>=1&&e.velocity<=127, 'Invalid arranged pitch/mute/velocity');
      check(Number.isFinite(e.onset_beats)&&e.onset_beats>=0&&Number.isFinite(e.duration_beats)&&e.duration_beats>0&&e.onset_beats+e.duration_beats<=16, 'Invalid arranged timing');
      if(s.rest) check(e.rest&&!e.muted&&e.onset_beats===s.onset_beats&&e.duration_beats===s.duration_beats&&e.velocity===s.velocity&&!l, 'Raw rest was changed');
      else {
        check(l && l.run_id===raw.run_id && l.round_id===s.round_id && l.event_id===s.event_id && l.source_id===e.source_id && l.transformation_id===e.transformation_id && e.event_id===e.transformation_id && transforms.has(e.transformation_id) && l.muted===e.muted && e.rest===e.muted, 'Invalid output/source/transform lineage');
        const active=raw.events[method].filter(s=>s.voice===e.voice&&!s.rest);
        check(e.source_id===`${e.voice}:n${active.findIndex(s=>s.event_id===e.source_event_ids[0])}` && e.transformation_id===`${raw.run_id}/arranged/rules/${method}/${e.output_id}` && Number.isInteger(e.onset_beats*raw.ppq)&&Number.isInteger(e.duration_beats*raw.ppq), 'Invalid MIDI tick projection');
        lines.delete(e.output_id);
      }
    }
    check(seen.size===32&&lines.size===0&&a.events.some(e=>e.voice==='alice'&&!e.rest), 'Incomplete/silent arrangement');
    events[method]=a.events;
  }
  check(p.available===(errors.length===0), 'Projection availability contradicts policy outcomes');
  return {events, errors, available:errors.length===0};
}
