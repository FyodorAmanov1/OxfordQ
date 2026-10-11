# Source disclosure

This component was developed with OpenAI Codex assistance at the direction of
Shi Qiu. The musical graph, coherent dynamics, theme/variation composer and MIDI
writer are extracted and adapted from the local investigation
`quantum_musical_graph_20261011`. That investigation is disclosed as the starting
point, rather than representing this extraction as an independently invented
project. The repository's other music components remain separate.

The submission adaptation adds the six-qubit selected-backend entrance, full
Qiskit Statevector continuation, portable sample renderer, accessible browser
interface, one-job bridge, judge CLI, deployment builder, and verification.
No training corpus, learned checkpoint, recorded melody or external model API
is used. The team should disclose any work predating the hackathon build window
on its final project page; the commit history does not prove when the original
research ideas were developed.

`data/piano.json` contains losslessly extracted PCM regions from
`florestan-piano.sf2`, a subset of Florestan Basic GM GS:

Copyright (c) 2016, Nando Florestan. **Public Domain.**

Source: [pinned piano bank](https://raw.githubusercontent.com/amberwhitehead/tinysoundfont-pybind/b70694b02c2464853e1a9c50282a616129c4217e/test/florestan-piano.sf2)
and [authoritative source notice](https://github.com/amberwhitehead/tinysoundfont-pybind/blob/b70694b02c2464853e1a9c50282a616129c4217e/NOTICE).
Original SF2 SHA-256:
`f4f69027c04e8f1e0b87ee7ffad254d133ca8e07740844ea14307821a1dbb221`.
No TinySoundFont library, sample MIDI, or third-party synthesizer code is bundled.
Our small renderer uses those public-domain samples with resampling, sustain
loops and a decaying envelope; it does not implement every SF2 generator.

Qiskit is an external Apache-2.0 SDK required by Qollab; NumPy is an external
BSD-licensed library available in Pyodide. Neither library is copied into this
project. The component's original code and documentation are MIT licensed.

This effort is supported by Qollab & IonQ
