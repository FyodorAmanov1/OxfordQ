# Expressive composition from QML sources

The old arranger preserves lead timing and note count. The new composition path
selects and develops source motifs before arranging the ensemble. It is a separate
API, so existing orchestration and paired Quantum Duet evidence retain their behavior.

## Local usage

Install the root package with its quantum extra, then run:

~~~powershell
python -m orchestrator.composition --style all --out output-expressive-studies --require-audio
# Installed console entry point:
qml-compose --style debussy --out output-debussy --no-audio
~~~

Choose a fresh output directory. Audio uses the existing FluidSynth/SoundFont
discovery, or explicit --fluidsynth and --soundfont paths. The four-study collection
has piece1 through piece4 directories and an index.html listening page. Each study
includes the fixed-grid reference, local composition, MIDI, score JSON, plan JSON,
immutable source bank, diagnostics and file hashes. WAV comparisons use matched
audible-sample RMS and shared peak headroom; this is not perceptual LUFS matching.

### Instrument volume and note envelopes

Playback now shapes each note independently, including simultaneous notes. A piano
or drum strike rises quickly and decays; bowed strings have a quick bow attack and
shaped sustain; flute has a slower breath attack and release. Other winds/brass and
low strings have their own defaults. Short notes shorten the attack/release to fit.
The sustained envelopes include a gentle swell and easing before the release.
These are editable articulation defaults rather than a claim that an instrument
always has one fixed envelope.

Score JSON stores an InstrumentPerformance per part: volume, attack/decay/release
seconds, sustain level, swell, tremolo depth and struck/sustained mode. Set balance
with repeated --part-volume arguments, for example:

~~~powershell
qml-compose --style mozart --part-volume flute=0.9 --part-volume cello=0.5 --out output-balanced
~~~

