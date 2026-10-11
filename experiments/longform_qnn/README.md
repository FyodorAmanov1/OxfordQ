# Long-form conditional QNN pilot

An isolated research experiment. It does not import or change Quantum Duet,
its CHSH/QCBM weights, browser, contracts, musical mapping or Qollab deployment.
All execution is offline CPU statevector simulation. Training this experiment
was explicitly authorized by the Milestone 4 request, overriding the earlier
coordinator-session prohibition on new training only for this new directory.

Read [REPORT.md](REPORT.md) for the executed pilot, negative comparative result,
verification and integration recommendation. Aggregate results and source metadata
are versioned under `results/`; playable files and checkpoints stay local and ignored.

## Reproduce

Run from the repository root using Python 3.12. A separate environment is required;
do not replace the root project's dependency versions. On Windows:

```powershell
python -m venv experiments/longform_qnn/.venv
experiments/longform_qnn/.venv/Scripts/python.exe -m pip install -r experiments/longform_qnn/requirements.txt
experiments/longform_qnn/.venv/Scripts/python.exe -m pytest -q experiments/longform_qnn/tests --basetemp experiments/longform_qnn/artifacts/pytest
experiments/longform_qnn/.venv/Scripts/python.exe -m experiments.longform_qnn equivalence
experiments/longform_qnn/.venv/Scripts/python.exe -m experiments.longform_qnn prepare
experiments/longform_qnn/.venv/Scripts/python.exe -m experiments.longform_qnn train --steps 320 --seeds 11 22 33 --budget-seconds 1800
experiments/longform_qnn/.venv/Scripts/python.exe -m experiments.longform_qnn generate
experiments/longform_qnn/.venv/Scripts/python.exe -m experiments.longform_qnn.benchmark
experiments/longform_qnn/.venv/Scripts/python.exe -m experiments.longform_qnn.verify_artifacts
experiments/longform_qnn/.venv/Scripts/python.exe -m experiments.longform_qnn.summarize
experiments/longform_qnn/.venv/Scripts/python.exe -m experiments.longform_qnn.reproduce_checkpoint
```

Use `bin/python` on POSIX. CPU Torch is sufficient; no GPU, API credentials,
paid services, quantum hardware, SoundFont or native audio tools are needed.
The exact transitive environment is recorded separately in `requirements-resolved.txt`.
The final three commands verify all exported files, create `artifacts/listen.html`
and scientific plots, and independently retrain the selected full QNN seed in a
separate artifact directory, requiring an identical checkpoint SHA-256.
The initial budget is **30 minutes total training, one CPU thread, 4 GiB resident
memory**. The driver checks elapsed time and memory between optimizer steps and
stops rather than substituting another generator. Checkpoint/evaluation overhead
can exceed a wall-clock deadline by one bounded step/evaluation. No training run
above three hours is accepted by the first-pass CLI.

Artifacts, environments, corpus-derived event files, checkpoints and audio are
ignored under `experiments/longform_qnn/artifacts/`. Re-running prepare/train with
the same output directory replaces experiment artifacts; supply a fresh
`--artifacts PATH` for an independent run. No legacy held-out motif is read.
The test-source score loader is deliberately unavailable during development.

## Circuit and probability contract

The reference is Qiskit, using its [little-endian convention](https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering).
Eight qubits start with H on each qubit. Three shared layers each apply context
RY/RZ, trainable RY/RZ, then the connected CNOT ring 0→1→…→7→0. Final H gates
make final-layer phase rotations observable. There are **48 trained circuit angles**.
The fixed context projection is generated from seed 20261011, with 3×8×2×80
coefficients; these 3840 public coefficients are not trained. Count this fixed
encoder's work as part of inference, not as free quantum computation.

For each layer/qubit/axis, the context angle is π times a fixed random projection
of the 80 causal features. Every successive event uses the same circuit angles.
No future event is an input. Rotation and parameter order is layer, qubit,
RY then RZ; `build_circuit`, `bind_parameters`, `qiskit_probabilities`,
`QuantumModel.joint`, `next_event` and `sample` expose the requested boundaries.

The seven measured qubits encode:

| Qubits | Meaning |
|---|---|
| q0–q2, low-order bits | degree 0=rest, 1..7=C..B |
| q3 | register 0=C4..B4, 1=C5..B5 |
| q4–q6 | duration code 0..7 → 0.5..4 quarter-note beats |
| q7 | latent/context ancilla, summed out |

A displayed seven-bit result is `d2 d1 d0 register degree2 degree1 degree0`.
For rests, both register outcomes are summed. The semantic distribution therefore
has 120 tokens (15 pitch/rest choices × 8 durations), not 128 distinct musical
events. Full statevector basis index is q7…q0. Ancilla marginalization sums the
two 128-element halves. Illegal durations receive exactly zero probability.
Add ε=1e-9 to each **legal** semantic probability and renormalize; training and
sampling call the same function. Reported NLL always uses normalized probabilities.

The PyTorch complex128 simulator implements the same gate sequence, including
little-endian CNOT permutations. Twelve fixed context/parameter cases must match
Qiskit within 1e-10 before training. Finite differences independently verify
autograd. Every QNN event in the two exported music examples is also checked
against Qiskit and sampled from that reference distribution.

## Data and causal context

