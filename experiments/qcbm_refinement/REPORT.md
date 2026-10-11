# Completed integrated classical refinement

Branch: `codex/qcbm-musical-refinement-20261011`, based exactly on PR #8 head
`f42bcf1e3db5a2cc7d86e82d4dc6c06a0c6a440d`. Source changes are confined to the new
`experiments/qcbm_refinement/` directory. The original experiment and all validated
Duet/Qollab sources are unchanged. No training, sampling or backend execution is
performed by this refinement. No PR has been merged or public demonstration published.

## Listening result

Generated at **2026-10-11 16:06:54 UTC**. Listen locally at
`experiments/qcbm_refinement/artifacts/listening/listen.html`, or through the
loopback preview `http://127.0.0.1:8781/listen.html` while the preview server runs.
The page offers exactly original/refined versions, each melody-only or arranged.

- Refined lead: `artifacts/listening/improved-melody.mid` and `.wav`.
- Refined accompaniment: `artifacts/listening/improved-arranged.mid` and `.wav`.
- Immutable reference exports: `original-melody.mid/.wav`, `original-arranged.mid/.wav`.
- Full source/transformations: `raw-samples.json`, `trace.json`.
- Harmonic decisions: `harmonic-analysis.json`; diagnostics: `analysis.json`.

Every WAV and MIDI is exactly 32 seconds, sixteen 4/4 bars, 120 BPM. All four
original reference exports reproduce PR #8 bytes exactly. One scalar WAV gain
matches reference RMS within 0.01 dB without changing MIDI dynamics or timbre.
The synthetic audition sound is identical in type/instrumentation across versions.

The piece retains A–A′–B–A″, all source identities, twenty theme repetitions, 62
sounding melody events and two rest events. The new version combines phrase-aware
sevenths/inversions, less angular bass, controlled bar variation, a contrasting
offbeat B texture, dynamic phrasing, release space and a root-position V7–I finish.
Only the four permitted phrase-final slots can change sampled pitch class; three
actually do. Compared with PR #8, only bar 8 changes pitch class (G to D), with
other pitch changes limited to register. The final resolution is C4 instead of C5.

## Bar-by-bar harmonic plan

Inversions are zero-based; numeric voicings/bass are concert MIDI pitches.
Candidate melody costs, accented note roles, passing/neighbor-tone discounts,
resolutions and avoidance fragments are available in the harmonic JSON.

| Bar | Section | Chord | Inversion | Chord voicing | Downbeat bass |
|---|---|---|---:|---|---:|
| 1 | A | I | 0 | 48,52,55 | 36 |
| 2 | A | ii7 | 0 | 50,53,57,60 | 38 |
| 3 | A | I | 1 | 52,55,60 | 40 |
| 4 | A | V | 0 | 55,59,62 | 43 |
| 5 | A′ | Imaj7 | 2 | 55,59,60,64 | 43 |
| 6 | A′ | ii7 | 1 | 53,57,60,62 | 41 |
| 7 | A′ | ii | 1 | 53,57,62 | 41 |
| 8 | A′ | V7 | 0 | 55,59,62,65 | 43 |
| 9 | B | vi7 | 2 | 52,55,57,60 | 40 |
| 10 | B | I | 1 | 52,55,60 | 40 |
| 11 | B | ii7 | 1 | 53,57,60,62 | 41 |
| 12 | B | V7 | 0 | 55,59,62,65 | 43 |
| 13 | A″ | I | 2 | 55,60,64 | 43 |
| 14 | A″ | IVmaj7 | 0 | 53,57,60,64 | 41 |
| 15 | A″ | V7 | 0 | 55,59,62,65 | 43 |
| 16 | A″ | I | 0 | 48,52,55 | 36 |

Accompaniment adds 31 bass and 110 chord-note events. Most chord attacks are
simultaneous voicings in two windows, not 110 successive melody notes. Melody
track bytes decode identically with and without accompaniment. Avoidance only
changes accompanying fragments; it does not repair the lead or alter source rests.

## Objective changes and tradeoffs

