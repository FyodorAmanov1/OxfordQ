// UI-only projection. This does not execute inference or central arrangement.
const check = (ok, message) => { if (!ok) throw Error(message); };
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const text = value => typeof value === 'string' && value.length > 0;
export function freezeJSON(value) {
  if (value && typeof value === 'object') { Object.values(value).forEach(freezeJSON); Object.freeze(value); }
  return value;
}
function musicalEvent(e) {
  check(['alice','bob'].includes(e.voice), 'Unknown event voice');
  check(typeof e.rest === 'boolean' && (e.rest ? e.pitch_midi === null : Number.isInteger(e.pitch_midi) && e.pitch_midi >= 0 && e.pitch_midi <= 127), 'Invalid MIDI pitch/rest');
  check(Number.isInteger(e.velocity) && e.velocity >= 1 && e.velocity <= 127, 'Invalid MIDI velocity');
  check(finite(e.onset_beats) && e.onset_beats >= 0 && finite(e.duration_beats) && e.duration_beats > 0 && e.onset_beats + e.duration_beats <= 16, 'Invalid four-bar event timing');
  check(Math.round(e.duration_beats*480)>0, 'Event duration is below MIDI tick resolution');
}
export function validateEnvelope(result) {
  check(result?.contract_version === 'qm.run-result.v1', 'Unknown run-result contract version');
  check(text(result.run_id) && ['raw','arranged'].includes(result.mode), 'Invalid run identity/mode');
  check(['completed','failed'].includes(result.status) && Array.isArray(result.errors), 'Invalid result status/errors');
  for (const e of result.errors) check(text(e.stage) && text(e.code) && text(e.message), 'Invalid structured error');
  check(result.fallback && typeof result.fallback.requested === 'boolean' && typeof result.fallback.used === 'boolean', 'Missing explicit fallback');
  check(!result.fallback.used || result.fallback.requested && text(result.fallback.reason), 'Undeclared fallback');
  if (result.status === 'failed') {
    check(result.errors.length > 0, 'Failed result requires explicit errors');
    check(!result.events || Object.values(result.events).every(events => events.length === 0), 'Failed result cannot contain successful events');
    return result;
  }
  check(finite(result.tempo_bpm) && result.tempo_bpm > 0 && result.tempo_bpm <= 400 && result.beats_per_bar === 4 && result.ppq === 480, 'Unsupported tempo/metre/ppq');
  check(hash(result.raw_source?.sha256) && hash(result.raw_source?.canonical_json_sha256) && text(result.raw_source.asset), 'Missing raw source identity');
  check(hash(result.models?.bell_checkpoint_sha256) && hash(result.models?.qcbm_checkpoint_sha256) && result.models.qcbm_parameters === 84 && result.models.qcbm_qubits === 12 && result.models.bell_angles_radians?.length === 4 && result.models.bell_angles_radians.every(finite), 'Invalid model provenance');
  const execution = result.execution;
  check(execution && ['recorded','live','mock'].includes(execution.data_status) && text(execution.backend_name) && text(execution.backend_class) && ['five-live','four-recorded'].includes(execution.mode), 'Missing execution provenance');
  check(Number.isInteger(execution.backend_run_calls_this_replay) && execution.backend_run_calls_this_replay >= 0, 'Missing replay call count');
  check(Number.isInteger(execution.backend_run_calls) && execution.backend_run_calls >= 0 && text(execution.backend_version) && text(execution.execution_mode) && typeof execution.execution_mode_verified === 'boolean', 'Missing backend/simulator identity');
  check(execution.data_status !== 'recorded' || execution.backend_run_calls_this_replay === 0, 'Recorded replay cannot submit new calls');
  check(result.rounds?.length === 16, 'Expected all 16 paired rounds');
  result.rounds.forEach((r,i) => {
    check(r.index === i && r.round_id === `${result.run_id}/r${String(i).padStart(2,'0')}`, 'Invalid paired round identity');
    check([r.cues?.alice,r.cues?.bob,r.quantum?.alice,r.quantum?.bob,r.classical?.alice,r.classical?.bob].every(v => v === 0 || v === 1), 'Invalid paired decisions');
    check(r.quantum.displayed_ba === `${r.quantum.bob}${r.quantum.alice}`, 'Invalid ba bit order');
    for (const method of ['quantum','classical']) check(r[method].win === ((r[method].alice ^ r[method].bob) === (r.cues.alice * r.cues.bob)), 'Invalid round win');
    check(r.classical.shared_strategy?.length === 4 && r.classical.shared_strategy.every(v => v === 0 || v === 1) && text(r.measurement_provenance), 'Missing classical/measurement provenance');
    check(r.classical.alice === r.classical.shared_strategy[r.cues.alice] && r.classical.bob === r.classical.shared_strategy[2+r.cues.bob], 'Classical decision contradicts precommitted strategy');
  });
  for (const method of ['quantum','classical']) {
    const events = result.events?.[method], ids = new Set(), pairs = new Set();
    check(events?.length === 32, 'Expected 32 events per comparator including rests');
    for (const e of events) {
      musicalEvent(e);
      check(Number.isInteger(e.round) && e.round >= 0 && e.round < 16 && e.run_id === result.run_id && e.round_id === result.rounds[e.round].round_id && text(e.event_id) && !ids.has(e.event_id), 'Invalid event lineage');
      check(e.base_token === result.rounds[e.round].base_token && e.local_output === result.rounds[e.round][method][e.voice], 'Event changed local mapping identity');
      ids.add(e.event_id); pairs.add(`${e.voice}/${e.round}`);
    }
    check(pairs.size === 32, 'Duplicate/missing voice round');
  }
  const settings = execution.experiments?.filter(e => e.role === 'coordination');
  check(settings?.length === 4 && new Set(settings.map(e => e.name)).size === 4, 'Missing named CHSH histograms');
  let total = 0, wins = 0;
  for (let i=0;i<4;i++) {
    const e=settings.find(s=>s.name===`duet_xy_${Math.floor(i/2)}${i%2}`);
    check(e && e.setting?.join('') === `${Math.floor(i/2)}${i%2}` && Number.isInteger(e.shots) && e.shots > 0 && e.shots === result.statistics.shots_per_setting, 'Invalid named setting allocation');
    let count = 0;
    for (const [ba,n] of Object.entries(e.counts)) {
      check(/^[01]{2}$/.test(ba) && Number.isInteger(n) && n >= 0, 'Invalid integer histogram'); count += n;
      if ((Number(ba[0]) ^ Number(ba[1])) === e.setting[0]*e.setting[1]) wins += n;
    }
    check(count === e.shots, 'Histogram allocation mismatch'); total += count;
  }
  check(result.statistics?.total_independent_shots === total && Math.abs(result.statistics.expected_success - wins/total) < 1e-12, 'CHSH statistic mismatch');
  check(result.statistics.success_interval?.length === 2 && result.statistics.success_interval.every(v => finite(v) && v >= 0 && v <= 1) && result.statistics.success_interval[0] <= result.statistics.expected_success && result.statistics.success_interval[1] >= result.statistics.expected_success, 'Invalid conditional interval');
  check(text(result.statistics.interval_method) && text(result.statistics.independence_assumption), 'Missing interval assumptions');
  return result;
}

