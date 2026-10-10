# Worker A — Qollab/IonQ compatibility (highest priority)

Objective: establish the exact failing boundary and a supported fix, or a precise
platform-maintainer reproduction. First reproduce through ACTUAL Qollab with the
smallest single two-qubit circuit using its passed backend (probe.py, 32 shots).
Historical evidence shows only four/five-circuit IonQ failures, NOT single-circuit.
Do not assume count caused it or that backend.run extra kwargs control HTTP JSON.

Read first: components/quantum_duet/src/quantum_duet/probe.py, duet_quantum.py
(run_batch/setting_batch), integration.py (backend_limits/generate_take), web/main.js,
evidence/platform-history.json and DEPLOYMENT_NOTES.md. Inspect actual backend
identity/free simulator selection and installed Python/Qiskit/qiskit-ionq versions,
SDK serialization, endpoint/API version and platform proxy before choosing a fix.
Official references (read fresh, browser if web reader fails):
https://docs.ionq.com/api-reference/v0.4/migration-from-v0.3
https://qollab.xyz/learn/docs/runtime-environment
https://qollab.xyz/learn/docs/js-qiskit-projects
https://qiskit-community.github.io/qiskit-ionq/_modules/qiskit_ionq/helpers.html
Retain only redacted request schemas/trace boundaries; no cookies, tokens or keys.

Exact allowed writes:
- components/quantum_duet/src/quantum_duet/probe.py
- components/quantum_duet/src/quantum_duet/duet_quantum.py
- components/quantum_duet/src/quantum_duet/integration.py
- components/quantum_duet/tests/backend_a/ (new tests/fixtures only)
- docs/team/results/worker-a.md (new report)
Outside scope: web/dev/UI, adapter, shared contract/config/lockfiles, model/circuit/
mapping changes, multi-job bypasses, replacement provider or local substitution.
Preserve existing generate_take bridge signature and raw take; schema changes require
coordinator. If supported code cannot fix platform-controlled rejection, create the
minimal reproduction/report; do not claim app fix or fabricate accepted counts.

Acceptance: smallest actual free IonQ test FIRST, then supported four/five path only
when justified; one supplied-backend submit, result names/bit order/integer allocations
validated, errors propagated, no retries/new paid jobs. Distinguish local regressions,
mocked serialization checks, actual Qollab built-in run, actual free IonQ run. Record
job ID/32-shot counts or explicit rejection with versions/API path; mark blocked if
platform permission/runtime missing. Mock is never proof of real remote success.
Exact checks after adding backend tests:
```powershell
.venv-worker/Scripts/python.exe -m pytest -q components/quantum_duet/tests/backend_a components/quantum_duet/tests --basetemp .test-a
```
Also run the common full suite/Node commands. Actual bridge steps are manual browser:
select FREE built-in, run separate probe; select FREE IonQ simulator, run separate
single probe; record backend/run/logs; never select hardware. The current account's
private draft may be used only with established user access/authorization; if missing,
finish a reviewable probe and report exact manual step without requesting credentials.
B/C proceed on the frozen fixture and do not wait for your diagnosis. Do not edit their
files. Maintainer report is an artifact, not permission to send it.

Repository: https://github.com/FyodorAmanov1/OxfordQ.git. This is a separate worker
session, not permission to start other agents. First read AGENTS.md and docs/team/
README.md, repository-map.md, run-contract.md, verification.md and the role prompt.
Use a new clean clone/worktree; never overwrite a dirty/unrelated checkout.

The starting revision is the immutable FINAL PLANNING COMMIT containing all three
prompts. Determine it from the prompt path, not whichever tip happens to be latest:
```powershell
git clone --no-checkout https://github.com/FyodorAmanov1/OxfordQ.git OxfordQ-worker-a
Set-Location OxfordQ-worker-a
git fetch origin
$handoffSha = git log -1 --format=%H origin/codex/import-quantum-duet -- docs/team/prompts/worker-a.md
$bSha = git log -1 --format=%H origin/codex/import-quantum-duet -- docs/team/prompts/worker-b.md
$cSha = git log -1 --format=%H origin/codex/import-quantum-duet -- docs/team/prompts/worker-c.md
if (-not $handoffSha -or $handoffSha -ne $bSha -or $handoffSha -ne $cSha) { throw 'Handoff mismatch: stop and obtain coordinator SHA' }
git cat-file -e "$handoffSha^{commit}"
git merge-base --is-ancestor $handoffSha origin/codex/import-quantum-duet
if ($LASTEXITCODE -ne 0) { throw 'Handoff absent from import branch' }
git switch -c codex/duet-backend-20261010 $handoffSha
git rev-parse HEAD
```
Confirm HEAD equals the printed handoff SHA and report it. If a coordinator gave an
explicit SHA, require equality; if prompt history changes after handoff, stop for a
new pin rather than guessing. Use unique branch suffix if branch already exists;
do not overwrite it. Fresh Python >=3.11 and Node >=16:
```powershell
python -m venv .venv-worker
uv pip install --python .venv-worker/Scripts/python.exe '.[dev]' './components/quantum_duet[dev]'
.venv-worker/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests --basetemp .test-worker
node components/quantum_duet/tests/ui_checks.mjs
```
If uv absent, use that venv's `python -m pip install` with the same arguments.
Shared fixture docs/team/fixtures/run-result.v1.json is RECORDED historical built-in
Qollab data; original take components/quantum_duet/tests/fixtures/qollab-local-run.json.
Models are src/quantum_duet/data inside the component. No held-out motifs, retraining,
changed weights/circuits/mapping, paid Gemini/hardware, provider credentials or
silent fallback. Raw events and shots remain immutable under playback/arrangement.
85.3553% exact coordination vs 75% local classical/100% central is not musical-quality
advantage or speedup; melody validation QCBM 1.8217789 loses classical 1.7114360.
FluidSynth is optional local tooling, not assumed on Qollab. Preserve visible export
and active Run lifecycle. Rebuild generated uploads with a FRESH output path:
`.venv-worker/Scripts/python.exe components/quantum_duet/tools/build_qollab.py --out components/quantum_duet/build/worker-a-check`.
Generated files are ignored and must not be committed. Only canonical source edits.

Coordinator owns root pyproject/config/locks, licences, contract/schema/fixtures,
packaging tools and imported checkpoints. No other-owner files. Necessary out-of-scope
change -> record exact proposed diff/dependency; do not edit unilaterally. Commit
only allowed reviewed files. Push your new branch and open a draft PR targeting
codex/import-quantum-duet (temporary stacked PR), not main; no merge/automerge.
Completion report: starting/current SHA, PR URL, exact changed paths, behavior and
contract mapping, commands/results/scopes/timestamps, remaining failures, provenance
limitations and coordinator dependencies. Publication/video/submission need explicit
human authorization. Do not send a maintainer message without explicit authorization.
