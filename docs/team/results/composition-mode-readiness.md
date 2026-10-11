# Frozen composition and optional app readiness, 2026-10-11

The user listened to PR #9 and accepted it as musically suitable for the demonstration.
This records a human listening decision; it asserts no scientific musical-quality
advantage. The musical version is frozen. No generation, sampling, training, model
changes or quantum submissions were performed in this preparation.

## Merge readiness

Fetched GitHub and checked the exact heads against the remote refs:

| PR | Head | Base | Review |
|---|---|---|---|
| #8 | `f42bcf1e3db5a2cc7d86e82d4dc6c06a0c6a440d` | main | Draft, open, mergeable; additive isolated composition |
| #9 | `2801ba46ed5acdc7fbf0d3cca635f50aa8a2b88c` | PR #8 branch | Draft, open, mergeable; additive classical refinement, now accepted by user |

Current main remains `c49c2e6cace0790211ae6808f4ecdc4cb77faa01`.
Neither PR depends on PR #7. Recommended sequence after human merge approval:

1. Re-fetch and require PR #8's exact head; mark ready, regular merge commit.
2. Verify main contains #8. Retarget #9 to main only then; require the unchanged
   #9 head, mergeability and a diff containing just its fourteen refinement files.
3. Mark #9 ready and regular merge commit. Verify main and rerun combined checks.
4. Review the separate coordinator optional-mode commit. It does not alter either
   frozen PR head and must be integrated separately; no publication is authorized.

No blocker was found for #8/#9. Neither PR was merged or retargeted in this preparation.
Mergeability must be checked again at execution, especially after the base changes.

## Optional PRE-GENERATED mode

Coordinator branch: `codex/pregenerated-composition-mode-20261011`, from PR #9's
exact head. Existing Experiment HTML, UI, CSS, bridge, fixtures, raw contract,
models, mapping and statistics remain unchanged. The sole existing-code change is
an opt-in packaging flag. Default upload contents remain byte-identical.

Canonical frozen files are in `components/quantum_duet/composition/`: accepted
melody/arranged WAV and MIDI, exact raw-samples JSON, exact trace JSON and freeze
manifest. Their bytes match the accepted listening artifacts. Git attributes prevent
line-ending conversion of the immutable JSON sources and binary recordings.
The freeze manifest separately records the user's acceptance; original historical
trace text saying listening was pending is preserved and explained in the UI.

The new `composition_showcase.py` loader uses only Python's standard library,
checks asset SHA-256 and source identities, and reads literal data paths supported
by Qollab. No arranger, music21, Mido, QNN or generator is needed for platform
playback. The existing Qiskit/NumPy requirements remain unchanged.

Optional markup and entry wrap the unmodified Experiment UI. Mode changes stop
existing audio; Composition has a native audio player with seeking and melody-only
or accompaniment selection. Its page hides Experiment statistics, labels the
recording PRE-GENERATED, explains offline statevector source sampling versus classical
development, and makes no selected-backend execution claim. Missing/corrupt optional
assets produce an explicit error and leave Experiment available, without fallback.
MIDI and provenance use separate filenames, visible lossless payloads, console
envelopes and a standalone decoder. Existing Duet exports/decoder are unchanged.

## New verification executed

- PR #8/#9 combined suite: **154 passed in 14.69s**.
- Optional-mode combined suite: **161 passed in 14.97s**, including seven new
  freeze/packaging/export tests. The seven separately passed in 3.39s.
- All three existing Node suites passed again at 16:52:16–16:52:20 UTC; the new
  mocked DOM/media/export suite passed at 16:52:20.382 UTC.
- Both original orchestration CLI examples passed with rules, no audio and
  provider disabled. Four MIDI/four WAV refinement exports reverified at
  16:38:09.347 UTC; original and accepted media hashes remain unchanged.
- Default build: **25 files / 208,598 bytes**, every file identical to a fresh
  baseline build, including its manifest. ZIP hashes differ because ZIP timestamps
  differ; file-byte equality is the preservation criterion.
- Optional build: **34 files / 3,266,684 bytes**, largest file **1,411,244 bytes**.
  Actual Qollab upload accepted these files. The current runtime documentation,
  read through Chrome, permits 100 files / 2 MB per file / 200 MB across the account:
  https://qollab.xyz/learn/docs/runtime-environment#limits
- Local Chrome: recorded fixture, both 32-second recordings, playback, pause,
  seeking, texture/mode separation, both MIDI exports and complete provenance.
- Actual private Qollab: literal-file loader/hash validation through its Python
  bridge; both recordings loaded, played and paused; arranged seeking reached
  **15.99972 seconds**. Texture switching paused the prior recording. Switching
  back preserved the recorded **4,096-shot / 85.89%** Experiment result and stopped
  audio. No new Experiment generation was requested.
- Both actual browser MIDI payloads, locally and on Qollab, were decoded with the
  new utility, parsed as exactly 32-second MIDI, and matched the accepted bytes:
  melody `f6b3a813b3c71ce1171b40ff5e65dc1428bd4ddb36107fc805f8a0d3558a41b7`;
  arranged `33ba5acb41935481496d9a465cb03515c24ead6c0af7ee31eb4ff744617af16c`.
  Exported raw-source and trace strings re-encode to their exact original bytes.

The initial preview invocation as a file could not resolve the repository namespace;
the documented module invocation below resolved it. An initial automation read of
the large provenance textarea was truncated by the tool's 200,000-character result
cap, not the application; bounded reads captured all 249,283 characters and both
complete export decodes passed. No access controls were changed or bypassed.
Native Qollab/browser file downloads were attempted by the UI but are not certified;
the verified platform export route is the visible lossless payload/console envelope.
Browser checks establish functionality, not an additional subjective quality rating.

## Build, preview and export reproduction

From the repository root, using a fresh output directory every time:

```powershell
.venv-final/Scripts/python.exe components/quantum_duet/tools/build_qollab.py --with-composition --out components/quantum_duet/build/composition-candidate-new
.venv-final/Scripts/python.exe -m components.quantum_duet.dev.composition_preview --directory components/quantum_duet/build/composition-candidate-new --port 8782
.venv-final/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests experiments/qcbm_composition/tests experiments/qcbm_refinement/tests --basetemp .test-composition-new
node components/quantum_duet/tests/ui_checks.mjs
node components/quantum_duet/tests/ui_c/contract_checks.mjs
node tests/duet_projection_checks.mjs .venv-final/Scripts/python.exe
node tests/composition_mode_checks.mjs
.venv-final/Scripts/python.exe components/quantum_duet/tools/extract_composition_exports.py copied-payload.txt --filename oxfordq-composition-arranged.mid --output-dir composition-exports-new
```

Without `--with-composition`, the original release is generated unchanged. The
local package preview deliberately disables live backend generation; it tests the
actual bundled loader/assets and recorded Experiment, not a Qollab bridge substitute.

Private candidate: https://qollab.xyz/u/Floris/oxfordq-composition-verificati#run
It remains Draft / Editing, with no published versions. The user explicitly
approved separate project creation and Qollab's stated terms. The original
https://qollab.xyz/u/Floris/quantum-duet draft was not edited. Generated ZIP,
browser screenshots, exact captured/decoded exports and verification JSON are in
the ignored `components/quantum_duet/build/` directory.

Before any canonical deployment, repeat playback/export and Experiment checks on
the exact final upload after merges. Publication, presentation-video upload and
hackathon submission still need separate authorization. Free IonQ multi-circuit
Duet status is unchanged and is not exercised by this optional mode. If integration
or timing becomes risky, keep the original release and use the frozen recording
in the presentation video instead; no new musical work is required.
