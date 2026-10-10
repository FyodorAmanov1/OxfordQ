# Quantum Duet inference package

Upload this directory's files or the root-level ZIP as a JS/Qiskit project.
index.html is body content, main.js awaits the documented Python callPromising
bridge, and main.css is the only stylesheet. Use a free simulator. Generate take
submits one job, then all playback/export controls reuse that result. For a new
experiment, Qollab Stop then Run; never silently retry a failed batch.

Default: 1,024 shots per circuit, four CHSH settings plus one existing 12-qubit
QCBM. Explicit four-circuit mode uses recorded M3A motifs. Unknown result
representations or missing circuit names fail visibly. On October 10, 2026 the
real Qollab built-in simulator passed the separate one-circuit bridge probe and
full five-circuit batch. IonQ Aria 1's free noise-model route rejected five-live
and a separately selected four-recorded batch with HTTP 400: "Only job type
ionq.circuit.v1 is supported". No remote counts were produced.

Qollab's preview sandbox blocks native downloads. Export buttons show lossless
JSON or base64 MIDI payloads and print console export envelopes. The Run stays
active until Stop so these messages are retained. Use the platform output controls
or copy the visible payload. The separate research repository supplies
scripts/extract_duet_exports.py; --filename decodes a single copied payload.
Native platform Download/Copy output could not be verified by automation;
visible payload export and console-envelope extraction passed. Archive manifest
hashes describe the ZIP bytes; editor insertion may normalize line endings.

This package adapts the existing MIT inference executor to match results by name,
and copies its circuit, referee and classical-policy modules. Music projection
is copied unchanged with rendering dependencies removed. Frozen Bell angles,
84 QCBM angles and four recorded motifs are the only model/data assets. Their
research-source hashes are in manifest.json and in exported run metadata.
Python reads data files through literal paths. There is no corpus, held-out data,
training, credential, replacement provider, persistent storage or outside service.

Starting experiments and the first duet implementation predate the official build
window. Integration/UI/deployment work was added October 10, 2026, with actual
timestamps recorded in the separate research provenance. Verification timestamps
are not authorship timestamps. No model was retrained.

Our code is MIT. Runtime dependencies are installed by Qollab, not redistributed
here: Qiskit (Apache-2.0), NumPy (BSD-3-Clause). Their notices still apply.
SOURCE_NOTICES.md preserves the separate Bach-edition/corpus attribution; the
MIT license does not relicense those editions or derived data. Generated motifs
are from the frozen model, not copies of corpus files.

CHSH is an established coordination game. Our contribution is trained parameters,
local musical mapping, interactive comparison and reproducible evaluation.
The central program is classically simulatable. No musical-quality advantage or
computational speedup is claimed; earlier classical melody models remain better.

This effort is supported by Qollab & IonQ

## Coordinator integration, 2026-10-10

The generated Qollab upload deliberately provides RAW duet execution/playback and
the unchanged RECORDED fixture. `quantum_duet.recorded_fixture.load_fixture` reads
literal `data/run-result.v1.json` and `data/qollab-local-run.json` paths through
the supported asynchronous Python bridge. It checks the source byte digest and
requires recorded provenance/zero replay calls. No private repository fetch is used.

Optional rules orchestration runs in the separate local CPython application with
both repository packages installed. Its music21/pydantic/orchestrator dependencies
have NOT been verified in the actual Qollab Pyodide runtime. The build excludes
orchestration_adapter.py and browser_projection.py; it adds no orchestration
dependencies to the working Qiskit/NumPy requirements. The platform's supplied
backend and legacy generate_take API remain unchanged. A valid local creative
playback sidecar may be imported, with its raw evidence retained separately.

Worker A's standalone 32-shot probes succeeded on Qollab built-in and free IonQ
Aria 1 simulators on 2026-10-10 UTC, with one accepted job each. Actual IonQ SDK
was 1.0.2 and the accepted type was ionq.circuit.v1. This does not establish a
supported four/five-circuit duet path or verify this canonical upload. Historical
multi-circuit HTTP400 remains unresolved; no provider substitution is added.

Current runtime documentation was read through Chrome on 2026-10-10:
https://qollab.xyz/learn/docs/runtime-environment . Its limits are 100 files,
2 MB per file, and 200 MB across the account. The builder enforces the per-project
limits; account-wide capacity must be checked at upload. Full private canonical
upload, recorded replay, built-in duet, sandbox exports and error verification
remain required before separately authorized publication. Native platform
downloads remain unverified; visible lossless JSON/base64 remains available.
