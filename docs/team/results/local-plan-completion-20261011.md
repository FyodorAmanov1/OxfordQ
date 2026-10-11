# Local plan completion — 2026-10-11

## Scope and location

User instructions: reuse the existing models and adapt notes to each instrument;
compile locally for eventual GitHub submission; do not push.

Work is isolated in branch `codex/local-plan-completion-20261011`, worktree
`build/plan-completion-20261011`, from main
`c49c2e6cace0790211ae6808f4ecdc4cb77faa01`. Main is unchanged.
No remote branch merge, GitHub push, platform upload, paid API execution,
physical QPU job, new training, or held-out motif inspection was performed.
Source changes are preserved locally; generated artifacts remain ignored.

## Ordered completion

| Step | Local outcome |
|---|---|
| 1. Integrated environment | Both packages installed; Python/Qiskit dependencies available; original rules CLIs run without audio |
| 2. POP909 integration | Selected source from collaborator snapshot 747871ce68ebbd7b9febe42c08c020aa688cb432; unchanged packaged weights; validated JSON/NPZ loaders; provenance and notices; studio safeguards and nondestructive ZIP build |
| 3. Flat harmony | Core music21 flat spelling preserved; major/minor inference and chromatic POP909 spellings covered |
| 4. Instrument generators | Frozen QCBM reused through distinct instrument decoders; all sixteen profiles exercised; registry remains replaceable |
| 5. Existing ML arranger | Optional Gemini path integrated into paired Duet projection/UI; offline typed responses and explicit failure tested; raw source retained |
| 6. Music assessment | Sixteen-bar original/baseline/arranged MIDI and WAV, listening page, seed/key checks and full-palette run |
| 7. Local release | Two wheels, two ZIPs, compilation/dependency checks, hash manifests, generated namespace and installed-wheel inference |

The modular generation → arrangement → validation design matches the original
plan. The selected implementation uses the existing Gemini option rather than
training a new orchestration transformer. Instrument differences currently come
from classical decoding of shared QCBM weights, as requested.

## Verification and resolved failures

- Initial combined suite: 2 failed / 136 passed. One frozen fixture hash was
  affected by Windows checkout newline conversion; another failure came from
  assigning Node 20's read-only global crypto property. Restored canonical fixture
  bytes, added byte-preserving Git attributes and guarded crypto initialization.
  The repaired baseline then passed all 138 tests.
- Final combined command:
  `python -m pytest -q tests components/quantum_duet/tests --basetemp .test-final-motion`:
  **199 passed in 12.88 seconds** on 2026-10-11, before final documentation.
- Node projection checks passed at 2026-10-11T14:54:46.310Z, including offline
  Gemini projection, real paired rules conversion, byte hashes, source IDs, rests,
  failure isolation, export/import and no resampling. UI and contract checks also
  passed at 14:50:46.815Z and 14:50:46.957Z. These use mocked DOM/AudioContext;
  no fresh interactive browser or Qollab claim is made.
- Real loopback HTTP smoke passed for /api/config, /api/fixture, /api/arrange and
  /api/run. Fixture arrangement preserved raw evidence; the local BasicSimulator
  run used one batch. Recorded local run ID:
  `qm-local-d2e9879e-e392-42b2-bce8-3a0e4e1637c1`.
- Local builds uncovered and fixed browser .js files checked as CommonJS,
  a verification venv that did not inherit development dependencies, and
  Python 3.12 Windows .pth handling of Cyrillic paths. Wheel verification imports
  project code from the fresh environment's site-packages; already installed
  dependencies are reused without running editable project finder files.
- The release builder checks hashes, ZIP contents/budget, fixture byte identity,
  installed model assets and both local inference paths. Its manifest identifies
  the source commit and hashes of canonical source files.

## Musical results

The five-part C-major example contains 271 notes, with all 63 lead notes retained
through MIDI export and no accompaniment notes muted. Hard validation and
structural warning lists are empty.

| Metric | Independent parts | Arrangement |
|---|---:|---:|
| Heuristic score | 0.69660 | 0.79099 |
| Harmonic fit with ornaments | 0.45833 | 0.61699 |
| Rough interval ratio | 0.10411 | 0.08818 |
| Mean melodic motion, semitones | 3.538 | 3.523 |
| Accompaniment note retention | 1.000 | 1.000 |
| Individual edit fraction | 0.00000 | 0.01476 |

The rules baseline and final arrangement are identical for this run.
Motion is measured from actual monophonic lines even when a section permits
divisi; drum sound numbers are excluded from melodic leap warnings.
Earlier score readings of 0.74082/0.83502 preceded that motion-metric correction.

WAV verification: original 43.51s, baseline/arrangement 43.60s; stereo 44.1kHz;
nonzero audio, peaks 0.4694 and 0.5182, below the -1dB ceiling.
FluidSynth 2.6.1 and GeneralUser GS were explicitly supplied from the workspace's
existing assets directory; assets are not duplicated into the worktree or wheels.

Nine runs completed at 2026-10-11T14:55:57.428110Z:
seeds 42/43/44 × C major/E-flat major/A minor, sixteen bars each. Major keys use
POP909 and minor uses inferred harmony. Every lead was preserved, with zero
hard errors/warnings and mean heuristic improvement 0.08009.
The sixteen-instrument palette also passed with no structural warnings.
These are decoder/arrangement robustness checks, not new model generalization
or a listening study.

## Artifacts and commands

Paths relative to the worktree:

- `output-plan-assessment/comparison.html`: listening page.
- `output-plan-assessment/assessment.json`: compact metrics and MIDI/WAV hashes.
- `output-plan-assessment/{original,baseline,arrangement}.{mid,wav}`.
- `output-plan-evaluation-final/evaluation.json`: nine-run assessment.
- `output-plan-full-palette/assessment.json`: all sixteen instruments.
- `dist/local-release-final/`: wheels, quantum-duet.zip, pop909-studio.zip,
  installed-wheel smoke results and release-manifest.json.

~~~powershell
python -m quantum_models.orchestra --bars 16 --backend rules --no-audio --out output-models
python scripts/evaluate_model_orchestra.py --out output-evaluation
python scripts/build_local_release.py --out dist/new-local-release
~~~

For WAV output, omit --no-audio and supply --fluidsynth / --soundfont.
For optional Gemini, set GEMINI_API_KEY, choose --backend gemini and add
--require-gemini. Paired UI: start components/quantum_duet/dev/server.py with
--arrangement-backend gemini. No key was configured in this session.

## Future work outside this local iteration

1. Listen to the comparison and revise harmonic/texture choices using musician
   feedback. A valid MIDI score does not guarantee pleasing orchestration.
2. Exercise live Gemini when credentials and API execution are authorized.
   The official [Gemini 3.8 Flash documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
   was checked on 2026-10-11; current verification is SDK shape and offline
   injected responses, not live model output.
3. Replace instrument adapters with your smaller checkpoints as they become
   available, retaining decoded note/provenance contracts.
4. Integrate your eventual hardware execution behind those adapters.
   Fresh Qollab/IonQ verification is outside the user-selected local scope.
   The experimental POP909 studio can submit multiple single-circuit jobs per
   progression; it is separate from the one-batch Duet contract.
5. Review the local branch for eventual GitHub submission. No push was made.

See [orchestration theory and model boundaries](../../orchestration.md),
[model source notices](../../../quantum_models/SOURCE_NOTICES.md), and
[exact import hashes](../../../quantum_models/IMPORT_MANIFEST.json).
