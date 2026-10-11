# OxfordQ submission materials — Phase 0, 2026-10-11

Prepared for source `0debfbc1a3effb962f6a9bc157798feb2c672359`. This is approval-ready
copy and a capture plan, not a published project page, video or submission.

## Project-page copy

### OxfordQ: hear quantum coordination, inspect its source

OxfordQ makes the CHSH coordination game audible through two musical voices.
Alice and Bob each receive only their own cue and use fixed local musical rules.
A trained Bell-pair strategy is compared with noncommunicating classical policies
that may share randomness. The interface keeps full-count evidence separate from
the short musical excerpt, with the same voices, tempo and playback controls for
both comparisons.

Under this restricted protocol, the local classical success bound is 75%, and
ideal quantum success is approximately 85.355%. Unrestricted centralized
classical coordination with both cues can reach 100%. This centrally simulated
demonstration establishes neither quantum computational speedup nor a
musical-quality advantage, and is not a loophole-free Bell test.

The optional Composition mode presents a frozen, **PRE-GENERATED** sixteen-bar,
32-second piece at 120 BPM. Its source is sixteen saved four-note motifs from the
existing trained 12-qubit QCBM's exact offline statevector distribution, using
NumPy PCG64 seed 20261011. All sixteen draws and 64 tokens were retained, without
favorable-sample filtering. The A–A′–B–A″ structure, repetition, rhythm, register,
cadences, harmony, accompaniment and dynamics are classical musical development.
Twenty positions replaced by the fixed repetition schedule are explicitly listed
in the trace; the original samples remain available. Accompaniment does not change
the developed melody. Audio is rendered by an additive synthesizer, not an acoustic
instrument recording or a trained instrument-specific model.

The user listened to and accepted this version for the demonstration on October
11. That is subjective listening feedback, not a scientific quality result. The
historical trace's earlier pending-assessment text is preserved and explained by
the separate freeze manifest. Composition playback, seeking and exports run no
sampling, training or quantum jobs and do not execute on the selected backend.
CHSH statistics describe Experiment mode only.

### Run the Qollab demonstration

1. Use a recent supported Chrome/Edge browser. Choose the **free built-in simulator**
   and press Qollab Run. No paid hardware or external API is required.
2. In Experiment, choose **Load RECORDED Qollab fixture** for reliable replay. It
   is labelled RECORDED, preserves the historical 4,096 CHSH shots and submits no
   new job. Play Quantum, stop, then choose Local classical and play again.
3. For a new Experiment take, use Qollab Stop → Run, explicitly choose the free
   built-in simulator, choose a batch and shot count, declare the simulator type
   accurately and click Generate once. A five-circuit batch uses one job. Errors
   remain errors; there is no provider substitution or automatic retry.
4. Choose **Composition · PRE-GENERATED**, then Melody only or Melody with
   accompaniment. Native audio controls provide play/pause and seeking. Changing
   modes or recordings stops previous audio. This recording remains the same on
   every run.
5. Export MIDI or provenance. If the sandbox blocks native downloads, copy the
   visible lossless payload or console export envelope and use the documented
   decoder. Composition JSON preserves the original sample/trace strings and hashes.

Verified here: recorded replay, composition playback/exports and a complete
five-circuit job on the Qollab built-in simulator. **The full four/five-circuit
Duet workflow on free IonQ remains unverified and historically rejected by the
platform job-type boundary.** A separate 32-shot single-circuit IonQ diagnostic
succeeded; it does not certify the Duet batch. No hardware success is claimed.
The current live platform route uses the preserved legacy take schema and labels
it as such; the recorded shared `qm.run-result.v1` envelope remains unchanged.

### Reproduce the exact showcase locally

```powershell
git clone https://github.com/FyodorAmanov1/OxfordQ.git
cd OxfordQ
git checkout 0debfbc1a3effb962f6a9bc157798feb2c672359
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r experiments/qcbm_composition/requirements.txt
.venv/Scripts/python.exe -m pip install -e . -e components/quantum_duet
.venv/Scripts/python.exe components/quantum_duet/tools/build_qollab.py --with-composition --out components/quantum_duet/build/showcase-fresh
.venv/Scripts/python.exe -m components.quantum_duet.dev.composition_preview --directory components/quantum_duet/build/showcase-fresh --port 8782
```

Open http://127.0.0.1:8782/. This loopback preview deliberately supports recorded
Experiment and bundled Composition only; it does not substitute a local backend
for Qollab's supplied backend. Building/loading the frozen example performs no
sampling. Use a fresh output path; existing outputs are never overwritten.
These installation commands are reproduction instructions; a clean installation
was not executed in Phase 0. The resolved verification environment is recorded
in the readiness report.

For a copied composition payload:

```powershell
.venv/Scripts/python.exe components/quantum_duet/tools/extract_composition_exports.py copied-payload.txt --filename oxfordq-composition-arranged.mid --output-dir recovered-new
```

For JSON use `--filename oxfordq-composition-provenance.json`. For whole console
envelopes omit `--filename`. Existing outputs cause an explicit error.
Duet exports use the separate `scripts/extract_duet_exports.py` utility.

### Pre-existing code and attribution

The starting orchestration application, Quantum Motif experiments, first Quantum
Duet implementation, trained Bell angles, 12-qubit QCBM weights and musical mapping
predate the official build window. They were reused rather than retrained. Import
or verification timestamps are not evidence of original authorship. The CHSH game
and quantum bound are established results, not new discoveries.

