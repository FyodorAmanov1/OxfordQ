# Quantum Duet component

Frozen inference, source UI and selected evidence imported additively. Distribution
`oxfordq-quantum-duet` installs `quantum_duet`; the team package stays unchanged.
Separate project boundaries keep Qiskit out of orchestration-only installations.
Both can be installed into one environment: their NumPy ranges overlap.
No training, corpus or remote-provider dependency is required for this demo.

From repository root in PowerShell:
```powershell
python -m venv .venv-duet
uv pip install --python .venv-duet/Scripts/python.exe './components/quantum_duet[dev]'
.venv-duet/Scripts/python.exe -m quantum_duet --out output-duet/run.json
.venv-duet/Scripts/python.exe -m pytest -q components/quantum_duet/tests
node components/quantum_duet/tests/ui_checks.mjs
.venv-duet/Scripts/python.exe components/quantum_duet/dev/server.py
.venv-duet/Scripts/python.exe components/quantum_duet/tools/build_qollab.py
```
Use `python -m pip install './components/quantum_duet[dev]'` inside the activated
environment if uv is unavailable. Open http://127.0.0.1:8766 for the local UI.
Qollab upload is generated under `components/quantum_duet/build/qollab` with its ZIP
alongside it. Choose fresh `--out` for rebuilds. Canonical files are `src/`, `web/`
and selected `src/quantum_duet/data/`; generated files are ignored, never edited.
The installed CLI loads bundled assets independently of the current directory.
Qollab keeps literal `data/*.json` paths for its static loader; the Python bridge
now imports `quantum_duet.integration`. No platform re-verification is claimed for
this namespace adaptation. `DEPLOYMENT_NOTES.md` describes original historical evidence.

`tools/extract_duet_exports.py` decodes the existing visible JSON/base64 console
export workaround. Qollab native iframe downloads were blocked; platform toolbar
downloads remain unverified. Preserve this route until supported replacement verified.

Tests preserve ten original inference cases in a separate subprocess (without
music21/training imports), installed-asset inference outside the checkout, and Node
AudioContext race/cleanup/MIDI checks. The exhaustive old mapper comparison uses a
frozen 32-entry reference with its original source hash. Held-out motifs were not read.
Research/data tests requiring excluded corpora are archived in the preserved original
project, not imported or represented as new passes. External FluidSynth rendering,
Gemini and actual Qollab/IonQ checks are separate verification scopes.

Scientific conclusions: Bell coordination exact success about 85.3553%, local
classical maximum 75%, centralized reference 100%. No speedup or musical quality
advantage. QCBM validation NLL 1.8217789 nats/event remains worse than classical
1.7114360. Histograms are reconstructed, not chronological memory. Raw events
include rests; all counts contribute to statistics. Simulated noncommunicating
policies do not certify a loophole-free Bell experiment.

MIT notice applies to this component's original code, with corpus/edition and
checkpoint provenance qualifications in SOURCE_NOTICES.md. The team's existing
root licence and notices retain their own authorship. No corpus encodings copied.
See IMPORT_MANIFEST.json and evidence/ for hashes, changes and historical limits.

`requirements-verified.txt` pins the minimal environment used for this import. For reproducible installation: `uv pip sync --python .venv-duet/Scripts/python.exe components/quantum_duet/requirements-verified.txt`, then `uv pip install --python .venv-duet/Scripts/python.exe --no-deps ./components/quantum_duet`. These are verification versions, not changes to the team dependency ranges.
