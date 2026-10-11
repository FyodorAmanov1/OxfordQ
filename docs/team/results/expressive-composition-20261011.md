# Expressive composition implementation — 2026-10-11

## Scope and location

Implemented locally in build/plan-completion-20261011 on
codex/local-plan-completion-20261011, starting from
23d4c79387f9c57d4c531aef5c5699f10f458c53.
The original main checkout remains at c49c2e6cace0790211ae6808f4ecdc4cb77faa01.
No GitHub push, merge, publication, paid API execution, physical QPU execution,
new training or held-out motif inspection was performed.

## Plan delivery

1. Added separate CompositionRequest, SourceBank, CompositionPlan and ComposedScore
   contracts, preserving legacy lead/timing/edit-budget behavior.
2. Preserved decoded QCBM notes/rests and POP909 chord-source IDs. Every composed
   note keeps its source pitch class, records an octave offset, and has a unique
   occurrence ID. Motif ordering and rest timing are checked.
3. Added variable bar signatures, accent groups, quarter-note tick timing, tuplets,
   tempo maps, dynamic conductor MIDI export and exact event round trips.
4. Added reproducible local Bach/Mozart/Debussy/Rachmaninoff references, thematic
   return, contrasting development, a lead break, variable rhythm/register,
   chord textures, root bass placement, velocities, accents and CC11 expression.
5. Added qml-compose / python -m orchestrator.composition, source-bank replay,
   interchangeable small-model registries, a separate Gemini composition prompt,
   three-attempt validation feedback and explicit missing-provider status.
6. Generated four roughly one-minute local studies with fixed-grid references,
   MIDI/WAV, source/plan/score/report JSON, artifact hashes and listening pages.
7. Added contract/adversarial/round-trip/offline-provider/model-replacement tests,
   artifact verification and installed-wheel composition smoke checks.

## Final listening artifacts

Directory: ../../../../../output-expressive-studies-final-20261011 relative to
this report's directory in the isolated worktree. From the workspace root it is
output-expressive-studies-final-20261011/index.html.

| Piece | Inspiration | Timeline seconds | Ensemble span | Flute span | Flute duration classes | Metre |
|---|---|---:|---:|---:|---:|---|
| piece1 | Bach | 61.95 | 63 semitones | 34 semitones | 11 | 4/4 |
| piece2 | Mozart | 61.76 | 62 semitones | 35 semitones | 11 | 3/4 |
| piece3 | Debussy | 59.30 | 60 semitones | 29 semitones | 14 | 6/8, 5/4, 3/4 |
| piece4 | Rachmaninoff | 61.21 | 63 semitones | 34 semitones | 15 | 12/8 |

FluidSynth 2.6.1 and the existing GeneralUser GS font rendered all eight comparison
WAVs at 44.1 kHz, with matched audible-sample RMS and shared peak headroom.
Release tails are approximately 3.4–3.5 seconds beyond the integrated timelines.
These metrics describe structure; they do not establish beauty or composer authenticity.

## Verification

Final checks completed locally on 2026-10-11 around 17:02 UTC:

- Full Python suite: **241 passed in 28.03 seconds** (tests and Quantum Duet tests).
- Existing Node projection/UI checks: passed, including paired source identity,
  MIDI metadata, playback cleanup and offline provider failure isolation.
- Final artifact verification: all four studies passed saved source/score/MIDI,
  tempo/metre/expression, WAV format/duration, file hash and local-link checks.
- Local HTTP listening index: status 200. The temporary loopback server was stopped.
- Browser preview: unavailable because the computer-use Node runtime could not start.
  No real browser listening or visual review is claimed.
- Installed editable qml-compose console command: registered and help verified.
- Local release builder compiles both packages and JavaScript, checks dependencies,
  builds wheels and both existing upload archives, checks generated namespace/source
  identity, and exercises installed-wheel inference. The final build is in
  dist/expressive-release-final-20261011; consult release-manifest.json for exact
  source HEAD, versions, file hashes and check results.

The initial --compare command was rejected by automatic approval review because it
could reach a paid external API. The new composition interface requires explicit
--live-gemini / allow_live_api before initializing Gemini. Tests prove that local
comparison requests do not initialize a live provider without that opt-in.

## Limits and remaining evaluation

The local planner is procedural. Existing QCBM weights remain shared by instrument
decoders; distinct trained instrument checkpoints are still replaceable through
the registry. POP909 is major-trained; minor studies transparently use relative-major
material. No transformer or composer-style model was trained.

Gemini schema, dedicated prompt, retries, rejection, source preservation and
comparison labeling were verified using injected/offline providers. A live Gemini
composition and human listening comparison remain unverified. Local rendering does
not establish playability, authentic counterpoint, advanced chromatic harmony,
classical form, or quantum musical advantage. See docs/composition.md for extension
points and the listening criteria.
