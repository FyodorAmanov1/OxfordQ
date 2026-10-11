"""Observable diagnostics, explicitly not a perceptual or scientific quality score."""
from collections import Counter
import numpy as np
from .refine import moving_voices


def measure(events, bass, chords, harmony):
    sounding = [e for e in events if not e['rest']]
    pitches = [e['pitch'] for e in sounding]
    intervals = np.diff(pitches)
    patterns = [tuple(round(e['slot_beats'],6) for e in events if e['bar']==bar) for bar in range(16)]
    velocities = [e['velocity'] for e in sounding]
    gates = [e['duration']/e['slot_beats'] for e in sounding]
    chord_weight = total_weight = 0.
    tension_count = resolved = 0
    sustained_clash_beats = 0.
    for index, e in enumerate(sounding):
        pcs = harmony[e['bar']]['pitch_classes']
        accent = 1.65 if e['onset']%4 in (0,2) else 1.
        weight = e['duration']*accent
        total_weight += weight
        if e['pitch']%12 in pcs:
            chord_weight += weight
        else:
            tension_count += 1
            if index+1 < len(sounding):
                n = sounding[index+1]
                resolved += int(abs(n['pitch']-e['pitch'])<=2 and n['pitch']%12 in harmony[n['bar']]['pitch_classes'])
            if e['duration'] >= .85:
                for c in chords:
                    if c['bar']!=e['bar'] or (e['pitch']-c['pitch'])%12 not in (1,11):
                        continue
                    sustained_clash_beats += max(0,min(e['onset']+e['duration'],c['onset']+c['duration'])-max(e['onset'],c['onset']))
    bass_pitches = [e['pitch'] for e in sorted(bass,key=lambda e:e['onset'])]
    bass_jumps = np.abs(np.diff(bass_pitches))
    voicings = [h.get('voicing') or [48+pc for pc in h['pitch_classes']] for h in harmony]
    transitions = [moving_voices(a,b) for a,b in zip(voicings,voicings[1:])]
    boundaries = []
    for bar in (3,7,11,15):
        phrase_last = [e for e in sounding if e['bar']==bar][-1]
        next_phrase = next((e for e in sounding if e['bar']>bar),None)
        boundaries.append(dict(bar=bar,pitch=phrase_last['pitch'],chord=harmony[bar]['chord'],
            following_jump=abs(next_phrase['pitch']-phrase_last['pitch']) if next_phrase else None,
            breath_beats=4*(bar+1)-(phrase_last['onset']+phrase_last['duration'])))
    agreement = []
    for offset in (4,12):
        for bar in range(4):
            a = [e for e in events if e['bar']==bar]
            b = [e for e in events if e['bar']==bar+offset]
            agreement.extend((x['pitch'] is None and y['pitch'] is None) or
                (x['pitch'] is not None and y['pitch'] is not None and x['pitch']%12==y['pitch']%12)
                for x,y in zip(a,b))
    return dict(sounding_notes=len(sounding),rest_events=len(events)-len(sounding),
        mean_abs_melody_interval=float(np.abs(intervals).mean()),
        interval_histogram={str(int(k)):v for k,v in sorted(Counter(intervals).items())},
        melody_leaps_over_octave=int(sum(abs(i)>12 for i in intervals)),
        rhythm_patterns=len(set(patterns)),distinct_note_lengths=len({round(e['duration'],6) for e in sounding}),
        velocity_range=[min(velocities),max(velocities)],distinct_velocities=len(set(velocities)),
        gate_fraction_range=[min(gates),max(gates)],
        accented_duration_chord_tone_fraction=chord_weight/total_weight,
        nonchord_events=tension_count,stepwise_resolved_nonchord_events=resolved,
        sustained_nonchord_semitone_overlap_note_beats=sustained_clash_beats,
        mean_abs_bass_interval=float(bass_jumps.mean()),maximum_bass_jump=int(bass_jumps.max()),
        mean_chord_nearest_voice_motion=float(np.mean(transitions)),
        A_reprise_pitch_class_agreement=float(np.mean(agreement)),
        preserved_source_repetitions=sum(e['source_event_id'].split(':')[0]!=e['assigned_motif'] for e in events),
        phrase_boundaries=boundaries,final_cadence=[harmony[-2]['chord'],harmony[-1]['chord']],
        final_pitch=boundaries[-1]['pitch'])


def compare(original, improved):
    return dict(original=measure(**original),improved=measure(**improved),
        limitations=[
            'One fixed piece, no listening-quality ranking or quantum musical-quality claim',
            'Chord membership and semitone overlap are limited tonal proxies, not an auditory clash detector',
            'Sevenths count as chord tones here; expanded vocabularies affect compatibility diagnostics',
            'Voice motion is symmetric nearest-tone distance, not perceptual voice tracking',
            'Literal pitch-class agreement measures repeated slots, not human motif recognition',
            'All measured changes are classical arrangement decisions'],
        subjective_listening=dict(status='Pending user assessment',winner=None,ratings=None))
