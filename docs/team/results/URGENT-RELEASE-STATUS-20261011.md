# Urgent OxfordQ release status — 2026-10-11

Verified at approximately **22:43 UTC**, before the 22:45 feature cutoff.
Three actual Codex workers ran concurrently; the coordinator handled A because
only three worker slots were available alongside the coordinator. All workers
had separate clean worktrees/branches and disjoint file ownership. No merge,
force push, paid execution, video upload or captain submission occurred.

| Workstream | Actual result | Source | Remaining boundary |
|---|---|---|---|
| A / coordinator | Exact PR #12 published as separate v1.0 public/default project. Public page and main.js readable without sign-in; Sign in displayed in separate browser. | f9f1f38462fec38cf258f541f14add538bf5713a | Existing PR #10 public v1.0 untouched; no automatic entry submission |
| B | Truthful project copy, 2:40 video script and captain checklist completed. User explicitly said they will do video without Codex. | 43f129a0b5893d5a4e8561e4df19000557461f4d | No video file/public URL supplied; no upload or form submission |
| C | Actual fresh frozen 12-qubit QCBM succeeded on FREE IonQ Aria 1, 32 returned counts, one circuit/object/call. | bb842ed1dbabd6098f5da79068d638c88c6fdc89 | SDK probability/count representation limits disclosed; no hardware claim |
| D | Compact existing-rule extraction produced five parts, correct GM programs, 16 bars/32 seconds, MIDI and complete classical lineage. | 71335142a56337c6705f2fb0372847e1655a8a34 + 081596c75681838187731e83ba605ae62df84780 | Human musical assessment pending; simple oscillators are not acoustic samples |
| Coordinator | Private Generate → Compose → Play → Export passed on actual IonQ source; lossless exports reproduced locally with zero additional jobs. | codex/fresh-music-integration-20261011, based on exact PR #12 | Private experimental surface; teammate UI still in progress; publication needs separate approval |

## Published submission-safe release

**Public URL:** <https://qollab.xyz/u/Floris/oxfordq-ionq-joint-cue-verific>.
Unchanged rollback: <https://qollab.xyz/u/Floris/oxfordq-composition-verificati>.

Before publication, freshly verified PR #12 head equals f9f1f384...; all 35
original manifest entries, manifest bytes and original ZIP hashes match. Uploaded
main.js and joint_cue.py were copied through the editor and matched the original
package text exactly. The file tree reported Uploaded 36 files, and no runtime
source upload/edit occurred. The existing dormant template main.py remains as in
the tested private project; HTML/JS is the actual entry. Only authorized project
copy/repository/about/release notes were added, including simulator, inconclusive
32-shot result, recorded melody, pre-generated composition, MIT notices, existing
code/AI disclosures and Qollab/IonQ attribution. Publication controls exposed only
version/visibility/notes, not a hackathon submission action. v1.0/Public/Default
was observed after publication; anonymous project page and source access passed
in the separate browser whose navigation showed Sign in. No authentication or
security controls were disabled.

Original ZIP SHA-256:
`d29fd7525a6b8890886a4b74ce171b58f41776ca011034e9546636b5b132ad0a`.
Original manifest SHA-256:
`b89fb43b6b1efdd316021ca337e3326263d7fd40ae0985fa6be618d56b3b2c7e`.
Source/date/job evidence remains in `IONQ-END-TO-END-READINESS.md` and the
joint-cue evidence directory. No new CHSH job was submitted in this urgent turn.

## Actual fresh QCBM execution and five-part private workflow

**Private URL:** <https://qollab.xyz/u/Floris/oxfordq-fresh-music-verificati#run>.

- Actual FREE option observed: **IonQ Aria 1 (25q) Noise model Free**.
- Job **01a12d1e-0398-78eb-a4ae-16e82466b52b**, result UTC
  **2026-10-11T22:38:36.232999+00:00**.
- Backend `qiskit_ionq.ionq_backend.IonQSimulatorBackend`, `ionq_simulator`,
  `noise_model=aria-1`, `gateset=qis`; result/experiment success true, job DONE.
- Actual Python 3.14.2, Qiskit 2.5.2, qiskit-ionq 1.0.2, NumPy 2.4.6.
- One compiled twelve-qubit QuantumCircuit object, one backend.run, 32 requested
  and 32 returned shots; H59/RY48/RZ47/CX36/measurement12. No CHSH circuit or
  second QCBM job. Wire type independently observed only in offline SDK check
  (`ionq.circuit.v1`), not an invented remote transport trace.
- Original checkpoint SHA-256
  `ecd7faaa232a15c261a5e3daf8047e0b4d71be9f4eb4bb597e70acb671c5b8a4`;
  exact frozen 84-angle parameter SHA-256
  `9c0e4f62413257d90d575300a1ce856143e728c637e1fc1c9e4ffdc9ce4c843a`.
- All 32 measured histogram occurrences and 128 tokens preserved, including
  duplicate bitstrings with distinct occurrence IDs. Prespecified PCG64 seed
  **20261011** permutes the complete multiset; first twenty distinct occurrences
  supply four motifs each to Flute/Clarinet/Violin/Cello/Piano; twelve unused
  occurrences remain. No favorable-result selection or chronological-memory claim.
