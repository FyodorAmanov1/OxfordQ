# Fresh QCBM source contract

`qm.fresh-qcbm-source.v1` is independent of both `qm.run-result.v1` and
`qm.joint-cue-result.v1`. It contains no CHSH rounds, wins or Bell statistics.
`generate_fresh(backend, shots=32, assignment_seed=20261011)` returns JSON text.
The browser must invoke this operation in its own fresh Qollab Run, with a visibly
selected FREE simulator. It must not automatically launch the CHSH operation.

One existing twelve-qubit circuit is bound to the exact frozen 84 angles, measured
q0->c0 through q11->c11 and decomposed into IonQ-supported QIS H/CX/RY/RZ/X gates.
One `QuantumCircuit` object is submitted in exactly one `backend.run` call. Unknown
or physical providers and non-QIS IonQ backends fail before submission. Provider
errors propagate without retry, alternate simulator, recorded substitution or
automatic additional jobs. The module cannot independently certify the platform's
free billing selection; the browser coordinator must verify it.

Top-level fields:

| Field | Meaning |
|---|---|
| contract_version/status/run_id | Literal contract, completed, qm-fresh-{actual-job-id} |
| execution | Supplied backend class/name, actual job/result status, runtime versions, requested/returned shots, gates/noise model and compiled operation counts; one circuit/call |
| models | Original checkpoint SHA-256; exact asset bytes SHA-256; canonical 84-angle array SHA-256; one shared model for all five instruments |
| histogram_y12bit/histogram_sha256 | Complete actual returned integer histogram in q11..q0 bit order, including unused outcomes; canonical sorted compact JSON SHA-256 |
| source_occurrences | Every returned measurement occurrence, distinct occurrence ID and reconstructed index, measured bitstring and four original tokens; duplicates retain distinct IDs |
| instrument_sources | Flute, Clarinet, Violin, Cello, Piano, in that order, four distinct assigned occurrence IDs each |
| unused_occurrence_ids | All remaining occurrences, twelve for the initial 32-shot execution |
| randomness | Decimal-string seed specified before submission; exact full PCG64 permutation; no favorable-result selection |
| warnings/errors/fallback | Explicit classical adaptation and measurement-memory limits; no fallback |

Tokens are decoded in original least-significant-register-first order:
`[q2q1q0, q5q4q3, q8q7q6, q11q10q9]`. Token zero is a rest. The source never discards
or replaces these tokens. Instrument register choices, repetition, harmony, cadence
and arrangement are classical operations performed after inference.

Occurrences are first reconstructed in sorted-bitstring order, then a single
`numpy.random.Generator(numpy.random.PCG64(seed)).permutation(total_shots)` chooses
their order without replacement. IDs are `{run_id}/m{reconstructed_index:04}`;
they denote histogram occurrences, not actual chronological measurement memory.
The first twenty permuted occurrences supply five parts; all others stay in source.
Repeating a theme musically is never another quantum measurement.

Frozen identities:

- Original checkpoint: `ecd7faaa232a15c261a5e3daf8047e0b4d71be9f4eb4bb597e70acb671c5b8a4`.
- Canonical parameters: `9c0e4f62413257d90d575300a1ce856143e728c637e1fc1c9e4ffdc9ce4c843a`.

`validate_source(source)` verifies the histogram hash, occurrence/token identities,
complete deterministic permutation, five assignments, unused occurrences and job
allocation. Arrangement and playback must preserve the exact original JSON text
and its bytes hash alongside their own classical output. They submit zero jobs.

Dependencies are existing NumPy/Qiskit and the existing component helper modules;
there is no music21, scipy, native audio stack, Gemini or additional model import.
The existing `quantum_models/qcbm_instrument.py` uses this same token order and
explicit classical instrumental decoding, but its desktop dependencies are not
imported into Qollab.

Local SDK serialization is not remote IonQ success. In SDK 1.0.2 noisy simulator
results may be integer histograms reconstructed from rounded provider probabilities;
the raw returned counts are preserved without claiming chronological independent
shot memory. This contract makes no statistical or musical-quality advantage claim.
