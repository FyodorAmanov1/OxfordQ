# IonQ end-to-end readiness — 2026-10-11

**GO for the verified private single-circuit IonQ application. Public release,
main integration, video upload and captain submission still need authorization.**
The required real free-simulator execution succeeded, with returned counts,
functional quantum/classical playback and lossless exports. This is not a claim
that the legacy four/five-circuit IonQ batch works or that 32 shots establish a
statistically significant Bell violation.

## Immutable source and release boundary

- Feature branch: `codex/ionq-joint-cue-20261011`.
- Verified implementation/evidence commit: `800b9b8c3e6fc5d3aed952a4de9786cefb745fd2`.
  This report is committed separately; the final branch head is printed in the PR
  and coordinator response to avoid a circular self-hash.
- Parent: `db21e9e1324f9337ef4b229bfd5725960650cd70`, previously submitted readiness
  documentation atop approved PR #10 `0debfbc1a3effb962f6a9bc157798feb2c672359`.
- Initial main inspected: `c49c2e6cace0790211ae6808f4ecdc4cb77faa01`.
  PR #8 `f42bcf1e3db5a2cc7d86e82d4dc6c06a0c6a440d`, #9
  `2801ba46ed5acdc7fbf0d3cca635f50aa8a2b88c` were the pinned composition source.
  **Final fetch at 22:12 UTC detected concurrent external changes**: remote main
  is now `d8214741ba69167c90939347646c9371edc055cd` (Graph Composer/PR #11),
  and PR #10 was merged into PR #9's branch at
  `d43d7cc607c99f8f5ba0cb246e61bcea899b2762` around 21:43 UTC. PR #8 and #9
  remain open/draft. PR #10's source branch still points to the exact approved
  `0debfbc...` commit. None of these external changes were applied here; this
  session merged nothing and the coordinator checkout stayed clean. Test results
  below cover the isolated candidate, not the newly advanced main.
- Isolated worktree: `build/ionq-e2e-20261011` under the coordinator checkout.
  No worker worktree was modified. Unrelated repository branches were excluded.
- Private candidate: <https://qollab.xyz/u/Floris/oxfordq-ionq-joint-cue-verific#run>.
- Existing approved showcase: <https://qollab.xyz/u/Floris/oxfordq-composition-verificati>.
  Its exact PR #10 source was left unchanged. Previously authorized publication
  completed as **v1.0 / Public / Default**, verified in the actual Chrome project
  card on October 11 around 22:06 UTC. Prepared page copy and release notes retain
  the legacy IonQ limitation and exact PR #10 source link. Publication did not
  open or submit the hackathon captain form. The public version page was accessible
  in the authenticated browser; anonymous access was not independently tested
  (the web reader could not retrieve this dynamic project page).
- Rollback project <https://qollab.xyz/u/Floris/quantum-duet#code> remains untouched.

## Official requirements and actual platform

Official pages were inspected in supported Chrome, including the account's
actual Select QPU dialog, before the remote jobs:
[terms](https://qollab.xyz/programs/hackathon/terms),
[how it works](https://qollab.xyz/programs/hackathon/how-it-works),
[runtime](https://qollab.xyz/learn/docs/runtime-environment), and
[compute backends](https://qollab.xyz/learn/docs/compute-backends).

The required runnable free simulator includes IonQ. The selected account option
was **FREE IonQ Aria 1 (25q), Noise model, Free**, positively observed before each
job. It supplied `qiskit_ionq.ionq_backend.IonQSimulatorBackend`, named
`ionq_simulator`, with `noise_model=aria-1`, `gateset=qis` in the complete app.
Physical/credit hardware was never selected. Other free simulator options were
visible, but no provider substitution was attempted.

The runtime allows **one backend job per Qollab Run**, at most **100 files**, and
**2 MB per file**. The existing multi-circuit path historically exceeded the
accepted `ionq.circuit.v1` representation; this task neither assumed that changed
nor resubmitted it. Actual account free quota and provider maximum shots were
not advertised. Successful 32-shot requests establish only that tested size;
the app's 16–4096 input range is not evidence of a free quota. SDK max_shots and
max_circuits were null; its generic max_qubits=29 differs from the displayed Aria
25-qubit option. The four-qubit circuit fits both.

Actual Qollab runtime: **Python 3.14.2, Qiskit 2.5.2, qiskit-ionq 1.0.2,
NumPy 2.4.6**. Local verification: Python 3.12.14, Qiskit 2.5.2,
qiskit-ionq 1.0.2; Node 16.13.2 for the existing compatible test harness.
The asynchronous documented `.callPromising` bridge ran successfully in Chrome.

The deadline is October 11 19:00 Eastern / **23:00 UTC**. Eligibility still needs
the captain to confirm registration/team association, public runnable code,
required licenses/attribution and pre-existing work disclosure, a publicly
accessible **2–3 minute video**, and the captain form. Public availability must
continue for the stated twelve months. No video or form was submitted here.

## Implementation and scientific boundary

`quantum_duet/joint_cue.py` reuses the previously verified four-qubit design:
q0=a, q1=b form the Bell pair; q2=x, q3=y start in independent |+> states.
Own-cue-only controlled RY rotations use the unchanged frozen [A0,A1,B0,B1]
angles. QIS transpilation produces H×3, CX×5, RY×4 and four measurements, with
qi mapped to ci; displayed bits are **yxba**. Exactly one compiled
`QuantumCircuit` object is passed to the supplied backend's `run`, never a list.
No new provider, credentials, QCBM sampling, retry or fallback is introduced.
Physical/unknown backends fail before submission; legacy batches fail before
submission when supplied IonQ is detected.

`qm.joint-cue-result.v1` is explicitly separate from unchanged `qm.run-result.v1`.
It stores the full histogram/hash, actual Nxy and Wxy, correlations, uniform
setting estimate `p=sum(Wxy/Nxy)/4`, `S=8p-4`, and pooled W/N separately.
The weighted conditional Hoeffding radius is
`sqrt(log(40)/2 * sum(1/(16*Nxy)))`. Empty groups yield null conditional
statistics and usable raw playback, without another job. The interval assumes
independent fresh preparations and a fixed channel conditional on allocation.
It is not hardware certification, a speedup result or musical-quality evidence.

Important SDK limitation: installed qiskit-ionq 1.0.2 uses its random sampler for
`noise_model=ideal`, but maps other models' returned probabilities to integers
with `round(probability*shots)`. We preserve the supplied SDK's integer counts
and enforce exact total accounting; no raw per-shot chronology or independent
provider wire trace was available. Consequently, the displayed interval is an
assumption-based calculation, not a verified confidence guarantee for Aria's
internal noise simulation or proof that SDK rounding preserves an independent
sampling law. Actual Qollab's visible probabilities matched the returned 1/32
count fractions. No scientific significance claim is made for these jobs.

Cues are generated centrally inside a coherent simulation, not by external
spacelike-separated choices. Ideal conditional equivalence does not imply
noise-model equivalence to four separately compiled circuits.

Before submission, independent RNG streams precommit sixteen shared classical
strategies and the presentation RNG. After return, a uniform permutation of the
complete measured multiset supplies the first sixteen entries without replacement.
There is no second cue draw, favorable-result selection or discarded loss.
The classical comparator uses those same cues, independently committed local
functions, identical RECORDED M3A tokens, voice mapping, tempo and synthesis.
All rests, run/round/event identities and histogram lineage remain present.
This is reconstructed order, not chronological measurement memory.

The interface explicitly selects joint cues, retains built-in-only legacy
choices, validates the new contract separately, and guards generation once per
Run. Its actual source label is **LIVE IonQ simulator coordination + RECORDED
QCBM melody**, derived from supplied backend metadata. Optional central
arrangement is unavailable for the new contract; raw coordination bypasses it.
Frozen PRE-GENERATED Composition remains separate and carries no CHSH claims.

## Actual fresh remote executions

Both runs used the observed free Aria 1 option. The diagnostic succeeded first;
the complete application then used a **new deliberate Qollab Run**, not a retry.
Two accepted jobs total, 32 requested/returned shots each. Playback/exports/mode
switches and recorded replay added **zero backend submissions**.

| Evidence | Diagnostic | Complete application |
|---|---|---|
| Job ID | `01a12cf0-11ac-7c0a-ba52-ad10bfb1377f` | `01a12cf4-020b-77a7-a0f0-d6b3b8f5b56e` |
| Result UTC | 2026-10-11T21:48:25.167000+00:00 | 2026-10-11T21:52:43.638000+00:00 |
| Calls / circuits / shots | 1 / 1 / 32 | 1 / 1 / 32 |
| N00,N01,N10,N11 | 3,12,5,12 | 8,7,8,9 |
| W00,W01,W10,W11 | 2,11,5,10 | 4,5,7,9 |
| Uniform-setting p | 0.8541666666666666 | 0.7723214285714286 |
| S | 2.833333333333333 | 2.178571428571429 |
| Pooled success | 0.875 | 0.78125 |
| Conditional interval | [0.5700993541177879,1] | [0.531289912375597,1] |

Full **yxba** histograms (omitted keys have zero counts):

```json
{
  "diagnostic": {"0001":1,"0011":2,"0100":2,"0111":3,"1000":4,"1001":1,"1011":7,"1100":1,"1101":5,"1110":5,"1111":1},
  "application": {"0000":1,"0001":2,"0010":2,"0011":3,"0100":3,"0110":1,"0111":4,"1000":2,"1001":2,"1011":3,"1101":2,"1110":7}
}
```

Application status: result_success=true, experiment_success=true,
job_status=`JobStatus.DONE`. SDK's optional result.status was unpopulated (`None`);
this was not mistaken for a failed job. The diagnostic precedes the added
explicit success/status metadata, but returned a complete valid histogram.
Both original raw JSON strings are saved verbatim in
`components/quantum_duet/evidence/joint-cue/`. Offline serialization verified
`ionq.circuit.v1`; the remote wire job-type field was not independently observable.
Acceptance is supported by actual returned results, not serialization alone.

## Newly executed verification

- Final complete Python suite at approximately **22:08 UTC: 196 passed in 21.64 s**,
  including **35 joint-cue tests**. All original scientific expectations remained.
- All five Node checks passed at **22:08 UTC**: UI/audio lifecycle,
  worker-C contract/MIDI, real raw/arranged duet projection, frozen Composition,
  and new joint-cue validator/mounted UI. Node tests use mocked DOM/audio where
  stated; these are separate from the actual Chrome/Qollab checks below.
- Existing feasibility script rerun at **22:10 UTC**: maximum
  conditional error **2.7755575615628914e-16** for reference/frozen/arbitrary
  angles, P(x,y)=1/4, compiled statevector equality, QIS serialization and
  measurement ordering passed. Local-only 4096-shot allocation with seed 32003
  was 1056,1001,1038,1001; p=0.8495957919729596. This was not an IonQ remote job.
- Both original orchestration CLI examples passed with `--backend rules
  --bars 4 --no-audio`; original/baseline/arranged MIDI and JSON were produced.
  Existing flat-chord inference limitation remains unchanged; no musical fix
  or new model was introduced.
- Focused tests check one object/one call, all sixteen bit decodes, unequal/zero
  groups, precommitment timing, independent strategies, source/rest preservation,
  unknown/physical backend rejection, provider failure/shot mismatch without
  retry, and exact offline replay of both actual IonQ results.
- Actual Chrome/Qollab quantum and corresponding classical playback both
  scheduled 30 sounding notes (two retained rests), eight seconds at 120 BPM.
  Comparison changes and Stop worked. Generation remained disabled after the
  one app job, including after import/replay/export.
- Both actual duet MIDI exports decoded losslessly through the existing decoder
  and matched the browser encoder byte-for-byte; independent Mido parsing
  verified three tracks, PPQ 480, note onsets/ends/velocities and 7680 end ticks.
  JSON export retained the exact original raw source string and job identity.
- Both frozen 32-second Composition recordings actually played in Chrome.
  Seeking worked; changing texture reset/paused playback; the arranged recording
  reached ended=true; switching to Experiment stopped Composition. Both MIDI
  exports matched canonical bytes. The complete 249,283-character provenance
  export decoded with original raw_samples_text/trace_text and hashes unchanged.
- Original RECORDED fixture loaded at 85.89%, 4096 historical shots, zero calls
  this replay. The actual live app result was then restored by import, with zero
  jobs, for handoff. Human-approved Composition quality remains unchanged;
  this verification makes no additional listening-quality judgment.

Earlier infrastructure failures were corrected and distinguished from application
results: sandbox blocked the existing preview test's loopback port (193 pass/1
fail); authorized unrestricted reruns passed. A missing pytest temp parent was
created. Node 24 conflicted with an existing test's global.crypto assignment,
so the established Node 16 harness was used. Initial large browser textarea
capture was truncated; bounded chunks captured the complete provenance, which
then decoded exactly. Native sandbox downloads were not independently saved;
the visible lossless payload route was exercised and verified instead. Browser
upload delay was not a backend error. No failed remote job or hidden retry occurred.

## Package and preserved identities

Canonical generated upload: `build/ionq-candidate-final.zip` in the isolated
worktree, **36 files, 3,288,267 uncompressed bytes, largest file 1,411,244 bytes**.
All 35 manifest-listed file hashes matched; manifest itself is excluded from its
own file list to avoid circular hashing. Generated build files are not committed.

- ZIP SHA-256: `d29fd7525a6b8890886a4b74ce171b58f41776ca011034e9546636b5b132ad0a`.
- Manifest byte SHA-256: `b89fb43b6b1efdd316021ca337e3326263d7fd40ae0985fa6be618d56b3b2c7e`.
- Diagnostic raw JSON byte SHA-256: `c8eda2bfff5c77fd6db6f6d290714fc92bce374c40f14d1bd580ffc9d627e871`.
- Application raw JSON byte SHA-256: `f25708db79a0d9301b019a6a9562736a488b1cadef146342d365580fccc1cfaa`.
- Application histogram canonical SHA-256: `3863e597553ae0cce7ef113e1aaf068c34dd4002802457f14883a073751614b5`.
- Quantum MIDI SHA-256: `8c06d9d42ee9939e794b0e11f87d08b8cc57c226df587abe9029e35b47fd545e`.
- Classical MIDI SHA-256: `24fc907792991a591d7ccb3d32d3d8243c1cf9ce6616d994da5fa6ba79502948`.

No new dependency is required: Qollab supplies Qiskit/NumPy and the IonQ backend;
the ZIP contains the necessary Python modules and browser scripts with literal
data paths. Optional CPython orchestrator/music21/Pydantic modules remain local.
The private scratch retains one unused default template `main.py`, because the
unpack Replace dialog would permanently delete it; that action was cancelled
and Keep-and-add used. HTML/JS is the active entry, as actually executed. Thus
the scratch has one extra dormant file; the clean canonical ZIP has 36 files.
No template/source removal or permanent deletion was performed.

All frozen Composition manifest hashes passed; both WAVs/MIDIs, raw samples,
trace and freeze manifest are unchanged. Old backend/CHSH modules, trained angles,
QCBM weights, musical mapping, old run contract/projection and historical fixture
were not edited. New code is isolated in joint_cue.py/joint-cue-contract.mjs,
focused tests/export verifier/evidence, and four small browser integration edits.

## Reproduce without remote jobs

Use a fresh output/temp path, in this feature checkout, with its Python path first
(an editable installation in another checkout otherwise points to old code):

```powershell
$env:PYTHONPATH=(Join-Path $PWD 'components/quantum_duet/src')+';'+$PWD
python -m pytest -q tests components/quantum_duet/tests experiments/qcbm_composition/tests experiments/qcbm_refinement/tests --basetemp build/tests-review-fresh
node components/quantum_duet/tests/ui_checks.mjs
node components/quantum_duet/tests/ui_c/contract_checks.mjs
node tests/duet_projection_checks.mjs <verified-python-executable>
node tests/composition_mode_checks.mjs
node components/quantum_duet/tests/joint_cue_checks.mjs <verified-python-executable>
python scripts/assess_duet_cue_circuit.py
python -m orchestrator --generation-manifest examples/generation.json --backend rules --bars 4 --no-audio --out build/cli-generation-review
python -m orchestrator --manifest examples/note_events.json --backend rules --bars 4 --no-audio --out build/cli-events-review
node components/quantum_duet/tools/verify_joint_exports.mjs components/quantum_duet/evidence/joint-cue/application-browser-export.json components/quantum_duet/evidence/joint-cue/quantum-duet-raw-quantum.mid components/quantum_duet/evidence/joint-cue/quantum-duet-raw-classical.mid
python components/quantum_duet/tools/build_qollab.py --with-composition --out build/ionq-upload-review-fresh
```

ZIP byte hashes can change with filesystem timestamps; compare manifest content
hashes to identify an equivalent rebuild. Remote verification would need a new
explicit Run and free-status/quota check, but no further execution is needed for
the initial demonstrated acceptance or to play/export the saved result.

## Remaining release decision and video handoff

**IonQ compatibility: GO for this exact private build. Overall submission:
NOT COMPLETE / hold for release approval, video and captain form.** Recommend
releasing the new verified candidate after approval, preserving the existing
public v1.0 as rollback. Main integration must separately handle the still-open
#8 → #9 stack (which now includes #10), then reconcile concurrent main changes
to shared UI/projection/orchestration files before this feature. The draft feature
targets the exact pinned PR #10 source branch for a bounded review; it must not
be merged into main by blindly retargeting. No deadline-driven silent merge is proposed.

The existing 2:40 storyboard remains in `SUBMISSION-MATERIALS.md`. After approval
to publish the new candidate, replace only its 0:55–1:15 segment/old IonQ paragraph
with the following accurate candidate copy:

> A real Qollab Free IonQ Aria 1 noise-model simulator run returned 32 outcomes
> from one four-qubit joint-cue circuit in one job. Both quantum and local
> classical duet playback and lossless MIDI/provenance exports were verified.
> Coordination is LIVE simulator evidence; the base QCBM melody is RECORDED.
> Actual setting allocations were 8,7,8,9, with a uniform-setting estimate of
> 77.23% and a wide assumption-based interval. This verifies execution, not a
> significant Bell violation, hardware certification, speedup or superior music.
> The separately accepted 16-bar Composition is PRE-GENERATED and runs no jobs.

Keep source/job labels visible in the video and use this saved result, not a
favorable new sample. No supported screen-and-system-audio recording was performed
here, and no video URL exists. The user must record/approve hosting of the required
2–3 minute video and authorize the captain submission separately. Public copy
asserting the new result and publication of the modified build are not yet
authorized. Do not submit the form, upload a video, merge or publish this new
application as part of this review.
