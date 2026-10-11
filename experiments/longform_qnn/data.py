"""Metadata-first grouped split; held-out test scores are never opened."""
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import numpy as np
from .encoding import Event, SCALE, teacher_examples

def canonical(text):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode().lower())

def source_groups(rows):
    """Union same BWV work OR same hymn title, conservatively including variants."""
    parents = list(range(len(rows)))
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]; i = parents[i]
        return i
    seen = {}
    for i, row in enumerate(rows):
        for key in ('bwv:'+row['bwv'].split('.')[0], 'title:'+canonical(row['title'])):
            if key in seen:
                parents[root(i)] = root(seen[key])
            seen[key] = i
    groups = {}
    for i, row in enumerate(rows):
        groups.setdefault(root(i), []).append(row)
    result = []
    for group in groups.values():
        identity = '|'.join(sorted({r['source'] for r in group}))
        gid = hashlib.sha256(identity.encode()).hexdigest()[:16]
        bucket = int(hashlib.sha256(('longform-v1:'+gid).encode()).hexdigest()[:8], 16) / 2**32
        split = 'train' if bucket < .70 else 'validation' if bucket < .85 else 'test'
        result.extend([dict(r, group=gid, split=split) for r in group])
    return sorted(result, key=lambda r:r['riemenschneider'])

def metadata():
    from music21 import corpus
    rows = []
    for number, info in sorted(corpus.chorales.ChoraleListRKBWV().byRiemenschneider.items()):
        source = next(iter(corpus.chorales.Iterator(numberList=[number], returnType='filename')))
        rows.append(dict(source=source, bwv=str(info['bwv']), title=info['title'], riemenschneider=number))
    return source_groups(rows)

class Reject(ValueError):
    pass

def half_units(value):
    units = round(float(value)*2)
    if abs(float(value)*2-units) > 1e-6:
        raise Reject('unsupported_sub_half_beat_or_tuplet')
    return units

