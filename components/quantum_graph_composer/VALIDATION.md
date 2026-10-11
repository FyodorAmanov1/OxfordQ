# Verification record — 2026-10-11

Checks below concern this component, with additional repository regressions
reported separately. They do not establish perceptual quality or quantum advantage.

## Local quantum and composition checks

Seven `unittest` checks passed, first using the prior research Qiskit runtime,
then in a newly created CPython virtual environment installed from the submitted
`requirements.txt`. The fresh environment used Python 3.12.14, Qiskit 2.5.2,
NumPy 2.5.4 and SciPy 1.18.1; the verified dependency versions are also recorded.

- Efficient unitary evolution agrees with an independently constructed Qiskit
  circuit using DiagonalGate and local unitary gates, to below 1e-11 in amplitude.
- States with equal present probabilities and different phases produce different
  future probabilities under the same dynamics.
- The entrance interaction changes the joint contour law.
- The selected backend is called exactly once. Invalid results and backend
  failures raise errors without substitution or additional submissions.
- The same seed and entrance histogram reproduce the same musical events.
  Sixteen-bar output has four theme bars, a consistent form, valid notes and a
  tonic ending. The variation actuator preserves hard support constraints.
- The 10 public-domain piano sample regions cover MIDI pitches 0–127.

Default complete take: seed 1201, 64 bars, 104 BPM, interaction 0.7, 512 shots.
Qiskit BasicSimulator executed one six-qubit circuit, with compiled depth 70 and
145 instructions including measurement. The persistent ideal continuation used
13 qubits, 8,192 vertices and 64 substeps per bar. It produced 1,250 note events,
four generated theme bars, and a stereo WAV of 152.943854875 seconds at 22,050 Hz.
Maximum state-norm error was approximately 8e-12. NumPy audio peak was 0.54723.

## Browser and deployment checks

The canonical interface was exercised in the Codex in-app browser against the
localhost preview, using a freshly generated local score. Rendering completed,
the native audio player loaded a 2:33 WAV, and WAV/MIDI/JSON links were created.
Web Audio produced 13,489,692 WAV bytes, with peak approximately 0.59467. The
browser renderer and NumPy renderer use different performance random streams
and envelope implementations; their audio is not promised to be bit-identical.
The score and MIDI come from the same quantum-generated take.

Accessibility uses native labelled inputs, a keyboard-operable form, native
audio transport, status/alert regions, readable text, and no autoplay. This is
implementation and browser inspection, not a complete WCAG conformance audit.

The Qollab upload contains 16 files, each under the documented 2 MB limit. It
has top-level index.html/main.js, an asynchronous callPromising Python bridge,
a literal data/piano.json asset path, Qiskit/NumPy requirements, source notices,
an MIT license and an automatically imported project-page write-up. No audio
runtime, external API, environment folder or precomputed soundtrack is uploaded.

## Existing repository checks

The existing repository's 48 root tests passed. Windows Git checkout had converted
one pre-existing raw JSON fixture to CRLF, changing its byte hash; restoring its
exact Git blob locally resolved the two digest failures without a tracked edit.
Tests used a fresh writable --basetemp because the system pytest temp directory
was inaccessible. The existing rules-only orchestration CLI also completed with
audio disabled and no paid model calls. Root sources and existing components
have no tracked changes from this extraction.

## Platform verification boundary

Qollab's official runtime, compute, upload, publication and hackathon pages were
read on October 11, 2026. The browser/Pyodide deployment is designed for their
documented APIs and limits. The session was initially signed out; the user
subsequently signed in and authorized creation of a private test draft, including
its creation terms. The draft is
[Quantum Graph Composer](https://qollab.xyz/u/SQqqqq/quantum-graph-composer).
It remains unpublished and has no final hackathon submission.

**Authenticated Qollab built-in simulator: passed.** The initial interface
revealed a sandbox restriction: native form submission was blocked by the
iframe's `allow-scripts` policy. The button was changed to a direct click handler
with Enter-key support. The restored complete bundle generated a 64-bar take
with 512 shots, one six-qubit backend job and 1,258 note events. The ideal
continuation took approximately 2.263 seconds. Qiskit 2.5.2 and NumPy 2.4.6 were
reported by the actual browser Python runtime. Maximum state norm error was
9.89e-13. The WAV decoded with readyState 4 and duration 152.943855 seconds;
its playback time advanced during the transport check. The actual take is
retained locally and its execution metadata is recorded in
`evidence/qollab-local-runtime.json`. Job ID:
`4bc775bc-5fe4-4f51-91f9-eeee0f81a864`.

**Qollab free IonQ Forte 1 simulator: passed.** An initial attempt failed with
`requests.exceptions.ConnectionError: Failed to fetch` after the JS entry had
finished initialization. Keeping the entry's promise pending until Stop/pagehide
preserved Qollab's remote-job bridge. A fresh run then returned 128 measured shots
from one six-qubit circuit and produced a complete 64-bar score with 1,245 events.
The actual SDK reported `IonQSimulatorBackend` / `ionq_simulator`, compiled depth
87 and 223 instructions. The ideal continuation took approximately 3.450 seconds;
its maximum norm error was 1.01e-12. The WAV loaded with readyState 4 and duration
152.943855 seconds. Actual returned counts and metadata are in
`evidence/qollab-ionq-runtime.json`. Confirmed job ID:
`01a12d13-d0a3-7cfe-850a-4c0d7d422d27`.

The selected dialog entry was the **Noise model / Free** IonQ Forte 1 simulator,
not its credit-consuming physical counterpart. No physical hardware was used.
This verifies the supplied Qollab simulator route; it does not certify the noise
model independently or establish musical-quality advantage. The failed initial
attempt has no confirmed job ID and is not counted as a completed simulation.

The six-qubit selected-backend entrance and the 13-qubit browser-host ideal
continuation are explicitly separate. Non-disturbing readout is a simulation
assumption, and the measured histogram is classically embedded into a coherent
initial state with chosen phases. The remote simulator is not asked to perform
nonphysical amplitude readout or a sequential 64-job feedback loop.
