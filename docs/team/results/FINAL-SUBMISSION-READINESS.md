# OxfordQ final submission readiness — Phase 0

Prepared 2026-10-11, verification began approximately 20:51 UTC; tests/browser/
package verification completed 21:05 UTC. Deadline: **2026-10-11 23:00 UTC**
(October 11, 19:00 US Eastern), confirmed against the official timeline.

**GO for the privately verified built-in-simulator / recorded demonstration.
NO-GO for claiming a complete eligible submission now.** The candidate remains
private, the required video does not exist yet, and full free-IonQ Duet execution
is unresolved. Nothing was published, submitted, merged or retargeted. Do not let
Local Studio, natural performance or POP909 integration delay these final steps.

## Exact sources inspected

Fetched origin and compared GitHub PR metadata and remote branch heads before edits.
All supplied revisions matched; no unexpected divergence was found.

| Source | Exact SHA / state |
|---|---|
| Current main | `c49c2e6cace0790211ae6808f4ecdc4cb77faa01` |
| PR #8 | `f42bcf1e3db5a2cc7d86e82d4dc6c06a0c6a440d`; open draft, mergeable; base main |
| PR #9 | `2801ba46ed5acdc7fbf0d3cca635f50aa8a2b88c`; open draft, mergeable; base #8 branch |
| PR #10 | `0debfbc1a3effb962f6a9bc157798feb2c672359`; open draft, mergeable; base #9 branch |
| Expressive | `e6e637a807a74070d144fb08bcb051367ac351e6` |
| Natural performance | `b41a1dd3a0450560eff70b0990ef0977bf5bc2e7`; expressive is its ancestor |
| Hansheng POP909 | `7793294fe1c20294e3042fdd4fe97c2b0dd52647` |
| Experimental PR #7 | `241e508405b8617323e275a3b110179473621b87`; open draft, mergeable, excluded |

PR #10's parent is the exact accepted #9 head, whose parent is the exact #8 head,
whose parent is current main. Thus the tested tree already contains the frozen
composition stack in dependency order, without importing PR #7 or later engines.

Coordinator checkout was clean before work. Worker A/B/C statuses were read only
and all were clean (initial restricted reads failed; normal authorized read-only
escalation succeeded). Existing integration/merge worktrees were clean; the old
detached review worktree has staged historical combined changes and an untracked
review directory. It was preserved unchanged. No other worktree was edited.

New local branch: `codex/submission-readiness-20261011`, from PR #10's exact head.
Its new tracked files are this report and `SUBMISSION-MATERIALS.md` only. No
Phase 1 combined integration branch or draft PR has been created in this pass.
No musical, scientific, model, interface or deployment source was changed.

Read AGENTS.md, team README/map/run contract/verification and applicable ownership
instructions, worker completion reports, coordinator integration and composition
readiness reports, deployment/source notices and actual package/loader/player
source. Older reports are historical evidence; their test counts are not reused
as this pass's results.

## Precise candidate and rollback

Preferred private project:
https://qollab.xyz/u/Floris/oxfordq-composition-verificati#run

It remains **Draft / Editing**. Previously uploaded archive:
`components/quantum_duet/build/composition-candidate-20261011.zip`, SHA-256
`e29da2a4fbb2e4dc16e9527b93aadf7dfd7cbbf6f0adc4781f5cda572a298832`.
Source revision is PR #10's exact head above, not current main alone.

New rebuild: `components/quantum_duet/build/submission-candidate-phase0-20261011.zip`,
SHA-256 `d2c07286ca7bf69e2d5c08aed58152c1daf145e1536f1b99a3dd3868d7ea5144`.
Every extracted file is byte-identical to the actual uploaded archive's build,
including `manifest.json`; ZIP timestamps explain the different archive hash.
Manifest SHA-256: `9d4ad54d8756179c34015165743cb9348a446503041ec36afbb54d7b24a72d74`.
The manifest records file hashes, not a source SHA; the source-to-build linkage is
recorded explicitly in this report and `submission-phase0-verification.json`.

Budget: **34 upload files, 3,266,684 bytes total; largest 1,411,244 bytes**.
Official runtime limits were reread in Chrome: 100 files, 2 MB per file, 200 MB
across the account. The previously uploaded candidate was accepted by the platform;
this pass did not upload another copy or certify account-wide free capacity.
Qollab-managed project-page metadata is separate from this upload manifest.

Rollback: https://qollab.xyz/u/Floris/quantum-duet#code, original private draft.
Read-only inspection confirmed Draft / Editing and the unchanged twelve-line
canonical entry using the asynchronous supplied-backend bridge. No file, card,
setting or project version was edited. Historical extra `quantum_motif` module
copies in that draft were not deleted or altered.