def preprocess(score):
    from music21 import meter
    if not score.parts:
        raise Reject('no_parts')
    part = score.parts[0]
    key = score.analyze('key')
    if key.mode != 'major':
        raise Reject('non_major_key')
    signatures = list(part.recurse().getElementsByClass(meter.TimeSignature))
    if not signatures or any(ts.ratioString not in ('4/4', '2/2') for ts in signatures):
        raise Reject('unsupported_metre')
    measures = list(part.getElementsByClass('Measure'))
    complete = [m for m in measures if abs(float(m.duration.quarterLength)-4)<1e-6 and not m.paddingLeft]
    if not complete:
        raise Reject('no_complete_bar')
    start, end = float(complete[0].offset), float(complete[-1].offset)+4
    if end-start < 16:
        raise Reject('fewer_than_four_complete_bars')
    notes = list(part.stripTies(inPlace=False).flatten().notesAndRests)
    spans = []
    for note in notes:
        onset, duration = float(note.offset), float(note.duration.quarterLength)
        if onset+duration <= start or onset >= end:
            continue
        if duration <= 0 or note.isChord:
            raise Reject('grace_or_polyphonic_soprano')
        lo, hi = max(start, onset), min(end, onset+duration)
        a, b = half_units(lo-start), half_units(hi-start)
        midi = None if note.isRest else int(note.pitch.midi)-int(key.tonic.pitchClass)
        if midi is not None and midi % 12 not in SCALE:
            raise Reject('chromatic_pitch_after_major_normalization')
        spans.append((a, b, midi, bool(note.expressions)))
    sounding = [p for _,_,p,_ in spans if p is not None]
    if not sounding:
        raise Reject('silent_source')
    shifts = [v for v in (0, -12, 12, -24, 24) if min(sounding)+v >= 60 and max(sounding)+v <= 83]
    if not shifts:
        raise Reject('exceeds_two_octave_vocabulary')
    shift = shifts[0]
    events, cursor, split_notes, phrase_ends = [], 0, 0, []
    for a,b,midi,expression in spans:
        if a != cursor or b <= a:
            raise Reject('gap_overlap_or_zero_quantized_duration')
        pitch = 0 if midi is None else 1+SCALE.index((midi+shift)%12)+7*((midi+shift-60)//12)
        continuation = False
        while a < b:
            units = min(b-a, 8-a%8)
            events.append(Event(pitch, units, a, continuation))
            a += units
            if a < b:
                split_notes += 1; continuation = True
        cursor=b
        if expression:
            phrase_ends.append(b)
    if cursor != half_units(end-start) or cursor%8:
        raise Reject('incomplete_final_bar')
    return events, dict(original_key=str(key), transpose_semitones=-int(key.tonic.pitchClass)+shift,
        retained_beats=end-start, trimmed_prefix_beats=start,
        trimmed_suffix_beats=max(0,float(part.highestTime)-end),
        split_at_barlines=split_notes, expression_phrase_end_units=phrase_ends,
        tie_policy='Merge notated ties, then split sustained notes at barlines with continuation provenance; model has no tie token')

def prepare(out, exclusions=None):
    from music21 import corpus
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    rows = metadata()
    # Optional metadata-only prior source exclusions, never motif content.
    old = set(json.loads(Path(exclusions).read_text())) if exclusions else set()
    excluded_groups = {r['group'] for r in rows if r['source'] in old or r['bwv'] in old}
    (out/'source_split.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    retained, rejected, seen_sources = [], [], set()
    for row in rows:
        if row['split']=='test' or row['group'] in excluded_groups:
            continue  # critical: do not parse these scores
        if row['source'] in seen_sources:
            rejected.append(dict(source=row['source'], reason='duplicate_edition_same_source'))
            continue
        seen_sources.add(row['source'])
        try:
            score = corpus.parse(row['source'], forceSource=True)
            events, transforms = preprocess(score)
            retained.append(dict(row, events=[asdict(e) for e in events], transforms=transforms))
        except Reject as error:
            rejected.append(dict(source=row['source'], reason=str(error)))
        except Exception as error:
            # Parsing errors are reported, never filled with synthetic music.
            rejected.append(dict(source=row['source'], reason='parse_error:'+type(error).__name__+':'+str(error)))
    # Exact normalized melody duplicates across train/validation are unioned to a
    # single split by dropping the validation duplicate, with explicit provenance.
    fingerprints = {tuple((e['pitch'],e['units']) for e in p['events']):p['source'] for p in retained if p['split']=='train'}
    clean = []
    for piece in retained:
        sig = tuple((e['pitch'],e['units']) for e in piece['events'])
        if piece['split']=='validation' and sig in fingerprints:
            rejected.append(dict(source=piece['source'],reason='normalized_duplicate_of_training:'+fingerprints[sig]))
        else:
            clean.append(piece)
    for split in ('train','validation'):
        (out/f'{split}.json').write_text(json.dumps([p for p in clean if p['split']==split]),encoding='utf-8')
    events = [e for p in clean for e in p['events']]
    report = dict(corpus='music21 9.9.2 Bach chorale soprano; J. S. Bach; metadata Riemenschneider/BWV',
        corpus_distribution='Local use only; no score encodings or corpus event files committed',
        prior_test_exclusions='Supplied metadata honored' if exclusions else 'No prior source-level split metadata in repository; separate experiment, no cross-dataset test comparison',
        total_metadata_entries=len(rows), unique_metadata_sources=len({r['source'] for r in rows}),
        source_split_sizes={s:len({r['source'] for r in rows if r['split']==s}) for s in ('train','validation','test')},
        group_split_sizes={s:len({r['group'] for r in rows if r['split']==s}) for s in ('train','validation','test')},
        test_scores_opened=0, retained_pieces=len(clean), retained_events=len(events),
        retained_by_split={s:dict(pieces=sum(p['split']==s for p in clean),events=sum(len(p['events']) for p in clean if p['split']==s)) for s in ('train','validation')},
        duration_units_distribution=dict(Counter(e['units'] for e in events)),pitch_distribution=dict(Counter(e['pitch'] for e in events)),
        rejection_counts=dict(Counter(r['reason'].split(':')[0] for r in rejected)),rejected=rejected,
        transformations=[dict(source=p['source'],**p['transforms']) for p in clean],
        duplicate_safeguards='Union same BWV work or normalized hymn title BEFORE score access; deduplicate source editions; remove exact normalized validation/training duplicates',
        limitations=['Unknown cross-title near duplicates may remain; test scores remain unopened',
                    'Only fully representable major 4/4 or 2/2 pieces retained; strong selection bias',
                    'Whole contiguous complete-bar passages retained; pickups/end partial bars explicitly trimmed',
                    'No forced cadence or note repair; expression boundaries are metadata, not phrase labels learned by the model'])
    (out/'dataset_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('rejected','transformations')},indent=2),flush=True)
    if not all(report['retained_by_split'][s]['pieces'] >= 2 for s in ('train','validation')):
        raise RuntimeError('Insufficient source-isolated data; inspect rejection report')
    return report

def load_examples(directory, split):
    if split not in ('train','validation'):
        raise ValueError('Test score access is intentionally disabled during development')
    pieces=json.loads((Path(directory)/f'{split}.json').read_text())
    arrays=[teacher_examples([Event(**e) for e in p['events']]) for p in pieces]
    return tuple(np.concatenate([a[i] for a in arrays]) for i in range(3)), pieces
