# Fresh frozen QCBM inference — Agent C

Starting revision: `f9f1f38462fec38cf258f541f14add538bf5713a` (verified PR #12).
Isolated branch: `codex/fresh-qcbm-20261011`. No existing source, model, raw contract,
CHSH implementation, shared UI or canonical Qollab release was changed.

Implemented `fresh_qcbm.py` and the independent `qm.fresh-qcbm-source.v1` contract.
One frozen twelve-qubit, 84-parameter measured circuit is decomposed into supported
IonQ QIS gates and passed as a single object in one supplied-simulator call. Complete
returned counts, exact checkpoint identities, job provenance and all occurrence
identities are retained. A predeclared seed 20261011 permutes all histogram
occurrences, without favorable-result filtering. Twenty draws supply four motifs
per Flute/Clarinet/Violin/Cello/Piano; twelve remain unused at 32 shots. All five
share the same trained model. Tokens equal zero remain explicit rests.

New focused verification executed 2026-10-11 approximately 22:29 UTC:

```powershell
$env:PYTHONPATH=(Join-Path $PWD 'components/quantum_duet/src')+';'+$PWD
& 'C:\Users\flori\source\OxfordQ-quantum-duet\.venv-final\Scripts\python.exe' -m pytest -q components/quantum_duet/tests/test_fresh_qcbm.py --basetemp build/fresh-tests
```

Result: **17 passed in 2.29 seconds**. Checks cover frozen hashes, all measurement
bit mappings, full statevector equivalence after compilation, real SDK 1.0.2
serialization with network explicitly forbidden, token order, all occurrences and
unused draws, duplicate identities, rests, deterministic reconstruction, invalid
counts, rejected changed checkpoint, unknown provider and no retry after failure.

An initial run had 16 passes and one temporary-directory setup error; creating the
fresh ignored build parent corrected it. The first SDK test constructed a provider
and attempted metadata access (network denied); it was replaced by the same offline
SDK serialization technique as the existing joint-cue tests. The final test forbids
network calls explicitly, so no provider job is submitted by that test.

Actual LOCAL BasicSimulator 32-shot generation also completed, saved as ignored
`build/local-source.json` for Agent D's direct contract acceptance. Local statevector
and BasicSimulator success are **not actual free IonQ evidence**. The coordinator
owns the separately authorized browser check, current free selection and private
fresh-music candidate. Do not label this new feature IonQ verified until that job
actually succeeds. No browser operation or public release was performed by Agent C.

The complete component suite, including the new tests, also passed: **142 passed
in 19.92 seconds**. Compiled operations are H59/RY48/RZ47/CX36/measure12.

An important simulator SDK limitation was checked locally at approximately 22:30
UTC: the frozen ideal statevector's maximum outcome probability is
0.009123182307412268, and independently rounding every probability times32 produces
zero integer counts for every outcome. SDK1.0.2's noisy-IonQ result conversion is
known to use probability rounding rather than chronological shot memory. Thus a
32-shot noisy Aria result may be accepted remotely yet yield insufficient/zero SDK
counts. This is a prospective compatibility risk, **not an observed remote failure**.
The module rejects insufficient counts and preserves returned histogram diagnostics;
it never draws invented replacement measurements, requests more shots automatically
or silently changes the selected noise model. The coordinator was informed before
the actual platform job. A separately selected built-in-simulator test is permissible
if the free IonQ operation fails, with clear platform labels.

The new module needs the existing component helpers, frozen melody JSON, Qiskit and
NumPy only; it does not import music21 or the desktop sound stack. For Qollab the
coordinator must include it in the generated package, supply `data/melody_angles.json`
and invoke it from a fresh Run that does not launch CHSH. Agent D's source-preserving
composition accepts the independently documented source envelope and adds only
classical development. Public publication, merges and entry submission remain
separate approvals.
