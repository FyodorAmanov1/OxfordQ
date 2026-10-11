"""One deterministic arrangement: phrase planning, expressive timing, register and texture.

No RNG, statevector evaluation, sampling, model updates or backend calls occur here.
Costs below are declared classical preferences, not listening-quality predictors.
"""
from copy import deepcopy

from experiments.qcbm_composition.composition import compose, base_pitch

RHYTHMS = (
    (1, .75, .75, 1.5), (1, .5, 1, 1.5), (1, .75, 1.25, 1), (.75, .75, 1, 1.5),
    (1.25, .5, .75, 1.5), (1, .75, .75, 1.5), (1.5, .5, .5, 1.5), (.75, .5, 1.25, 1.5),
    (.5, .5, 1, 2), (.75, .25, 1, 2), (.5, 1, .5, 2), (.75, .75, .5, 2),
    (1, .75, .75, 1.5), (1, .5, 1, 1.5), (.75, .75, 1, 1.5), (.75, .5, .75, 2),
)
INTENSITY = (76, 78, 81, 75, 80, 84, 86, 79, 86, 89, 87, 82, 79, 78, 74, 70)
CADENCE_PCS = {3: 7, 7: 2, 11: 11, 15: 0}  # V root, V fifth, V third, I tonic
CHORDS = {
    'I': (0, 4, 7), 'Imaj7': (0, 4, 7, 11), 'ii': (2, 5, 9), 'ii7': (2, 5, 9, 0),
    'iii7': (4, 7, 11, 2), 'IV': (5, 9, 0), 'IVmaj7': (5, 9, 0, 4),
    'V': (7, 11, 2), 'V7': (7, 11, 2, 5), 'vi': (9, 0, 4), 'vi7': (9, 0, 4, 7),
}
OPTIONS = (
    ('I',), ('IV', 'IVmaj7', 'ii7'), ('I', 'vi', 'vi7'), ('V', 'V7'),
    ('I', 'Imaj7', 'vi7'), ('IV', 'IVmaj7', 'ii7'), ('ii', 'ii7', 'IV'), ('V7',),
    ('vi', 'vi7'), ('iii7', 'I', 'Imaj7'), ('IV', 'IVmaj7', 'ii7'), ('V7',),
    ('I',), ('IV', 'IVmaj7', 'ii7'), ('V7',), ('I',),
)
FUNCTION = {'I': 'tonic', 'Imaj7': 'tonic', 'vi': 'tonic', 'vi7': 'tonic',
            'iii7': 'tonic', 'IV': 'predominant', 'IVmaj7': 'predominant',
            'ii': 'predominant', 'ii7': 'predominant', 'V': 'dominant', 'V7': 'dominant'}


def decision(rule, source_ids, **values):
    return dict(rule='classical_' + rule, source_event_ids=list(source_ids), **values)


