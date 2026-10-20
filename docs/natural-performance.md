# Acoustic rendering and expressive performance

The composed score and its performance are separate artifacts. Smaller instrument
generators remain replaceable through `GenerationRegistry`; their source bank is
immutable. The local orchestration and performance policies are deterministic,
procedural baselines, not newly trained models or authentic composer imitation.

## Setup and use

```powershell
python scripts/setup_acoustic.py
qml-compose --style all --require-audio --out output-natural-studies
```

The default ensemble is flute, clarinet, violin, cello, double bass **and piano**.
The keyboard receives a dedicated bass-and-upper-hand accompaniment: broken chords
for Mozart, arpeggios elsewhere, and sustained chords at arrivals. Its tones retain
the quantum harmony bank's source references; strike dynamics and harmonic pedal
changes are performed by the existing keyboard policy. Explicit `--instruments`
still selects a custom ensemble.

The Windows x64 installer downloads sfizz 1.2.3 and VSCO 2 CE 1.1.0 into
`assets/acoustic`, verifies pinned SHA-256 digests, validates archive paths, and writes
an installation receipt. About 2.2 GiB is downloaded; extracted samples need additional
disk space. Files and previous output directories are preserved. Audio assets are
ignored by Git and are not included in the Python wheel.

`--sample-library` selects the directory containing `Flute-KS.sfz`, and
`--sfizz-library` selects the native shared library. On Linux/macOS provide a separately
installed sfizz library. `QML_ACOUSTIC_ASSETS` can point to an installer receipt directory;
`VSCO_PATH` and `SFIZZ_LIBRARY` can select the two assets independently. Missing assets
produce an explicit audio error; `--require-audio` makes the CLI fail. There is no automatic
SoundFont substitution. Windows non-ASCII sample paths use a verified ASCII short-path
alias; systems without such aliases require an ASCII asset directory.

Use `--expression-strength 0` for unshaped performance, `.6` (default) for subtle
expression, or `1` for the full rule policy. `--reverb-wet .14` is the default shared
algorithmic room; `0` disables it. `--part-volume cello=.5` controls ensemble balance.
`--renderer soundfont --fluidsynth ... --soundfont ...` uses native FluidSynth envelopes
and the performed MIDI. The old isolated-note renderer is retained only for comparisons.

## Musical writing

The local planner establishes a source theme, develops and rhythmically varies it,
and returns to it. Phrases span several bars; motifs can cross bar lines rather than
restarting at every bar. Countervoices enter later, and accompaniment leaves space
at openings and arrivals. Harmonic roots request tonic/subdominant/dominant functions,
then select actual model-produced chords. Chord variants are refitted to the notes
on musical accents. A small beam search coordinates sustained chord voicings,
favoring short motion, a root foundation and separation between parts.

`MotifOccurrence.event_order` can be a complete permutation of source event indices,
including rests. It is recorded in occurrence lineage; repetition and reordering never
invent pitch classes. `PhraseMark` records part, bounds, peak, function and articulation.
Old plans and scores without either addition remain readable. Missing harmonic roots
and missing major dominants in minor keys are reported instead of manufactured.
`CompositionRequest.register_limits` optionally narrows each instrument's physical
range. Selecting sfizz intersects those limits with VSCO's actual patch coverage
before compiling octave placements. Raw reference notes keep their original pitches;
unsupported raw-source registers cause an explicit audio error.

## Performer boundary

```python
from orchestrator.composition import RulePerformer, compose

class MyPerformer:
    def perform(self, score, *, style, seed, strength):
        # Return PerformancePlan: one PlayedNote per sounding logical note,
        # the shared tempo map, per-part CC11/CC64, phrases and warnings.
        ...

# compose(request, performance_adapter=MyPerformer(), ...)
```

`CompositionResult.performances` exposes the validated plans even when no output
directory is supplied. Injected performers receive deep copies of logical scores;
their returned note and source identities are checked against the originals.

`PerformancePlan` (`qm.performance.v1`) references the SHA-256 of the exact logical
score and its source bank. Played notes preserve note ID, source ID and pitch while
recording performed timing, velocity and articulation. Validation protects note
identity, metre, PPQ, part capacity, positive duration and repeated-pitch releases.

The first adapter applies phrase arcs, instrument-specific gating, breath gaps and
one shared rubato map. Seeded onset deviations are correlated, capped at 12 ms at full
strength, and structural attacks stay aligned. Piano uses strike velocity and pedal
changes at harmonic boundaries; its ringing notes receive no continuous expression
swell. Strings and winds receive smooth expression across whole phrases. Native
sample envelopes, recorded vibrato and available velocity layers remain intact.

sfizz maintains a persistent sampler per part. Private keyswitches choose sustained,
short or pizzicato samples and never enter musical MIDI or source lineage. The current
violin/cello patches are sections, not solo recordings; bass and winds are solo patches.
Mappings with no dedicated short articulation use note gating and report that limitation.
All samples are preloaded for offline rendering rather than relying on live disk streaming.

## Listen and inspect

Each piece contains logical MIDI/score JSON, performed MIDI, performance JSON, native
and expressive WAVs, and dry stems. Native-versus-expressive versions use the same
logical notes, library and room. Whole-mix constant RMS gains match overall loudness;
internal dynamics are not compressed. A shared peak adjustment provides -1 dBFS
headroom. This is an audible-RMS proxy, not LUFS normalization. Stems receive their
mix's constant gain; summing them produces the dry mix, not the reverberated mix.

For the three-way phrase comparison against the previous envelopes:

```powershell
python scripts/render_performance_comparison.py --score previous/local.score.json --out output-phrase-comparison --fluidsynth PATH --soundfont FONT
```

It replays four bars of an existing score with zero generator/provider calls. The
page includes previous envelopes, native acoustic samples, and expressive acoustic
performance. The acoustic versions share the room setting; the previous renderer is
dry. Use the native-versus-expressive pair to isolate added performance shaping.

Compilation/rendering and structural diagnostics cannot establish beauty or realism.
Listen for connected phrases, clean retriggers, clear accompaniment, breaths, musical
arrivals and restrained timing. These free samples lack recorded interval-legato
transitions; connected sustain approximates them. A richer source model is still
needed for longer motifs and chromatic harmony.

## Third-party assets

Repository code remains MIT. Asset rights remain separate:

- [VSCO 2 CE](https://github.com/sgossner/VSCO-2-CE), tag 1.1.0: **CC0-1.0**.
  Samples by Versilian Studios / Sam Gossner and Ivy Audio / Simon Dalzell, with
  sample editing by Elan Hickler / Soundemote. Upstream license remains in the
  extracted library. [Publisher documentation](https://versilian-studios.com/vsco-community/).
- [sfizz](https://github.com/sfztools/sfizz), release 1.2.3: **BSD-2-Clause**, with
  its own dependency notices. This repository downloads the official binary and
  does not include it in its source or wheel. Keep upstream licenses if redistributing
  binaries. [Upstream license](https://github.com/sfztools/sfizz/blob/1.2.3/LICENSE).
- GeneralUser GS / FluidSynth remain optional assets for native SoundFont playback
  and historical comparison; their existing upstream terms continue to apply.

## Compact local submission

See [submission packaging](submission.md). A separate runnable snapshot preserves
the original module paths and contains compact sample banks for six instruments.
The original high-quality assets, previous pieces, and directory layout are retained.