| Diagnostic | Original PR #8 | Refined |
|---|---:|---:|
| Accented duration on chord tones | 56.7% | 70.7% |
| Sustained nonchord semitone overlap, summed chord-note beats | 3.15 | 0 |
| Mean absolute melody interval, semitones | 2.459 | 2.426 |
| Melody jumps larger than an octave | 0 | 0 |
| Distinct bar rhythm patterns | 4 | 12 |
| Distinct sounding note lengths | 5 | 20 |
| MIDI velocity range | 82–82 | 63–93 |
| Distinct MIDI velocities | 1 | 24 |
| Mean absolute bass interval, semitones | 4.419 | 2.533 |
| Maximum bass jump | 7 | 5 |
| Mean nearest-tone chord motion | 1.356 | 1.347 |
| Literal A/reprise pitch-class agreement | 71.9% | 68.8% |
| Stepwise-resolved nonchord events | 9 of 29 | 7 of 24 |
| Final harmonic cadence | V–I | V7–I |

Not every diagnostic increases: literal reprise agreement falls by one compared
slot due to bar 8's explicit cadence; stepwise resolutions fall as chord membership
changes. All twenty source repetitions are retained. Phrase-boundary jumps are
5/3/1 semitones versus 5/2/1 originally. Phrase-end release space is .135/.135/.180
beats, with .040 at the final ending. Increased rhythmic/dynamic diversity may
also feel too elaborate; smoother bass may feel restrained. Those tradeoffs require
listening. Sevenths expand the chord vocabulary, so membership percentages alone
are not a fair perceptual ranking. The overlap diagnostic targets only sustained
nonchord semitone relations, not every possible audible clash.

**Subjective assessment: pending the user's audition.** No winner, aesthetic
superiority, learned long-form structure or quantum advantage is asserted.

## Actual new verification

- **154 combined Python tests passed in 28.53s:** 138 existing project checks,
  eight original-composition checks and eight refinement checks. The new tests
  also passed separately in 4.34s. No existing assertions were changed.
- **All three existing Node suites passed:** legacy UI at 16:07:35.355 UTC,
  contract checks at 16:07:35.730 UTC, paired projection/export checks at
  16:07:44.166 UTC. These remain mocked UI/AudioContext checks, not browser results.
- Both original rules/no-audio orchestration CLI examples passed, provider disabled.
- Independent new media verifier passed at **16:07:40 UTC**: four MIDI and four
  WAV files, exact duration, valid timing/velocities/programs, closed notes,
  non-silent bounded waveforms, preserved sources, four eligible cadence slots,
  unchanged reference hashes and melody protected from accompaniment.
- Two fresh generations in the new tests reproduce MIDI/WAV, harmonic analysis
  and diagnostics byte-for-byte. Creation-time metadata in trace/page and their
  associated manifest hashes vary. Generation is guarded against original sampling, statevector evaluation
  and simulator submissions. Legacy tests separately recheck their original
  deterministic sampler; they do not replace this refinement's saved source.
- Preservation audit: **215 existing artifact/protected files unchanged**, including
  original PR #8 artifacts, frozen weights/circuit, recorded fixture and raw contract.
- Early development verification found an empty chord-plan path because the
  initial range excluded a root-position V7. The upper chord range was corrected
  to MIDI 67, without changing melody/source or weakening tests. The first local
  HTTP test also met sandbox socket restrictions; approved loopback execution
  resolved that environment limit. The final combined suite passed completely.

### Actual Chrome checks, separately

Approved loopback-only preview with HTTP byte ranges; no browser protections
changed. All four audio variants loaded, played, paused and reported no errors.
Starting another version paused the previous one. Texture selection paused all
players. Refined accompaniment seeking reached 23.335s and resumed at 23.632s.
The visible full-provenance panel parsed correctly, exposing the preserved hash,
16 motifs, 64 tokens, 64 refined events and zero backend jobs.

The **refined arranged MIDI downloaded successfully** and its bytes/hash match:
`33ba5acb41935481496d9a465cb03515c24ead6c0af7ee31eb4ff744617af16c`.
A second browser download, original-arranged MIDI, timed out. Remaining direct
downloads were not claimed verified and no access controls were bypassed. All
four local MIDI exports independently decode and match their event traces, but
complete repeated browser-download verification remains a manual/platform check.
Opening the full JSON initially exceeded the tool's accessibility-tree timeout;
the visible textarea was then read through the approved DOM API and closed.

Browser evidence is saved in ignored `artifacts/listening/browser-verification.json`
and `browser-preview.png`; portable verification summaries are in `results.json`.
No Qollab/IonQ check or canonical deployment modification was attempted. Before any
future app integration, repeat private platform playback/serving/export checks.
