# QML music orchestrator

Arrange independently generated instrument parts as tonal cinematic orchestral MIDI.
Gemini proposes harmony, roles and bounded edits. Python protects the main melody,
checks instrument limits, and records the source of every output note.

Licensed under the [MIT License](LICENSE).

Instrument sequence generation is pluggable: each instrument can use a distinct smaller
classical or QML model. This version uses an existing Gemini model through inference for
arrangement. A local rule baseline is available for development and comparison.

## Setup and quick demo

Python 3.11 or newer is required. From this directory in PowerShell:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts\make_example.py
.\.venv\Scripts\python.exe scripts\setup_audio.py
.\.venv\Scripts\python.exe -m orchestrator --manifest examples\parts.json --config examples\orchestration.json --backend rules --out output-demo --require-audio
~~~

The audio installer downloads FluidSynth's official Windows x64 release and GeneralUser
GS into assets/, preserving licenses and recording versions and archive hashes. On
macOS/Linux install FluidSynth separately, then run with --skip-fluidsynth.
Existing assets can be supplied using --fluidsynth and --soundfont; environment
alternatives are FLUIDSYNTH_PATH and SOUNDFONT_PATH.

The example contains 16 synthetic parts with different source tempi and some transposed
harmony. **These fixtures are not quantum-generated music.** Replace them with your
QML parts to evaluate the real system.

## Gemini

Set GEMINI_API_KEY in your process environment without committing it to a file.
GOOGLE_API_KEY is also accepted. Then run:

~~~powershell
.\.venv\Scripts\python.exe -m orchestrator --manifest examples\parts.json --config examples\orchestration.json --out output-gemini --require-gemini --require-audio
~~~

