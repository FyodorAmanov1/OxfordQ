# Milestone 4: executed long-form QNN pilot

Executed locally on 2026-10-11, based on main
`c49c2e6cace0790211ae6808f4ecdc4cb77faa01`. This is a reproducible research
experiment, not a replacement for Quantum Duet. Its correctness checks pass,
but it is **not yet worth integrating into the canonical application**: classical
baselines predict the validation music substantially better, and useful learned
long-range structure has not been established.

## Six completion answers

1. **Trained successfully:** yes. The synthetic learning check reduced NLL from
   4.52083 to 2.85906. The selected real-data full-history QNN reduced validation
   NLL from 4.51155 to 4.01990. Three seeds completed 320 optimizer steps each.
2. **Varied pitches/rhythms:** yes. The free sample contains 14 sounding pitches,
   seven durations, 45 notes and two rests. Diversity alone is not musical quality;
   its rhythm distribution differs markedly from training and it makes large jumps.
3. **Complete 16 bars:** yes. Both requested examples and both accompaniment
   variants independently parse as exactly 64 beats / 32 seconds at 120 BPM.
4. **Meaningful multi-bar use:** not established. Removing history can hurt this
   fitted model, but the separately trained short-context QNN is better. Permuted
   history effects have exploratory source-bootstrap intervals containing zero.
5. **Competitive with classical models:** no, on this pilot's primary metric.
   Neither parameter counts nor the separate CHSH experiment establish an advantage.
6. **Interactive feasibility:** local CPU simulation appears feasible: about
   0.52 seconds for 16-bar full-QNN sampling with the differentiable simulator,
   approximately 1.8 seconds including per-event Qiskit reference checks for the
   free demonstration. These are local timings, not web-service or IonQ guarantees.

## Data, architecture and budget

The implementation uses an eight-qubit, three-layer conditional circuit with
48 shared trainable RY/RZ angles, fixed causal data re-uploading, a connected
CNOT ring, and final Hadamards. Seven output qubits encode degree/rest, register
and duration; the eighth qubit is marginalized. The two rest-register outcomes
are aggregated into the same semantic token. See [README.md](README.md) for exact
bit ordering, 80 context features and legal-duration normalization with epsilon 1e-9.

Metadata grouping precedes score access: 350 distinct sources in 371 metadata
entries split into 262 train, 44 validation and 44 reserved test sources, with
129/31/30 duplicate groups. After strict representability filtering, **53 training
pieces / 2,358 events** and **6 validation pieces / 218 events** remain. Test score
content was not opened, selected on or evaluated. No old held-out motifs were read.
No prior source-level test-exclusion metadata was available in the imported repo.

Main rejection counts: 148 minor-key sources, 52 chromatic sources, 23 unsupported
sub-half-beat rhythms, 21 unsupported metres, 18 duplicate editions, two incomplete
final bars and one grace/polyphonic source. The [dataset report](results/dataset-report.json)
contains source IDs, transformations, rejection reasons and pitch/duration counts,
without score encodings. Most accepted events are one beat long (1,797 of 2,576).
The highest vocabulary pitch and durations 2.5/3.5 beats have no accepted data;
generating them is not evidence they were learned. Barline splitting preserves
duration but the no-tie-token model loses sustained articulation. Selection bias,
unknown cross-title near-duplicates and the six-piece validation sample limit inference.

Declared pilot budget: 30 minutes, one CPU thread, 4 GiB resident memory, under
the authorized three-hour ceiling. The complete synthetic + 12-model real-data
training run took **244.71 seconds**, from 13:36:04 to 13:40:09 UTC. Peak RSS was
**0.355 GiB**. Each model used batches of 64; seeds were 11, 22 and 33.
Adam rates were .025 for QNNs and .003 for classical networks; validation selected
iterations and seeds. Selection therefore biases these validation estimates;
they are not untouched-test results or an exhaustively tuned architecture comparison.

Selected checkpoint: `artifacts/training/qnn_full-22.json`, step 320,
SHA-256 `be989df730b33685ed15ea867eb49da799d23f1e478ed1259cf122979b68a625`.
An independent 320-step rerun reproduced this file byte-for-byte and reproduced
loss/gradient values (elapsed times naturally differ). The rerun command is in the
README. Checkpoints and corpus-derived event files are local ignored artifacts.

## Matched comparisons

All models use the same examples, causal information and duration masks. The two
classical networks are autoregressive MLPs over exactly those features. Markov
uses smoothed full-context keys with short n-gram backoff. NLL is nats per event;
lower is better. Means and sample SD use three training seeds, except deterministic
Markov. Generation timings use three matched sampling seeds and each family's
best validation checkpoint, on one CPU thread.

| Model | Validation NLL | Pitch accuracy | Duration accuracy | Training seconds/model | 16-bar sampling seconds |
|---|---:|---:|---:|---:|---:|
| Full-history QNN | 4.0820 ± .0575 | 11.31% | 49.54% | 37.11 | .522 |
| Short-history QNN | 3.7060 ± .0535 | 11.31% | 66.06% | 38.56 | .440 |
| Small classical MLP | 2.5067 ± .0052 | 25.99% | 78.90% | .71 | .039 |
| Larger classical MLP | 2.2310 ± .0194 | 34.86% | 80.28% | 1.47 | .041 |
| Smoothed Markov | 2.0620 | 56.42% | 81.19% | .10 | .041 |

QNNs have 48 trained angles; the MLPs have 6,552/42,360 parameters. Markov stores
3,870 nonzero count entries, which are not equivalent to neural parameters.
The fixed QNN context projection also performs classical computation.