def melody(raw):
    """Retain PR #8's source schedule; re-plan register globally after four cadences."""
    original = compose(raw)
    events = deepcopy(original['events'])
    cadence_indices = {}
    for bar, pc in CADENCE_PCS.items():
        sounding = [i for i, e in enumerate(events) if e['bar'] == bar and not e['rest']]
        if sounding:
            cadence_indices[sounding[-1]] = pc
    for i, e in enumerate(events):
        e['reference_event_id'] = e['event_id']
        e['event_id'] = e['event_id'].replace('composition:', 'refinement:')
        e['reference'] = {key: e[key] for key in ('pitch', 'onset', 'duration', 'velocity')}
        e['reference_transformations'] = e.pop('transformations')
        e['transformations'] = []
        e['origin'] = 'classical_refinement_of_preserved_qcbm_source'
        slot = RHYTHMS[e['bar']][i % 4]
        e['onset'] = 4*e['bar'] + sum(RHYTHMS[e['bar']][:i % 4])
        e['slot_beats'] = slot
        gate = (.90, .78, .88, .84)[i % 4]
        if e['bar'] // 4 == 2 and i % 4 < 2:
            gate = .74  # lighter offbeats, not a new rest token
        if i in cadence_indices:
            gate = .98 if e['bar'] == 15 else .91
        e['duration'] = slot*gate
        e['velocity'] = INTENSITY[e['bar']] + (4, -4, 1, -2)[i % 4]
        if i in cadence_indices:
            e['velocity'] -= 5
        source = [e['source_event_id']]
        e['transformations'].extend([
            decision('rhythmic_phrasing', source, reference_onset=e['reference']['onset'],
                     onset=e['onset'], slot_beats=slot, section=e['section']),
            decision('articulation', source, reference_duration=e['reference']['duration'],
                     duration=e['duration'], gate_fraction=gate,
                     silence_after_beats=slot-e['duration']),
            decision('dynamic_arch', source, reference_velocity=e['reference']['velocity'],
                     velocity=e['velocity'], bar_intensity=INTENSITY[e['bar']]),
        ])
        if e['source_event_id'].split(':')[0] != e['assigned_motif']:
            e['transformations'].append(decision('theme_repetition_retained', source,
                assigned_motif=e['assigned_motif'], reference_event_id=e['reference_event_id']))

    # Dynamic programming over two octaves: timing, sampled pitch class and source
    # schedule are fixed. Only the four phrase-final sounding slots may change pc.
    sounding = [i for i, e in enumerate(events) if not e['rest']]
    previous_states = {67: (0., [])}
    for i in sounding:
        e = events[i]
        pc = cadence_indices.get(i, base_pitch(e['sampled_token']) % 12)
        choices = (60+pc, 72+pc)
        target = (67, 70, 74, 67)[e['bar']//4]
        states = {}
        for pitch in choices:
            candidates = []
            for previous, (cost, path) in previous_states.items():
                jump = abs(pitch-previous)
                movement = jump + .7*max(0, jump-5)**2 + 3*max(0, jump-12)**2
                candidates.append((cost+movement+.18*abs(pitch-target), path+[pitch]))
            states[pitch] = min(candidates, key=lambda pair: (pair[0], pair[1]))
        previous_states = states
    path = min(previous_states.values(), key=lambda pair: (pair[0], pair[1]))[1] if sounding else []
    for i, pitch in zip(sounding, path):
        e = events[i]
        e['pitch'] = pitch
        source = [e['source_event_id']]
        e['transformations'].append(decision('global_register_voice_leading', source,
            reference_pitch=e['reference']['pitch'], sampled_pitch=e['sampled_pitch'],
            pitch=pitch, octave_semitones=pitch-(60+pitch%12)))
        if i in cadence_indices:
            e['transformations'].append(decision('contextual_phrase_ending', source,
                sampled_pitch=e['sampled_pitch'], reference_pitch=e['reference']['pitch'],
                pitch=pitch, target_pitch_class=cadence_indices[i],
                harmonic_function='tonic' if e['bar'] == 15 else 'dominant',
                note='Only this already-sounding phrase-final event may change source pitch class'))
    return dict(events=events, unused_sampled_positions=original['unused_sampled_positions'],
                source_schedule=original['source_schedule'],
                cadence_event_ids=[events[i]['event_id'] for i in cadence_indices])


def voicings(name):
    pcs = CHORDS[name]
    result = []
    for inversion in range(len(pcs)):
        rotated = pcs[inversion:] + pcs[:inversion]
        for low in range(45, 58):
            if low % 12 != rotated[0]:
                continue
            notes = [low]
            for pc in rotated[1:]:
                notes.append(next(p for p in range(notes[-1]+1, notes[-1]+13) if p%12 == pc))
            if notes[-1] <= 67:
                result.append(dict(name=name, voicing=notes, inversion=inversion,
                                   bass_pitch=36+notes[0]%12))
    return result


def moving_voices(a, b):
    # Symmetric nearest-tone distance tolerates selected 3/4-tone chords; this is
    # a declared heuristic, not proof that particular voices are perceived.
    return .5*(sum(min(abs(p-q) for q in b) for p in a)/len(a)
               + sum(min(abs(q-p) for p in a) for q in b)/len(b))


def note_role(events, index):
    e = events[index]
    if index == 0 or index+1 == len(events) or e['rest']:
        return 'structural'
    before, after = events[index-1], events[index+1]
    if before['rest'] or after['rest'] or e['slot_beats'] > 1:
        return 'structural'
    a, b = e['pitch']-before['pitch'], after['pitch']-e['pitch']
    if abs(a) <= 2 and abs(b) <= 2 and a*b > 0:
        return 'passing'
    if abs(a) <= 2 and abs(b) <= 2 and before['pitch'] == after['pitch']:
        return 'neighbour'
    return 'structural'


def compatibility(events, bar, name):
    pcs = CHORDS[name]
    terms = []
    cost = 0.
    for i, e in enumerate(events):
        if e['bar'] != bar or e['rest']:
            continue
        role = note_role(events, i)
        accent = 1.65 if e['onset'] % 4 in (0, 2) else 1.
        weight = e['duration']*accent*(.45 if role == 'passing' else .65 if role == 'neighbour' else 1.)
        nonchord = e['pitch']%12 not in pcs
        semitone = nonchord and any((e['pitch']-pc)%12 in (1,11) for pc in pcs)
        penalty = weight*(4*nonchord + 2*semitone)
        cost += penalty
        terms.append(dict(source_event_id=e['source_event_id'], event_id=e['event_id'],
            role=role, accent_weight=accent, duration=e['duration'], chord_tone=not nonchord,
            semitone_risk=bool(semitone), cost=penalty))
    return cost, terms


def harmony_plan(events):
    """Whole-piece least-cost path constrained by phrase functions and V7–I return."""
    layers = []
    for bar, options in enumerate(OPTIONS):
        layer = []
        for name in options:
            fit, terms = compatibility(events, bar, name)
            for state in voicings(name):
                # Root bass frames tonic endpoints and phrase-final dominants;
                # inversions elsewhere are
                # selected jointly with chord and bass transitions, not per bar.
                if bar in (0,3,7,11,14,15) and state['inversion'] != 0:
                    continue
                layer.append(dict(**state, fit_cost=fit, melody_terms=terms,
                    local_cost=fit+state['inversion']+.1*abs(sum(state['voicing'])/len(state['voicing'])-54)))
        if not layer:
            raise ValueError(f'No valid chord voicing in bar {bar+1}')
        layers.append(layer)
    paths = [(s['local_cost'], [s]) for s in layers[0]]
    for layer in layers[1:]:
        following = []
        for state in layer:
            candidates = []
            for cost, path in paths:
                previous = path[-1]
                bass = abs(previous['bass_pitch']-state['bass_pitch'])
                motion = moving_voices(previous['voicing'], state['voicing'])
                weak = (FUNCTION[previous['name']] == 'predominant' and FUNCTION[state['name']] == 'tonic')
                transition = .8*bass+1.4*motion+2*max(0,bass-5)+3*weak
                candidates.append((cost+state['local_cost']+transition, path+[state]))
            following.append(min(candidates, key=lambda pair: (pair[0], [s['name'] for s in pair[1]], [s['voicing'] for s in pair[1]])))
        paths = following
    cost, plan = min(paths, key=lambda pair: (pair[0], [s['name'] for s in pair[1]], [s['voicing'] for s in pair[1]]))
    return plan, cost


def safe_intervals(start, end, pitch, pcs, lead):
    """Shorten/delay accompaniment, never the melody, around sustained nonchord clashes."""
    spans = [(start, end)]
    blocked = []
    for e in lead:
        if e['rest'] or e['pitch']%12 in pcs or e['duration'] < .85:
            continue
        if (e['pitch']-pitch)%12 not in (1,11):
            continue
        a, b = max(start,e['onset']), min(end,e['onset']+e['duration'])
        if b <= a:
            continue
        blocked.append(dict(source_event_id=e['source_event_id'],event_id=e['event_id'],onset=a,end=b))
        next_spans = []
        for lo, hi in spans:
            if b <= lo or a >= hi:
                next_spans.append((lo,hi))
            else:
                if lo < a:
                    next_spans.append((lo,a))
                if b < hi:
                    next_spans.append((b,hi))
        spans = next_spans
    return [(a,b) for a,b in spans if b-a >= .25], blocked


def accompany(events):
    plan, cost = harmony_plan(events)
    analysis, bass, chords = [], [], []
    for bar, state in enumerate(plan):
        lead = [e for e in events if e['bar'] == bar]
        source_ids = [e['source_event_id'] for e in lead]
        pcs = CHORDS[state['name']]
        chord_windows = [(0,3.92)] if bar == 15 else [(0,1.82),(2,1.70)]
        if bar//4 == 2:
            chord_windows = [(.5,1.25),(2.5,1.25)]  # restrained offbeat contrast
        avoidance = []
        for window, (offset, duration) in enumerate(chord_windows):
            for voice, pitch in enumerate(state['voicing']):
                spans, blocked = safe_intervals(4*bar+offset,4*bar+offset+duration,pitch,pcs,lead)
                if blocked:
                    avoidance.append(dict(pitch=pitch,window=window,blocked=blocked,retained_intervals=spans,
                        origin='classical_accompaniment_clash_avoidance',source_event_ids=source_ids))
                for fragment, (start, end) in enumerate(spans):
                    chords.append(dict(event_id=f'refinement:chord:b{bar:02}:w{window}:v{voice}:f{fragment}',
                        bar=bar,pitch=pitch,onset=start,duration=end-start,velocity=round(INTENSITY[bar]*.47)+(2 if window==0 else -2),
                        origin='classical_phrase_harmony',source_event_ids=source_ids,
                        transformations=[decision('harmonic_voicing_and_texture',source_ids,chord=state['name'],
                            inversion=state['inversion'],voicing=state['voicing'],window=[4*bar+offset,4*bar+offset+duration],
                            pitch=pitch,onset=start,duration=end-start),decision('accompaniment_clash_avoidance',source_ids,blocked=blocked)]))
        next_bass = plan[min(15,bar+1)]['bass_pitch']
        bass_pitches = [p for p in range(36,48) if p%12 in pcs and p!=state['bass_pitch']]
        second = min(bass_pitches,key=lambda p:(abs(p-next_bass)+.4*abs(p-state['bass_pitch']),p))
        bass_windows = [(0,3.92,state['bass_pitch'])] if bar==15 else [(0,1.7,state['bass_pitch']),(2.5 if bar//4==2 else 2,1.25 if bar//4==2 else 1.7,second)]
        for beat,(offset,duration,pitch) in enumerate(bass_windows):
            bass.append(dict(event_id=f'refinement:bass:b{bar:02}:n{beat}',bar=bar,pitch=pitch,
                onset=4*bar+offset,duration=duration,velocity=round(INTENSITY[bar]*.64)+(2 if beat==0 else -3),
                origin='classical_bass_voice_leading',source_event_ids=source_ids,
                transformations=[decision('bass_voice_leading',source_ids,chord=state['name'],
                    inversion=state['inversion'],next_bar_bass=next_bass,pitch=pitch,onset=4*bar+offset,duration=duration)]))
        previous = plan[bar-1] if bar else None
        notes = []
        for e in lead:
            if e['rest']:
                notes.append(dict(event_id=e['event_id'],source_event_id=e['source_event_id'],role='preserved_rest'))
                continue
            following = next((n for n in events if n['onset']>e['onset'] and not n['rest']),None)
            nonchord = e['pitch']%12 not in pcs
            resolution = nonchord and following is not None and abs(following['pitch']-e['pitch'])<=2 and following['pitch']%12 in CHORDS[plan[following['bar']]['name']]
            notes.append(dict(event_id=e['event_id'],source_event_id=e['source_event_id'],
                role='chord_tone' if not nonchord else 'nonchord_tension',
                stepwise_resolution=bool(resolution),resolution_event_id=following['event_id'] if resolution else None))
        analysis.append(dict(bar=bar,section=lead[0]['section'],chord=state['name'],pitch_classes=pcs,
            function=FUNCTION[state['name']],inversion=state['inversion'],voicing=state['voicing'],bass_pitch=state['bass_pitch'],
            candidates={name:compatibility(events,bar,name)[0] for name in OPTIONS[bar]},
            selected_melody_terms=state['melody_terms'],melody_fit_cost=state['fit_cost'],
            chord_motion_from_previous=moving_voices(previous['voicing'],state['voicing']) if previous else None,
            bass_motion_from_previous=abs(previous['bass_pitch']-state['bass_pitch']) if previous else None,
            melody_analysis=notes,accompaniment_avoidance=avoidance,
            origin='classical_phrase_aware_harmonic_plan',source_event_ids=source_ids))
    return dict(harmony=analysis,bass=bass,chords=chords,planning_cost=cost)


def refine(raw):
    developed = melody(raw)
    return dict(**developed,**accompany(developed['events']))
