# Worker B — paired orchestration adapter and provenance (priority 2)

Objective: connect one completed paired result to the existing orchestrator without
resampling either voice; raw replay stays independent of creative arrangement.
Read first: docs/team/run-contract.md and fixture; orchestrator/generation.py
(GenerationRegistry.generate_parts/orchestrate_generated), models.py, midi_io.py,
pipeline.py, baseline.py, validation.py; component integration.py/music.py as read-only.

Exact allowed writes:
- components/quantum_duet/src/quantum_duet/orchestration_adapter.py (new module/CLI)
- components/quantum_duet/tests/adapter_b/ (new tests only)
- examples/duet_integration/ (new examples only, no generated outputs)
- docs/team/results/worker-b.md (new report)
Outside scope: all existing orchestrator implementation/tests, backend files, browser,
dev server, root config/dependencies, shared fixture/schema, cli.py, build tools,
checkpoints. Do not change GenerationRegistry's interface. Missing root entrypoint or
dependency change is coordinator work; new module CLI can run with python -m.

Implement a pure raw-take -> contract conversion and to_manifest(completed_result),
returning both parts using existing InputNote/PartSpec/Manifest. Caller executes once;
conversion never executes. If registry adapters needed, both explicitly receive the
same immutable previously computed result; no globals or cache keyed only by seed.
Preserve all 16 rounds/32 events, rests in sidecar, timing/velocity, paired IDs,
model/backend/provenance/errors. Both voices refer to identical run/round IDs. Reject
contradictory metadata. Source strings carry IDs/hashes; keep rich immutable sidecar
and active-note-to-round map for source IDs assigned by midi_io.import_parts.
Raw mode bypasses arrange_baseline/orchestrate. Optional arranged mode uses copies and
rules/render_audio=False; retains raw source/hash and output transformation lineage,
reports silent-lead/other errors. No paid Gemini dependency or false raw labelling.

Acceptance tests: both voices request <=1 actual execution (zero for fixture conversion),
quantum a/b actually change InputNote pitches/onsets as fixed mapping; identical
run/round IDs and rest retention; exact quarter-beat conversion; raw evidence unchanged
after rules arrangement; distinct raw/arranged labels; failure without hidden fallback;
original CLI works. Work starts immediately from recorded fixture, independent of A.
C consumes same schema while you work; coordinate final serialized output via report,
not edits to C files or shared schema.
```powershell
.venv-worker/Scripts/python.exe -m pytest -q components/quantum_duet/tests/adapter_b tests components/quantum_duet/tests --basetemp .test-b
.venv-worker/Scripts/python.exe -m orchestrator --generation-manifest examples/generation.json --backend rules --bars 4 --no-audio --out output-b-registry
.venv-worker/Scripts/python.exe -m orchestrator --manifest examples/note_events.json --backend rules --bars 4 --no-audio --out output-b-events
```
Provide module CLI usage and run its frozen-fixture demo in your report. Do not route
through raw MIDI if it loses rest/round lineage. Do not turn arrangement quality into
a CHSH or QCBM advantage claim. No actual platform job needed for acceptance here.

Repository: https://github.com/FyodorAmanov1/OxfordQ.git. This is a separate worker
session, not permission to start other agents. First read AGENTS.md and docs/team/
README.md, repository-map.md, run-contract.md, verification.md and the role prompt.
Use a new clean clone/worktree; never overwrite a dirty/unrelated checkout.

The starting revision is the immutable FINAL PLANNING COMMIT containing all three
prompts. Determine it from the prompt path, not whichever tip happens to be latest:
```powershell
git clone --no-checkout https://github.com/FyodorAmanov1/OxfordQ.git OxfordQ-worker-b
Set-Location OxfordQ-worker-b
git fetch origin
$handoffSha = git log -1 --format=%H origin/codex/import-quantum-duet -- docs/team/prompts/worker-a.md
$bSha = git log -1 --format=%H origin/codex/import-quantum-duet -- docs/team/prompts/worker-b.md
$cSha = git log -1 --format=%H origin/codex/import-quantum-duet -- docs/team/prompts/worker-c.md
if (-not $handoffSha -or $handoffSha -ne $bSha -or $handoffSha -ne $cSha) { throw 'Handoff mismatch: stop and obtain coordinator SHA' }
git cat-file -e "$handoffSha^{commit}"
git merge-base --is-ancestor $handoffSha origin/codex/import-quantum-duet
if ($LASTEXITCODE -ne 0) { throw 'Handoff absent from import branch' }
git switch -c codex/duet-adapter-20261010 $handoffSha
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
`.venv-worker/Scripts/python.exe components/quantum_duet/tools/build_qollab.py --out components/quantum_duet/build/worker-b-check`.
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
