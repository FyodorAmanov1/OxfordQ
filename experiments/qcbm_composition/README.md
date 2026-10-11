# Frozen QCBM composition: sixteen bars

This isolated experiment uses the existing trained 12-qubit/84-angle QCBM once
to compute its exact local statevector distribution. It draws sixteen four-token
motifs with replacement, using **NumPy PCG64 seed 20261011**, declared before the
draw. There is no training, backend submission, quality filtering or audition-based
selection. The entire sample is retained, including unused positions and rests.
The experiment does not import the CHSH execution pipeline or existing arranger.

Read [REPORT.md](REPORT.md) for actual results, verification and limitations.

## Run

From the repository root, use the existing verified `.venv-final` environment, or
create an isolated environment and install only this experiment's dependencies:

```powershell
python -m venv experiments/qcbm_composition/.venv
experiments/qcbm_composition/.venv/Scripts/python.exe -m pip install -r experiments/qcbm_composition/requirements.txt
experiments/qcbm_composition/.venv/Scripts/python.exe -m pip install --no-deps -e components/quantum_duet
experiments/qcbm_composition/.venv/Scripts/python.exe -m experiments.qcbm_composition
experiments/qcbm_composition/.venv/Scripts/python.exe -m experiments.qcbm_composition.verify
experiments/qcbm_composition/.venv/Scripts/python.exe -m pytest -q experiments/qcbm_composition/tests --basetemp experiments/qcbm_composition/artifacts/pytest
```

Optional comparisons use previously generated eight-qubit examples from draft
PR #7, commit `241e508405b8617323e275a3b110179473621b87`. Supply their existing
`artifacts/examples` directory without importing that experiment or retraining:

```powershell
.venv-final/Scripts/python.exe -m experiments.qcbm_composition --qnn-examples experiments/longform_qnn/artifacts/examples
.venv-final/Scripts/python.exe -m experiments.qcbm_composition.verify
```

Open `experiments/qcbm_composition/artifacts/listen.html` locally. It links melody,
arranged and straight-sample MIDI/WAV, the original recorded four-bar melody/duet,
available QNN comparisons, JSON traces and diagnostics. Missing QNN examples are
reported unavailable; no substitutes are generated. All audio uses the same
22050 Hz mono 16-bit additive three-harmonic audition synthesizer. It is a simple
listening renderer, not an acoustic instrument or a perceptual-quality measure.
The page requires no server, external assets, network access or dependencies.
Outputs and environments are ignored. Run with `--out PATH` to preserve an older
generation; by default a rerun replaces only experiment artifacts. Use `bin/python`
instead of `Scripts/python.exe` on POSIX.

## Exact sampling and source identity

Canonical checkpoint: `components/quantum_duet/src/quantum_duet/data/melody_angles.json`.
Its embedded original checkpoint identity is
`ecd7faaa232a15c261a5e3daf8047e0b4d71be9f4eb4bb597e70acb671c5b8a4`.
The unmodified `quantum_duet.circuit` constructs and binds the trained circuit.
`Statevector.from_instruction` yields all 4096 probabilities; division by their
sum corrects floating-point mass only. No amplitudes are clipped or reweighted.

Each displayed string is q11…q0. Token i is `(basis_index >> (3*i)) & 7`, so
the rightmost three bits are the first note. Token 0 is a rest; 1…7 map to
C4 D4 E4 F4 G4 A4 B4 in the straight reference. This standalone reference's
quarter-note timing is a classical convention, not the unchanged Quantum Duet map.

`raw-samples.json` stores all sixteen strings, integers, tokens, exact probabilities,
seed/RNG/runtime versions, byte and canonical checkpoint digests, circuit source
digest and normalized float64 distribution digest. The historical checkpoint
digest and current packaged-file digest are distinct, explicitly named identities.
`trace.json` references the raw file's exact bytes and canonical SHA-256. No raw
sample fields are changed during composition. Tests and the verifier repeat the
same seeded draw to establish identity; these are not searches for a nicer draw.

