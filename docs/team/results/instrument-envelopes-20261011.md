# Instrument volume and note envelopes — 2026-10-11

Implemented on the existing isolated composition worktree, following
8cd73440d838df2982ba83a51c0d543d94f5c275. The separate GitHub branch is
codex/expressive-composition-20261011.

## Changes

- Editable instrument performance profiles: part volume, attack, decay, sustain,
  release, swell, small amplitude modulation, and struck/sustained mode.
- Piano/percussion strike and decay; fast bowed-string attacks; breath-shaped
  wind attacks/releases; individual defaults for flute, clarinet, oboe, bassoon,
  cello, double bass, horn and tuba. Piano is now a supported instrument profile.
- Independent per-note SoundFont rendering with explicit amplitude envelopes.
  Overlapping notes retain independent attacks/releases. Velocity affects native
  sample synthesis; volume, interpolated CC11 expression and panning affect the mix.
- Composition and general orchestration WAV paths use this renderer. MIDI-only
  rendering remains available through the existing CLI path. Missing native library
  is explicitly reported; there is no silent substitute renderer.
- Composition score JSON records performance settings. MIDI records per-part CC7
  and envelope text metadata. Generic MIDI players choose their own envelopes.
- Composition CLI accepts repeated --part-volume instrument=level arguments.
  Listening pages and both browser previews have an overall playback volume slider.
- Duet preview distinguishes flute from cello note shape; POP909 preview offers
  piano, bowed-string, flute, percussive and synth shapes. Playback settings leave
  measured source events, paired identities and experimental shots intact.

## Local artifacts and compilation

The four updated studies are at workspace-root
output-instrument-envelopes-20261011/index.html. All four rendered successfully,
including raw/reference WAVs. Their deterministic model seeds and symbolic
composition rules match the prior studies; this update changes sound production.
The SoundFont renderer is dry, without reverb/chorus. Defaults are approximations
of ordinary articulation, not a complete model of a human performer.

Compilation completed for the Python package, Duet module and POP909 browser module.
The root Python wheel built locally in dist/instrument-envelopes-wheels-20261011.
Fresh canonical browser archives are built in dist/instrument-envelopes-duet-20261011
and dist/instrument-envelopes-studio-20261011.zip. Automated test suites were not
added or rerun for this change; the earlier 241-pass report predates it. No real
browser listening review, live API, physical QPU, new training or held-out motif
inspection is claimed. MIDI round-trip and timeline checks execute as part of
normal composition export/rendering and completed for the saved examples.

See docs/composition.md for parameters, the FluidSynth API references and the
distinction between exact WAV envelopes and ordinary MIDI playback.
