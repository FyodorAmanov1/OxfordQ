# qm.joint-cue-result.v1

This opt-in runtime representation is separate from unchanged `qm.run-result.v1`.
The original four/five-circuit executor and historical fixture are retained.

One frozen four-qubit circuit prepares Bell a/b and independent uniform coherent
cue registers x/y, then applies own-cue-only controlled measurement rotations.
Qubits q0=a, q1=b, q2=x, q3=y are measured into matching classical bits; displayed
counts are **yxba**. QIS decomposition H/CX/RY/RZ/X precedes exactly one supplied
simulator `backend.run(QuantumCircuit, shots=N)` call. A list is never submitted.
The Python executor rejects physical/unknown backends, preserves provider errors,
and blocks legacy multi-circuit selection on IonQ. No provider credentials,
replacement simulator, automatic retry or second QCBM job exists.

`joint_histogram_yxba` contains every returned integer shot, its canonical SHA-256
is `histogram_sha256`, and `statistics.allocation` retains actual Nxy, Wxy, ba
histograms and correlations for all four settings, including empty ones. Total
shots are not shots per setting. Uniform-setting success is sum(Wxy/Nxy)/4;
S=8p-4. Pooled W/N is reported separately. The conditional 95% weighted Hoeffding
radius is sqrt(log(40)/2 * sum(1/(16*Nxy))), clipped to [0,1]. Empty Nxy makes
conditional success/S/interval null; usable playback remains available. The
interval assumes independent fresh preparations and fixed channel, conditional
on allocations. Centrally generated coherent cues are not external independent
choices in a spacelike-separated Bell experiment. Ideal conditional equivalence
does not prove noise-model equivalence or hardware certification.

Before submission, two independent SeedSequence children commit sixteen shared
classical strategies (SHA-256 retained), and initialize the presentation RNG.
After measurement, a uniform permutation of the **complete measured multiset**
supplies the first sixteen entries without replacement, never a new cue draw or
a favorable-win filter. Both policies use each entry's same x/y and the identical
RECORDED M3A tokens, voices, tempo and mapping. Alice's classical response sees
only x and her two-entry function; Bob's sees y and his. Every rest/loss remains.
Run IDs derive from actual job IDs, paired round IDs and per-policy/voice event
IDs retain the measured bitstring, reconstructed index and source histogram hash.
Ordering is reconstructed, never claimed chronological hardware memory.

`execution` records actual supplied backend class/name, positive simulator
verification, IonQ class detection, runtime versions, job ID, result status,
requested/returned total shots, one circuit/one call, compiled gate counts, and
advertised limits. `expected_job_type` is serialization expectation, not an
observed remote request trace. Selector declarations are not IonQ evidence.
`base_melody` is always RECORDED with unchanged source/checkpoint identity.
The original JSON text is preserved by browser exports; MIDI carries run/job,
histogram, policy, round and event identity. Loading, playback, mode switches and
exports submit zero new jobs. Generation is guarded once per Qollab Run.

The browser separately validates allocations, estimates, hashes, precommitments,
sample-without-replacement identity, both local policies and direct musical
mapping. Central arrangement is unavailable for this new contract. Frozen
Composition remains a separate PRE-GENERATED recording without CHSH statistics.

Reproduce offline checks from this feature tree with its Python path first:

```powershell
$env:PYTHONPATH=(Join-Path $PWD 'components/quantum_duet/src')+';'+$PWD
python -m pytest -q tests components/quantum_duet/tests experiments/qcbm_composition/tests experiments/qcbm_refinement/tests --basetemp build/tests-fresh
python scripts/assess_duet_cue_circuit.py --out build/cue-assessment-fresh.json
node components/quantum_duet/tests/joint_cue_checks.mjs <verified-python-executable>
python components/quantum_duet/tools/build_qollab.py --with-composition --out build/ionq-upload-fresh
```

Build directory/ZIP must be fresh. Upload only to a separate private project;
select the displayed FREE IonQ simulator, begin at 32 total shots, generate once,
and preserve its actual returned counts before declaring platform success.