## Prespecified classical development

Four bars per section; four events per bar, including rests:

| Section | Source schedule | Rhythmic slots, beats |
|---|---|---|
| A | All four tokens of motifs 0…3 | 1, 1, 1, 1 |
| A′ | First two tokens repeat matching A bar; last two from motifs 4…7 | 1.5, .5, 1, 1 |
| B | All four tokens of motifs 8…11 | .5, .5, 1, 2 |
| A″ | First three repeat matching A bar; last token from motifs 12…15 | 1, .5, .5, 2 |

Every sampled motif contributes; 20 of the 64 original token positions are
replaced by the predetermined theme-repetition schedule. All 64 originals remain
in the sample JSON and straight-reference MIDI/WAV. Replaced positions are listed,
not discarded according to their musical content. A copied rest remains a rest;
the developed rest count can differ because the source schedule changes.

For sounding notes choose between the original C4–B4 mapping and its octave-up
version by minimizing `abs(p-previous) + .45*abs(p-section_target)`, with targets
65/72/69/65 and lower-pitch tie breaking. The initial previous pitch is 67.
This is a declared classical register rule, not a new learned QCBM dependency.
The first three notes of each bar sound for 90% of their slot; the fourth fills
its slot. Source rests remain silent throughout their slots.

At bars 4/8/12/16, the last already-sounding event is assigned pitch class
G/G/B/C, in its nearest available octave, and fills its slot. All-rest bars
stay silent; no following rest is overwritten. This imposes classical phrase
endings. It is not sampled cadence evidence, and previous pitch/duration are
recorded in the transformation trace. Every developed note records source event,
sampled token/pitch, final timing/pitch and all applied rules.

Harmony follows a declared functional candidate schedule in `composition.OPTIONS`:
I begins/ends the outer sections, V ends the first three phrases, vi starts B,
and the final two bars are V–I. Intermediate candidates maximize duration-weighted
melody pitch-class overlap, with declared order breaking ties. Bass plays root and
fifth on beats 1/3; chords sustain below the lead. The trace contains candidates,
scores and choices. Accompaniment never modifies the developed melody. This small
rule set does not call or fix the canonical arranger's known flat-chord inference.

## Interpretation and comparison

This is creative composition, **not 64 Bell rounds**, a new CHSH result, quantum
hardware evidence or a newly trained long-range model. Musical form is imposed
classically. Original raw envelopes, recorded counts, model weights, local music
mapping and Qollab sources are read-only and remain unchanged.

Comparisons retain original pitches/onsets/durations and use the same synthesizer.
Metrics compare melodies, while the original two-voice duet is separately playable.
The original is eight seconds; all new examples are 32 seconds. Notes per bar
normalizes density, but task/length differences and single fixed examples preclude
population-level quality claims. Mean jumps, duration variety, tonic ending and
literal bar agreement are diagnostics only. Modulo-seven diatonic interval
agreement additionally recognizes transposed themes; bars with no intervals in
either compared sequence are excluded. It does not measure listener recognition.

The page explicitly labels subjective listening assessment as pending human
audition and provides a rubric and notes area. Automated file verification proves
valid, non-silent audio, not aesthetic superiority. No auditory opinion is fabricated.

## Existing regression checks

```powershell
.venv-final/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests --basetemp .test-qcbm-composition
node components/quantum_duet/tests/ui_checks.mjs
node components/quantum_duet/tests/ui_c/contract_checks.mjs
node tests/duet_projection_checks.mjs .venv-final/Scripts/python.exe
.venv-final/Scripts/python.exe -m orchestrator --generation-manifest examples/generation.json --backend rules --bars 4 --no-audio --out experiments/qcbm_composition/artifacts/regression-cli/generation
.venv-final/Scripts/python.exe -m orchestrator --manifest examples/note_events.json --backend rules --bars 4 --no-audio --out experiments/qcbm_composition/artifacts/regression-cli/events
```
