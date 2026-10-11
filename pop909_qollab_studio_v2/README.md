# Quantum Harmony Studio — Qollab v2

Interactive POP909 quantum-harmony demo with **separately trained major and minor hierarchical PQCs**.

## What is quantum?

For each mode, the harmony model is autoregressive:

```text
previous coarse chord
        |
        v
3-qubit coarse PQC
        |
        +--> one of 7 core harmonic classes
        |
        +--> OTHER
               |
               v
        4-qubit resolver PQC
               |
               v
     concrete chromatic chord
```

The two modes use independent trained parameters:

- **Major 3q coarse states:** `I, ii, iii, IV, V, vi, vii°, OTHER`
- **Minor 3q coarse states:** `i, III, iv, v, V, VI, VII, OTHER`
- Each mode has its own **4-qubit OTHER resolver** with 15 common chromatic classes plus `RARE_OTHER`.

Major parameters were trained from POP909 **major-key sections**. Minor parameters were trained separately from POP909 **minor-key sections**; minor mode is not a relabelled or transposed major model.

Training used exact Qiskit Statevector probabilities to fit POP909 transition distributions. In the Qollab demo, the trained circuits are executed with **shots** on the backend supplied by Qollab, one circuit per backend submission. Measured histograms are cached separately by mode and harmonic context during the page session.

## What is classical?

The following parts are intentionally classical:

- sampling the next chord from the measured histogram;
- `In-key` / `Adventurous` post-filtering after quantum measurement;
- key transposition and chord-to-MIDI mapping;
- the frequency-weighted fallback when `RARE_OTHER` is selected;
- browser audio synthesis and MIDI export;
- all UI logic.

`Authentic` uses the measured coarse distribution unchanged. `In-key` removes the `OTHER` branch and renormalizes; `Adventurous` increases the measured `OTHER` weight before renormalizing.

## Model bundle

`data/models.json` uses schema version 3:

```text
modes
├── major
│   ├── coarse_contexts
│   ├── resolver_labels
│   ├── coarse_theta
│   ├── resolver_theta
│   └── rare fallback table
└── minor
    ├── coarse_contexts
    ├── resolver_labels
    ├── coarse_theta
    ├── resolver_theta
    └── rare fallback table
```

The exported JSON is included in the repository so the Qollab project can run without retraining.

## Rebuild the model bundle

From `pop909_qollab_studio_v2/`:

```bash
python tools/export_models.py \
  --major-coarse /path/to/coarse_3q_theta_models.npz \
  --major-resolver /path/to/other_4q_theta_models.npz \
  --major-rare-csv /path/to/pop909_other_ranked_4q.csv \
  --minor-coarse /path/to/minor_coarse_3q_theta_models.npz \
  --minor-resolver /path/to/minor_other_4q_theta_models.npz \
  --minor-rare-csv /path/to/pop909_minor_other_ranked_4q.csv

python tools/build_zip.py
```

Upload the generated `quantum-harmony-studio-qollab.zip` to a Qollab JS/Qiskit project.

## Qollab execution status

The Qollab **built-in simulator** has been verified with this workflow.

The Qollab-provided IonQ browser route was previously blocked at the browser transport layer by CORS when requesting `api.ionq.co`. That is not evidence of an IonQ circuit failure, but it also means this repository does **not** claim successful IonQ execution unless a later run is verified.

## Scientific boundary

This project demonstrates a quantum-first generative harmony layer and transparent quantum measurement workflow. It does **not** claim quantum advantage, superior generalization, or superior musical quality over classical models.

The quantum component generates harmony; audio rendering and the rest of the browser experience are classical.