The source is the [music21 Bach chorale corpus](https://music21.org/music21docs/moduleReference/moduleCorpusChorales.html),
with Riemenschneider/BWV IDs, titles and J. S. Bach attribution preserved in local
metadata. Corpus encodings and editions are not relicensed as this repository's
code and are not committed. This experiment uses its own source split because
the imported repository does not contain prior source-level split metadata.
An optional `prepare --prior-test-sources IDs.json` accepts a metadata-only list
of corpus IDs or BWV IDs and excludes their entire duplicate groups.

Metadata is grouped BEFORE any score parsing: union same BWV work or normalized
hymn title, including alternate movements/editions conservatively. A fixed SHA-256
rule assigns groups 70/15/15 to train/validation/test. Test scores are never opened.
Repeated source editions are deduplicated. Exact normalized validation melodies
matching training are excluded. Unknown near-duplicates under different titles
remain a limitation; test content is not inspected to discover them.

Whole-score key analysis chooses major pieces, then a fixed semitone transposition
normalizes the tonic to C. A documented whole-piece octave shift is used only if
needed to fit C4–B5; otherwise unsupported ranges are rejected. Normalization is
preprocessing, not a causal key detector. Chromatic notes are rejected rather than
snapped to a scale. Only complete contiguous bars in 4/4 or 2/2 are retained;
pickups and final partial bars are explicitly reported as trims. Whole passages
remain intact, including expression/fermata boundary metadata, rather than reducing
them to four-note motifs. No independent phrase labels are inferred.

Onsets/durations must already lie on the half-beat grid; off-grid rhythms, tuplets,
grace notes, polyphony, gaps and overlaps are rejected explicitly. No invented
notes or rests fill missing material. Ties are merged before splitting sustained
events at barlines. Each continuation retains a provenance flag; the vocabulary
has no tie bit, so learning those segments loses articulation continuity. Durations
and onsets remain exact within accepted material. This strict selection is biased
toward simple diatonic, representable chorales; see the report, including rejections.

Features 0:32 encode the last eight events' pitch, duration, sounding flag and
melodic interval. Features 32:40 encode bar position, 16-bar phrase clock, beginning
of piece and history availability. Features 40:80 summarize each of the previous
four **complete** bars: presence, pitch mean/spread/first/last, rest duration,
density, duration mean/spread and eighth-note share. The context routine accepts
only a prefix and rejects overlapping/future events. Teacher forcing builds it
before appending the target. The phrase clock is a supplied composition schedule,
not evidence that Bach phrase boundaries have been learned.

## Training, controls and interpretation

First run a tiny synthetic causal learning check (same data for fit and numerical
verification, explicitly not a held-out score). Then train full-history and short-
history QNNs and small/large autoregressive MLPs over the same training events,
320 batches of 64 per seed, seeds 11/22/33. These MLPs are classical autoregressive
neural baselines with exactly the QNN features, avoiding extra recurrent history
unavailable to the QNN. The smoothed Markov backoff model also receives the full
feature vector; sparse full-context keys back off to two/one prior events.

Adam rates are .025 for QNNs and .003 for MLPs, with gradient norm clipping at 5.
Check validation at initialization, step 1 and every 40 steps. Save the lowest
validation NLL checkpoint, then select the full QNN seed on validation only.
Histories include loss, gradient norm, iterations, elapsed time, RSS and hashes.
There is no claim of equally exhaustive optimizer tuning. Parameter counts alone
are not evidence of an advantage.

Long-range controls include retraining with features 40:80 zeroed, removing those
features at inference, and permuting them across validation examples matched on
bar position. Short features, targets, legal masks and batch schedules are fixed.
Report per-source bootstrap differences with the small validation sample caveat.
Likelihood changes and generated lag-4 pitch summaries are diagnostics; supplying
history does not establish learned long-range structure. The reserved test set
remains unused, so these are validation pilot results only.

## Music outputs

`examples/free/` contains a completely autoregressive 16-bar QNN melody, starting
from an empty prefix and ending exactly at 64 beats (32 seconds at 120 BPM).
All notes/durations are sampled; no cadence repair or quality filtering is applied.
`examples/structured/` has A–A′–B–A″: A is sampled, A′ is a classical one-degree
upward transformation of A, B is QNN-sampled conditioned on the actual prefix,
and A″ is a classical one-degree downward transformation of A. Pitch transforms
wrap within the 14-note vocabulary and preserve rests/rhythms. The trace marks
each operation; repeated material is not claimed as a learned quantum dependency.

Each contains melody and arranged MIDI/WAV plus `generation.json`. The optional
accompaniment is a deterministic classical I–vi–IV–V progression with I–IV–V–I
ending; the melody track is byte-equivalent in note events before/after arranging.
Audio uses a documented additive three-harmonic synthesizer, not FluidSynth or an
acoustic instrument. The files are listening demonstrations, not perceptual-quality
evidence. Generated pitch/rhythm diversity, n-gram matches, contour, lagged bar
statistics and ending tonic are reported without hardcoded quality conclusions.

This model is classically simulated, and autoregressive sampling requires one
distribution evaluation per event. It is not an IonQ/Qollab one-job demonstration.
No CHSH result is used as evidence of melody quality or computational advantage.
Integration or publication requires a separate review and authorization.
