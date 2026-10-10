# Quantum Harmony Studio — Qollab v2

Interactive POP909 hierarchical quantum harmony demo.

Quantum: 3-qubit coarse PQC, 4-qubit OTHER resolver, Qollab-selected measured backend, one circuit per backend call, measured-distribution cache.

Classical: harmonic-colour post-filter, sampling from returned histograms, major-key transposition, rare OTHER fallback, browser audio, UI.

Build:

```bash
python tools/export_models.py \
  --coarse "C:/Users/叶瀚升/Downloads/pop909_quantum_3q_starter/coarse_3q_theta_models.npz" \
  --resolver "C:/Users/叶瀚升/Downloads/pop909_quantum_3q_starter/other_4q_theta_models.npz" \
  --rare-csv "C:/Users/叶瀚升/Downloads/pop909_quantum_3q_starter/pop909_other_ranked_4q.csv"

python tools/build_zip.py
```

Upload `quantum-harmony-studio-qollab.zip` to a Qollab JS/Qiskit project.

Current platform note: Qollab built-in simulator was verified with the v1 probe. The Qollab-provided IonQ browser route was blocked by browser CORS when calling `https://api.ionq.co/v0.4/jobs`. Do not claim IonQ execution unless a later run succeeds.
