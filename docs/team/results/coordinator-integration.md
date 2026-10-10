# Executed coordinator integration review — 2026-10-10

Verdict: approve the three worker changes together with the coordinator seam,
subject to human merge approval. The combined local application works. No PR/main
merge, worker-worktree modification, remote push, publication or submission occurred.

## Verified revisions and ownership

GitHub was read and Git fetched before combining the work. Main was
`bff4c0e0ff1d67f73503724b5d3e303eaf696103`; handoff
`3eb26f205f9b68c9e7f01cff9ca26f74315882a1` has the same source tree.

| Worker | Verified head | Verdict |
|---|---|---|
| A / PR3 | 6cf2c4e1de980dd4d0cd73e21d9c3288ee11b25f | Safe backend hardening; single free IonQ acceptance documented, batch success unverified |
| B / PR2 | 71827c37b51172df6b7a7c728ef1551ee4f7f61a | Approved paired immutable adapter; explicit creative rules plan |
| C / PR4 | bf46780f77a65340c3d6fbe0cdaebed0db446ccc | Approved with coordinator projection/failure/fixture seam below |

All changed paths match their exact prompt allowlists (A11, B4, C9). There are no
cross-worker file collisions. A retains generate_take/probe APIs, rejects ambiguous
results and propagates errors without backend replacement. B is additive. C retains
the original Python bridge, raw local mapping and playback/export controls.
Checkpoint/data/evidence files, root orchestrator code, AGENTS.md, shared raw contract
and frozen fixture are unchanged from main. No new model, training or scientific
claim change. No held-out material, paid API, physical QPU or native audio used.

Isolated branch: `codex/duet-integration-review-20261010`, based on fetched main.
Worktree: `build/coordinator-integration-20261010` in the coordinator workspace.
A's two commits and B/C commits were locally cherry-picked onto this branch;
their original branches and main were untouched. Coordinator changes are a separate
local commit atop those four worker commits, for later reviewed integration.

## Newly executed checks, separate from worker reports

Local environment: Python3.12.14, Qiskit2.5.2, NumPy2.5.3, qiskit-ionq1.0.2,
music21 9.9.2, pydantic2.14.0, mido1.3.3, pytest9.1.1, Node16.13.2.
The IonQ SDK matches A's observed SDK; this CPython environment is not Pyodide.
All times are UTC; London was UTC+1.

| New verification | Actual result |
|---|---|
| Worker-only combined Python suite | 119 passed, no skips, 50.34s |
| Final integrated full Python suite, completed by16:50:28 | **133 passed, no skips, 25.73s**: common32 + A48 + B39 + coordinator14 |
| Original Node audio/MIDI command | Passed17:01:34.738Z; mocked AudioContext races, repeat, Stop, mutes |
| C Node contract command | Passed17:01:34.929Z; schema, MIDI parser, paired identity, single-request lifecycle |
| Coordinator Node projection command | Passed17:01:40.457Z; real B quantum/classical rules outputs, strict hashes/lineage/ticks, unchanged raw, export reimport, failed-policy isolation, DOM transport/evidence-replacement errors, no jobs |
| Existing generation-manifest and note-event orchestration CLIs | Both passed, rules/provider disabled, --no-audio |
| B frozen fixture CLI, both policies | Both passed; each creates separate raw.mid and arranged.mid, zero submissions |
| Original Quantum Duet CLI | Passed, one local BasicSimulator batch, 16 shots/circuit |
| Independent Mido parsing of8 MIDI files | Passed: both policies/raw-arranged/CLI-browser, exact pitches/ticks/velocities, PPQ480; program distinction documented below |
| Generated upload verification | Passed: hashes, ZIP entries/bytes, unchanged fixture/source, requirements and all generated Python namespace imports |
| Generated namespace LOCAL probe | 32 shots,00:16/11:16, one call, job044f1cef-08e8-43d9-bcf3-51509c298379 (16:50:39.54Z) |
| Generated namespace LOCAL five-live | One call,128 CHSH shots, job4bd06d95-1973-476f-ba07-bbc50d3c657c; QCBM excluded from CHSH denominator |
| Local HTTP four-recorded + pure arrangement | Passed; one execution,64 CHSH shots, job5272a083-f7f8-4b09-b018-ef4ac9f1289d; actual melody reference data/recorded_melody.json |
| Real Chrome,16:36–16:54Z | RECORDED raw and both arranged policies; repeat/Stop/keyboard/mutes/90BPM; JSON and MIDI visible payloads; failed quantum arrangement keeps RAW enabled and successful classical arrangement selectable |
| Real Chrome live route | Five-live,16 shots/circuit/64 CHSH shots, one job; run ID assigned before execution; Generate remains disabled |
| 375x812 responsive check | scrollWidth=clientWidth=360; no horizontal overflow; viewport reset |
| Offline four-qubit assessment | Analytical/statevector/bit-order/SDK serialization checks passed; local4096-shot allocation1056/1001/1038/1001; no remote job |

