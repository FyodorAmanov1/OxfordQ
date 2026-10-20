# POP909 quantum harmony integration

This bridge connects Hansheng's POP909 hierarchical PQC to the existing OxfordQ
orchestration pipeline without changing the orchestrator core.

Flow:

```text
POP909-trained 3q coarse PQC
          |
          v
I / ii / iii / IV / V / vi / vii° / OTHER
          |
          | if OTHER
          v
4q chromatic resolver PQC
          |
          v
resolved harmonic labels
          |
          v
music21 chord symbols
          |
          v
OrchestrationConfig.chords
          |
          v
existing OxfordQ orchestration / validation / MIDI / WAV
```

Important boundary:
- Qiskit Statevector is currently used, not IonQ hardware.
- Rare OTHER states beyond the top 15 use the existing classical POP909-frequency fallback.
- The full existing resolver cache is depth 4. The adapter infers depth from theta length,
  so a future full depth-6 `theta_0 ... theta_7` archive can replace it without changing
  integration code.

## Install

The integration and unchanged JSON checkpoints are packaged in this repository.
External NPZ files are optional.

~~~powershell
python -m pip install -e ".[dev,quantum]"
~~~

## Run

From the OxfordQ repo root:

~~~powershell
python -m quantum_models.orchestra --bars 16 --seed 42 --backend rules --no-audio --out output-quantum-harmony
~~~

This generates five independent parts using the existing frozen QCBM, decodes them
for their instruments, supplies POP909 harmony, then arranges and exports them.
To select instruments, use --instruments flute cello oboe --lead flute.
All sixteen repository instrument profiles are supported.
The scale/register/phrasing adaptation is classical; no instrument-specific
checkpoint training is claimed. Recorded tokens, checkpoint hashes and note
lineage are saved in generated_parts.json and report.json.

For minor keys, use --harmony infer --key "A minor": POP909 weights were trained
on major-key sections and the adapter rejects minor-key POP909 requests.

~~~powershell
python -m quantum_models.orchestra --backend gemini --require-gemini --no-audio --out output-model-gemini
~~~

Set GEMINI_API_KEY before running Gemini. --require-gemini exits with code 2 if
Gemini does not complete every stage; the report identifies any fallback.
Offline verification uses injected responses and makes no live API calls.

To apply only quantum harmony to your own MIDI or note manifest:

~~~powershell
python scripts/run_quantum_harmony_orchestrator.py --manifest examples/note_events.json --bars 16 --backend rules --no-audio --out output-harmony-only
~~~

The runner defaults to packaged weights. To replace them, supply --model-json or
both --coarse-model and --resolver-model; --rare-csv supplies the rare-class table.
Checkpoint arrays must be finite and contain all eight coarse contexts.

The output includes `quantum_harmony.json`, and the existing orchestrator report receives
a `quantum_harmony` section recording the exact generated sequence and quantum provenance.

Source revisions, byte hashes and dataset notices are in
quantum_models/IMPORT_MANIFEST.json and quantum_models/SOURCE_NOTICES.md.
The separate pop909_qollab_studio_v2 is an experimental browser harmony demo:
it can submit multiple jobs per progression and is not the single-batch Duet run.
