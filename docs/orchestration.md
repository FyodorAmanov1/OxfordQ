# How independent parts become an arrangement

A composer assigns each part a musical job, gives the parts a common timeline,
and chooses which contrasts to keep. Notes need not all belong to one chord:
passing notes, suspensions and other tensions can sound intentional when their
rhythm and resolution make sense.

## Decisions that make instruments work together

| Decision | Musical purpose | Current implementation |
|---|---|---|
| Key and chord progression | Give melodies a shared tonal context and places of rest/tension | Explicit progression, inferred harmony, or POP909 checkpoint |
| Lead, bass, harmony, countermelody, rhythm | Avoid every instrument competing for attention | Part roles and section directives |
| Register and spacing | Keep bass clear, give melodies room, avoid impossible pitches | Concert-pitch profiles and phrase transposition |
| Voice leading | Move lines between chords with understandable contour | Phrase register continuity and bounded local repairs |
| Rhythmic alignment | Establish metre while allowing complementary rhythms | Shared quarter-note beats, 4/4 and tempo normalization |
| Density and rests | Leave space for the lead and changes in texture | Explicit muting, section capacity and preserved rest lineage |
| Dynamics and timbre | Make the intended foreground audible | Velocity/expression, MIDI programs, panning and optional rendering |
| Phrase and form | Create beginnings, development, contrasts and endings | Four-bar windows; external arranger may propose a global plan |

Instrument ranges use sounding pitch. A playable orchestral score also needs
player-specific review of breathing, bowing, articulation, written transposition,
and technique. Conservative MIDI section profiles do not certify playability.

## Model boundary

~~~mermaid
flowchart LR
    Q[Independent instrument generators] --> D[Decode to timed notes]
    H[Harmony model or supplied chords] --> A[Rules or Gemini arranger]
    D --> A
    A --> V[Validate melody, lineage, range and edit budget]
    V --> M[MIDI and optional audio]
~~~

The current frozen QCBM supplies four-token motifs. Its distribution is sampled
separately for each part, then a classical decoder maps tokens to the selected
instrument's scale, register, rhythmic stride and note gate. A zero token remains
a rest. All instruments currently share those weights; their different registers
and rhythms come from the decoder, not distinct learned instrument models.

POP909 supplies a separate harmonic progression through three-qubit coarse
and four-qubit resolver circuits. Local Statevector inference samples their
distributions. Rare labels use the recorded classical frequency fallback.
The training scope is major keys, so minor-key runs use the ordinary inferred
harmony path.

The arranger protects the lead's notes, allowing only a uniform octave placement
when needed. Accompaniment phrases may be transposed together; a limited fraction
of individual notes may receive small pitch or duration repairs. Muted notes
keep their IDs. The system records what changed instead of inventing replacement
notes without provenance.

Gemini is the existing external model option. It proposes a typed global plan and
bounded edits; Python accepts only valid proposals and retains validated output
when generic orchestration cannot complete a model request. The paired Duet UI
requires the requested backend to finish successfully and otherwise preserves
raw playback with an explicit arrangement failure.

## Replacing the smaller models

Implement generate(GenerationRequest) and return GeneratedSequence containing
notes or a MIDI path. Register the adapter for an instrument; it can own a
checkpoint, a simulator or your hardware execution code. Existing generators
receive instrument guidance and a seed, and do not receive other parts by default.
You can supply conditioning through options if a future model needs it.

The contract uses quarter-note beats, sounding MIDI pitch and source metadata.
Keep measurement provenance in the generator; send decoded musical events to the
arranger. This allows QML, transformers and simpler models to use the same seam.

A separately trained orchestration transformer remains a future option. It would
need licensed multi-part symbolic training data, instrument/role and timing tokens,
source-conditioned edit targets, constraint-aware decoding, and held-out musical
evaluation. This iteration implements the requested existing-model route without
claiming new training.

## Judging the result

Hard checks establish valid timing, ranges, channel capacity, preserved lead and
source lineage. Harmonic fit, rough intervals, motion, retention and velocity
balance are useful diagnostics, with imperfect relationships to perceived quality.
The comparison page lets a listener judge recognisable motifs, balance, cadences
and intentional tension. A CHSH result measures the coordination experiment and
does not measure orchestration quality.
