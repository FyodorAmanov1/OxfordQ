# Worker C — integrated browser experience (priority 2)

Objective: reuse existing UI for explicit raw/arranged mode, provenance, paired playback
and export, starting with the shared recorded fixture while A/B work.
Read first: docs/team/run-contract.md/fixture, component web/ui.mjs (mountDuet,
DuetAudio,midiBytes/assertTake), index.html, main.js, main.css, dev/server.py/main.mjs,
tests/ui_checks.mjs and DEPLOYMENT_NOTES.md. Preserve useful existing controls/lanes.

Exact allowed writes:
- components/quantum_duet/web/index.html
- components/quantum_duet/web/main.js
- components/quantum_duet/web/main.css
- components/quantum_duet/web/ui.mjs
- components/quantum_duet/web/run-contract.mjs (new envelope UI helper only)
- components/quantum_duet/dev/server.py
- components/quantum_duet/dev/main.mjs
- components/quantum_duet/tests/ui_c/ (new Node/browser tests only)
- docs/team/results/worker-c.md (new report)
Outside scope: all backend/adapter/Python package/shared schema/checkpoint files,
existing inference/UI tests, root config/locks/build tools; no independently generated
deployment-copy edits. Keep supported Qollab Python bridge, active Run lifecycle and
original raw take compatible. A owns Python backend API; B owns conversion/arrangement.

Implement fixture-mode rendering now, visibly RECORDED Qollab built-in simulator
(zero new backend shots). Display actual backend/model/recorded-live-mock status,
paired run/round identity, shots and errors. Do not label pending arranged null as
available: show unavailable until supplied validated arranged output. Raw input events
remain direct local mapping; optional arranged output separately labelled with raw
source/transform provenance. Match quantum/classical voices, instruments/gain/tempo
and playback conditions. Play/Stop/repeat/mutes/tempo must reuse existing measurements.
JSON/MIDI exports preserve run/round and source identity; retain original raw envelope.
Never expose credentials, assume FluidSynth on Qollab, or replace free playback with
paid API. Keep visible JSON/base64/console envelope exports until supported downloads
are actually verified. Public/video/hackathon actions stay manual.

Acceptance: frozen fixture playable/exportable, raw/arranged/current/recorded labels
accurate, unknown schemas/errors visible, no extra backend calls on replay/switch,
raw provenance unchanged after arrangement display, no stacked audio/race restart,
equal comparator production, keyboard/narrow layout, valid MIDI timing/velocities.
Record real browser behavior separately from mocked AudioContext checks.
```powershell
node components/quantum_duet/tests/ui_checks.mjs
node components/quantum_duet/tests/ui_c/contract_checks.mjs
.venv-worker/Scripts/python.exe components/quantum_duet/dev/server.py --port 8767
```
Use browser at http://127.0.0.1:8767; inspect controls, replay/mutes, recorded status,
raw JSON/MIDI payloads and 375px layout. Local HTTP is not Qollab bridge verification.
Add test entry contract_checks.mjs at the exact command above. B's real arranged
output hookup waits for coordinator integration; use contract fixture/errors meanwhile.
Qollab fixture inclusion/build changes outside current tool need a coordinator request,
not browser fetch to unsupported private files. Preserve working live legacy route.

Repository: https://github.com/FyodorAmanov1/OxfordQ.git. This is a separate worker
session, not permission to start other agents. First read AGENTS.md and docs/team/
README.md, repository-map.md, run-contract.md, verification.md and the role prompt.
Use a new clean clone/worktree; never overwrite a dirty/unrelated checkout.

The starting revision is the immutable FINAL PLANNING COMMIT containing all three
prompts. Determine it from the prompt path, not whichever tip happens to be latest:
```powershell
git clone --no-checkout https://github.com/FyodorAmanov1/OxfordQ.git OxfordQ-worker-c
Set-Location OxfordQ-worker-c
git fetch origin
$handoffSha = git log -1 --format=%H origin/codex/import-quantum-duet -- docs/team/prompts/worker-a.md
$bSha = git log -1 --format=%H origin/codex/import-quantum-duet -- docs/team/prompts/worker-b.md
$cSha = git log -1 --format=%H origin/codex/import-quantum-duet -- docs/team/prompts/worker-c.md
if (-not $handoffSha -or $handoffSha -ne $bSha -or $handoffSha -ne $cSha) { throw 'Handoff mismatch: stop and obtain coordinator SHA' }
git cat-file -e "$handoffSha^{commit}"
git merge-base --is-ancestor $handoffSha origin/codex/import-quantum-duet
if ($LASTEXITCODE -ne 0) { throw 'Handoff absent from import branch' }
git switch -c codex/duet-interface-20261010 $handoffSha
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
`.venv-worker/Scripts/python.exe components/quantum_duet/tools/build_qollab.py --out components/quantum_duet/build/worker-c-check`.
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
