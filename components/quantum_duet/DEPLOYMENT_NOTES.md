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