export function readEnvelope(value) {
  let rawText=typeof value==='string'?value:JSON.stringify(value), result=JSON.parse(rawText);
  if(result.run_result) {
    check(typeof result.raw_envelope_text==='string', 'Missing original envelope text in export');
    const original=JSON.parse(result.raw_envelope_text);
    check(JSON.stringify(original)===JSON.stringify(result.run_result), 'Export result contradicts original envelope');
    rawText=result.raw_envelope_text;result=original;
  }
  return {rawText,result};
}

// Optional paired playback projection only: arranged.events.{quantum,classical}.
// Production B output mapping is a coordinator dependency; no schema is invented
// for B's score/parts. Metadata can be inspected even without this projection.
export function arrangedPlayback(result) {
  const a = result.arranged;
  check(a && a.events, 'Arranged playback unavailable: no supplied paired event projection');
  check(a.raw_source_sha256 === result.raw_source.sha256 && Array.isArray(a.transformation_ids) && a.transformation_ids.length > 0 && a.transformation_ids.every(text), 'Arranged source/transform provenance mismatch');
  check(text(a.requested_backend) && text(a.actual_backend) && Array.isArray(a.errors) && a.errors.length === 0 && a.fallback && typeof a.fallback.used === 'boolean', 'Arranged errors or missing backend/fallback report');
  for (const method of ['quantum','classical']) {
    check(Array.isArray(a.events[method]) && a.events[method].length > 0, 'Arranged comparator unavailable');
    const sources = new Map(result.events[method].map(e => [e.event_id,e]));
    const ids = new Set();
    for (const e of a.events[method]) {
      musicalEvent(e);
      check(text(e.event_id) && !ids.has(e.event_id) && e.run_id === result.run_id && Array.isArray(e.source_event_ids) && e.source_event_ids.length > 0 && e.source_event_ids.every(id => sources.get(id)?.round_id === e.round_id && sources.get(id)?.voice === e.voice), 'Invalid arranged source/round lineage');
      ids.add(e.event_id);
    }
    check(a.events[method].some(e => e.voice === 'alice' && !e.rest) && a.events[method].some(e => e.voice === 'bob'), 'Arranged lead/comparator silent or missing');
  }
  return a.events;
}

export function envelopeView(result) {
  validateEnvelope(result);
  if (result.status === 'failed') throw Error(result.errors.map(e => `${e.stage}/${e.code}: ${e.message}`).join('; '));
  const rounds = {};
  for (const method of ['quantum','classical']) rounds[method] = result.rounds.map(r => ({x:r.cues.alice,y:r.cues.bob,a:r[method].alice,b:r[method].bob,required_parity:r.cues.alice*r.cues.bob,win:r[method].win,round_id:r.round_id}));
  return { ...result, rounds, excerpt:Object.fromEntries(['quantum','classical'].map(m => [m,{wins:rounds[m].filter(r => r.win).length}])) };
}

export function exportEnvelope(rawText, result, view) {
  // Original text and parsed envelope stay intact, including arranged provenance.
  return JSON.stringify({raw_envelope_text:rawText,run_result:result,export_view:{...view,experimental_shots_unchanged:true}},null,2);
}
