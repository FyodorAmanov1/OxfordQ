# Quantum Graph Composer

Generate a theme, develop it, and hear it return: a quantum walk and a persistent
quantum state supply melodic, rhythmic and harmonic material for a complete piece.
The project explores quantum dynamics as a creative compositional medium.

**Quantum Playground · OxfordQ · MIT licensed**

This effort is supported by Qollab & IonQ

## Run and listen

Press **Run**, choose the free **Built-in simulator**, and press **Generate music**
in the interface. The recommended settings are seed 1201, 64 bars, 104 BPM,
interaction 0.7, and 512 shots. The generated piece lasts about 2:33. Press Play,
or download WAV, MIDI and the score with every quantum decision.

Select 16 bars for a short audition. Change the seed for another composition, or
change the phase interaction to alter the coupled quantum dynamics. Use Qollab's
**Stop → Run** before another generation. The code submits one circuit in one
backend job, including on free IonQ simulators. Start remote runs at 128 shots.
No account key, external model service or paid hardware is needed by the code.

## The generative mechanism

A six-qubit coupled quantum walk supplies a measured joint distribution over
three musical intervals. This initializes contour amplitudes in a persistent
13-qubit ideal Qiskit state over 8,192 possible contour/rhythm/harmony gestures.
The state evolves with musical-neighborhood Hamiltonians and interacting phases.
Past gestures change a phase feedback field; retained phases affect later
interference and the next joint gesture probabilities.

The first theme is generated from this material. Classical rules govern register,
voice leading, section form, theme-distance control and the final tonic. They
turn quantum proposals into a structured piece. Piano samples and accompaniment
are rendered classically. The downloadable score explains those boundaries and
records each gesture, constraint and ending override.

**Two execution stages:** the selected simulator runs the six-qubit entrance;
the rest is an explicitly ideal Qiskit Statevector calculation in browser Python.
Non-disturbing probability access and coherent initialization from a measured
histogram are simulation capabilities. IonQ is not assumed to expose state
amplitudes. Backend failures are reported without simulator substitution.

## What we can claim

The composer runs end to end locally, on Qollab's free built-in simulator, and
on its free IonQ Forte 1 simulator. Both authenticated platform tests generated
complete 64-bar, 2:33 compositions, with one six-qubit backend job per run.
Tests establish unitary circuit
equivalence, phase-dependent memory and one selected-backend job per generation.
Browser playback uses an acoustic piano sample bank and exports a real WAV and
MIDI. These findings demonstrate a compositional mechanism, not a quantum
speedup or superiority in musical quality. Musical quality remains a listening
question. There is no learned model or training corpus.

## Sources and build disclosure

This is an adaptation of Shi Qiu's disclosed quantum musical-graph investigation
with OpenAI Codex assistance. The adaptation adds the selected-backend circuit,
Qiskit continuation, portable rendering, accessible interface and deployment.
See SOURCE_NOTICES.md for the research starting point and asset provenance.
The acoustic PCM samples are a public-domain Florestan piano subset by Nando
Florestan. Original project code and documentation use the MIT license.

Source branch: [ShiQiu/quantum-graph-composer](https://github.com/FyodorAmanov1/OxfordQ/tree/ShiQiu/quantum-graph-composer/components/quantum_graph_composer).

**Team completion before publication:** add the public 2–3 minute demo-video
link and disclose any work predating the build window. Actual built-in and IonQ
simulator verification records are retained in the repository. Physical hardware
was not used, and this private test draft is not a final hackathon submission.
