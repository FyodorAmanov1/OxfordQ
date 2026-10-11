# Quantum Graph Composer

A quantum-dynamics composer that generates a four-bar theme, develops it, and
returns to it in a complete 64-bar piece. Melodic contour, attack rhythm and
harmonic node are chosen jointly from an evolving quantum state. The output
includes acoustic piano, accompaniment, a WAV, a MIDI and an auditable score.

**Hackathon theme: Quantum Playground.** This effort is supported by Qollab & IonQ.
Original code and documentation: [MIT](LICENSE). Source history and the
public-domain piano bank: [SOURCE_NOTICES.md](SOURCE_NOTICES.md).

## Judges: run on Qollab

1. Build the upload from this component: `python tools/build_qollab.py`.
2. In Qollab, choose **New Project → Upload your own files** and upload
   `build/qollab.zip`. The archive has `index.html` and `main.js` at its root;
   it is an HTML/JS project. Its `README.md` becomes the project write-up.
3. Press **Run** and select the free **Built-in simulator**. In the page, keep
   seed **1201**, **64 bars**, **104 BPM**, interaction **0.7**, and **512 shots**.
4. Press **Generate music**. When the player appears, press Play. Download the
   WAV, MIDI, or score JSON. A 16-bar audition is available for a shorter run.
5. To generate another piece, use Qollab's **Stop → Run**, then change the seed
   or phase interaction. Each project run submits exactly one backend job.

If the embedded frame blocks file downloads, open **Export text if file downloads
are blocked**, copy its text to `take.json`, then run locally
`python tools/render_score.py take.json`. Listening uses the embedded audio player
and does not depend on file downloads.

Free IonQ simulators use the same one-circuit route. Start with **128 shots** on
those remote noise-model simulators; they simulate each shot and can take longer.
The remote histogram can vary between runs, even with the same composition seed.
The default local route is the recommended judging workflow.

**Execution is explicit:** your selected simulator executes a six-qubit musical
entrance. Its measured distribution sets the initial melodic-contour amplitudes.
The complete composition then uses a **13-qubit ideal Qiskit Statevector
calculation in browser Python**, with non-disturbing access to probabilities.
That continuation is not a claim that IonQ returned amplitudes or that the entire
piece ran on the selected remote simulator. There is no automatic fallback if
the selected backend fails. Neither Aer nor a native audio library is required.

Authenticated execution has been verified on **Qollab's free built-in simulator
and free IonQ Forte 1 simulator**. Both generated complete 64-bar, 2:33 pieces;
their actual score/MIDI exports and execution metadata were retained. The button
uses a sandbox-compatible click handler, and the page keeps Qollab's Run active
until Stop so its remote-job bridge remains available. See
[VALIDATION.md](VALIDATION.md) for the separate verification records.

## Judges: run locally

Use Python 3.11 or newer. From the repository root:

```sh
cd components/quantum_graph_composer
python -m pip install -r requirements.txt
python run.py
```

This writes `output/composition.wav`, `.mid`, `.json`, and `.audio.json`.
The default WAV is approximately **2 minutes 33 seconds**. For a short audition:

```sh
python run.py --seed 1201 --bars 16 --out output/audition
```

To preview the same browser interface, run `python tools/preview.py`, open
`http://127.0.0.1:8772`, and press **Render local composition**. The preview plays
the most recent `run.py` score; it does not submit a new quantum job.

Use a virtual environment if preferred. On Windows, create it with
`python -m venv .venv` and substitute `.venv\Scripts\python.exe` for `python`.
On macOS/Linux, substitute `.venv/bin/python`.

## What makes this a quantum composer?

The musical state is indexed by three four-valued interval registers, a
16-valued attack-rhythm register, and an eight-valued harmony register:

\[
|\psi\rangle=\sum_{c,r,h} a_{crh}|c,r,h\rangle,
\qquad 64\times16\times8=8192=2^{13}.
\]

Each contour is a four-note scale-degree gesture. Rhythms are actual four-attack
patterns in a 4/4 bar. Harmonic nodes are diatonic degree sets. Graph edges join
nearby interval values, similar attack patterns, and chords sharing scale degrees.
Evolution uses the Hermitian Hamiltonian

\[
H_b=\sum_j(-A_j)\otimes I_{\bar j}+gV(c,r,h)+F_b(c,h),
\qquad |\psi_{b+1}\rangle\approx
\left[e^{-i\Delta t(gV+F_b)/2}\prod_j e^{i\Delta t A_j}
e^{-i\Delta t(gV+F_b)/2}\right]^{64}|\psi_b\rangle.
\]

The diagonal interaction couples contour span/direction to harmonic tension and
rhythmic syncopation. The feedback phase field depends on earlier selected
gestures. A single state persists through all bars: its phases affect future
interference, even when two states have the same present probabilities.
`quantum_engine.py` uses Qiskit `Statevector.evolve` for register unitaries and
an exact elementwise diagonal phase operation to avoid an enormous dense matrix.
Tests independently reconstruct the evolution with Qiskit circuit gates.

The six-qubit entrance implements coupled path walks on the same three interval
registers. Its joint measurement histogram—not a random seed—is embedded as
contour amplitudes, using disclosed half-count smoothing and seeded initial
phases. Those phases and the 13-qubit continuation are simulation assumptions.

The Born distribution proposes the **whole contour/rhythm/harmony gesture**.
Classical rules choose a singable register, favor harmonic continuity, form a
four-bar theme from the generated material, and set section-level variation.
The variation controller uses the KL-minimal exponential tilt
`q ∝ p × musical_weights × exp(lambda × theme_distance)`; it is a classical
controller. Chord voicing, accompaniment texture, tempo, mix and final tonic
are also authored rules. The lead's interval material and attack pattern,
selected harmony, and conditional answering gesture depend on the quantum law.

The JSON preserves every selected node, theme, readout entropy, constraint
strength, variation target, and explicit closing override. This is a hybrid
generative mechanism with a substantial compositional quantum state, rather
than mapping arbitrary physical coordinates directly to frequencies.

No quantum speedup or musical-quality advantage has been established. Entanglement
and interference explain the mechanism; they do not certify good music. The
composer is fully classically simulatable, as intended for this submission.
Classical comparison experiments from the research are not included here.

## Verification and submission

```sh
python -m unittest discover -s tests -v
python tools/build_qollab.py
```

The upload has fewer than 100 files and no file over 2 MB. It includes the piano
PCM bank, requires no external model service, and does not package environments
or pregenerated soundtracks. A public project-page draft is in
[PROJECT_PAGE.md](PROJECT_PAGE.md), and a 2–3 minute demo outline is in
[DEMO_SCRIPT.md](DEMO_SCRIPT.md).

The team still needs to run and **publish** the project on Qollab, add a public
demo-video link, and submit it before **October 11, 2026, 19:00 ET**. The rules
also require source disclosure and continued availability for 12 months.
This branch does not register a team, publish a Qollab version, or submit an entry.
Sources: [hackathon rules](https://qollab.xyz/programs/hackathon/terms),
[how it works](https://qollab.xyz/programs/hackathon/how-it-works),
[runtime environment](https://qollab.xyz/learn/docs/runtime-environment),
[compute backends](https://qollab.xyz/learn/docs/compute-backends), and
[file upload](https://qollab.xyz/learn/docs/upload-your-files).
