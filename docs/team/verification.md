# Import verification and preservation

Executed 2026-10-10 from a new checkout outside OneDrive. Reviewed code commit
e9f02aecfcd973dbe8e235d74265515b65aca348; default main inspected/fetched at
7b9b6b0f6a27425645c01389ccbcd7d63b4a3982. GitHub connector authenticated as
FlorisOrd, repository permissions include push. Local commit identity uses that
account's public GitHub noreply address, configured only in this checkout.

Original project is not a Git repository: no tracked/uncommitted Git status exists,
no origin repointed, no original .git copied/created. A metadata comparison checked
723 noncache source/deploy/scripts/tests/dev/artifact/deliverable files: no changed,
removed or new files. Original artifacts remain in place. Held-out motif contents
were never read; preservation comparison uses filenames/size/mtime only. Imported
source/checkpoint/report hashes are in components/quantum_duet/IMPORT_MANIFEST.json.

Existing team modifications are exactly additive: .gitignore gains seven lines for
additional environments/build/tests/env exclusions; README.md gains four lines linking
the component/handoff. Existing ignore rules retained. Existing pyproject.toml,
orchestrator, examples, tests and root LICENSE unchanged. New root AGENTS.md establishes
ownership/verification. No teammate implementation replaced or reorganized.

| Newly executed check | Result / scope |
|---|---|
| Clean unchanged team install: python -m venv .venv; uv pip install --python .venv/Scripts/python.exe -e '.[dev]' | Passed; no original environment used |
| .venv/Scripts/python.exe -m pytest -q --basetemp .test-before | 29 passed in 10.10s before import |
| Minimal noneditable component install: python -m venv .venv-duet; uv pip install --python .venv-duet/Scripts/python.exe './components/quantum_duet[dev]' | Passed; quantum_duet imported from this venv's site-packages, not original source |
| .venv-duet/Scripts/python.exe -m pytest -q components/quantum_duet/tests --basetemp .test-final-duet | 3 passed in 4.16s, including ten original isolated inference cases, inference from unrelated temporary cwd, historical counts/checkpoint checks |
| node components/quantum_duet/tests/ui_checks.mjs | Passed 2026-10-10T15:01:32.866Z; mocked AudioContext resume races/repeat/Stop/mutes, immutable shots/take and both MIDI headers |
| Install component + Qiskit into team env without team dependency upgrades; final .venv/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests --basetemp .test-audited | 32 passed in 8.67s, including existing SDK serialization tests with intercepted HTTP; no paid API calls |
| .venv/Scripts/python.exe -m orchestrator --generation-manifest examples/generation.json --backend rules --bars 4 --no-audio --out output-generators | Passed; synthetic generation routes, MIDI/JSON/report, provider disabled |
| .venv/Scripts/python.exe -m orchestrator --manifest examples/note_events.json --backend rules --bars 4 --no-audio --out output-events | Passed; original event-manifest CLI, MIDI/JSON/report |
| .venv/Scripts/python.exe scripts/check_environment.py | Python deps present; Gemini key false; SDK structured Interactions accepted; FluidSynth/SF2 absent |
| .venv-duet/Scripts/python.exe components/quantum_duet/dev/server.py --port 8766; GET / and POST /api/run with 32 shots/five-live | Passed local HTTP + real BasicSimulator, one call/128 CHSH shots. Not an interactive browser/Qollab proof |
| .venv-duet/Scripts/python.exe components/quantum_duet/tools/build_qollab.py --out components/quantum_duet/build/final-check | Passed; ZIP SHA-256 cae1925ee1e126fbaa059e34964943f427bdbe264fdef5a1ea139a3bb75b0d68; ignored output |
| Generated upload directory: local generate_take(BasicSimulator,32,'five-live','ideal-local-development',32002) | Passed using generated namespace and literal data files, one batch/128 CHSH shots |
| Final diff/allowlist audit | No deleted paths, unintended existing-code modifications, credentials/private keys/personal Windows paths in imported source/docs, oversized files, environments or generated deployment outputs staged; git diff --check passed after copy-only LF normalization |

Minimal verification versions are pinned in component requirements-verified.txt.
Team resolved Python deps: mido 1.3.3, music21 9.9.2, pydantic 2.14.0,
google-genai 2.29.0, numpy 2.5.3. Component: Python 3.13.5/Qiskit 2.5.2,
NumPy 2.5.3/SciPy 1.18.1. Node 16.13.2. Root declared ranges are unchanged.

## Historical evidence and checks not executed here

Original 66-test full research pass is historical, not a new 66-test import pass.
Training/gradient/corpus tests require excluded research materials; no held-out motifs,
new training or paid API/hardware execution was performed. Current active tests were
ported without weakening assertions; original mapper comparison uses the complete
32-case frozen reference plus source hash rather than reaching into OneDrive.

Historical platform summary and original frozen exported run are retained. Actual
Qollab built-in simulator passed 4096 CHSH shots, final success 0.85888671875 with
conditional interval [0.8376663825665528,0.8801070549334472]; no QCBM shots added.
Four/five free IonQ runs failed HTTP400 'Only job type ionq.circuit.v1 is supported',
no accepted job/counts. Single-circuit IonQ is UNTESTED. Cause is not confirmed.
New namespace/asset-path adaptation has local regression/build checks only; real
Qollab/Pyodide and free IonQ tests are delegated to A, not claimed newly passed.
Interactive local browser execution remains historical; this import smoke-checked
HTTP and Node playback. FluidSynth/native audio and live Gemini are unexecuted.

Original private Qollab draft stays unpublished/unsubmitted. Visible payload/console
exports passed historically; native iframe downloads blocked, toolbar routes unverified.
MIT notices and corpus/edition qualifications retained. Learned checkpoint values are
included; raw corpus encodings, splits and test motifs are excluded, not relicensed.

## Scientific / authorship provenance

Four-angle Bell and 12-qubit/84-parameter QCBM checkpoints retain source SHA-256 IDs.
Inference reproduces them, not their excluded full training histories. Historical
diagnostic summary/CSV retains optimizer caps, validation selection, negative result:
best full QCBM 1.8217788505759362 vs classical empirical Markov 1.7114360 nats/event.
No held-out evaluation or musical-quality advantage. Original milestone1/2/2B and
initial 3A were pre-window work; 3B browser integration/verification occurred October
10. Official stated build window was October 9 23:00 UTC through October 11 23:00 UTC.
Git import timestamps record import, not original authorship or a new training date.
AI assistance disclosed; captain must review event eligibility and source notices.

Copied reports remove personal draft URL/consent/editor details, normalize path
separators/LF, and replace unusable historical reproduction commands with the excluded
research boundary. Scientific numerical conclusions are unchanged. New package paths
and optional asset_dir address installation only; default Qollab literal paths stay.

## Remote freshness

Second pre-push fetch still found main at 7b9b6b0f6a27425645c01389ccbcd7d63b4a3982;
only main existed and there were no open PRs. No stale base at that check. After push,
coordinator re-fetches/reports current main and exact handoff branch SHA in final reply.
No merging, force pushing, worker implementation or worker sessions occurred.