The WAV renderer uses the FluidSynth shared library and SoundFont timbres. It renders
each note separately, replaces the sample's volume envelope with the explicit
instrument envelope, applies velocity-sensitive sample synthesis, per-part volume,
smoothly interpolated CC11 expression and panning, then mixes the notes. Overlapping
notes therefore keep separate attacks/releases. Rendering is dry, without artificial
reverb/chorus. A missing shared library is an explicit audio failure; MIDI and scores
remain available. The Windows bundle installed by setup_audio.py includes that library.
See the official [voice API](https://www.fluidsynth.org/api/group__voices.html) and
[audio rendering API](https://www.fluidsynth.org/api/group__audio__rendering.html).

Comparison WAVs still have matched overall RMS. Per-part volume sets ensemble
balance; the listening page's volume slider sets overall listening level after
normalization. MIDI exports record track volume with CC7 and preserve the envelope
parameters as text metadata. Ordinary MIDI players choose their own instrument
envelopes; reproducing the exact WAV shape requires this renderer.

The Duet and POP909 browser previews also have explicit volume controls and note
envelopes. They use oscillator approximations rather than SoundFont samples. These
controls affect playback preferences and add no quantum shots or source-note edits.

| Study | Inspiration | Default bars | Main contrast |
|---|---|---:|---|
| piece1 | Bach | 24 | Delayed instrumental imitation and sustained support |
| piece2 | Mozart | 36 | Short articulated phrases, question/answer rhythms and broken chords |
| piece3 | Debussy | 18 | Sparse sustained texture, 6/8 → 5/4 → 3/4 and tempo shading |
| piece4 | Rachmaninoff | 18 | Broad register, moving arpeggios, compound metre and dynamic rise |

These are inspired ensemble studies, not models trained to imitate these composers.
Names do not imply authentic counterpoint, sonata form, impressionist harmony or
virtuoso piano writing. The default ensemble is flute, clarinet, violin, cello and
double bass. It spans multiple octaves within instrument ranges; eight octaves per
instrument would be physically inappropriate.

## Data flow and music decisions

~~~mermaid
flowchart LR
    Q[Frozen QCBM or smaller instrument generators] --> B[Immutable source bank]
    H[POP909 harmonic labels and decoded chord tones] --> B
    B --> P[Local or Gemini composition plan]
    P --> C[Rhythm, octave placement, texture, expression]
    C --> V[Source, range, timing and capacity validation]
    V --> M[Metre and tempo maps, MIDI and WAV]
~~~

- **Identity:** Each source event has a stable ID and pitch or explicit rest. A
  SHA-256 ties every plan and score to the exact source bank. Every sounding output
  occurrence references one source event and retains its pitch class. Only octave
  displacement is allowed. Repetition creates new output IDs without changing the source.
- **Form:** The local plan introduces a theme, opens a contrasting development
  section with a lead break, and returns to introduced material. The validator
  requires the lead's return to reuse an introduced motif.
- **Rhythm:** A source motif gets explicit positive tick allocations for each
  token, including rests. Gates shape articulation, phrase ends leave gaps, and
  accompaniment can sustain, break chords or arpeggiate. Tick time represents
  tuplets; the local reference uses a 40-tick grid at PPQ 480.
- **Register and balance:** Motifs prefer uniform octave displacement to retain
  their contour. Harmony spreads chord tones among parts and uses prior placement
  when choosing register. Local phrases rise into development and settle on return.
- **Expression:** Note velocities, CC11 expression and section/phrase tempo
  changes shape a recorded performance. Debussy and Rachmaninoff references also
  include intrabar tempo steps. These are discrete MIDI maps rather than continuous curves.
- **Time:** Bar signatures use quarter-note ticks, with optional accent grouping.
  Tempo integration gives duration in seconds. MIDI records changing signatures,
  tempo events and grouping markers; velocities accent group boundaries. The original fixed-4/4 importer is unchanged;
  composition has its own conductor export and event reader.

The source reference plays all independent instrument motifs on a fixed grid and
shares the local composition's tempo/metre map. POP909 is added during composition.
This is a transparent pipeline comparison, not an experiment isolating one variable.
An AI plan may choose another valid timeline; compare its reported duration too.

## Gemini integration and comparison

Local runs make no API calls. --compare records explicit unavailability unless a
provider is injected or live calls are explicitly enabled. --planner gemini exits
with status 2 when Gemini cannot complete; local outputs remain labelled local.
No local result is renamed Gemini.

For a separately authorized live run, configure GEMINI_API_KEY or GOOGLE_API_KEY
in the process environment and pass --live-gemini with --planner gemini or --compare.
This sends the source bank and plan to an external service and may incur charges.
The repository's shared-work instructions prohibit paid execution during local
development. No live API or QPU calls were made for this implementation.

The AI gets a dedicated composition instruction and JSON schema, source IDs,
instrument constraints and the local reference plan. It can select/repeat motifs,
change rhythm, octave targets, texture, dynamics and timeline. It cannot supply
new pitches. Up to three proposals pass through the same compiler/validator;
errors are returned as correction feedback. Reports distinguish injected providers
from live API execution, record attempts and redact credentials from errors.

~~~python
from orchestrator.composition import CompositionRequest, compose

request = CompositionRequest(style="mozart", compare=True)
# provider.request(CompositionPlan, payload, feedback) returns a typed plan.
# An injected provider enables local or offline comparisons with no external calls.
result = compose(request, provider=my_local_planner, output_dir="output-local-ai")
~~~

## Replacing the smaller models

Keep the existing GenerationRegistry interface. Each adapter implements
generate(GenerationRequest) and returns GeneratedSequence with concert-pitch notes
or a MIDI path. The generation request provides range, capacity and an independent
seed. Different instruments can route to different model instances/checkpoints.

~~~python
from orchestrator import GenerationRegistry
from orchestrator.composition import CompositionRequest, generate_source_bank, compose

registry = GenerationRegistry()
registry.register("flute-small", flute_adapter, instruments=["flute"])
registry.register("cello-small", cello_adapter, instruments=["cello"])
request = CompositionRequest(instruments=["flute", "cello"], bars=12)
bank = generate_source_bank(request, registry=registry)
result = compose(request, bank=bank, output_dir="output-small-models")
~~~

Generated note sequences become source motifs; QCBM adapters additionally preserve
zero-token rests. External adapters may construct a SourceBank directly to supply
explicit rests and their own motif/harmony groupings. A serialized bank can be
replayed with --source-bank without rerunning instrument inference. The current
generic sequence importer accepts fixed-4/4 sources; composition retimes them
after import. It does not yet import arbitrary expressive MIDI source maps.

The default QCBM still emits four tokens with seven non-rest scale degrees. Every
instrument shares frozen weights; different seeds/decoders are not distinct trained
instrument models. POP909 was trained on major-key material. Minor studies use
relative-major chord sources and source-preserving classical selection; the report
records that policy and the original model provenance. No checkpoint is retrained.

## Evaluation and limits

Run the regression suite and build:

~~~powershell
python -m pytest -q tests components/quantum_duet/tests
python scripts/verify_composition_artifacts.py output-expressive-studies
python scripts/build_local_release.py --out dist/expressive-release
~~~

Checks cover motif/rest lineage, pitch classes, source hashes, register and capacity,
thematic return, rhythmic/dynamic variation, tempo/metre maps, exact MIDI note
round trips, local determinism, interchangeable smaller models, offline Gemini
corrections and installed-wheel inference. Render reports measure WAV duration
against the integrated tempo timeline while allowing a synthesizer release tail.

Pitch span, duration classes, silence fraction, motif repetition and dynamics are
descriptive diagnostics. They cannot prove beauty or authentic style. Human
listening should judge phrase direction, contrapuntal clarity, harmonic arrival,
balance and whether surprises feel purposeful.

Further improvements need richer source models/datasets and a learned planner:
longer conditional motifs, richer chromatic/harmonic vocabulary, phrase and
cadence conditioning, articulation, detailed voice-leading objectives, and listening
evaluation against classical scores. An injected transformer can implement the
same plan contract. This implementation adds a procedural baseline and optional
Gemini planner; it does not train a transformer or claim quantum musical advantage.