The October 10–11 contribution is the reviewed backend/adapter/interface
integration, explicit raw/creative boundary, paired source provenance, platform
packaging and verification, export compatibility, offline sixteen-bar composition,
classical refinement and isolated pre-generated showcase. See the exact commits
and completion reports below. AI coding assistance was used in development and
coordination; the frozen showcase uses no paid AI planning API.

Original repository code/documentation retain their MIT notices, including
Copyright (c) 2026 Fyodor Amanov. Qiskit is Apache-2.0; NumPy is BSD-3-Clause.
Qollab installs these dependencies rather than redistributing their packages in
the upload. Local MIDI tooling uses Mido (MIT), and local optional orchestration
uses music21 (BSD software license), Pydantic (MIT) and the Google GenAI SDK
(Apache-2.0). Each dependency retains its own license; runtime playback adds no
new dependency.

The reused model's Bach-derived training provenance refers to Johann Sebastian
Bach's Riemenschneider chorales and the music21 corpus, whose MusicXML editions
credit Margaret Greentree. `SOURCE_NOTICES.md` preserves the distinction between
compositions, encoded editions, software and derived data. No corpus MusicXML,
held-out motifs, native samples or retraining pipeline is bundled; the project's
MIT license does not relicense third-party editions or derived data.

**This effort is supported by Qollab & IonQ.**

### Source links

- Repository: https://github.com/FyodorAmanov1/OxfordQ
- Exact showcase: https://github.com/FyodorAmanov1/OxfordQ/tree/0debfbc1a3effb962f6a9bc157798feb2c672359
- Original composition: https://github.com/FyodorAmanov1/OxfordQ/pull/8
- Accepted refinement: https://github.com/FyodorAmanov1/OxfordQ/pull/9
- Optional UI: https://github.com/FyodorAmanov1/OxfordQ/pull/10
- License/notices: `LICENSE`, `components/quantum_duet/SOURCE_NOTICES.md`,
  `components/quantum_duet/DEPLOYMENT_NOTES.md` at the exact showcase revision.
- Completion and verification: `docs/team/results/FINAL-SUBMISSION-READINESS.md`
  and earlier worker/coordinator reports, distinguished by their timestamps.

## Video storyboard and capture checklist

**Status: NOT RECORDED; NOT UPLOADED; no video URL.** The available browser tool
supports interaction and screenshots, not screen-and-system-audio recording.
No supported video recording tool was available in this session (`ffmpeg` was
not on PATH). This storyboard is a production-ready handoff, not a completed video.
Use an already available screen recorder that captures system audio and microphone.
Target **2 minutes 40 seconds**, within the official 2–3 minute requirement.

| Time | Screen/action | Narration / sound |
|---|---|---|
| 0:00–0:15 | Project title and two mode choices | “OxfordQ turns a restricted coordination game into two musical voices, then separately shows what classical musical development can do with saved quantum-sampled material.” |
| 0:15–0:35 | Experiment evidence card; 75%, 85.36%, 100% reference | Explain each side sees only its own cue. “The 75% bound concerns noncommunicating classical policies. The ideal quantum strategy reaches about 85.355%; a centralized classical coordinator can reach 100%.” |
| 0:35–0:55 | Click Load RECORDED fixture; play Quantum then Local classical, eight seconds each | Let both examples be heard. Keep RECORDED and 4,096 historical CHSH-shot labels visible. “Replay adds no shots; both use identical sound and tempo controls.” |
| 0:55–1:15 | Show the separately verified live job export and built-in backend identity | “A complete five-circuit, one-job built-in simulator run passed. Free IonQ passed a separate single-circuit diagnostic, but the full duet batch remains unresolved. This is simulation, not hardware or a speedup claim.” |
| 1:15–1:30 | Switch Composition, choose Melody only, play an excerpt | Keep PRE-GENERATED visible. “Sixteen saved motifs from the existing 12-qubit QCBM form the source. Repetition, rhythm, harmony and endings are classical.” |
| 1:30–2:02 | Choose accompaniment, play the entire frozen 32-second recording | Let music play without narration. Do not change the accepted music, pitch, tempo or audio gain in the application. |
| 2:02–2:22 | Export MIDI and provenance; show sample seed, source hash and classical transformation labels | “All sixteen motifs and 64 tokens survive in the source trace. Exports are byte-verifiable. Composition playback makes zero backend jobs and carries no CHSH success claim.” |
| 2:22–2:40 | Source links, disclosed starting code, exact revision and support attribution | “We reused existing trained weights and experiments, adding integration, reproducibility and this optional showcase during the build window. This effort is supported by Qollab & IonQ.” |

Before recording: close unrelated tabs/notifications; never display credentials
or account-sensitive data. Verify system sound capture and microphone levels with
a short test. Use the exact candidate and its recorded fixture, not a favorable
new sample. Keep the source and PRE-GENERATED/RECORDED/LIVE labels legible. The
small fresh live result is verification evidence, not a replacement frozen result.

After recording: verify duration is 120–180 seconds, music is audible, narration
is intelligible and labels/exports are visible. **Do not upload without separate
authorization.** After authorized hosting on YouTube/Loom/Vimeo/Drive, test its
public link without sign-in. Do not claim that check until actually performed.

The team captain must separately authorize publication and submission, supply the
video URL and confirm the existing registration/team association. Do not change
registration or accept new agreements on the user's behalf without the required
approval. Do not submit until the remaining official simulator requirement has
been resolved or explicitly clarified by the organizers.
