# Combined repository review

Reviewed code commit: `e9f02aecfcd973dbe8e235d74265515b65aca348`. Team base: `7b9b6b0f6a27425645c01389ccbcd7d63b4a3982` (main, Add MIT license).
The earlier 680e403 observation is its parent. Initial remote inventory contained
only main and no open PRs. No unreviewed branch was merged. The final handoff adds
documentation only after this code revision; resolve HANDOFF_SHA as in README.md.

| Component / actual functions | Status and flow |
|---|---|
| orchestrator/generation.py: GenerationRegistry.generate_parts, registry_from_manifest, orchestrate_generated | Implemented sequential per-instrument factory routing; notes/MIDI -> Manifest -> pipeline. Saves original generated parts and snapshots reused MIDI. No trained generators bundled |
| orchestrator/models.py: InputNote, PartSpec, Manifest, Score, ArrangementResult | Implemented validated types, beat input and tick output, string source metadata; no paired run/result schema yet |
| orchestrator/generator_examples.py: DemoMelodyGenerator, DemoBassGenerator; examples/generation.json | Synthetic fixture adapters, explicitly not QML checkpoints |
| orchestrator/midi_io.py: load_manifest, import_parts, export_midi | Implemented concert-pitch MIDI/events -> tick score. Explicit track/channel selectors, sustain, tempo/metre rejection, excerpt clipping; rests implicit in score |
| orchestrator/theory.py: baseline_plan, musical_metrics; baseline.py: arrange_baseline | Implemented harmony inference, register placement, bounded repair/muting. Central arrangement changes raw music; metrics heuristic |
| orchestrator/validation.py: validate_plan, validate_score, apply_proposal | Implemented source/lead protection, atomic edits, range/polyphony and cumulative budget validation |
| orchestrator/pipeline.py: orchestrate | Implemented rules/Gemini planning, validated corrections, report + original/baseline/arrangement MIDI/JSON; explicit degraded/unavailable provider state |
| orchestrator/gemini.py: GeminiProvider.request | Real SDK inference implementation; remote API/key required for live calls. Offline tests intercept HTTP. Catalogue availability/model access not validated in this import |
| orchestrator/audio.py: discover_audio, render_comparisons | Implemented subprocess FluidSynth + SF2 comparison renderer. Local native tools absent in new checkout; unavailable audio reported. Not a Qollab/Pyodide renderer |
| orchestrator/cli.py: main; __main__.py; quantumOrchestrator.py | Working existing CLI, strict require flags. Existing examples and root packaging retained |
| scripts/setup_audio.py, check_environment.py, make_example.py, inspect_output.py | Implemented setup/inspection utilities. Audio setup downloads external native assets; not run here. Example MIDI generation is optional and excluded output |
| components/quantum_duet/src/quantum_duet/circuit.py: build_circuit, bind_parameters | Frozen 12-qubit, 84-angle QCBM circuit and canonical parameter order; selected checkpoint bundled |
| .../duet_quantum.py: setting_batch, run_batch, decode_outcome; integration.py: generate_take, assemble_take | Implemented one supplied-backend batch, labelled counts, ba bit order, four-setting stats, local event projection and explicit recorded melody mode. Backend's real IonQ representation unresolved |
| .../duet_classical.py, duet_referee.py, music.py: shared_choices, cues, sampled_metrics, musical_event | Precommitted noncommunicating comparator, independent cue streams and fixed local musical mapping; no central success-based musical repair |
| .../cli.py: main; dev/server.py: Handler | Added offline installed-asset inference and explicit loopback development UI; no original research path dependency |
| components/quantum_duet/web/ui.mjs: DuetAudio, mountDuet, midiBytes; web/main.js | Working legacy two-voice comparison/playback/export UI and documented Python bridge. JSON/base64 visible exports preserved. No integrated orchestration UI yet |
| components/quantum_duet/tools/build_qollab.py | Canonical source -> ignored root-entry upload directory/ZIP/hash manifest; no generated copies committed |
| tests/test_orchestrator.py; components/quantum_duet/tests | 29 existing test cases plus 3 imported pytest checks (ten inference cases inside isolated subprocess), Node audio/MIDI checks. GenerationRegistry has no dedicated team test coverage in this revision; B owns paired integration tests |
| docs/team/run-contract.md and prompts | Design and planned adapter/UI/backend diagnosis; not implemented features |

The two independent chains currently terminate separately: instrument generators ->
Manifest -> central arranger -> MIDI/(optional native WAV); frozen quantum batch ->
paired rounds -> local events -> equal WebAudio/MIDI. B supplies the explicit shared
result boundary, C its user-facing raw/arranged controls. Both repeat MIDI/event
conversion legitimately; do not replace existing pipelines or relabel synthetic demos.

## Highest-priority risks

1. IonQ: historical four/five requests rejected before accepted job/counts. Smallest
   single-circuit IonQ request is untested. Transport/SDK/proxy cause remains inference.
   A must reproduce single-circuit first and inspect actual serialization/versions.
2. Pair identity: GenerationRegistry invokes generate per instrument; independent
   calls would destroy paired evidence. One completed immutable result is mandatory.
3. Raw/arranged: baseline.arrange_baseline modifies accompaniment even with rules;
   separate direct raw playback and preserved evidence before invoking pipeline.
4. Deployment: FluidSynth/subprocess/SF2 cannot be assumed in Qollab. Runtime inference
   requires only Qiskit/NumPy. Keep API keys out of JS/assets. Free local demo required.
5. Result labels/counts: run_batch rejects missing/duplicate labels or unknown result
   formats; do not add positional guessing or probabilities dressed as integer shots.
6. Browser lifecycle/export: main.js awaits mountDuet until Stop/pagehide to retain
   platform console capture. Visible payload route is verified historically; toolbar
   downloads are not. Namespace/build adaptation needs new real platform check.
7. Provenance: generated source strings allow caller metadata precedence in registry;
   B must reject contradictory run/checkpoint identifiers, not hide them behind routing.
8. Scientific scope: histograms have reconstructed ordering, conditional shot intervals,
   and simulated policies. QCBM NLL worse than classical. Arranged polish is not proof.

Official [IonQ migration documentation](https://docs.ionq.com/api-reference/v0.4/migration-from-v0.3)
describes job-type and result-response changes; it does not diagnose this bridge.
Qollab runtime/JS documentation URLs in A's prompt were inaccessible to the web
reader here; A must inspect them through a supported browser and installed bridge.