The configurable default is gemini-3.8-flash, listed in the
[Google model catalogue](https://ai.google.dev/gemini-api/docs/models).
The adapter uses the GenAI SDK's Interactions API with a JSON schema. Earlier compatible
SDKs use generate_content. Timeouts, call budgets and up to two correction attempts are
configurable. Credentials are excluded from prompts and reports.

When a key is missing or proposals fail validation, the CLI writes the latest validated
local arrangement and reports the fallback. --require-gemini returns exit code 2 if
Gemini did not complete every stage. Offline tests make no paid API calls; live API
access depends on your Google project.

## Supply QML output

Write a manifest naming the lead and each part:

~~~json
{
  "lead_track": "theme",
  "parts": [
    {
      "id": "theme",
      "instrument": "flute",
      "path": "quantum/theme.mid",
      "source": {"generator": "your QML model", "backend": "your actual hardware"}
    },
    {"id": "bass", "instrument": "cello", "path": "quantum/bass.mid"}
  ]
}
~~~

Paths are relative to the manifest. For multitrack files set midi_track to its zero-based
index; optional channel is also zero-based (0–15). Multiple note-bearing tracks require
explicit selection. Instrument labels are explicit and MIDI notes use sounding pitch.

Beat-based events are supported through notes with pitch, onset_beats, duration_beats
and velocity; see examples/note_events.json. Supply exactly one of path or notes per
part. IDs use letters, digits, underscores and hyphens. Optional tempo_bpm, role and
source metadata are accepted.

The orchestral palette is:

~~~text
piccolo flute oboe clarinet bassoon
horns trumpets trombones tuba
violin_1 violin_2 viola cello double_bass
timpani percussion
~~~

These are section tracks: 15 pitched channels plus one unpitched percussion channel.
Players within a section use configured polyphony. String sections use an ensemble
patch. Conservative concert-pitch profiles and divisi capacity are in
orchestrator/instruments.py.

## Plug in smaller instrument models

The pipeline separates sequence generation from arrangement:

~~~mermaid
flowchart LR
    F[Flute sequence model] --> P[Independent instrument parts]
    C[Cello sequence model] --> P
    O[Other instrument models] --> P
    P --> A[Gemini or local arrangement rules]
    A --> V[Musical constraints and melody protection]
    V --> M[MIDI and audio]
~~~

Implement generate(request) on each adapter. A GenerationRequest supplies the part ID,
instrument, bars, 4/4 metre, tempo, concert-pitch range, section polyphony, optional seed
and adapter-specific options. Return a GeneratedSequence or its dictionary equivalent
containing exactly one of:

- notes: InputNote events with MIDI pitch and quarter-note beat times;
- path: an existing MIDI file, with optional midi_track and channel selectors.

Adapters handle your models' checkpoints, inference, QML execution and token decoding.
For models producing audio, the adapter must first transcribe it to MIDI/events.
Raw tokens, audio arrays and quantum measurement counts cannot be arranged directly.
The orchestration package introduces no dependency on PyTorch, a quantum SDK or a
particular sequence architecture.

The generator receives instrument limits as guidance. The arranger applies its existing
range, polyphony, tempo reconciliation and lead protection checks to the output. The
request does not impose shared chords or give generators another instrument's sequence;
harmonic reconciliation happens after independent generation. Explicit conditioning can
be passed in options if your models support it. A seed may control local sampling but
does not guarantee reproducible results on quantum hardware.

### Python integration

Here is a reusable adapter pattern; adapt sample() and decode() to your model's API:

~~~python
from orchestrator import (
    GeneratedSequence, GenerationRegistry, GenerationJob,
    OrchestrationConfig, orchestrate_generated,
)

class InstrumentAdapter:
    def __init__(self, model, decode):
        self.model = model
        self.decode = decode

    def generate(self, request):
        tokens = self.model.sample(
            instrument=request.instrument,
            length_beats=request.duration_beats,
            seed=request.seed,
            **request.options,
        )
        # decode must return InputNote objects or dictionaries in quarter-note beats.
        return GeneratedSequence(
            notes=self.decode(tokens), tempo_bpm=request.tempo_bpm,
        )

# Supply your own loaded models and decoders here.
registry = GenerationRegistry()
registry.register(
    "flute-qml-v1", InstrumentAdapter(flute_model, decode_flute),
    instruments=["flute"], source={"model_version": "1", "backend": "your hardware"},
)
registry.register(
    "cello-small-v2", InstrumentAdapter(cello_model, decode_cello),
    instruments=["cello"], source={"model_version": "2"},
)
result = orchestrate_generated(
    [GenerationJob(id="theme", instrument="flute", seed=17),
     GenerationJob(id="bass", instrument="cello", seed=23)],
    "theme", registry,
    OrchestrationConfig(backend="rules", bars=16, output_dir="output-models"),
)
~~~

Use CallableGenerator(function) to wrap a function that already returns decoded output.
For an explicit per-part model override, set GenerationJob.model to a registered name;
otherwise its instrument route is used. register() keeps one model instance per name,
so multiple section tracks can reuse a checkpoint. Generation is sequential. Model
instances supplied through Python remain owned by the caller.

To inspect or save the generated material separately, use
registry.generate_parts(jobs, lead_track, bars=16, tempo_bpm=96, parts=existing_parts).
It returns a normal Manifest, which can be passed to orchestrate(). The optional parts
argument accepts existing MIDI/event parts alongside generated jobs. IDs must be unique
across both lists, and the lead can come from either.
Pass retain_midi_dir="retained-midi" to snapshot returned files immediately. Without
retention, your adapter must keep its MIDI output files stable until arrangement finishes.

### CLI integration

Run the supplied two-adapter example:

~~~powershell
.\.venv\Scripts\python.exe -m orchestrator --generation-manifest examples\generation.json --backend rules --bars 16 --no-audio --out output-generators
~~~

**The example adapters are synthetic fixtures, not trained models or quantum hardware.**
Replace their factory entries with your own importable Python factories. Each factory
returns an object implementing generate(request), for example:

~~~json
{
  "lead_track": "theme",
  "models": {
    "flute-qml": {
      "factory": "my_music.adapters:build_flute",
      "kwargs": {"checkpoint": "checkpoints/flute", "device": "cpu"},
      "source": {"model_version": "1"}
    },
    "cello-small": {
      "factory": "my_music.adapters:build_cello",
      "kwargs": {"checkpoint": "checkpoints/cello"},
      "source": {"model_version": "2"}
    }
  },
  "routes": {"flute": "flute-qml", "cello": "cello-small"},
  "jobs": [
    {"id": "theme", "instrument": "flute", "seed": 17},
    {"id": "bass", "instrument": "cello", "seed": 23}
  ]
}
~~~

Only factories used by jobs are instantiated. Routes and model references are checked
before loading them. Job fields also support model, bars, tempo_bpm, role, options and
source. An optional parts array has the existing PartSpec format. Factories execute
Python code: use manifests from trusted sources. Install your adapter module into the
same environment. Factory kwargs and options are passed through as supplied; paths in
them are interpreted by your adapter (the examples assume the current working directory).
Existing parts' MIDI paths resolve relative to the manifest, whereas returned MIDI paths
resolve relative to the Python process. Keep credentials in the environment, not JSON.

--model selects the Gemini arranger, while generation models are selected in the
generation manifest. Change --backend to gemini to use Gemini after generation.
There is no automatic substitution of failed generators. A failure identifies the
part and model; Python callers can inspect its chained exception for diagnostics.

With an output directory, generated_parts.json saves the unarranged inputs before
arrangement starts; each MIDI input is copied into input_midi/ immediately, so an adapter
can reuse a temporary output filename without overwriting earlier parts. Model name,
adapter, supplied version/backend metadata,
requested length/tempo and seed are retained in each part's source and report.json.
Sensitive options and factory kwargs are not copied into reports. Default generation
length covers start_bar + bars; a job's bars can override it. Replay saved material with:

~~~powershell
.\.venv\Scripts\python.exe -m orchestrator --manifest output-generators\generated_parts.json --backend rules --bars 16 --no-audio --out output-replay
~~~

This adds the integration boundary for your future models. It does not train smaller
generators or a new orchestration transformer; Gemini remains an inference provider and
the local orchestrator remains a rule implementation.

## Configuration and edit policy

The example configuration supplies key/chord overrides. Omit them to infer harmony from
the lead or let Gemini propose a progression.

| Setting | Default |
|---|---|
| Length / metre | 16 bars / 4/4 |
| Excerpt start | Bar 0 |
| Resolution | 480 ticks per quarter note |
| Tempo | Lead's tempo, otherwise 96 BPM |
| Model window | 4 bars plus a preceding context bar |
| Individual accompaniment edits | 20% per phrase, rounded down |
| Individual pitch / duration repair | Two semitones / half to twice the source |
| Cumulative phrase transpose / placement | 48 semitones / one bar |
| Model calls / correction attempts | 18 total / at most 2 per stage |

Configuration fields include bars, start_bar, window_bars, ppq, tempo_bpm, key, chords,
backend, model, edit_budget, max_corrections, max_api_calls, api_timeout_seconds,
render_audio, soundfont, fluidsynth and sample_rate. A supplied chord list repeats with
one chord per bar. Config-relative SoundFont paths are resolved relative to that file.

Lead timing and pitches are preserved except one uniform octave shift to fit its
instrument. A lead that cannot fit this way is rejected. Gemini may adjust lead
dynamics and pan. Phrase transforms affect every source note equally; individual
edits count cumulatively against the source after group transposition, including
baseline repairs.

Muting retains source identifiers and is reported separately from the edit budget.
Muting over half a part's notes generates a review warning. Proposals are atomic and
rejected for unknown IDs, edits to context, broken timing, range/polyphony violations,
or excessive edits. Valid window proposals are kept when the diagnostic score does
not substantially worsen.

Source tempi map to a shared pulse, preserving beat positions. Input with metre changes,
non-4/4, or tempo changes within a file is rejected. Short parts end in rests; excerpt
boundary clipping is reported. Sustain becomes longer note durations. Other controllers
and pitch bends are omitted with warnings. Entrances/rests are primarily scheduled at
note onsets; a note sustaining from a preceding region is not cut by a silence directive.

## Outputs and assessment

The output folder contains original.mid, baseline.mid and arrangement.mid plus WAV
comparisons when rendering succeeds. normalized_input.json and arrangement.json
preserve exact note state. report.json includes source metadata, harmonies, edits,
model failures, lineage, metrics and artifact paths.

WAV comparisons use the same SoundFont and sample rate. Audible-sample RMS is matched
with shared peak headroom; this is a comparison proxy, not perceptual LUFS.
Baseline and arrangement are identical in rule-only mode.

Metrics consider chord coverage with short passing/neighbor notes, monophonic melodic
motion, accompaniment retention, rough intervals, density, edit severity and a MIDI
velocity balance proxy. They do not establish musical quality or actual audibility.
Listen for melody clarity, coherence, phrasing, balance, transitions and recognisable
QML motifs. Preview rendering and range checks do not certify live performance.

## Python API

~~~python
from orchestrator import load_manifest, orchestrate, OrchestrationConfig

manifest = load_manifest("my_parts.json")
result = orchestrate(
    manifest.parts, manifest.lead_track,
    OrchestrationConfig(backend="gemini", output_dir="output"),
)
print(result.report["provider_status"])
~~~

Use output_dir=None for in-memory results. A custom provider adapter can be injected
with provider=. quantumOrchestrator.py is a compatibility CLI entry.

## Checks

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\check_environment.py
.\.venv\Scripts\python.exe scripts\inspect_output.py output-demo
~~~

Tests cover lead/provenance protection, independent tempi, MIDI selection, sustain,
excerpt boundaries, key reconciliation, budgets, malformed edits, instrument
constraints, failed plans, correction feedback, provider failures and SDK request shape.

## Quantum Duet import

The separately installed [Quantum Duet component](components/quantum_duet/README.md) provides frozen inference and a source browser demo. It does not yet connect paired Bell outputs to the generation registry. Shared design and separate-session tasks are in [docs/team](docs/team/README.md).
