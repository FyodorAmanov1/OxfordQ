# OxfordQ · Quantum Music & Orchestration

**Turn independent musical ideas into an ensemble while keeping a trace from each sounding note back to its source.**

OxfordQ brings quantum-music experiments, instrument-generation adapters and a conductor into one research codebase. A frozen quantum circuit Born machine supplies motif tokens, a separate POP909-derived component supplies harmony, and classical or Gemini-based planning shapes the result into arrangements and expressive composition studies.

The central question is musical and computational: how much can a conductor change rhythm, texture and instrumentation while preserving the identity of its source material?

## Choose a path

| Path | What to explore |
|---|---|
| **Arrange existing parts** | Import MIDI or timed note events, reconcile tempi, protect a lead and validate accompaniment edits |
| **Generate instrument parts** | Route instrument requests to pluggable generators, including the frozen motif adapter |
| **Compose from motifs** | Develop source material through explicit form, rhythm, register, changing metre and expression |
| **Quantum Duet** | Inspect a paired musical-coordination experiment and export its two voices without resampling |
| **Graph composer / POP909 studio** | Explore the additional component interfaces and their own documented assumptions |

## Quick start: local arrangement

Requires Python 3.11 or newer. Create and activate a virtual environment, then run from the repository root:

```bash
python -m pip install -e .
python scripts/make_example.py
python -m orchestrator --manifest examples/parts.json --config examples/orchestration.json --backend rules --no-audio --out output-demo
```

The example parts are synthetic fixtures. This first command path demonstrates MIDI import, arrangement and reporting without an external model or audio renderer.

For audio, use `python scripts/setup_audio.py` to prepare the supported FluidSynth/SoundFont setup, then replace `--no-audio` with `--require-audio`. Platform-specific installation and asset-license details are in the [arrangement guide](ORCHESTRATION_GUIDE.md).

## Generate and develop motifs

Install the root package's quantum extra for the supplied QCBM-based path:

```bash
python -m pip install -e ".[quantum]"
python -m orchestrator --generation-manifest examples/qcbm_generation.json --backend rules --no-audio --out output-qcbm
python -m orchestrator.composition --style debussy --no-audio --out output-composition
```

Use a new output directory for each example. The composition path is separate from the fixed-timeline arranger and supports motif development, metre and tempo maps. Its inspired ensemble studies are compositional examples, not models trained to reproduce the named composers.

The frozen twelve-qubit motif model is shared across instruments. A classical decoder supplies instrument-specific register, scale and rhythmic choices; the repository does not claim separately trained quantum models for every instrument. Local statevector inference and recorded device evidence are labeled according to their actual source.

## The conductor and its constraints

```text
Instrument models or MIDI → timed source events → arrangement / composition plan
                                              → constraint validation
                                              → MIDI, optional audio and reports
```

The arranger protects the lead's pitches and timing apart from a permitted uniform octave placement. Accompaniment changes are bounded by range, polyphony and edit constraints. The separate composition path references immutable source events while developing rhythm, form and octave placement.

Gemini is an optional external planning provider. The rules path works without an API key. For the provider path, set `GEMINI_API_KEY` or `GOOGLE_API_KEY` in the process environment and follow the relevant guide. Reports identify provider completion and fallback behavior; use the documented strict flags when successful provider execution is required.

## Outputs worth inspecting

- **MIDI and optional WAV:** hear original, baseline and arranged material where the selected path supplies comparisons.
- **Structured scores and plans:** inspect timing, instruments, motif use and expression.
- **Reports and source lineage:** trace changes, source IDs, validation diagnostics and artifact hashes.
- **Listening pages:** compare composition/performance variants with their accompanying metadata.

Musical diagnostics measure properties such as harmonic fit, motion, density and source retention. They do not replace listening evaluation. CHSH evidence concerns the paired coordination experiment and should not be used as a score for musical quality or quantum speedup.

## Guides and components

- [Arrangement setup, manifests and generator adapter examples](ORCHESTRATION_GUIDE.md)
- [How orchestration decisions work](docs/orchestration.md)
- [Expressive composition](docs/composition.md) and [natural performance](docs/natural-performance.md)
- [Quantum Duet](components/quantum_duet/README.md) and [paired export integration](examples/duet_integration/README.md)
- [Quantum graph composer](components/quantum_graph_composer/README.md)
- [POP909 integration](README_POP909_INTEGRATION.md)

## Attribution and license

The original integration code is covered by the [MIT license](LICENSE). Imported components, model snapshots, training corpora and optional audio assets retain their own notices. The POP909 harmony integration includes collaborator Hansheng's exported snapshot; the frozen motif model comes from Quantum Duet. See [model source notices](quantum_models/SOURCE_NOTICES.md) and each component's notices for provenance and redistribution boundaries.
