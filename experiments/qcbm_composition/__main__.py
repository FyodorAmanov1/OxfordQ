"""Generate the prespecified composition, comparison files and local listening page."""
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import time

from .composition import ROOT, SEED, sample_motifs, raw_events, compose, harmonize, canonical, digest
from .render import export
from .compare import comparisons


def listening_page(out, comparison):
    items = [('melody', 'Developed QCBM melody — 16 bars'),
             ('arranged', 'Developed QCBM + classical bass/chords — 16 bars'),
             ('sampled-reference', 'Same 16 sampled motifs, straight quarter notes — 16 bars'),
             ('original-four-bar-melody', 'Original RECORDED Alice melody — four bars / 8 seconds'),
             ('original-four-bar-duet', 'Original RECORDED duet — four bars / 8 seconds')]
    items += [(f'qnn-{name}-melody', f'Prior 8-qubit QNN {name} melody — 16 bars')
              for name, status in comparison['qnn_availability'].items() if status.startswith('included')]
    players = ''.join(f'<section><h2>{html.escape(label)}</h2><audio controls preload="metadata" src="{name}.wav"></audio> <a href="{name}.mid">MIDI</a></section>' for name, label in items)
    columns = ('name', 'bars', 'distinct_pitches', 'distinct_durations', 'mean_abs_semitone_interval', 'stepwise_fraction', 'final_tonic')
    table = '<table><tr>' + ''.join(f'<th>{c.replace("_", " ")}</th>' for c in columns) + '</tr>'
    for row in comparison['metrics']:
        table += '<tr>' + ''.join(f'<td>{html.escape(str(round(row[c], 3) if isinstance(row[c], float) else row[c]))}</td>' for c in columns) + '</tr>'
    table += '</table>'
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>OxfordQ — frozen QCBM composition</title>
<style>body{font:17px system-ui;max-width:1100px;margin:36px auto;padding:0 20px;background:#f7f5ef;color:#26362f}h1{font-size:32px}section{background:white;padding:12px 20px;margin:14px 0;border-radius:8px}h2{font-size:19px}audio{width:80%}table{border-collapse:collapse;font-size:14px}td,th{padding:8px;border:1px solid #b9bfb7}textarea{width:96%;height:90px}p{line-height:1.5}</style>
<h1>A seed, sixteen motifs, one classical composition</h1>
<p>Frozen 12-qubit QCBM · seed 20261011 · exact offline statevector · zero backend jobs · no training or sample filtering.</p>
<p><strong>A–A′–B–A″</strong>, 16 bars, 120 BPM, 32 seconds. QCBM supplies motif tokens. Repetition, rhythm, octave placement, phrase endings and accompaniment are explicitly classical. This is not a Bell experiment or new raw Quantum Duet evidence.</p>
<p>All comparison melodies use the same additive synthesizer. Original four-bar events retain their exact timing; longer does not automatically mean better. Use melody-only versions to compare generators; compare arranged versions separately.</p>'''
    page += players + '<h2>Observable melody diagnostics</h2>' + table
    page += '''<h2>Subjective listening assessment — human audition pending</h2><p>No claim that this sounds better has been made from metrics alone. Listen once to each melody, then compare motif recognizability, rhythmic interest, smooth contour, phrase boundaries and ending. Rate each 1–5 and note tradeoffs. This is an unblinded informal assessment, not scientific evidence.</p><textarea aria-label="Your subjective listening notes" placeholder="Example: QCBM developed — motifs / rhythm / contour / phrasing / ending: …; compared with original and QNN: …"></textarea><p>Notes remain in this page only; copy them before closing. No data is sent.</p><p><a href="trace.json">Composition provenance</a> · <a href="raw-samples.json">All original samples</a> · <a href="comparison.json">Comparison and original evidence references</a></p></html>'''
    (out / 'listen.html').write_text(page, encoding='utf-8')


def run(out, qnn_examples=None):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    raw = sample_motifs()
    raw_bytes = canonical(raw)
    (out / 'raw-samples.json').write_bytes(raw_bytes)
    developed = compose(raw)
    harmony, bass, chords = harmonize(developed['events'])
    raw_notes = raw_events(raw)
    audio = dict(melody=export(out, 'melody', [('Classically developed QCBM melody', developed['events'])]),
                 arranged=export(out, 'arranged', [('Classically developed QCBM melody', developed['events']), ('Classical bass', bass), ('Classical chords', chords)]),
                 sampled_reference=export(out, 'sampled-reference', [('Unmodified sampled pitch mapping, classical quarter-note timing', raw_notes)]))
    comparison = comparisons(out, developed['events'], raw_notes, qnn_examples)
    (out / 'comparison.json').write_bytes(canonical(comparison))
    trace = dict(schema='oxfordq.qcbm-composition.v1', created_utc=datetime.now(timezone.utc).isoformat(),
                 experiment_version='qcbm-composition-v1', tempo_bpm=120, metre='4/4', bars=16,
                 beats=64, seconds=32, backend_jobs=0, training_steps=0,
                 raw_samples_file='raw-samples.json', raw_samples_sha256=digest(raw_bytes),
                 raw_samples_canonical_sha256=digest(canonical(raw)),
                 source_checkpoint_sha256=raw['original_checkpoint_sha256'],
                 scope='Creative classical development of frozen-QCBM samples; no CHSH rounds or statistics calculated',
                 **developed, harmony=harmony, bass=bass, chords=chords, audio=audio)
    if canonical(raw) != raw_bytes:
        raise AssertionError('Raw sample evidence mutated')
    (out / 'trace.json').write_bytes(canonical(trace))
    listening_page(out, comparison)
    result = dict(elapsed_seconds=time.perf_counter()-start, sample_seed=SEED,
                  sampled_bitstrings=[m['bitstring'] for m in raw['motifs']],
                  comparison=comparison['metrics'], raw_samples_sha256=digest(raw_bytes))
    print(json.dumps(result, indent=2))
    return trace


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path(__file__).parent / 'artifacts')
    parser.add_argument('--qnn-examples', type=Path, help='Existing PR #7 artifacts/examples; read-only, no retraining')
    args = parser.parse_args()
    run(args.out, args.qnn_examples)
