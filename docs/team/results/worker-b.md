# Worker B completion report

Executed 2026-10-10, Europe/London (BST, UTC+01:00). Role verified from
`codex/duet-adapter-20261010`; initial working tree was clean and HEAD was exactly
`3eb26f205f9b68c9e7f01cff9ca26f74315882a1`. Used the existing checkout and branch.
Read AGENTS.md, README, run-contract, repository-map, verification and worker-b
prompt before editing. The user's explicit overrides authorize commit/push and a
draft PR against `main`; no worktree creation, merge, publication or submission.
Fetched origin at 16:53 BST: main remains
`bff4c0e0ff1d67f73503724b5d3e303eaf696103` (merged PR #1), and contains HANDOFF_SHA.

The implementation commit SHA and draft PR URL are supplied in the final chat and
GitHub PR; this report is part of that commit, so it cannot include its own hash.

## Exact changed paths

- `components/quantum_duet/src/quantum_duet/orchestration_adapter.py` — new module/CLI.
- `components/quantum_duet/tests/adapter_b/test_adapter.py` — new acceptance tests.
- `examples/duet_integration/README.md` — new usage/integration example.
- `docs/team/results/worker-b.md` — this report.

No existing implementation, shared schema/fixture, dependencies, checkpoint,
scientific report, licence or other worker's source was edited. Generated test,
environment, demo and upload outputs remain ignored and are not committed.

## Implemented boundary

`from_take(take_json, run_id=..., data_status=..., source_asset=...)` converts the
unchanged completed `generate_take` bridge API without any backend call. Caller
assigns the run UUID before the single execution. It freezes original input bytes
(canonical bytes for dict input), records byte/canonical SHA-256, and preserves
model identifiers, Bell angles, 84/12 QCBM dimensions, full experiments/statistics,
backend metadata, simulator declaration/verification, recorded/live/mock label,
errors, explicit fallback and source lineage. Unknown SDK/platform versions are
explicitly labelled unknown. Four-recorded mode requires a recorded melody asset.

`freeze_result(contract_dict, raw_bytes=...)` consumes the shared recorded fixture
directly. Supplying raw bytes verifies canonical identity, checkpoints, execution
metadata, rounds and statistics against the source. Without raw bytes it validates
the contract internally; it does not claim to resolve/verify an external asset.
Historical fixture byte digest matches the current checkout:
`3f1901a7b132111752c35b4b62fba5cf1bee57a2811f28930199a420088d3e1a`.
Canonical identity also permits Git line-ending changes without relabelling evidence;
canonical JSON digest is `9dc550b1227b7854cbf91ee2c1b9ca8b7cb3b437fca3ffc7252e681edc438624`.
This is a design projection of retained historical evidence, not a new Qollab trial.

`CompletedResult` stores immutable bytes; dictionaries and manifests are fresh
copies. `to_manifest(completed_result)` returns both Alice flute/melody and Bob
cello/bass together using existing InputNote/PartSpec/Manifest. Both policies retain
16 rounds and 32 events including rests in the envelope; sounding notes alone enter
the manifest. String source metadata carries run/checkpoint/source/sidecar hashes,
sidecar reference, active-note index to round ID map and source-ID to event-ID map.
It rejects conflicting caller metadata. No registry interface change, independent
voice generators, global result cache, seed-derived identity or resampling.

`raw_score` projects fixed local pitches/onsets/velocity to ticks directly and
supports completely silent raw results. Raw export does not invoke import_parts,
baseline arrangement or orchestrate. The source maps also match import_parts IDs:
`alice:nN` / `bob:nN`; 0.4 quarter-note beats becomes 192 ticks at PPQ 480.

`arrange_result` is an explicit optional rules call on copied PartSpecs with
render_audio=False. Its default creative plan is C major, C/F/G/C, with configurable
Python key/chords and actual choices recorded in the pipeline report. It returns
mode=arranged, output parts, per-note transformation IDs and original event/round/run
and source-ID lineage, including muted notes. Raw rounds/events/counts/model/source
hashes remain unchanged. Silent lead and arrangement exceptions produce failed,
redacted structured errors and no hidden fallback. A failed execution envelope with
no successful counts/events is rejected by playback/manifest conversion.

Validation rejects contradictory round/event IDs, cue/output/ba/win/strategy data,
local mapping, noninteger counts, named settings, shot allocation, scientific
summaries, metadata and result labels. QCBM shots and the 16-round musical excerpt
remain excluded from the full-count CHSH denominator. Replays make zero submissions.
There is no claim of musical quality, hardware certification or quantum speedup.

## Verification log

All times below are actual 2026-10-10 BST unless shown as UTC. Python 3.13.5,
Qiskit 2.5.2, NumPy 2.5.3, music21 9.9.2, pydantic 2.14.0, mido 1.3.3,
pytest 9.1.1; Node 16.13.2. Installed both projects editable in `.venv-worker`.

| Time | Command/check | Result and scope |
|---|---|---|
| Before implementation tests | `python -m venv .venv-worker`; initial uv install | Failed: sandbox ensurepip/cache access, then restricted DNS to pypi.org. Retained local environment; set local ignored TEMP/UV cache and installed declared dependencies with approved network access. No dependency/config edits. |
| Finished 16:49:03 | `.venv-worker/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests --basetemp .test-b-before` | 32 passed in 50.85s; existing suite before adding adapter tests. SDK tests intercept HTTP. |
| Started 16:49:49 | Adapter first acceptance pass | 29 passed, 2 failed in 8.30s: unrestricted key inference generated Bb, rejected by music21. Diagnosed existing orchestrator/theory.py; no cross-owner edit. Explicit C major/C-F-G-C creative plan selected and documented. |
| Before 16:51:41 | Adapter second pass | 31 passed in 9.15s after explicit creative plan. |
| 16:51:41–16:52:11 | Full suite, `.test-b-full` | 63 passed in 27.60s after adding experiment/source checks. |
| 16:53:53–16:54:16 | `.venv-worker/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests --basetemp .test-b-final` | 70 passed in 20.23s: 32 existing + 38 adapter cases. Includes zero-submission fixture conversion, one actual local BasicSimulator call for paired voices, repeated conversions, output-driven pitch/onset change, exact ticks, rests, source identity, immutable raw bytes after arrangement, distinct labels, silent/error handling, source conflict rejection and failed execution rejection. |
| 16:56:07–16:56:08 | Final fresh build `--out components/quantum_duet/build/worker-b-final` | Passed; ZIP SHA-256 `64d50854b35ad184a19a1730aaf75c5594ecac19e3bcf7009cde5eb083c05c95`. Further velocity/source review below supersedes this intermediate build. |
| 16:57:09–16:57:35 | `.venv-worker/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests --basetemp .test-b-reviewed` | **71 passed in 23.61s: 32 existing + 39 adapter cases.** Final reviewed source includes rejection of velocity changes against immutable raw bytes. |
| 16:57:35 | `python components/quantum_duet/tools/build_qollab.py --out components/quantum_duet/build/worker-b-reviewed` | Passed with final source; ZIP SHA-256 `2a35faad52ec6ab75bac4e0b5d6c1aa16f99944ff503f827150620307fe816d2`. Ignored, uncommitted, not published or platform-tested. |
| 16:57:29 | `git diff --exit-code HANDOFF_SHA -- .`; `git status --short` | All tracked handoff files unchanged; only four new allowed files. Checkpoints, raw evidence, scientific reports, shared schema and other worker sources are identical to handoff. |
| 16:52:27–16:52:37 | `python -m orchestrator --generation-manifest examples/generation.json --backend rules --bars 4 --no-audio --out output-b-registry` and `--manifest examples/note_events.json ... --out output-b-events` | Both passed. Original generated/event input CLIs, provider disabled, audio not_requested, MIDI/JSON/report exports. |
| 15:52:27.715Z (16:52 BST) | `node components/quantum_duet/tests/ui_checks.mjs` | Passed. Node fake AudioContext races/repeat/Stop/mute/immutable shots and MIDI headers. **Mocked UI check, not browser verification.** |
| 16:52:27–16:52:37 | Frozen module demo below and `.venv-worker/Scripts/python.exe -m quantum_duet --shots 16 --out output-b-original/take.json` | Both passed. Module replay recorded historical run, zero backend submissions, raw/arranged MIDI + contract/manifest. Original CLI one local BasicSimulator batch, no native audio. |
| 16:52:27–16:52:28 | `python components/quantum_duet/tools/build_qollab.py --out components/quantum_duet/build/worker-b-check` | Passed, fresh ignored upload/ZIP. Later final build repeated after final source changes; no platform execution. |

Frozen fixture demo command (output path must be fresh):

```powershell
.venv-worker/Scripts/python.exe -m quantum_duet.orchestration_adapter --result docs/team/fixtures/run-result.v1.json --out output-b-duet --arrange
```

Serialized outputs are in ignored `output-b-duet/`: `raw-result.json` matches the
shared fixture's content; `manifest.json`, `raw.mid`, `arranged-result.json` and
`arranged.mid` are separate. Run ID is
`qm3b-qollab-f788ed00-3823-4ae3-ab34-0131a4e7c744`. C should consume the arranged
envelope's `arranged.output_parts` and `arranged.lineage` for optional arranged
music while keeping top-level events/rounds/statistics as immutable raw evidence.
No source changes or messages were sent to Worker C.

## Remaining problems / coordinator dependencies

1. Existing unrestricted arranger key inference can emit flat spellings such as
   Bb that music21 9.9.2 rejects. Proposed owner fix: review
   `orchestrator/theory.py:_diatonic_chords` flat-root formatting (currently replaces
   `-` with `b`) against music21's accepted chord notation; add owner regression
   coverage. B uses an explicit documented creative plan and does not edit that file.
2. The new adapter requires both installed projects, as shown in the example. The
   Qollab builder copies the new module but currently does not package root
   orchestrator dependencies/sources. Coordinator must decide packaging/inclusion
   before platform adapter use; the existing inference entrypoint is unchanged.
3. Coordinator/C owns production UI hookup and final integration; the frozen
   contract is ready for consumption without changing the shared fixture. Root CLI
   entrypoint/dependency updates, if wanted, remain coordinator work.
4. Browser, Qollab/Pyodide, IonQ, physical hardware, Gemini and native audio were
   **not executed** by B. Historical counts are explicitly recorded, not live results
   of this worker. A owns provider validation. No paid call, retraining, held-out
   motif access, weight edit, credential access, merge, publication or submission.

The recorded arrangement exports contain 2 output parts and 30 lineage entries;
30 notes receive central arrangement changes (including dynamics). Original model
metadata and raw evidence are unchanged. Final source passes all checks above.
The post-stage diff/allowlist audit and clean post-commit status are reported with
the commit/PR handoff.
