# Quantum Harmony Studio — Qollab v2

Interactive POP909 hierarchical quantum harmony demo.

Quantum: 3-qubit coarse PQC, 4-qubit OTHER resolver, Qollab-selected measured backend, one circuit per backend call, measured-distribution cache.

Classical: harmonic-colour post-filter, sampling from returned histograms, major-key transposition, rare OTHER fallback, browser audio, UI.

Build:

```bash
python tools/export_models.py \
  --coarse "/path/to/coarse_3q_theta_models.npz" \
  --resolver "/path/to/other_4q_theta_models.npz" \
  --rare-csv "/path/to/pop909_other_ranked_4q.csv"

python tools/build_zip.py --out ../build/pop909-studio.zip
```

The checked-in data/models.json is ready to use; export only to replace the
checkpoint. The ZIP builder preserves existing archives and includes file hashes
and source notices. Current verification is local compilation and BasicSimulator
inference. No fresh Qollab/Pyodide or IonQ execution is claimed.

A progression may submit several jobs, one circuit per submission. Context cache
hits reuse histograms without further jobs. This studio is separate from the
single-batch Duet run; a platform imposing one job per button press requires an
execution redesign before deployment. Unknown or physical backends are rejected.

Current platform note: Qollab built-in simulator was verified with the v1 probe. The Qollab-provided IonQ browser route was blocked by browser CORS when calling `https://api.ionq.co/v0.4/jobs`. Do not claim IonQ execution unless a later run succeeds.