Mean rhythm Jensen-Shannon divergence from training: full QNN .1577, short QNN
.1625, small MLP .0168, large MLP .0242, Markov .0115. Generated eight-token
training-match fractions were zero for the QNNs/MLPs and .00546 for Markov.
This short exact-match diagnostic cannot establish originality or absence of
memorization. Lag-four-bar pitch correlations vary by seed and do not establish
coherent form. [Aggregate results](results/pilot-summary.json) include all seeds,
histories, ablations, generated distributions and exported-file hashes.

For the selected QNN, validation NLL is 4.01990 with full history, 4.33977 with
long features removed, 4.11063 with them permuted, and 3.75364 after retraining
with only short history. Exploratory equal-piece mean differences relative to
full history are +.3051 [+.0184, +.6285], +.0953 [-.0531, +.2263] and
-.2957 [-.5218, -.0982], respectively (2,000 source-bootstrap resamples).
These piece-weighted differences differ from event-weighted table differences.
All three permuted-history intervals contain zero; all three retrained short
models outperform their full-context counterpart. Input sensitivity is not
evidence of useful learned musical structure.

## Listen and inspect

Open local `artifacts/listen.html` after running the README commands.

| Example | Melody | With classical accompaniment | Trace |
|---|---|---|---|
| Free, seed 101 | [WAV](artifacts/examples/free/melody.wav), [MIDI](artifacts/examples/free/melody.mid) | [WAV](artifacts/examples/free/arranged.wav), [MIDI](artifacts/examples/free/arranged.mid) | [JSON](artifacts/examples/free/generation.json) |
| A–A′–B–A″, seed 202 | [WAV](artifacts/examples/structured/melody.wav), [MIDI](artifacts/examples/structured/melody.mid) | [WAV](artifacts/examples/structured/arranged.wav), [MIDI](artifacts/examples/structured/arranged.mid) | [JSON](artifacts/examples/structured/generation.json) |

These local artifacts are intentionally excluded from GitHub. Every free melody
event is sampled directly from the QNN's Qiskit-verified conditional distribution.
The structured example contains 25 QNN-sampled events (A and conditioned B) and
20 documented classical transformations (A′/A″). Repetition in that form is
classically imposed. Accompaniment is deterministic classical bass/chords and
does not replace melody events. No post-sampling cadence or pitch repair occurs.

The free melody has no repeated exact four-event motifs and mean absolute
diatonic jump 4.45 steps. It happens to end on C4; this one unforced ending does
not demonstrate learned cadences. Structured lag-four pitch correlation .556
reflects classical phrase manipulation, not a learned quantum dependency; its
last melody pitch is not tonic. Listening examples support human assessment,
but no listening panel or perceptual score was conducted. Musical phrasing and
recognizable learned motifs remain unresolved.

## Executed verification

All checks below ran anew on 2026-10-11; none are inherited worker results.
One final rerun using the sandbox's default temporary directory hit four pytest
fixture-setup permission errors (23 tests passed). Using the explicit workspace
`--basetemp` documented in the README resolves that environment issue; test
assertions and implementations were not weakened.

| Check | Actual result |
|---|---|
| New experiment tests | 27 passed; encoding, causality, source isolation, gradients, checkpoint determinism, MIDI/WAV and ablations |
| Pre-training Qiskit equivalence | 12 contexts across three parameter seeds; max absolute error 2.22e-16, tolerance 1e-10 |
| Actual generated-event equivalence | Free max 5.00e-16; structured max 1.31e-15 |
| Independent selected-seed training | Exact checkpoint SHA-256 match |
| Actual exported-file verification | Four MIDI + four WAV files; all 32 seconds; legal notes/velocities, nonzero audio RMS, preserved melody events and causal provenance |
| Existing Python suites | 138 passed in 22.11s |
| Existing Node suites | All three passed at 13:41:01, 13:41:02 and 13:41:07 UTC; mocked browser/audio scope |
| Original rules-only CLI examples | Generation and event manifests both passed with `--no-audio`; provider disabled |

Regression commands (existing environment, no dependency replacement):

```powershell
.venv-final/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests --basetemp .test-longform-regression
node components/quantum_duet/tests/ui_checks.mjs
node components/quantum_duet/tests/ui_c/contract_checks.mjs
node tests/duet_projection_checks.mjs
.venv-final/Scripts/python.exe -m orchestrator --generation-manifest examples/generation.json --backend rules --bars 4 --no-audio --out experiments/longform_qnn/artifacts/regression-cli/generation
.venv-final/Scripts/python.exe -m orchestrator --manifest examples/note_events.json --backend rules --bars 4 --no-audio --out experiments/longform_qnn/artifacts/regression-cli/events
```

No new Qollab, free IonQ, physical QPU, paid API or platform execution was attempted.
Local statevector sampling is not evidence for Qollab's one-job IonQ restriction;
sequential generation requires many conditional circuit evaluations. Existing
scientific checkpoints, CHSH conclusions, frontend, raw contract, deployment and
orchestrator are unchanged. There is no silent simulator substitution.

## Recommendation

Keep this draft PR as an isolated, reproducible research result. It establishes
correct training and playable generation, not competitive musical modeling.
Before proposing an optional Long-form QNN application mode, investigate why
the full-history encoder underperforms, validate on more independent development
pieces and assess actual listening quality. Do not consume the reserved test set
for iterative tuning. Canonical Qollab integration requires separate review and
an execution design supported by real platform evidence.
