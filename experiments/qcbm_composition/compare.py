"""Observable melody metrics and faithful local comparison renders; no quality ranking."""
import json
from pathlib import Path
import numpy as np
from .composition import ROOT, digest
from .render import export


def metrics(events, beats):
    sounding = [e for e in events if e['pitch'] is not None]
    pitches = [e['pitch'] for e in sounding]
    intervals = np.abs(np.diff(pitches))
    patterns = []
    for bar in range(round(beats / 4)):
        patterns.append(tuple(None if e['pitch'] is None else e['pitch'] % 12
                              for e in events if int(e['onset'] // 4) == bar))
    same_a = None
    interval_agreement = None
    if len(patterns) == 16:
        same_a = float(np.mean([sum(a == b for a, b in zip(patterns[i], patterns[j])) /
                                   max(1, len(patterns[i]), len(patterns[j]))
                               for i, j in [(i, i + offset) for offset in (4, 12) for i in range(4)]]))
        scale = (0, 2, 4, 5, 7, 9, 11)
        def contour(pattern):
            return tuple(None if a is None or b is None else (scale.index(b)-scale.index(a)) % 7
                         for a, b in zip(pattern, pattern[1:]))
        contours = [contour(pattern) for pattern in patterns]
        pairs = [(i, i+offset) for offset in (4, 12) for i in range(4)
                 if max(len(contours[i]), len(contours[i+offset])) > 0]
        interval_agreement = float(np.mean([sum(a == b for a, b in zip(contours[i], contours[j])) /
                                          max(len(contours[i]), len(contours[j])) for i, j in pairs])) if pairs else None
    return dict(bars=beats / 4, seconds=beats * .5, events=len(events), sounding_notes=len(sounding),
                rest_events=len(events) - len(sounding), distinct_pitches=len(set(pitches)),
                distinct_durations=len({round(e['duration'], 6) for e in events}),
                notes_per_bar=len(sounding) / (beats / 4),
                mean_abs_semitone_interval=float(intervals.mean()) if len(intervals) else 0,
                stepwise_fraction=float(np.mean(intervals <= 2)) if len(intervals) else None,
                leaps_over_octave=int(np.sum(intervals > 12)),
                repeated_bar_pitch_class_fraction=1 - len(set(patterns)) / len(patterns),
                A_to_A_prime_and_double_prime_pitch_class_agreement=same_a,
                A_to_A_prime_and_double_prime_diatonic_interval_agreement=interval_agreement,
                last_pitch=pitches[-1] if pitches else None,
                final_tonic=bool(pitches and pitches[-1] % 12 == 0))


def comparisons(out, developed, raw, qnn_root=None):
    rows = [dict(name='QCBM developed melody', **metrics(developed, 64)),
            dict(name='Same 16 draws, straight quarter notes', **metrics(raw, 64))]
    sources = []
    fixture = ROOT / 'components/quantum_duet/tests/fixtures/qollab-local-run.json'
    fixture_bytes = fixture.read_bytes()
    take = json.loads(fixture_bytes)
    def event(e):
        return dict(pitch=e['pitch_midi'], onset=e['onset_beats'], duration=e['duration_beats'], velocity=e.get('velocity', 80))
    alice = [event(e) for e in take['events']['quantum'] if e['voice'] == 'alice']
    bob = [event(e) for e in take['events']['quantum'] if e['voice'] == 'bob']
    export(out, 'original-four-bar-melody', [('RECORDED original Alice', alice)], 16)
    export(out, 'original-four-bar-duet', [('RECORDED original Alice', alice), ('RECORDED original Bob', bob)], 16)
    rows.append(dict(name='Original four-bar RECORDED Alice melody', **metrics(alice, 16)))
    sources.append(dict(kind='original_fixture', path=fixture.relative_to(ROOT).as_posix(),
                        sha256=digest(fixture_bytes), original_statistics=take['statistics'],
                        original_execution=take['execution'], comparison_backend_jobs=0,
                        note='Exact recorded event pitches/onsets/durations; current common synth, not original browser audio'))
    availability = {}
    for name in ('free', 'structured'):
        path = Path(qnn_root) / name / 'generation.json' if qnn_root else None
        if path is None or not path.exists():
            availability[name] = 'unavailable: provide --qnn-examples from draft PR #7; no substitute'
            continue
        contents = path.read_bytes()
        trace = json.loads(contents)
        scale = (0, 2, 4, 5, 7, 9, 11)
        events = []
        for record in trace['events']:
            e = record['event']; p = e['pitch']
            events.append(dict(pitch=None if p == 0 else 60 + scale[(p-1) % 7] + 12 * ((p-1) // 7),
                               onset=e['onset'] / 2, duration=e['units'] / 2, velocity=84))
        if trace.get('model_version') != 'longform-qnn-v1' or trace['duration_beats'] != 64:
            raise ValueError('Unexpected 8-qubit comparison trace')
        export(out, f'qnn-{name}-melody', [('Previously generated 8-qubit QNN; see original trace', events)])
        rows.append(dict(name=f'8-qubit QNN {name} melody', **metrics(events, 64)))
        sources.append(dict(kind=f'qnn_{name}', trace_sha256=digest(contents),
                            checkpoint_sha256=trace['checkpoint_sha256'], seed=trace['seed'],
                            source_branch_commit='241e508405b8617323e275a3b110179473621b87',
                            note='Existing local example re-rendered, not retrained or resampled; structured form has classical A-prime/A-double-prime'))
        availability[name] = 'included, faithfully re-rendered with common synth'
    return dict(metrics=rows, sources=sources, qnn_availability=availability,
                limitations=['One prespecified sample per method; no statistical quality conclusion',
                             'Original has four bars; other examples have sixteen; notes-per-bar normalizes length but does not remove task differences',
                             'Metrics compare melody only; original duet is supplied separately for listening',
                             'Literal pitch-class agreement penalizes transposition; modulo-seven diatonic interval agreement also reports transposed theme retention, not human motif recognition',
                             'Register/rhythm/form/cadence improvements in developed QCBM are classical, not newly learned',
                             'No model training data or held-out motifs inspected'],
                subjective_listening=dict(status='Awaiting human audition', ratings=None,
                    assessment='No audible listening judgement is claimed by the coding agent. Use the common-synth players and rate motif clarity, rhythm, contour, phrasing and ending. Metrics alone cannot establish that this sounds better.'))
