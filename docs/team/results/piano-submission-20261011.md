# Piano and compact runnable submission — 2026-10-11

User requested piano in the generated pieces, a separate submission folder, and no
reorganization of the project. Clarification selected a smaller **runnable folder**
under 100 files after extraction, rather than split transport archives.

## Implementation

- Piano is now in the composition API and CLI defaults. It has a separate two-hand
  source-referenced harmony occurrence: bass foundation plus upper sustained chords,
  broken chords or arpeggios. Existing strike dynamics and CC64 pedal are retained.
- All original module/component paths remain. Existing source files, checkpoints,
  experiments and high-quality acoustic assets were not moved or replaced.
- `scripts/prepare_submission.py` selects the necessary runtime files at their
  original paths, retaining Quantum Duet/POP909 sources, model data and recorded
  fixtures. Development tests, historical reports and duplicate import manifests
  are omitted only from the submission copy. Its README is replaced with run instructions.
- 709 referenced samples become mono 22.05 kHz / 16-bit copies, then 40 kbit/s nominal
  Ogg Vorbis banks. Articulation groups, velocity layers and round robins remain.
  SFZ offsets/inclusive endpoints restrict each sample; embedded loops are rescaled.
  Samples decode directly through the pinned native sampler without runtime extraction.
- The Windows DLL is compressed for shipping; compressed/restored digests are checked
  before loading a generated native dependency in the OS temporary cache. The full
  bank frames are preloaded to avoid streaming underruns at large sample offsets.
- Relocatable installation receipts resolve asset paths relative to `assets/acoustic`.
  Upstream sample license and sfizz/dependency notices are included.

## Final deliverable and actual checks

Final folder: workspace-root `submission-oxfordq-20261011`.
Final compact listening collection: `output-submission-piano-studies-20261011/index.html`.
Full-quality piano collection: `output-piano-studies-20261011/index.html`.

Measured recursively on the final runnable folder:

| Measure | Actual | Limit |
|---|---:|---:|
| Shipped files, including manifest | 100 | 100 |
| Total bytes | 17,673,023 | 200,000,000 |
| Largest file bytes | 1,814,679 | 2,000,000 |
| Directly read audio banks | 10 | — |
| Source sample regions | 709 | — |
| Largest decoded bank frames | 9,368,886 | 16,777,216 preload frames |

Python compilation passed. Every shipped file digest other than the manifest's
own self-hash was checked. ffprobe metadata verified mono 22.05 kHz banks; all 709
sample offsets/endpoints and loop bounds fit their decoded bank frames. All 78
copied runtime/data files except the intentionally replaced root README match the
development checkout byte for byte.

The final folder itself ran `python -B -m orchestrator.composition --style all
--seed 20261012 --require-audio`, writing output outside the submission. All four
styles completed with rendered audio and `gemini: not_requested`. For every style,
its source bank and logical score equal the corresponding full-quality run.
The per-piece reports have actual `created_utc` timestamps 21:47:55.864962,
21:48:40.633672, 21:49:31.110039 and 21:50:12.991261 UTC on 2026-10-11.
The render process subsequently returned exit code 0. Final measurements:

| Piece | Piano notes | Compact piano RMS | Compact piano peak |
|---|---:|---:|---:|
| piece1 / Bach | 114 | 0.05314 | 0.78796 |
| piece2 / Mozart | 222 | 0.06378 | 0.65295 |
| piece3 / Debussy | 80 | 0.05444 | 0.73318 |
| piece4 / Rachmaninoff | 237 | 0.06353 | 0.68570 |

Every piano stem is non-silent; every piano performance contains pedal controls.
These are signal/structural checks, not human listening judgments. No automated
test suite was added or run. No paid API, training, physical QPU or platform upload
occurred. No GitHub push is part of this change.

## Scope and limitations

The package is a **local Windows x64 application**, not a Qollab/Pyodide browser
deployment. Python and pip dependencies are installed separately outside the
shipped folder. Instructions install dependencies without creating package build
files in the submitted tree, use `-B`, and write generated audio outside it.

Mono resampling and lossy Vorbis reduce fidelity; the full-quality project remains
available. Connected sustain still approximates legato. Other instruments' APIs
remain but their acoustic patches are not shipped. Text preference parsing and an
exact duration-in-seconds interface are not implemented by this packaging work.

The obsolete full-tree transport build was rejected by automatic approval review
after the user's clarification. It was replaced by the directly runnable folder;
the temporary unpacker was removed. A lower-bitrate prototype was retained under
the existing ignored `build` directory. The main checkout has no modified tracked
source files; only the authorized final submission folder is new at its root.
