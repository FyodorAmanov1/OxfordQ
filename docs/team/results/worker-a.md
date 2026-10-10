# Worker A backend diagnosis and verification

Worker branch: `codex/duet-backend-20261010`. Initial checkout was clean and HEAD
equalled the human-supplied handoff `3eb26f205f9b68c9e7f01cff9ca26f74315882a1`.
Existing worktree retained; no clone, rebase, merge or other worker session created.
User override targets the draft PR at `main`. Fetch at 2026-10-10 15:55:19 UTC
confirmed `origin/main` at `bff4c0e0ff1d67f73503724b5d3e303eaf696103`, the PR #1
merge, with the handoff as an ancestor. The delivery commit and PR link are supplied
in the chat/PR metadata (a commit cannot include its own SHA).

## Outcome and limits

The actual Qollab **single-circuit object path succeeds** on both visibly free
backends. A separate human-approved private scratch project was created at
[OxfordQ Worker A Private Bridge Probe](https://qollab.xyz/u/Floris/oxfordq-worker-a-private-bridg).
The original duet draft was unchanged and neither project was published. Each
execution used the supplied backend once, a named two-qubit H/CX/measurement
circuit object and exactly 32 shots. Labels, success flags, two-bit measurement
strings and integer totals were validated. Retained live observations are in
`components/quantum_duet/tests/backend_a/fixtures/qollab-single-probes.json`.

- Built-in: 16:11:49.998–16:11:50.146 UTC, job
  `30b5a853-75b9-4c91-b94c-53403f612fed`, counts `00:25,11:7`.
- Free IonQ Aria 1 simulator: 16:12:38.228–16:12:54.141 UTC, job
  `01a12696-88b0-73ab-ba43-b919b1180b11`, counts `00:18,11:14`.
  Actual runtime: Python 3.14.2, Qiskit 2.5.2, qiskit-ionq **1.0.2**, NumPy 2.4.6;
  backend `qiskit_ionq.ionq_backend.IonQSimulatorBackend`, name `ionq_simulator`.
  Sanitized actual SDK serialization: `type=ionq.circuit.v1`, `shots=32`,
  input keys `circuit,gateset,qubits`, width 2. Pyodide/Qollab distribution metadata
  was unavailable. Actual proxy/API routing is still unknown; no client credentials
  or headers were read. The SDK 1.0.2 default v0.4 URL is not proof of proxy routing.

Earlier browser binding failures (before 15:47:24 UTC) blocked the initial attempt;
a fresh authenticated Chrome tab recovered access after the first implementation
commit. ZIP upload then failed because Chrome file-URL access was disabled. Rather
than change browser permissions, the editor received a reviewed standalone Python
probe and JS `callPromising` entry under A's new test fixtures. This reproduces the
canonical probe's single circuit and validation without importing the full duet
package; it is **not** an actual deployment test of the canonical package.

No larger remote run was attempted: a supported multi-circuit schema has not been
confirmed, and historical four/five HTTP400 remains relevant. Both actual single
probes now precede any proposed larger remote test. No supported multi-circuit
app-level fix is claimed. The remaining boundary is list serialization/provider
or platform support, not a universal single-circuit failure. A precise maintainer
reproduction is ready below; it has not been sent.

## Changes (exact ownership scope)

- `components/quantum_duet/src/quantum_duet/probe.py`: preserve `probe(backend,
  shots=32)` dict/raising API; use preflight limits/hardware guards and shared strict
  measured-result validation. Transpile and submit a circuit object, not a list,
  exactly once. Add separate `probe_json` string bridge report with timestamps,
  Python/distribution versions, backend class/advertised limits, accepted job ID,
  failure stage and redacted errors. Failure has null result/no fabricated counts;
  preflight failure records zero submissions. Transport/platform/free-selection
  verification remains explicitly unknown/unverified. No arbitrary exception
  text, client, environment, token or headers are exported.
- `components/quantum_duet/src/quantum_duet/duet_quantum.py`: extract the existing
  named-result validation for reuse by the probe. Preserve batch options/shape and
  ordering by labels. Reject non-dictionary histograms and non-string count keys;
  preserve integer (including NumPy integer) allocations, measured ba bit order,
  result success/name checks and exact requested shot totals.
- `components/quantum_duet/src/quantum_duet/integration.py`: inspect the backend
  class ancestry for IonQ identity, so a platform subclass declared outside the
  provider module cannot bypass the existing physical/unknown-device guard.
- `components/quantum_duet/tests/backend_a/conftest.py`: source-only test import path.
- `components/quantum_duet/tests/backend_a/test_bridge.py`: 39 local/mocked cases.
- `components/quantum_duet/tests/backend_a/test_ionq_serialization.py`: 7 real-SDK,
  intercepted-HTTP checks; optional SDK missing means explicitly skipped module.
- `components/quantum_duet/tests/backend_a/test_scratch_probe.py`: two local checks
  for the separate reproduction's single submission/count validation and redacted
  failure with no retry or counts.
- `components/quantum_duet/tests/backend_a/fixtures/probe.py` and `main.js`: reviewed
  standalone private Qollab reproduction, pasted through the editor; production
  web files were not changed.
- `components/quantum_duet/tests/backend_a/fixtures/qollab-single-probes.json`:
  retained actual observations, selection, versions, IDs and counts; no credentials.
- `docs/team/results/worker-a.md`: this report and reproduction; no message sent.

`generate_take` signature/raw take schema is unchanged. No shared envelope/schema,
run/round IDs, model checkpoints, circuits, raw historical fixture, musical mapping,
scientific evidence or source lineage changed. No training, held-out motifs, paid
API/QPU execution, native audio, automatic fallback or extra app submission. Probe
diagnostics are separate from `qm.run-result.v1`, not a replacement take/envelope.

## SDK and transport findings

Public official references were freshly inspected on October 10, 2026:

- [IonQ v0.4 migration](https://docs.ionq.com/api-reference/v0.4/migration-from-v0.3)
  describes job-type and result-route changes, including `ionq.circuit.v1` and the
  probabilities result endpoint. It does not identify this platform's failure.
- [Qollab runtime](https://qollab.xyz/learn/docs/runtime-environment) and
  [JS/Qiskit bridge](https://qollab.xyz/learn/docs/js-qiskit-projects) were read via
  the in-app browser after the web reader returned Internal Error. They prescribe
  the supplied backend and asynchronous `callPromising` bridge, one IonQ job per
  code run, and passing all required circuits in one call. They do not document
  the private proxy's request schema or its installed IonQ SDK version.
- [Official provider serializer source](https://qiskit-community.github.io/qiskit-ionq/_modules/qiskit_ionq/helpers.html)
  and the installed **qiskit-ionq 1.1.1** source agree with the offline checks:
  a circuit object produces `type: ionq.circuit.v1` with `input.circuit`; a list
  produces `type: ionq.multi-circuit.v1` with named `input.circuits`, including a
  one-element list. Four settings produce width 2; five-live adds width 12.
  Ordinary passed arguments `type='ionq.circuit.v1'` do not change this selection.

The installed SDK's client serializes before POSTing to its configured base plus
`/jobs`. The offline HTTP tests configure the deliberately fictitious
`https://offline.invalid/v0.4/jobs`, intercept POST before any network operation,
and retain only URL/body schemas, never headers. Synthetic HTTP400 returns one
POST attempt and a propagated IonQAPIError. This verifies the local serialization
boundary, **not** the real Qollab SDK/API/proxy. The SDK itself has retries for
other retriable HTTP errors; this app adds no retry and does not modify SDK internals.

The historical rejection of multi-circuit requests is consistent with a job-type
compatibility issue, but this is still an inference. Circuit count alone is not
established as causal. Merely relabelling multi-circuit JSON or splitting it into
multiple jobs is not a verified supported fix and was not implemented.
Qollab's observed qiskit-ionq 1.0.2 was subsequently installed into an isolated,
ignored target directory. The same seven intercepted serialization/HTTP checks
passed (2.40s), with no network job/account creation. Its serializer has the same
object/list type selection; its default API base is `https://api.ionq.co/v0.4`.
Actual Qollab single-object serialization and simulator identity were verified as
above; actual API route/proxy boundary and supported list requests remain unknown.

## Newly executed verification

All listed times are **UTC, 2026-10-10** (Europe/London was UTC+1). Test results
below distinguish local/mocked checks from fresh actual Qollab execution evidence.

Environment: Python 3.13.5, Qiskit 2.5.2, NumPy 2.5.3, pytest 9.1.1,
qiskit-ionq 1.1.1; Node 16.13.2. `.venv-worker` was newly created. Initial
`python -m venv` ensurepip failed; uv installed the packages into that isolated
interpreter. Initial sandbox uv failed cache permissions, then restricted DNS;
approved escalation with a workspace-local cache succeeded. Root dependencies
and lock/config files were not edited. Final component was rebuilt/installed
noneditable from the final canonical source before full-suite/CLI verification.

| Scope / command | Time / result |
|---|---|
| Unchanged baseline: `.venv-worker/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests --basetemp .test-before-a` | Before source changes; 32 passed in 49.60s. Exact command timestamp not captured. |
| First added-check run: `... -m pytest -q components/quantum_duet/tests/backend_a --basetemp .test-a-first` | 38 passed, 7 failed in 8.31s. SDK test doubles lacked Qiskit Options and the correct error-response fields; fixtures corrected without weakening assertions. |
| Repaired added-check run: `... -m pytest -q components/quantum_duet/tests/backend_a --basetemp .test-a-repair` | 46 passed in 6.84s. |
| Assigned exact check: `.venv-worker/Scripts/python.exe -m pytest -q components/quantum_duet/tests/backend_a components/quantum_duet/tests --basetemp .test-a` | 15:53:45.522–15:53:58.452; 49 passed in 10.77s, including all 7 offline SDK checks, no skips. |
| Final common suite: `.venv-worker/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests --basetemp .test-worker` | 15:54:45.799–15:55:02.715; 78 passed in 14.18s, no skips. Existing isolated inference suite includes ten original cases. |
| `node components/quantum_duet/tests/ui_checks.mjs` | 15:53:56.181 passed; mocked AudioContext races/Stop/repeat/mutes, immutable take/shots and MIDI headers. No fresh interactive playback test. |
| `.venv-worker/Scripts/python.exe -m orchestrator --generation-manifest examples/generation.json --backend rules --bars 4 --no-audio --out output-worker-a-generators` | 15:54:45.859–15:54:53.014 command group; passed, provider disabled, audio not requested. |
| `.venv-worker/Scripts/python.exe -m orchestrator --manifest examples/note_events.json --backend rules --bars 4 --no-audio --out output-worker-a-events` | Same command group; passed with MIDI/JSON/reports, provider disabled, audio not requested. |
| `.venv-worker/Scripts/python.exe components/quantum_duet/tools/build_qollab.py --out components/quantum_duet/build/worker-a-check` | 15:54:28.953–15:54:29.786 passed; fresh ignored output, ZIP SHA256 `5aa45e6ba01eaaad0fdde768e20faad8b095aa5a515bfab5a93b63abe0293f5c`. |
| Installed local BasicSimulator `probe_json(...,32)` | 15:54:49.132–15:54:49.310; one submit, job `4667ad6e-e085-4631-88e7-1426f5a14542`, counts `11:21,00:11`. LOCAL ONLY. |
| Generated namespace local BasicSimulator `probe_json(...,32)` (build path prepended to sys.path) | 15:54:52.203–15:54:52.377; one submit, job `af5a6346-e005-4782-8fe5-2bc74b737044`, counts `11:16,00:16`. LOCAL ONLY. |
| Actual Qollab built-in single standalone probe | 16:11:49.998–16:11:50.146; completed, 32 shots, ID/counts above. Python 3.14.2/Qiskit 2.5.2/NumPy 2.4.6; IonQ distribution unavailable on this backend. |
| Actual free IonQ single standalone probe | 16:12:38.228–16:12:54.141; completed, 32 shots, ID/counts and SDK 1.0.2 above. No retry or fallback. |
| Actual remote four/five paths | Unexecuted: supported list schema not confirmed. Historical four/five HTTP400 unchanged. |
| Final assigned paths plus scratch tests (`--basetemp .test-a-final`) | Completed before 16:12:15 observation; 51 passed in 10.54s, no skips. Exact start/end not captured. |
| Repeated exact assigned command with `--basetemp .test-a` | 51 passed in 8.14s, no skips; after scratch additions, before final commit. Exact start/end not captured. |
| Final common suite plus scratch tests (`--basetemp .test-worker-final`) | Completed before 16:13:28 observation; 80 passed in 13.25s, no skips. Exact start/end not captured. |
| Final Node UI check | 16:13:28.844 passed; same mocked audio/MIDI scope. |
| SDK 1.0.2 serialization suite, isolated target on PYTHONPATH | 7 passed in 2.40s; intercepted synthetic HTTP, not a remote batch. |
| `git diff --check` / scope review | Passed; only allowlisted canonical paths. Generated outputs and environment excluded. |

Local/mocked tests cover invalid allocations and hardware before submit, unchanged
backend options, submission/result failure stages and accepted job retention,
redaction/no fallback, bad histograms/bit widths/fractional/negative/bool counts,
missing/duplicate/unknown/permuted labels, per-circuit failures, single object vs
four/five lists, 128 CHSH shots at 32 per setting, all 16 rounds/32 events per policy,
and unchanged checkpoint IDs. This evidence does not certify hardware, establish
musical quality, or show computational speedup. No CHSH replays are new trials.

## Manual platform reproduction and coordinator dependencies

1. Review the standalone reproduction in A's `tests/backend_a/fixtures/`.
   It has now run in the authorized private scratch project. To test the actual
   canonical package separately, the coordinator can prepare a generated upload
   with body-only `index.html` containing `<pre id="probe"></pre>` and this diagnostic
   `main.js` (production web changes are outside A's write ownership):

   ```javascript
   import * as diagnostic from 'quantum_duet.probe';
   const raw = String(await diagnostic.probe_json.callPromising(backend, 32));
   document.getElementById('probe').textContent = raw;
   console.log(raw);
   ```

2. Select the visibly **Free built-in simulator**, run this single probe once,
   and record selection, versions, diagnostic timestamp, job ID and integer counts
   or explicit failure stage. Stop. Do not run a duet in this same code run.
3. Select the visibly **Free IonQ simulator** (never hardware), start a separate
   code run, execute the same single probe once, and capture the same evidence.
   Keep credentials/headers/query strings out of retained logs. If rejected,
   stop: no app retries, extra jobs, backend changes or simulator substitution.
4. Only after a single accepted IonQ probe and confirmed supported batch schema,
   use a separate authorized run for the existing four/five path. Preserve named
   results and integer allocations; unknown representation stays an error.

Maintainer reproduction to review, **not sent**: single object versus named list
serialization differs as above in SDK 1.0.2 (actual runtime) and 1.1.1. The actual
single-object job succeeded at 32 shots; IDs/counts are retained above. Historical private platform batches
failed before an accepted ID with HTTP400 `Only job type ionq.circuit.v1 is supported`.
Qollab's public runtime asks for one job containing every needed circuit. Please
identify the proxy API version/path and supported single-job multi-circuit schema.
An app fix needs supported request/result handling and verified
integer named counts, rather than a forced type field or multiple jobs.

Coordinator owns any shared dependency pin (optional SDK 1.1.1 was installed only
for this offline investigation), diagnostic web entry/upload changes, proxy/vendor
compatibility decision, canonical-package platform verification and final B/C integration.
Standard declared dependencies run the local checks; the SDK module explicitly
skips if that optional investigation dependency is missing. No out-of-scope diff
was applied. Publication, maintainer contact, submission and merging remain human
actions. A supported actual four/five-circuit path and proxy routing are the remaining
unresolved compatibility limitations; the smallest free single-circuit acceptance
has been verified. No unsupported type override or multi-job workaround was added.
