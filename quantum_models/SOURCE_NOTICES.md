# Model sources

The repository MIT license covers its original integration code. Dependency and
training-data rights remain with their respective sources.

- POP909 harmony integration and exported weights were copied from collaborator
  Hansheng's branch snapshot `747871ce68ebbd7b9febe42c08c020aa688cb432`.
  The original export includes checkpoint basenames, depth, and training scope.
  No POP909 MIDI dataset is bundled. The checkpoint's training scope is major-key
  sections; dataset access and any further redistribution should retain upstream
  POP909 notices. This repository does not establish a separate checkpoint license
  or relicense the POP909 dataset.
- The frozen twelve-qubit motif QCBM comes from `components/quantum_duet` at
  `c49c2e6cace0790211ae6808f4ecdc4cb77faa01`. Its underlying Bach corpus and
  edition notices are retained in that component's `SOURCE_NOTICES.md`.
  The instrument adapter reuses its parameters without training; the original
  Duet mapping and evidence are unchanged.
- Qiskit, music21, NumPy, mido, Google GenAI and any rendering software retain
  their own licenses. External audio assets are optional and are not bundled in
  the Python wheels or upload ZIPs.

`IMPORT_MANIFEST.json` records byte hashes and the exact source revisions.
Local simulated inference and classical instrument decoding do not establish
physical quantum execution, instrument-specific training, or quantum advantage.