New default rebuild: `components/quantum_duet/build/submission-default-phase0-20261011.zip`,
SHA-256 `64a7a2d2bf9a4c90a5f8b79299c1f050ecc4cabf5f8c8f89c76767f29c6d8c7e`;
**25 files / 208,598 bytes**, all bytes equal to the preserved pre-composition
baseline. Manifest digest: `00f8dfb42c213c4ed2441c211a2dc645c5844d091bd6224950ba2dfd82fda493`.
Generate without `--with-composition` to retain this default release.

## Newly executed verification

Actual tested source tree: exact PR #10 head, containing #8/#9; later engines
were not present. Python 3.12.14; Qiskit 2.5.2; NumPy 2.5.3; Mido 1.3.3;
pytest 9.1.1; music21 9.9.2; Pydantic 2.14.0; google-genai 2.29.0; Node 16.
This existing environment was verified, not freshly installed.

- Complete relevant Python regression suite: **161 passed in 43.92s**.
- Four Node commands passed, at 20:56:05–20:56:14 UTC: original UI/audio checks,
  shared contract/MIDI checks, paired projection checks and optional Composition
  mocked DOM/media/export checks. The projection suite verified four MIDI files.
- Both original rules CLI examples passed, generated expected original/baseline/
  arranged MIDI and JSON, provider **disabled**, audio **not requested**.
- Fresh optional/default builds passed; full file-set equality, every manifest
  hash, file budget and six freeze asset hashes/lengths checked independently.
- Both frozen WAVs have 705,600 mono PCM16 frames at 22,050 Hz: **32 seconds**.
  Both MIDIs are **32 seconds**, 480 ticks/beat, tracks end at tick 30,720. The
  melody MIDI track is unchanged by accompaniment.
- Sixteen motifs / all 64 original tokens remain; 64 developed event records and
  twenty explicitly replaced source positions remain. The source schedule matches
  the original trace. Composition traces have no CHSH statistics and record zero
  generation/backend work during refinement and playback. Regression tests cover
  deterministic classical refinements, provenance and frozen functionality.
- **53 protected existing component/contract/fixture Git objects** match main,
  excluding the separately reviewed opt-in builder change. Working-tree checks
  confirm no modifications to those sources. Frozen weights/counts are unchanged.

Exact commands, run from the coordinator root:

```powershell
.venv-final/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests experiments/qcbm_composition/tests experiments/qcbm_refinement/tests --basetemp .test-phase0-final-20261011
node components/quantum_duet/tests/ui_checks.mjs
node components/quantum_duet/tests/ui_c/contract_checks.mjs
node tests/duet_projection_checks.mjs .venv-final/Scripts/python.exe
node tests/composition_mode_checks.mjs
.venv-final/Scripts/python.exe -m orchestrator --generation-manifest examples/generation.json --backend rules --bars 4 --no-audio --out output-phase0-generators
.venv-final/Scripts/python.exe -m orchestrator --manifest examples/note_events.json --backend rules --bars 4 --no-audio --out output-phase0-events
.venv-final/Scripts/python.exe components/quantum_duet/tools/build_qollab.py --with-composition --out components/quantum_duet/build/submission-candidate-phase0-20261011
.venv-final/Scripts/python.exe components/quantum_duet/tools/build_qollab.py --out components/quantum_duet/build/submission-default-phase0-20261011
.venv-final/Scripts/python.exe components/quantum_duet/tools/extract_composition_exports.py components/quantum_duet/build/submission-phase0-exports.jsonl --output-dir components/quantum_duet/build/submission-phase0-decoded
.venv-final/Scripts/python.exe components/quantum_duet/build/verify_submission_phase0.py
```

Use new output directories when repeating; no existing artifacts were overwritten.
The last script is an ignored independent audit helper, not an application change.

## Actual private Qollab / Chrome checks

New browser checks ran 20:55–21:03 UTC on the preferred project, with the free
built-in simulator selected. No simulator was silently substituted.

1. Recorded fixture loaded as **RECORDED**, 4,096 historical CHSH shots,
   85.89% with its unchanged 83.77%–88.01% conservative interval. Replay showed
   zero current backend calls. Quantum and classical playback both scheduled
   notes; the classical selection changed local policies/music, not full evidence.
2. Composition was prominently **PRE-GENERATED**, with offline statevector source
   and classical-development wording. Experiment statistics were hidden. Melody
   played with duration 32, readyState 4 and advancing time (8.620867 seconds
   observed). Arranged recording played and seeking reached **15.885216 seconds**.