Browser scheduling checks do not establish subjective audio quality or physical
speaker output. The final screenshot is ignored `output-integration/browser-final.png`.
Remote evidence below was supplied by A, not newly executed by the coordinator.

Initial coordinator failures were corrected and checks repeated: a negative test
indexed the policy dictionary incorrectly; text edits needed UTF-8/LF normalization;
the new provenance label initially read B/C metadata from the wrong container;
loopback HTTP required the authorized sandbox escalation. The independent MIDI
instrument assertion exposed an existing root section profile, not corrupt notes.
The unrestricted arranger failure below remains deliberately unfixed.

## Explicit browser boundary and resolved blockers

Original qm.run-result.v1 is unchanged. B's mode=arranged envelopes still contain
raw events, one selected policy, output_parts/lineage and backend_requested/actual.
C's earlier optional projection expected both event policies and reversed backend
field names, and rejected every failed envelope containing events. These were
integration blockers; they are resolved in the coordinator code.

`browser_projection.project(raw_bytes, outcomes, raw_source_bytes=...)` validates
both separate B outcomes and returns **qm.browser-playback.v1**, never raw evidence.
It validates exact original/source SHA256, canonical envelope identity, unchanged
raw fields, policy/backend/fallback metadata, source IDs, run/round/event identities,
one-to-one note lineage, integer MIDI ticks, transform coverage and four-bar bounds.
Quarter-note beats are onset_tick/ppq and duration_ticks/ppq (192ticks=0.4beats).
Muted notes remain silent events with null pitch and lineage. Original rests are
explicit events retaining timing/identity. Each policy retains32 events.

The export container has raw_envelope_text, unchanged run_result, raw_source_text
when available, separate playback_projection and separate export_view. Neither B's
raw schema nor output is silently renamed. The sidecar deliberately translates
backend_requested/backend_actual to requested_backend/actual_backend. It retains
the actual creative plan from B's report rather than inventing its harmony.

Failed policies contain explicit errors and zero arranged events. RAW remains valid;
each successful policy remains independently available. Unknown/invalid projections
disable creative playback and report errors without invalidating valid raw music.
Failed execution envelopes still disable playback. Browser raw validation also now
rejects changed canonical event IDs/pitches/timings against the original local mapping.

The browser also rejects an arrangement response that changes either exact raw text
or exact supplied source text before installing it. A failed transport or such
a contradiction leaves the previous playable raw result and export intact.

The existing local server assigns a UUID before its one generate_take invocation,
then uses B's pure conversion. `/api/arrange` receives that completed raw snapshot;
it never calls inference. Both policies use the same documented default C-major/
C-F-G-C creative plan. The existing page gains one optional local rules button.
Playback controls/lanes are preserved. Conversion, arrangement and replay tests
forbid BasicSimulator.run/generate_take; no additional quantum submissions occur.

## Coordinator-owned integration files

Only these17 canonical paths change in the coordinator commit; worker commits
remain separate and no A/B implementation was rewritten:

