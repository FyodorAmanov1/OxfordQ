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

## Copy into the repo

Copy:

```text
quantum_models/
scripts/run_quantum_harmony_orchestrator.py
```

into the OxfordQ repository.

## pyproject.toml

Add an optional dependency:

```toml
[project.optional-dependencies]
dev = ["pytest>=8,<10"]
quantum = ["qiskit>=2,<3"]
```

Change package discovery to:

```toml
[tool.setuptools.packages.find]
include = ["orchestrator*", "quantum_models*"]
```

Then install:

```powershell
python -m pip install -e ".[dev,quantum]"
```

## Run

From the OxfordQ repo root:

```powershell
python scripts/run_quantum_harmony_orchestrator.py `
  --manifest examples/parts.json `
  --coarse-model C:\path\to\coarse_3q_theta_models.npz `
  --resolver-model C:\path\to\other_4q_theta_models.npz `
  --rare-csv C:\path\to\pop909_other_ranked_4q.csv `
  --bars 16 `
  --seed 42 `
  --backend rules `
  --out output-quantum-harmony
```

The output includes `quantum_harmony.json`, and the existing orchestrator report receives
a `quantum_harmony` section recording the exact generated sequence and quantum provenance.