3. Recording switches paused/reset previous audio. Mode changes stopped Duet
   playback and paused Composition. Returning to Experiment preserved its evidence.
4. Actual platform UI exports were captured completely, then decoded: both MIDI
   bytes match the accepted files; raw-source and trace strings encode to their
   exact frozen bytes. The provenance payload has **249,283 characters**, captured
   through bounded DOM reads. Native sandbox downloads remain **uncertified**;
   the verified export route is visible payload / console envelope plus decoder.
5. Composition loading, playback, seeking and export made **zero backend jobs**.
   Its loader/player source has no execution path to a backend. The only new
   backend call in this pass was an explicit Experiment Generate click below.
6. A fresh **five-circuit / one-job built-in simulator take** succeeded, with 32
   returned shots per circuit (160 total; QCBM's 32 excluded from CHSH statistics).
   Live quantum playback worked; switching to Composition stopped its notes.
   No training or new sixteen-bar sampling occurred.

Fresh live evidence timestamp: `2026-10-11T20:58:40.836000+00:00`;
job `1dcabf43-0d27-482d-8f6a-3df5b64b3a79`;
actual backend `qiskit.providers.basic_provider.basic_simulator.BasicSimulator`,
name `basic_simulator`, version `0.1`, `backend_run_calls=1`.

| Cue setting | Actual counts in displayed ba order | Success |
|---|---|---|
| 00 | 00:19, 01:1, 10:2, 11:10 | 29/32 |
| 01 | 00:14, 01:4, 10:1, 11:13 | 27/32 |
| 10 | 00:19, 10:1, 11:12 | 31/32 |
| 11 | 00:4, 01:15, 10:12, 11:1 | 27/32 |

Total **114/128 = 89.0625%**, displayed two-sided conservative 95% Hoeffding
interval **77.0585%–100%**. These are actual new finite-shot results, not the
ideal value, a favorable-sample selection or replacement frozen evidence. The
interval assumes fresh independent preparations/strategy draws and fixed equal
setting allocation; it is not hardware-certified. Ideal-simulator type was an
explicit runner declaration, not independently attested noise metadata.

Known pre-existing live limitation: the Qollab supplied-backend route returns
legacy `schema_version:1` takes; UI explicitly says LIVE legacy take and indicates
run/round envelope integration pending. It must not be advertised as live
`qm.run-result.v1` support. Recorded/imported shared envelopes and local paired
projections retain their identities. This pass did not rewrite that backend route.

A browser log contained one automation clipboard signal rejected by Qollab's
already-started worker (20:55:53 UTC). No application playback/export/generation
failure occurred. An initial simulator select action used a wrong option value;
inspection identified `ideal-simulator`, then the action succeeded before the
single Generate call. No denied access or security control was bypassed.

Human listening: the user already accepted PR #9; no new listening-quality
verdict is inferred from these browser tests.

## Frozen identities and evidence artifacts

| Asset | SHA-256 |
|---|---|
| Improved melody WAV | `126f0f82d9bb7ac59aa526b1297bc4ec9563360e9e540fdfae5caff211a54705` |
| Improved arranged WAV | `2c2d5780bbe58838aafe34e3e11db508704ffd169abb007a1806918a4d6ad379` |
| Improved melody MIDI | `f6b3a813b3c71ce1171b40ff5e65dc1428bd4ddb36107fc805f8a0d3558a41b7` |
| Improved arranged MIDI | `33ba5acb41935481496d9a465cb03515c24ead6c0af7ee31eb4ff744617af16c` |
| Raw samples JSON | `be635526814540453ae31e34266207e4c59dd61468c5118bb3b0159ea389a5bb` |
| Trace JSON | `d4f5ca08e70fbf8dadf364863e9fb1f9cf4715239c3a68b7988caac9ade0eee5` |

Canonical assets: `components/quantum_duet/composition/`; immutable shared fixture:
`docs/team/fixtures/run-result.v1.json`. The frozen model/data files are unchanged.
Existing recorded fixture/run hashes remain in the package manifest.

New local ignored evidence under `components/quantum_duet/build/`:

- `submission-phase0-verification.json`: source SHA, exact package/media/hash
  comparisons, recovered exports, full actual job/counts and source invariants.
- `submission-phase0-exports.jsonl`, `submission-phase0-decoded/`: complete browser
  payloads and recovered MIDI/provenance files.
- `submission-phase0-live-export.json`: exact fresh live export, SHA-256
  `3441e08b7a446c206118bab1bcb638030a875bbe583c8cc38b56ad0d0535d465`.
- `submission-phase0-private.png`: actual private candidate screenshot.
- New/default build directories, ZIPs and their manifests named above.

Local listening-page preview: http://127.0.0.1:8782/ serves the previous byte-identical
candidate; frozen files also reside directly in the canonical composition directory.
No new local browser smoke pass was claimed here: the newly executed real browser
pass was on Qollab; prior local Chrome checks are explicitly historical.

## Official requirements, materials and remaining blockers

Current official pages were read directly through Chrome on October 11:

- https://qollab.xyz/programs/hackathon/how-it-works — deadline, video requirements,
  existing-code disclosure, captain submission and one-job IonQ guidance.
- https://qollab.xyz/programs/hackathon/terms — MIT code/docs and external code
  repositories, runnable public Qollab project, source disclosure, accessibility,
  free-simulator requirement including IonQ, attribution and 12-month availability.
- https://qollab.xyz/learn/docs/runtime-environment#limits — file limits, data-path
  loading, supported browser/runtime and one-job boundary.

The text web reader could not open the official page; the real browser did.
Third-party search results were not used as the source of submission requirements.

**[SUBMISSION-MATERIALS.md](SUBMISSION-MATERIALS.md)** contains ready project copy,
exact-source reproduction, source links, dependency/data attribution, pre-existing
code disclosure, the exact support wording and a timed **2:40** storyboard/capture
checklist. The copy is prepared locally, not yet applied to a public project page.

| Item | Status / next step |
|---|---|
| Recorded/built-in demo | GO; newly verified exact candidate |
| Frozen Composition | GO as optional PRE-GENERATED playback; human acceptance recorded |
| Public Qollab project/page | BLOCKED pending explicit publication approval and applying prepared page copy; no anonymous public-run check yet |
| Demo video | BLOCKED: no actual video file, upload or URL. Available browser tools capture screenshots, not screen/system audio; ffmpeg not available on PATH. Use storyboard and an available user screen recorder, then authorize hosting |
| Full free-IonQ Duet | UNVERIFIED / historical batch rejection. Official rules require simulator compatibility including IonQ; award eligibility cannot be certified by built-in success or a separate diagnostic. Resolve or obtain organizer clarification; no new production path was attempted |
| Team/captain submission | NOT VERIFIED/SUBMITTED; captain must confirm existing registration and perform/authorize the form action before deadline |
| Native downloads | Nonblocking documented limitation; exact visible-payload recovery passed |
| Main merges | NOT AUTHORIZED in this request; PR #8/#9/#10 remain unchanged |
| Local Studio / expressive / natural | Deferred phases, excluded from candidate; no combined tests or UI demo claimed |
| POP909 v2/v3 integration | Deferred; heads pinned only. No compatibility, rights or new backend verdict is inferred |
| Clean install / acoustic renderers | Deferred; no downloads, installs, renderer execution or missing-asset verification performed |

Historical IonQ evidence, **not newly executed**: October 10 16:12:38.228–16:12:54.141
UTC, free Aria 1 simulator, job `01a12696-88b0-73ab-ba43-b919b1180b11`, a single
32-shot Bell diagnostic returned 00:18 / 11:14, SDK qiskit-ionq 1.0.2, accepted
job type `ionq.circuit.v1`. Four/five-circuit requests separately failed HTTP400
with no counts. See worker A's completion report; no full-IonQ success is claimed.

Scientific wording remains: local noncommunicating classical bound **75%**;
ideal quantum success **approximately 85.355%**; unrestricted centralized
classical coordination **100%**; **no demonstrated quantum speedup or
musical-quality advantage**. Longer music is quantum-sampled material with
classical musical development, not a new 64-round Bell experiment.

**This effort is supported by Qollab & IonQ.** The shipped UI contains the required
wording; prepared project copy includes it with the requested punctuation.

## Immediate decision and rollback

Prepare/capture the required video and obtain publication approval now; do not
spend the remaining window importing expressive/acoustic/POP909 features. Keep
the exact optional candidate frozen. Public submission cannot be called complete
until the video, publication, anonymous access check, captain form and unresolved
IonQ requirement are addressed. Simulator/hardware results receive no judging
bonus according to the official FAQ, but that does not erase compatibility rules.

If the optional interface causes any late regression, retain the untouched original
Quantum Duet draft/default archive and use the accepted recording only in the
video, accurately labelled PRE-GENERATED. This rollback protects playback; it
does **not** resolve the original full-IonQ compatibility limitation.

Stop here for the user's GO/NO-GO decision. No later-phase work or publication/
submission should happen before this readiness result has been presented.