```text
components/quantum_duet/src/quantum_duet/browser_projection.py
components/quantum_duet/src/quantum_duet/recorded_fixture.py
components/quantum_duet/web/playback-projection.mjs
components/quantum_duet/web/run-contract.mjs
components/quantum_duet/web/ui.mjs
components/quantum_duet/web/main.js
components/quantum_duet/web/index.html
components/quantum_duet/dev/main.mjs
components/quantum_duet/dev/server.py
components/quantum_duet/tools/build_qollab.py
components/quantum_duet/DEPLOYMENT_NOTES.md
tests/test_duet_browser_integration.py
tests/duet_projection_checks.mjs
scripts/verify_duet_build.py
scripts/assess_duet_cue_circuit.py
docs/team/results/coordinator-integration.md
docs/team/followups/cue-circuit.md
```

## Packaging strategy and remaining findings

| Classification | Finding / disposition |
|---|---|
| Blocking integration, resolved | B/C policy, event, backend-name and failed-envelope mismatches; explicit sidecar plus focused tests implemented |
| Blocking integration, resolved | Qollab recorded fixture absent; unchanged raw/source files plus literal-path asynchronous Python loader included |
| Blocking publication, open | Fresh canonical Qollab upload/runtime/recorded replay/built-in duet/export checks have not run; do before separate publication approval |
| Blocking free IonQ duet claim, open | Four/five-circuit batch path unresolved; no supported proxy schema/accepted batch evidence |
| Nonblocking, explicit boundary | Full orchestrator's music21/pydantic/native dependencies unverified in actual Pyodide; creative feature runs locally and optional modules excluded from platform build |
| Follow-up | Existing flat-chord inference produces Bb rejected by music21; re-reproduced exactly, no root theory correction made; explicit C/F/G/C plan is documented |
| Nonblocking musical export distinction | Root cello section profile uses GM program48 (strings ensemble); browser cello uses41. All notes/timing/velocity match. Root profile retained, not silently corrected |
| Follow-up | Four-qubit cue proposal is promising offline only; see ../followups/cue-circuit.md |
| Follow-up | Native platform toolbar downloads and subjective/native audio remain unverified; visible lossless payload export retained |

Qollab raw generation deliberately retains the already working legacy supplied-
backend API. Platform live output therefore retains its legacy identity labels;
the fully paired live envelope conversion currently runs locally, where both
packages are installed. Recorded shared-envelope replay and imported local creative
sidecars work without orchestration dependencies. Platform live envelope conversion
is a later optional dependency-free seam, not required for the raw demonstration.

Qollab docs freshly read in Chrome: https://qollab.xyz/learn/docs/runtime-environment .
They allow100 files/2MB each; Python loads literal project-relative data paths;
JavaScript cannot fetch project data directly; compiled Python dependencies need
WebAssembly builds; IonQ allows one job per Run. The build enforces project limits,
ships only Qiskit2.5.2/NumPy>=2.1,<3 requirements, and excludes local creative modules.
The accepted candidate has25 files (~206KB), largest64738bytes. Account-wide200MB
capacity and actual Pyodide loading still need private upload verification.
Generated builds/manifests/ZIPs remain ignored. Final candidate/checksum is supplied
in the coordinator's final response; earlier intermediate build hashes are superseded.

## Latest IonQ evidence and scientific boundaries

A reports actual separate32-shot single-object jobs on2026-10-10:

| Free selection | UTC | Actual accepted job | Counts |
|---|---|---|---|
| Qollab built-in | 16:11:49.998–16:11:50.146 | 30b5a853-75b9-4c91-b94c-53403f612fed | 00:25,11:7 |
| IonQ Aria1 simulator | 16:12:38.228–16:12:54.141 | 01a12696-88b0-73ab-ba43-b919b1180b11 | 00:18,11:14 |

IonQ observed Python3.14.2/Qiskit2.5.2/qiskit-ionq1.0.2/NumPy2.4.6;
accepted ionq.circuit.v1. Each execution accepted one job. This was the standalone
fixture, not the final canonical package. The historical multi-circuit HTTP400
remains; no full IonQ duet fix is claimed. A's hardening is safe to integrate because
it makes unsupported execution explicit and preserves the local simulator.

