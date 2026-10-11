# Completion: frozen-QCBM sixteen-bar composition

Executed 2026-10-11 from main `c49c2e6cace0790211ae6808f4ecdc4cb77faa01`,
on `codex/qcbm-composition-20261011`. Implementation, documentation and tests
are confined to `experiments/qcbm_composition/`. No existing source, weight,
scientific contract, canonical deployment or original experiment was modified.

## Listening-ready result

The piece is **A–A′–B–A″, 16 bars, 4/4, 120 BPM, exactly 32 seconds**.
The frozen 12-qubit QCBM supplied sixteen four-token motifs using PCG64 seed
**20261011**, declared before the first draw. All sixteen original bitstrings,
tokens and probabilities are saved. There was no search over seeds, sample
rejection, training, backend submission, paid API or hardware execution.
Repeat executions were identity tests using the same sample, not new auditions.

Classical development creates 62 sounding notes and two rest events, using eleven
pitches and five sounding durations. It applies twenty theme repetitions,
31 octave placements, 64 timing/gate assignments and four explicit phrase endings.
All sixteen motifs contribute. Twenty original positions are replaced by the
prespecified repetition schedule; all 64 originals remain in the straight-reference
MIDI/WAV and sample file. No event is silently called raw quantum evidence.

The deterministic accompaniment selected this progression:
`I IV I V | I IV ii V | vi I IV V | I IV V I`.
Bass uses root/fifth pulses and chords sustain below the melody. The complete
melody track is unchanged between melody-only and arranged exports. The final
C5 is an imposed classical cadence, not evidence of a learned ending.

Open [the local listening page](artifacts/listen.html), or individual files:

| Output | Audio | MIDI |
|---|---|---|
| Developed melody | [WAV](artifacts/melody.wav) | [MIDI](artifacts/melody.mid) |
| With classical bass/chords | [WAV](artifacts/arranged.wav) | [MIDI](artifacts/arranged.mid) |
| All original sampled tokens, straight timing | [WAV](artifacts/sampled-reference.wav) | [MIDI](artifacts/sampled-reference.mid) |

These generated files are local and ignored; [README.md](README.md) gives exact
regeneration commands. The page also supplies the original recorded four-bar
melody/duet and both prior eight-qubit QNN melodies, with the same synthesizer.
Their pitches, onsets and durations are preserved; this is a fresh common-timbre
render, not a claim to reproduce the original browser's audio waveform.

## Observable comparison

| Melody | Bars | Sounding notes | Durations | Mean jump, semitones ↓ | Stepwise (≤2 semitones) | Jumps > octave |
|---|---:|---:|---:|---:|---:|---:|
| Developed frozen QCBM | 16 | 62 | 5 | 2.459 | 54.1% | 0 |
| Same QCBM draws, straight | 16 | 61 | 1 | 3.117 | 56.7% | 0 |
| Original RECORDED Alice lead | 4 | 15 | 1 | 5.143 | 35.7% | 0 |
| Eight-qubit QNN free | 16 | 45 | 7 | 7.659 | 25.0% | 6 |
| Eight-qubit QNN structured | 16 | 44 | 7 | 7.442 | 18.6% | 10 |

The developed melody has a smoother average contour than these fixed comparison
examples and more duration variety than the original. It does not beat its own
straight sample on every diagnostic: the straight sample has a slightly higher
stepwise fraction. More variety is not automatically better. The original is
eight seconds, while the new pieces are 32 seconds; no aggregate perceptual score,
statistical superiority or controlled model-ranking claim follows from these numbers.

The new piece retains 71.9% literal pitch-class agreement between corresponding
A and A′/A″ bar positions, versus 34.4% in its straight sample. This is imposed
by classical repetition. A transposition-tolerant diatonic interval diagnostic
gives 58.3% for the new piece, 16.7% for its straight sample, 7.1% for free QNN,
and **100% for structured QNN**. The earlier structured example therefore also
retains its deliberately transformed themes; literal pitch-class disagreement
must not be mistaken for absence of structure. Bars with no intervals on either
side are excluded from that diagnostic. None of these metrics measures human
motif recognition or proves learned long-range dependencies.

