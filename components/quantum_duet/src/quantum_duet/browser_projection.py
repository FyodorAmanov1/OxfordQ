"""Coordinator-owned local creative projection; no backend execution or raw schema edits."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from orchestrator.models import Part
from quantum_duet.orchestration_adapter import arrange_result, canonical_json, freeze_result

def require(value, message):
    if not value:
        raise ValueError(message)


def project(raw_bytes, outcomes, *, raw_source_bytes=None):
    raw = json.loads(raw_bytes)
    completed = freeze_result(raw, raw_bytes=raw_source_bytes)
    if raw_source_bytes is not None:
        require(sha256(raw_source_bytes).hexdigest() == raw['raw_source']['sha256'], 'Original raw source byte digest mismatch')
    require(raw['mode'] == 'raw' and raw['status'] == 'completed', 'Require completed raw envelope')
    require(set(outcomes) == {'quantum', 'classical'}, 'Both policies required')
    projection = dict(projection_version='qm.browser-playback.v1', run_id=raw['run_id'],
        raw_envelope_sha256=sha256(raw_bytes).hexdigest(),
        raw_envelope_canonical_json_sha256=completed.canonical_sha256,
        raw_envelope_canonical_json_text=completed._json.decode('utf-8'),
        raw_source=deepcopy(raw['raw_source']), tempo_bpm=raw['tempo_bpm'], ppq=raw['ppq'],
        policies={}, errors=[], available=True)
    for policy, outcome in outcomes.items():
        freeze_result(outcome)
        for key in raw.keys() - {'mode', 'status', 'errors', 'arranged'}:
            require(outcome[key] == raw[key], f'Raw field changed: {key}')
        a = outcome['arranged']
        require(a['policy'] == policy and a['raw_result_canonical_json_sha256'] == completed.canonical_sha256,
                'Wrong policy or raw envelope digest')
        p = dict(status=outcome['status'], requested_backend=a['backend_requested'],
                 actual_backend=a['backend_actual'], errors=deepcopy(a['errors']),
                 fallback=deepcopy(a['fallback']), events=[], lineage=deepcopy(a['lineage']),
                 transformation_ids=list(a['transformation_ids']),
                 arrangement_result_sha256=sha256(canonical_json(outcome)).hexdigest(),
                 creative_plan=deepcopy(a.get('report', {}).get('plans', {}).get('arrangement')))
        projection['policies'][policy] = p
        if outcome['status'] == 'failed':
            require(p['errors'] and not a['output_parts'] and not a['lineage'], 'Failed output has invented music')
            projection['available'] = False
            projection['errors'].extend(dict(policy=policy, **e) for e in p['errors'])
            continue
        require(p['requested_backend'] in ('rules', 'gemini') and
                p['actual_backend'] == p['requested_backend'], 'Unexpected arrangement backend')
        require(not p['errors'] and not p['fallback']['used'], 'Unexpected errors/fallback')
        source_events = {e['event_id']: e for e in raw['events'][policy]}
        source_ids = {e['event_id']: f'{voice}:n{i}' for voice in ('alice', 'bob')
                      for i, e in enumerate(e for e in source_events.values() if e['voice'] == voice and not e['rest'])}
        lines = {line['output_id']: line for line in a['lineage']}
        require(len(lines) == len(a['lineage']), 'Duplicate output lineage')
        transforms = set(a['transformation_ids'])
        require(len(transforms) == len(lines), 'Incomplete transform coverage')
        require(len(transforms) == len(a['transformation_ids']), 'Duplicate transforms')
        seen, ids, parts = set(), set(), set()
        for supplied in a['output_parts']:
            for note in supplied['notes']:
                require(all(type(note[k]) is int for k in ('pitch', 'velocity', 'onset_tick', 'duration_ticks'))
                        and type(note['muted']) is bool, 'Strict MIDI tick/note types required')
            part = Part.model_validate(supplied)
            require(part.id in ('alice', 'bob') and part.id not in parts, 'Invalid output part')
            parts.add(part.id)
            for note in part.notes:
                require(note.id not in ids and note.id in lines, 'Duplicate/unlinked output note')
                ids.add(note.id)
                line = lines[note.id]
                require(line['event_id'] in source_events, 'Unknown source event')
                e = source_events[line['event_id']]
                require(not e['rest'] and e['event_id'] not in seen, 'Duplicate/rest note source')
                seen.add(e['event_id'])
                require(line['run_id'] == raw['run_id'] and line['round_id'] == e['round_id']
                        and part.id == e['voice'] and line['source_id'] == note.source_id
                        and line['muted'] == note.muted and line['transformation_id'] in transforms,
                        'Invalid note/source/transform lineage')
                require(note.source_id == source_ids[e['event_id']] and
                        line['transformation_id'] == f"{raw['run_id']}/arranged/{p['actual_backend']}/{policy}/{note.id}",
                        'Contradictory source/transform identity')
                require(note.end_tick <= 16 * raw['ppq'], 'Output outside four bars')
                p['events'].append(dict(event_id=line['transformation_id'], source_event_ids=[e['event_id']],
                    source_id=note.source_id, output_id=note.id, transformation_id=line['transformation_id'],
                    run_id=raw['run_id'], round_id=e['round_id'], round=e['round'], voice=e['voice'],
                    rest=note.muted, muted=note.muted, pitch_midi=None if note.muted else note.pitch,
                    velocity=note.velocity, onset_beats=note.onset_tick/raw['ppq'],
                    duration_beats=note.duration_ticks/raw['ppq']))
        require(parts == {'alice', 'bob'} and ids == set(lines), 'Incomplete output/lineage coverage')
        require(seen == {e['event_id'] for e in source_events.values() if not e['rest']}, 'Missing source notes')
        for e in source_events.values():
            if e['rest']:
                p['events'].append(dict(event_id=e['event_id']+'/arranged/rest', source_event_ids=[e['event_id']],
                    run_id=raw['run_id'], round_id=e['round_id'], round=e['round'], voice=e['voice'],
                    rest=True, muted=False, pitch_midi=None, velocity=e['velocity'],
                    onset_beats=e['onset_beats'], duration_beats=e['duration_beats']))
        p['events'].sort(key=lambda e: (e['voice'], e['round']))
        require(len(p['events']) == 32, 'Retain rests and muted events')
    return projection



def browser_bundle(raw_bytes, projection=None, *, raw_source_bytes=None):
    """Lossless UTF-8 export container, distinct from qm.run-result.v1."""
    raw = json.loads(raw_bytes)
    freeze_result(raw, raw_bytes=raw_source_bytes)
    if raw_source_bytes is not None:
        require(sha256(raw_source_bytes).hexdigest() == raw['raw_source']['sha256'],
                'Original raw source byte digest mismatch')
    return dict(raw_envelope_text=raw_bytes.decode('utf-8'), run_result=raw,
                raw_source_text=None if raw_source_bytes is None else raw_source_bytes.decode('utf-8'),
                playback_projection=projection)


def arrange_browser(raw_bytes, *, raw_source_bytes=None, backend="rules", model=None, provider=None):
    """Apply the selected arranger separately with identical harmonic constraints."""
    frozen = freeze_result(json.loads(raw_bytes), raw_bytes=raw_source_bytes)
    outcomes = {p: arrange_result(frozen, policy=p, backend=backend, model=model, provider=provider).to_dict()
                for p in ('quantum', 'classical')}
    return browser_bundle(raw_bytes, project(raw_bytes, outcomes, raw_source_bytes=raw_source_bytes),
                          raw_source_bytes=raw_source_bytes)


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--result', type=Path, required=True)
    p.add_argument('--raw-source', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--backend', choices=('rules', 'gemini'), default='rules')
    p.add_argument('--model')
    a = p.parse_args()
    if a.out.exists():
        p.error('Choose a fresh output filename')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    source = a.raw_source.read_bytes() if a.raw_source else None
    a.out.write_bytes(canonical_json(arrange_browser(a.result.read_bytes(), raw_source_bytes=source,
                                                     backend=a.backend, model=a.model)))

if __name__ == '__main__':
    main()
