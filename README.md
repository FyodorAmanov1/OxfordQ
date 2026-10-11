# Quantum Harmony Studio

> **240-character pitch**  
> Quantum Harmony Studio uses separately trained 3q/4q PQCs on POP909 to generate major/minor chord progressions. Qollab runs shot-based Qiskit inference, and the Quantum Inspector shows how each chord was sampled.

**Hackathon Theme:** Quantum Playground  
**Source branch:** `hansheng/pop909-quantum-harmony`  
**Qollab-ready folder:** `pop909_qollab_studio_v2/`  

**Demo video:** _add final link_  
**Qollab project:** _add final link_  

> This effort is supported by Qollab & IonQ.

---

## Overview

**Quantum Harmony Studio** is an interactive quantum music generator built for the Qollab × IonQ Global Quantum Hackathon.

It uses separately trained hierarchical parameterised quantum circuits (PQCs) to generate Major and Minor chord progressions from harmonic transition statistics derived from the POP909 dataset.

Rather than using quantum measurement only as a source of randomness, the measured quantum distributions directly represent learned next-chord probabilities.

Users can choose a key, Major or Minor mode, progression length, harmonic style, number of shots, and random seed. The resulting progression can be played in the browser, exported as MIDI, and inspected chord-by-chord to reveal the measured quantum distributions that produced it.

---

## Key Features

- Separate **Major** and **Minor** trained quantum harmony models
- 3-qubit coarse harmony generator
- 4-qubit chromatic `OTHER` resolver
- Shot-based Qiskit inference in Qollab
- 12 selectable keys
- 8 / 16 / 32-bar progression generation
- `In-key`, `Authentic`, and `Adventurous` harmonic styles
- Interactive **Quantum Inspector**
- Browser playback with multiple instrument layers
- MIDI export
- Run-data export
- Measured-distribution caching for faster variations

---

## How It Works

The model is autoregressive. For each chord transition, the previous coarse harmonic state determines which trained 3-qubit PQC is executed.

```text
Previous coarse chord
        |
        v
  3-qubit PQC
        |
        +--> one of 7 core harmonic classes
        |
        +--> OTHER
               |
               v
        4-qubit resolver PQC
               |
               v
      Concrete chromatic chord
```

The Major and Minor modes use **independently trained parameter sets**.

### Major coarse states

```text
I, ii, iii, IV, V, vi, vii°, OTHER
```

### Minor coarse states

```text
i, III, iv, v, V, VI, VII, OTHER
```

If `OTHER` is measured, a second 4-qubit PQC selects one of fifteen common chromatic chord classes plus `RARE_OTHER`.

Major parameters were trained on POP909 major-key sections. Minor parameters were trained separately on POP909 minor-key sections, so Minor mode is **not** produced by simply transposing or relabelling the Major model.

---

## Quantum / Classical Boundary

The quantum component is responsible for the learned harmonic probability distributions.

The following parts are classical by design:

- sampling from the measured quantum histogram;
- `In-key` and `Adventurous` probability post-processing;
- key transposition and MIDI-note construction;
- the frequency-weighted `RARE_OTHER` fallback;
- browser audio synthesis;
- MIDI export;
- interface logic.

`Authentic` uses the measured coarse quantum distribution without harmonic reweighting.

This project does **not** claim quantum advantage, superior generalisation, or superior musical quality over classical methods.

---

## Training and Evaluation

Training used exact Qiskit Statevector probabilities to fit empirical POP909 chord-transition distributions.

For the separately trained Minor model:

- **3-qubit coarse model mean context TVD:** ~0.0377
- **4-qubit resolver mean TVD:** ~0.1306

These values measure aggregate training-distribution fit and are **not** presented as held-out generalisation results.

---

## Qollab Inference

At runtime, Qollab executes the frozen trained circuits with finite shots.

Each new mode/context requires one backend submission. Measured histograms are cached by mode and harmonic context so later variations can reuse previous quantum measurements.

The **Quantum Inspector** exposes the measured distribution for each generated chord. If a transition passes through `OTHER`, the Inspector also shows the 4-qubit resolver result.

---

## Running the Project

The Qollab-ready application is contained in:

```text
pop909_qollab_studio_v2/
```

Build the upload package from the repository root:

```bash
cd pop909_qollab_studio_v2
python tools/build_zip.py
```

This creates:

```text
quantum-harmony-studio-qollab.zip
```

Upload that ZIP to a Qollab JS/Qiskit project and select an available simulator backend.

---

## Model Bundle

Frozen trained parameters are stored in:

```text
data/models.json
```

Schema version 3 contains separate model bundles for Major and Minor:

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

The Qollab demo therefore runs without retraining.

---

## Judging Summary

### Novelty & Creativity

Most quantum music demos use quantum measurement mainly as a source of randomness. Here, trained PQCs represent **musically meaningful conditional chord distributions learned from a real pop-music dataset**.

The hierarchical design allows the system to model both common functional harmony and less common chromatic harmony without requiring one large circuit.

The **Quantum Inspector** also makes the quantum process part of the creative experience by showing the measured distribution behind individual chord transitions.

### Technical Execution

The system combines:

- independently trained Major and Minor 3-qubit coarse PQCs;
- mode-specific 4-qubit chromatic resolvers;
- Qiskit-based shot execution in Qollab;
- measured-distribution caching;
- interactive playback and MIDI export;
- explicit quantum/classical separation.

### Impact Potential

Music provides immediate feedback for concepts that are otherwise abstract.

Users can hear how a measured quantum probability distribution affects a creative result while inspecting the exact transition distribution behind it.

The project therefore functions both as a creative tool and as an educational interface for parameterised circuits, measurement distributions, hierarchical modelling, and hybrid quantum-classical workflows.

### Documentation & Reproducibility

The repository includes:

- the Qollab-compatible frontend;
- Qiskit inference code;
- exported Major and Minor trained parameters;
- model-export tooling;
- Qollab ZIP build tooling;
- documentation explaining the quantum/classical boundary.

The frozen model bundle allows the demo to run without retraining.

---

## Platform Status

The Qollab built-in simulator has been successfully verified with this workflow.

A previous attempt to use the Qollab-provided IonQ browser route was blocked at the browser transport layer by CORS before the request completed.

This repository therefore does **not** claim verified IonQ execution unless a later run succeeds.

---

## Dataset and Citation

This project derives its training statistics from the **POP909 Dataset for Music Arrangement Generation**.

If using or extending this work, please cite the associated POP909 paper:

> Ziyu Wang, Ke Chen, Junyan Jiang, Yiyi Zhang, Maoran Xu, Shuqi Dai, Guxian Bin, and Gus Xia. **“POP909: A Pop-song Dataset for Music Arrangement Generation.”** Proceedings of the 21st International Conference on Music Information Retrieval (ISMIR), 2020.

Only derived chord-transition statistics and trained model parameters are included in this project; the POP909 dataset itself is not redistributed here.

---

## Dependencies

- Qiskit 2.5.2
- NumPy 2.x

---

## License

MIT License.

---

## Acknowledgements

This effort is supported by Qollab & IonQ.