**Subjective listening assessment: pending human audition.** The coding agent
verified valid non-silent waveforms but did not hear or rate the compositions.
The listening page provides an explicitly subjective rubric: recognizable motifs,
rhythmic interest, contour, phrasing and ending, each 1–5 with free-text tradeoffs.
The user was invited to audition; no response had been received when this report
was prepared. No aesthetic verdict is fabricated. The technically supported
conclusion is smoother contour and explicit classical form, not proven superior music.

## Provenance and unchanged evidence

Original trained QCBM checkpoint identity:
`ecd7faaa232a15c261a5e3daf8047e0b4d71be9f4eb4bb597e70acb671c5b8a4`.
Current packaged checkpoint bytes SHA-256:
`6b57c0bd921b9fac673353034e66cd07dec648bce044d2d2a890e0d35e15c024`.
Raw sample bytes SHA-256:
`be635526814540453ae31e34266207e4c59dd61468c5118bb3b0159ea389a5bb`.

`artifacts/raw-samples.json` preserves exact sampling provenance, source/circuit
hashes and runtime versions. `artifacts/trace.json` records all original source
event identities, copied positions, replaced positions, pitch/timing changes,
cadence overrides and harmony decisions. [results.json](results.json) records
the executed sample, comparison diagnostics and verification hashes without
corpus data, model weights or large audio files.

This is **not a 64-round Bell experiment**. The comparison references the existing
recorded 4,096-shot CHSH result without changing its denominator, counts, run or
statistics. No statistics are calculated from the composition. New form and
coherence are classical arrangement choices, not a new QCBM training result,
quantum computational advantage or free IonQ compatibility evidence.

## Verification executed anew

Environment: Python 3.12.14, Qiskit 2.5.2, NumPy 2.5.3, Mido 1.3.3. No dependency
installation or modification was needed. Generation and rendering of all seven
MIDI/WAV pairs took approximately **0.42 seconds** after imports. First generation
completed at 14:12:53 UTC; actual artifact verification passed at 14:18:04 UTC.

- **8 experiment tests passed in 2.34 seconds:** exact seeded samples, bit order,
  immutable raw source, lineage, rests, every-motif participation, deterministic
  classical rules, note validity, duration, identical exports and protected assets.
- **138 existing Python tests passed in 25.42 seconds**, with unchanged assertions.
- **All three existing Node suites passed.** Legacy UI and contract checks passed
  at 14:13:59 UTC; paired projection checks passed at 14:15:14 UTC. These use mocked
  DOM/AudioContext, not real browser playback. The projection command initially
  failed because its default `.venv-review` interpreter was unavailable; specifying
  `.venv-final/Scripts/python.exe` resolved it without code/test changes.
- **Both original orchestration CLI examples passed**, rules backend, no audio,
  provider disabled.
- **All seven MIDI and seven WAV files independently parsed:** the five long-form
  variants are 32 seconds, original melody/duet are eight seconds; MIDI notes and
  velocities are valid, audio RMS is nonzero, peaks are bounded, and notes close.
- Main melody/arranged MIDI and WAV regenerated **byte-for-byte identically**.
  The raw sample SHA-256, source fixture SHA-256 and historical statistics match.
- Local listening-page links validated with an HTML parser. The browser tool
  rejected the `file:` URL; no bypass was attempted and interactive playback was
  not claimed. Open the saved page directly for human audition.

The existing regression suite uses its established local/mocked simulator checks;
the composition itself submitted zero backend jobs. No remote Qollab/IonQ or
physical hardware check was attempted. Source diff inspection confirms that only
the new experiment directory is added. The earlier QNN artifacts were read-only.

## Recommendation

This is ready for local listening and draft review as an optional creative
experiment. Its modest deterministic arrangement is a more direct way to obtain
form and smoother contour than training another model in this bounded task.
Human listening remains necessary before saying it sounds better. Keep canonical
Quantum Duet/Qollab unchanged; no merge, deployment publication or submission has
been performed. The original arranger's flat-chord issue remains outside scope.