The new offline four-qubit proposal preserves ideal conditional probabilities but
uses random unequal cue allocation and centralized coherent controls. It is not a
drop-in v1 result, noise-equivalence proof or loophole-free Bell experiment. No
production IonQ execution path was added. See the narrow follow-up for equations,
actual allocation, correct conditional uncertainty and separately authorized trials.

## Reproduction and merge acceptance

Run from the isolated integration worktree (fresh output paths for every build):

```powershell
uv venv .venv-review
uv pip install --python .venv-review/Scripts/python.exe -e '.[dev]' -e './components/quantum_duet[dev]' 'qiskit-ionq==1.0.2'
.venv-review/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests --basetemp .test-accept
node components/quantum_duet/tests/ui_checks.mjs
node components/quantum_duet/tests/ui_c/contract_checks.mjs
node tests/duet_projection_checks.mjs .venv-review/Scripts/python.exe
.venv-review/Scripts/python.exe -m orchestrator --generation-manifest examples/generation.json --backend rules --bars 4 --no-audio --out output-accept/generation
.venv-review/Scripts/python.exe -m orchestrator --manifest examples/note_events.json --backend rules --bars 4 --no-audio --out output-accept/events
.venv-review/Scripts/python.exe -m quantum_duet.orchestration_adapter --result docs/team/fixtures/run-result.v1.json --policy quantum --arrange --out output-accept/quantum
.venv-review/Scripts/python.exe -m quantum_duet.orchestration_adapter --result docs/team/fixtures/run-result.v1.json --policy classical --arrange --out output-accept/classical
.venv-review/Scripts/python.exe -m quantum_duet.browser_projection --result docs/team/fixtures/run-result.v1.json --raw-source components/quantum_duet/tests/fixtures/qollab-local-run.json --out output-accept/playback.json
.venv-review/Scripts/python.exe -m quantum_duet --shots 16 --out output-accept/live.json
.venv-review/Scripts/python.exe components/quantum_duet/tools/build_qollab.py --out components/quantum_duet/build/accept
.venv-review/Scripts/python.exe -I scripts/verify_duet_build.py components/quantum_duet/build/accept
.venv-review/Scripts/python.exe scripts/assess_duet_cue_circuit.py
.venv-review/Scripts/python.exe components/quantum_duet/dev/server.py --port 8780
```

The assessment script is OFFLINE only and not imported by any production executor.
The server is loopback local CPython, not a platform compatibility test. Frozen
source byte hashes are preserved; generated arrangement report timestamps vary.

After human approval: re-fetch/recheck heads/main, merge PR3 then PR2 then PR4,
then apply the single coordinator integration commit. PRs are mechanically
independent and mergeable, with disjoint files; B's optional feature requires the
root package and C's complete creative/fixture behavior requires this integration.
Do not cherry-pick the duplicated worker commits after the actual PR merges.

Acceptance checklist:

- [x] Exact PR heads/current main verified; clean isolated combination.
- [x] All133 Python tests and all3 Node commands pass without skipped SDK checks.
- [x] Both existing CLIs and both raw/arranged policy MIDI exports pass.
- [x] Exact raw/source bytes, hashes, pairing, rests/mutes and source lineage retained.
- [x] RAW/ARRANGED and RECORDED/LIVE are distinct; arrangement/playback add no jobs.
- [x] Failed arrangement retains raw and independent successful-policy playback.
- [x] Root checkpoints/scientific evidence/contract unchanged; no provider fallback.
- [x] Minimal raw Qollab build, fixture loader, hashes, file limits and local generated namespace verified.
- [ ] Human approval, actual worker PR merges and coordinator commit integration.
- [ ] Repeat full suite/Node/build checks on merged main.
- [ ] Private canonical Qollab recorded/built-in playback and lossless export verification.
- [ ] Separate publication authorization; no IonQ duet claim until a real supported job succeeds.

Shortest path to public demonstration: approve the reviewed merges and seam, run
post-merge checks, privately test the minimal Qollab build on built-in simulator
with recorded fallback, then obtain publication approval. Full orchestration remains
a separate working local creative feature. IonQ research need not block that demo.
Remaining integration complexity is low; platform verification is medium/uncertain.