- Composition preserves source JSON byte-for-byte, source/event IDs and rests.
  Theme reuse, register, C-major harmonic projection, rhythm, gate, dynamics and
  cadences are explicitly classical; all five parts share one frozen checkpoint.
  No CHSH statistic is attached to composition notes.
- Actual browser Generate/Compose/Play/Stop/export passed. **414 sounding notes**
  were scheduled across five tracks. Source/score JSON capture was complete at
  **378,254 characters**; both JSON and MIDI decoded/reproduced exactly. MIDI is
  type 1, conductor plus five parts, PPQ480, correct programs [73,71,40,42,0],
  and **32.0 seconds** independently parsed with Mido.
- Compose, play, stop, JSON/MIDI export and offline verification add zero jobs.
  Generate remained disabled after its one attempt. No retry, substitution or
  additional sample was made. The anticipated low-shot SDK rounding failure did
  **not** occur in this actual Qollab run; do not generalize success to all
  providers/shot sizes or claim SDK counts are chronological hardware memory.

Actual source/score/MIDI are saved in
`components/quantum_duet/evidence/fresh-music/`. Exact source byte SHA-256:
`020d4abd5b87b0ce3a6bf6a83a16d2fbcc6713bb7c7920e5d60be173433c3cad`.
Full histogram canonical SHA-256:
`79705a4304fe99fdd26c1f623c818c10a51596fdf2bdbe51c4fb49cd171dab77`.
MIDI SHA-256:
`cf00997fafa43d76e961df731f561cbaf63e8a049f635b41df0633ca42bbc0bd`.

## Verification, packaging and integration risks

- Final isolated pinned-release integration Python suite: **227 passed in 17.14s**,
  approximately 22:43 UTC. Earlier combined run was 226 passed in 16.98s before
  adding the actual captured-result regression. C's 17 focused tests and D's 12
  focused tests passed; two coordinator bridge/export tests passed in the full suite.
- All **five existing Node suites** passed at approximately 22:37 UTC; new
  standalone entry syntax passed. Actual browser verification above is separate
  from the mocked Node DOM/audio tests.
- D also tested its concurrent latest-main base d8214741...: **226 passed, 28
  failed** in 33.41s. Those existing desktop-composition fixtures fail because the
  default now includes Piano without fixture source motifs, plus error-text
  expectations. These failures were not hidden or changed; no claim that current
  main passes. This integration uses pinned PR #12 plus additive C/D code, not
  a blind merge of concurrent main or desktop runtime dependencies.
- New clean private package: `build/fresh-qollab.zip`, **22 files / 88,212 bytes**,
  largest **14,703 bytes**, all under Qollab's 100-file/2 MB-per-file limits.
  ZIP SHA-256 `8b8f757335425a3c7caa5ee96becd0c943ff3072852a9e08315dc039d6b46881`.
  Manifest byte SHA-256
  `dfea2030b78fd732c03218456ba859b1f9837622d3fddd19deb04906309ca3b7`.
- No new dependency, sound library, desktop orchestrator import, Gemini, POP909,
  retraining or paid hardware. A small stdlib extraction of existing planner,
  compiler and performer rules supplies orchestration. Native sandbox downloads
  remain uncertified; visible lossless MIDI/JSON payloads were actually recovered.
- Root added a separate `fresh_web/` private test page and bridge/builder. No
  teammate/shared `web/` file was edited. The original release builder excludes
  new experimental modules; its regenerated **36-file manifest is byte-identical**
  to the published release. Existing models, scientific evidence, mappings and
  accepted Composition assets remain unchanged.
- Teammate UI handoff is still pending according to the user. Do not replace their
  implementation or silently treat this plain private test surface as their UI.
  Musical quality of this new piece is pending human listening; the accepted
  PRE-GENERATED recording remains the public fallback/reference.

## Submission handoff / stop boundary

Official how-it-works page freshly read around 22:41 UTC confirms public MIT
Qiskit project runnable on free simulators including IonQ, existing-code disclosure,
public no-sign-in 2–3 minute video, and **Oct 11 19:00 ET / 23:00 UTC** deadline.
Its expanded FAQ confirms: captain submits from
<https://qollab.xyz/programs/hackathon/register>; up to five public projects owned
by captain or joined teammate; edits until deadline; only captain submits or
withdraws. The actual submission form was not filled or submitted here.

User is handling video without Codex. No public video URL was provided. Captain
registration/ownership eligibility still needs human confirmation, public-video
verification and separately authorized final submission. The published PR #12
release is available now and must not be delayed by new feature work.

**GO:** exact approved public IonQ duet, and actual private fresh QCBM → five-part
composition functionality. **HOLD:** new candidate publication, teammate UI
integration, main merges, video upload and captain entry, pending their respective
handoffs/authorizations. Feature implementation is frozen; no further model,
sampling, musical changes or backend submissions are required for this result.
