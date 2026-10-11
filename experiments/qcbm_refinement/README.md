# One integrated refinement of the saved PR #8 composition

This optional local experiment starts from PR #8 commit
`f42bcf1e3db5a2cc7d86e82d4dc6c06a0c6a440d`. It reuses the **existing** sixteen
QCBM motifs, PCG64 seed 20261011, without evaluating a statevector, invoking an
RNG, resampling, training or submitting any backend job. `data/raw-samples.json`
is an exact byte copy of the original saved source, with the original bitstrings,
64 tokens, exact probabilities, checkpoint identities and runtime provenance.
The current quantum model, Duet mapping, CHSH evidence and Qollab app are untouched.

There are only two main comparison versions: the original PR #8 composition and
one fully refined composition. Each has melody-only and arranged playback. Both
are **PRE-GENERATED**, A–A′–B–A″, sixteen bars of 4/4 at 120 BPM, exactly 32 seconds.
The page and report do not choose a perceptual winner. Human listening is pending.

## Reproduce and listen

Use the existing `.venv-final` environment, or the exact dependencies already
documented in `../qcbm_composition/requirements.txt` plus the editable
`components/quantum_duet` package. No additional dependencies are introduced.
NumPy, Qiskit and Mido are required by the reused reference modules; pytest is
test-only. The generator does not need ignored PR #8 artifacts or PR #7 files.

From the repository root:

```powershell
.venv-final/Scripts/python.exe -m experiments.qcbm_refinement --out experiments/qcbm_refinement/artifacts/listening
.venv-final/Scripts/python.exe -m experiments.qcbm_refinement.verify experiments/qcbm_refinement/artifacts/listening
.venv-final/Scripts/python.exe -m experiments.qcbm_refinement.preview --directory experiments/qcbm_refinement/artifacts/listening --port 8781
```

Open `http://127.0.0.1:8781/listen.html` in a browser. The server binds only to
loopback, serves that output directory, and supports byte ranges for WAV seeking.
It changes no browser security controls. Stop it with Ctrl+C. If the output
directory already exists, use a new `--out` path; generation refuses to replace
artifacts. The verifier writes only `verification.json` in the chosen output.
POSIX environments use their interpreter's `bin/python` path instead.

The listening page selects melody or accompaniment, pauses other players on
Play, pauses all on texture changes, exports MIDI and displays complete provenance.
Direct download behavior can depend on browser permissions/extensions; see the
actual browser verification limitation in REPORT.md. Files remain available
locally, with independently verified hashes and MIDI decoding.

| Version | Melody | With accompaniment |
|---|---|---|
| Original, unchanged | `original-melody.mid/.wav` | `original-arranged.mid/.wav` |
| Fully refined | `improved-melody.mid/.wav` | `improved-arranged.mid/.wav` |

Also generated: `raw-samples.json`, `trace.json`, `harmonic-analysis.json`,
`analysis.json`, `manifest.json`, `listen.html`. Audio and generated outputs are
ignored. The checked-in reference manifest verifies all four original exports
byte-for-byte. The same renderer, MIDI programs 73/32/0 and three-harmonic waveform
are reused. This additive audition renderer is not a realistic instrument renderer.
Only refined WAVs receive one documented scalar RMS-matching gain (approximately
+0.72 dB melody, +0.50 dB arranged); original files and MIDI velocities are unchanged.

## Declared classical musical decisions

- **Form and source:** PR #8's source schedule remains unchanged: 44 distinct
  original token positions feed 64 events, including twenty repetitions from A.
  Every motif contributes. All twenty unused original positions remain listed;
  the complete original 64-token sample is retained. No favorable-sample selection.
- **Rhythm:** twelve predetermined bar patterns on a quarter-beat grid, summing
  to four beats each. A's rhythmic gestures return in A″; A′ varies them and B
  uses lighter offbeats. All four source slots remain present. Shorter gates
  create breathing space without changing a sampled rest or inventing a token.
- **Dynamics/articulation:** a fixed sixteen-bar intensity arch, strong/weak
  beat accents and release at phrase ends; velocities 63–93. B builds contrast,
  the return relaxes. Gate fractions are 0.74–0.98. No random humanization.
- **Register:** dynamic programming over each allowed pitch class in octaves
  4/5. Movement cost is `jump + .7*max(0,jump-5)^2 + 3*max(0,jump-12)^2`,
  with `.18*abs(pitch-section_target)` and targets 67/70/74/67; initial pitch
  reference 67. Ties choose the lexicographically lower pitch path. Cadences are
  planned before register, so their transitions participate in the same cost.
- **Cadences:** only the last already-sounding events in bars 4/8/12/16 may change
  source pitch class. Targets G/D/B/C are respectively dominant root/fifth/third
  and tonic. Three of these differ from sampled pitch class; all four decisions
  are traced. Only bar 8 adds a pitch-class change compared with PR #8; the final
  tonic moves from C5 to C4 through register planning. Rests cannot be overwritten.
- **Harmony:** constrained phrase-level chord functions, diatonic triads and
  Imaj7/ii7/iii7/IVmaj7/V7/vi7 candidates. Score weights duration and strong beats;
  stepwise passing/neighbor notes receive reduced nonchord penalties. Whole-piece
  planning combines melody fit, inversions, register, symmetric nearest-tone
  chord motion, bass motion and weak predominant-to-tonic transition penalties.
  Exact candidates, scores and voice-leading terms are recorded per bar.
- **Bass/texture:** inversions connect inner bars; root-position dominants frame
  phrases and root-position tonic frames the piece. The second bass pulse moves
  to another chord tone toward the next downbeat. Chords use two restrained
  windows per bar, offbeat windows in B, and one sustained final tonic. Voicings
  span MIDI 45–67; bass spans 36–47. Sustained nonchord semitone clashes shorten
  or delay accompaniment fragments, never the developed melody. Very short
  fragments below .25 beats are omitted and the avoidance intervals are traced.

Costs are composition preferences, not listening-quality estimators. The known
canonical arranger's flat-chord inference issue is not changed or used here.

## Provenance and verification

Each refined melody event keeps its raw source ID, sampled token/pitch, original
event ID, original transformations, original values and explicit classical
refinements. Accompaniment and harmonic choices reference the bar's source IDs.
Global loudness matching references the same raw hash and source IDs. The preserved
source hash is `be635526814540453ae31e34266207e4c59dd61468c5118bb3b0159ea389a5bb`.
The historical checkpoint identity and packaged-checkpoint byte digest remain
distinct. Composition traces contain no CHSH statistics or selected backend claim.

```powershell
.venv-final/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests experiments/qcbm_composition/tests experiments/qcbm_refinement/tests --basetemp experiments/qcbm_refinement/artifacts/pytest-regression
node components/quantum_duet/tests/ui_checks.mjs
node components/quantum_duet/tests/ui_c/contract_checks.mjs
node tests/duet_projection_checks.mjs .venv-final/Scripts/python.exe
```

The preview test requires permitted loopback sockets. A network-restricted sandbox
must obtain normal approval for that test; do not weaken browser/network protections.
See REPORT.md and results.json for actual new checks, limitations and diagnostics.
