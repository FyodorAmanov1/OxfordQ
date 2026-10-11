# Compact five-instrument composition — 2026-10-11

Implemented in an isolated worker worktree from main
`d8214741ba69167c90939347646c9371edc055cd`, branch
`codex/five-part-orchestration-20261011`. Only three new files are owned here:
the Python module, its focused tests, and this report. Existing UI, raw Quantum
Duet contract, CHSH calculation, models, checkpoints and deployment are unchanged.

## Contract and use

`quantum_duet.five_part_composition.compose(source)` accepts Agent C's
`qm.fresh-qcbm-source.v1` JSON string or mapping. Its output has
`schema_version: qm.five-part-composition.v1`; execution and model metadata are
copied exactly. Passing the original JSON string preserves its exact UTF-8 text
in `source_json_text` and SHA-256 in `source_json_sha256`. A separate canonical
SHA-256 is provided. All returned measured occurrences, duplicate bitstrings,
tokens, histogram and unused occurrence IDs remain in the immutable source.

Five tracks are Flute, Clarinet, Violin, Cello and Piano, with zero-based GM
programs 73, 71, 40, 42 and 0 and distinct channels 0–4. Events use quarter-note
beats, `pitch_midi`, `onset_beats`, `duration_beats`, `velocity`, `rest`,
`source_occurrence_id`, `source_token_index`, `source_event_ids`, and
`transformation_lineage`. Output event IDs retain the original run ID. A source
event is `<occurrence_id>/token/<0..3>`; each reused motif preserves all four
source slots, including rests. Piano chord tones share the source slot that
conditioned the explicitly classical accompaniment. Original rest slots never
become sounding notes. All-silent assignments remain silent and issue warnings;
the module does not resample them.

```python
from quantum_duet.five_part_composition import compose, midi_bytes
score = compose(original_source_json_text)
midi = midi_bytes(score)
```

The pure module imports only Python standard-library modules. No Qiskit, NumPy,
music21, desktop orchestrator, native audio, POP909, Gemini, provider or sampler
is imported. Composition/playback requires **zero additional backend jobs**.
The MIDI export is type 1, one conductor plus five instrument tracks, PPQ 480,
120 BPM and end-of-track at beat 64: exactly sixteen 4/4 bars / 32 seconds.
Browser synthesis remains the coordinator's separate integration dependency.

## Classical musical rules and attribution

This is an explicit compact extraction/adaptation, not the full desktop stack.
The following existing algorithms informed the implementation:

- `orchestrator/composition/planner.py: local_plan` and `_steps`: recognizable
  theme introduction, development and return; four-token rhythmic patterns.
- `orchestrator/composition/compiler.py: _place`: octave candidates scored by
  register distance plus 0.25 times distance from the previous pitch.
- `orchestrator/composition/performer.py: _arc` / `RulePerformer`: phrase-shaped
  dynamics and shorter phrase-ending gates. Fixed tempo is retained here to
  guarantee 32 seconds; desktop timing jitter and rubato are omitted.
- `quantum_models/qcbm_instrument.py`: explicit classical C-major decoding and
  different instrument registers from one shared frozen checkpoint.
- `orchestrator/instruments.py`: conservative concert-pitch ranges. The compact
  Cello uses the specific GM cello program 42 and Violin uses solo Violin 40
  rather than the existing generic string-section program 48; existing profiles
  are not modified.

Four measured motif assignments per instrument are selected by C without
favorable-result selection. The deterministic classical bar-index sequences
are `[0,1,0,2] / [0,1,0,3] / [2,3,2,1] / [0,1,2,0]`, forming A–A′–B–A″.
All four assigned motifs are used. Rhythm, register, gates, phrase dynamics,
theme repeats and final tonic cadence are classical and labelled accordingly.
Cello and Piano use explicit classical harmonic projection onto
`C F G C / C F G C / Am Dm G G / C F G C`; Piano adds triad voicing. These pitches
are **not claimed as original model output**. This deliberately supplied harmony
does not call or silently correct the existing arranger's flat-chord inference.
Source tokens remain separately inspectable. No CHSH statistics describe this
composition, and no musical-quality or quantum-advantage claim is made.

The historical `experiments/qcbm_composition` and `qcbm_refinement` directories
are absent from this latest-main base; no missing comparison or old optional
experiment is a runtime dependency.

## Actual new verification

Executed locally between approximately 22:28 and 22:32 UTC on 2026-10-11,
Python 3.12.14, using the existing `.venv-final` environment:

```powershell
$env:PYTHONPATH=(Join-Path $PWD 'components/quantum_duet/src')+';'+$PWD
& 'C:\Users\flori\source\OxfordQ-quantum-duet\.venv-final\Scripts\python.exe' -m pytest -q tests/test_five_part_composition.py --basetemp build/test-five-part-final
```

**12 focused tests passed in 0.20 s**, covering deterministic reproduction,
exact original source text/SHA, unchanged source and actual execution metadata,
all 32 shots and twelve unused occurrences, all twenty assignments, all rests,
thematic return, distinct classical harmony, registers, source-event lineage,
corruption rejection, and an entirely silent source without replacement.
Independent Mido decoding checked five programs/channels, note count/onsets/
velocities, balanced note on/off edges, no overlapping unisons and 32-second MIDI.

Agent C's actual **LOCAL BasicSimulator** 32-shot source was composed successfully
without any new job. Original JSON text SHA-256:
`7ed2c1d0d45780d0501873115b01174681c91c0787e9a4fe6bc634a30b335505`.
The generated local test MIDI has six tracks and independently decoded length
32.0 seconds. Sounding event counts: Flute 56, Clarinet 64, Violin 64, Cello 62,
Piano 192. Flute retains eight rest events and Cello two; the other particular
assigned sources contained none. These counts are composition occurrences,
not additional quantum shots. Generated score/MIDI reside in the ignored worker
`build/five-part-local.json` / `build/five-part-local.mid`.

Full latest-main regression command:

```powershell
& 'C:\Users\flori\source\OxfordQ-quantum-duet\.venv-final\Scripts\python.exe' -m pytest -q tests components/quantum_duet/tests --basetemp build/regression-five-part
```

**226 passed, 28 failed in 33.41 s.** All failures are existing
`tests/test_composition.py` desktop-orchestrator cases, predominantly because the
current default ensemble includes Piano but the older fixture source bank lacks
a Piano motif; `local_plan` raises `No source motif for piano`. One error-string
test expects `No sounding source motif` while existing code says `No source motif`.
No existing implementation or tests were edited here, and none of these failing
cases imports the new module. This is an explicit current-main integration
blocker, not a claim that the new full-regression run passed. The coordinator
must verify its chosen integration base separately; the worker does not fix
unrelated desktop code under deadline pressure.

`git diff --check` passed. This worker performed no browser, Qollab or IonQ
execution and makes no remote claim. Actual private platform generation,
browser sound, seeking and export verification remain coordinator dependencies.
Human musical listening assessment remains pending. Nothing is published,
merged or pushed to main by this worker.
