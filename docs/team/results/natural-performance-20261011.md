# Acoustic performance implementation — 2026-10-11

Base: `e6e637a807a74070d144fb08bcb051367ac351e6`.
Canonical source worktree: `build/plan-completion-20261011`.

## Delivered

- Persistent sfizz 1.2.3 samplers with pinned VSCO 2 CE 1.1.0 acoustic samples,
  native envelopes, correct articulation keyswitches and preloaded sample data.
- Separate source-preserving performance plans and portable performed MIDI:
  phrase dynamics, breathing, gating, coordinated rubato, bounded seeded timing,
  piano pedal, explicit limitations and a replaceable performance adapter.
- Multi-bar questions/answers, motif development/reordering, source-fitted harmony,
  cadence requests, joint sustained voicings and sample-compatible octave placement.
- Source/reference, native and expressive WAVs, dry stems, volume controls and
  mutually exclusive comparison playback. Existing browser oscillators are unchanged.
- Free-asset setup and license documentation; no samples/native binaries in Git or wheels.

## Local artifacts and actual evidence

Delivery collection: `output-natural-studies-release-20261011/index.html` in the
workspace root. All four generation/render commands completed successfully on
2026-10-11. Each piece has three mixes and five dry stems for each mix.

| Piece | Inspiration | Performed music (s) | WAV with release tail (s) |
|---|---|---:|---:|
| piece1 | Bach | 59.902 | 63.902 |
| piece2 | Mozart | 59.881 | 63.881 |
| piece3 | Debussy | 51.753 | 55.753 |
| piece4 | Rachmaninoff | 57.723 | 61.723 |

Phrase comparison: `output-natural-calibration-final-20261011/index.html`.
It replays four bars from the previously generated Mozart score through the old
envelopes, native acoustic samples and expressive acoustic performance, with zero
generator/provider calls. Acoustic variants share the same room setting; the old
renderer remains dry. Overall constant RMS matching preserves internal dynamics.

Python compilation and the final root wheel build completed. `git diff --check`
reported no whitespace errors. Wheel:
`dist/natural-performance-final-wheels-20261011/quantum_music_orchestrator-0.1.0-py3-none-any.whl`.
SHA-256: `3c6fe9f28ebf23a63a17bd4d71666c030fd0035b5571b37934ebb0919cd233d6`.

Normal generation executed source/range/capacity/lineage validation, logical MIDI
round trips, performance identity/capacity validation and WAV timeline checks.
Automated test suites were not added or rerun. Installed-wheel inference, browser
playback and human listening have not been checked in this iteration.

## Resolved integration issues

- The first native render could not open the non-ASCII Windows user path. The
  wrapper now supplies a verified ASCII short-path alias; unsupported systems get
  an explicit instruction to use an ASCII asset directory.
- Static inspection found clarinet placements above the sample patch's maximum.
  Acoustic composition now narrows octave placement to actual VSCO ranges; raw
  source notes remain unchanged. Final collection uses the corrected ranges.
- Articulation controls were checked against the installed SFZ labels, including
  different string spiccato/pizzicato orders and the tuba's higher keyswitch octave.

## Limits and execution scope

The planner and performer are procedural baselines. No new model was trained;
small instrument generators remain replaceable through the existing registry.
VSCO violin/cello patches are sections and connected sustain approximates legato;
there are no recorded interval transitions. Missing minor-key major dominants are
reported when absent from the source bank. Compilation/rendering cannot prove
beauty or realism; the listening comparisons are the next human review step.

Model generation used local frozen inference/simulation only. There were no paid
API calls, held-out evaluation, physical QPU submissions, Qollab uploads or changes
to original checkpoints, raw evidence or experimental musical mappings.

Asset archive checksums:

- sfizz Windows x64: `7431cbe9b7f2e71a9ff4b12fbbe82c766dbf75b1eedecca627e7506cb06a9fcc`
- VSCO CE: `4a4446628df0e1a12aaee58e9f65f8fa7cde51971e961abb1b43083a6d3a8ab7`

See [setup, interfaces and asset licenses](../../natural-performance.md).
