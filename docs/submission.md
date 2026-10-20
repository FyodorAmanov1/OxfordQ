# Compact runnable submission

`scripts/prepare_submission.py` builds a separate, smaller **local Windows x64**
submission folder. It retains the original Python module paths, Quantum Duet and
POP909 component directories, required data, model weights and recorded fixtures.
Development tests, historical reports and duplicate import manifests are omitted
from this copy. The full development repository and original sample assets stay intact.

```powershell
python scripts/prepare_submission.py --out submission-oxfordq-20261011
```

The builder counts every shipped file recursively. It rejects more than **100 files**,
any file larger than **2,000,000 bytes**, or a total above **200,000,000 bytes**. These
are limits on the runnable folder itself, not a transport archive. The manifest
records file digests, source identity, bank mappings and the selected runtime files.

## Audio banks

All 709 unique samples referenced by the default six instrument patches are retained,
including their velocity layers, round robins and articulation groups. Compact copies
are resampled to mono 22.05 kHz / 16-bit PCM, then encoded into Ogg Vorbis banks at
nominal 40 kbit/s. The pinned native sampler supports direct Vorbis decoding. Every
SFZ region receives an exact sample offset and inclusive endpoint; guard gaps separate
samples. Embedded loop positions are rescaled and explicitly recorded per region.
No sample library is expanded during playback. Original SFZ names remain unchanged.

This is a fidelity tradeoff: bandwidth and recorded stereo width are reduced and
Vorbis is lossy. Native note envelopes, available velocity layers, articulation,
piano pedal, phrase dynamics and rubato remain. Full-quality recordings continue to
serve the original local project. Human listening is needed to judge compact quality.

The included Windows sfizz DLL is compressed to meet the per-file upload cap. Its
compressed and restored SHA-256 digests are checked before loading a generated copy
in the operating-system temporary dependency cache. The shipped project and audio
banks are not expanded or reorganized. Upstream and dependency licenses are included.

## Run without modifying the submitted folder

Use Python 3.11+ on Windows x64. Install dependencies and write outputs outside the
submitted directory:

```powershell
python -m venv ../OxfordQ-submission-env
../OxfordQ-submission-env/Scripts/python -B -c "import subprocess, sys, tomllib; p = tomllib.load(open('pyproject.toml', 'rb'))['project']; subprocess.check_call([sys.executable, '-m', 'pip', 'install', *p['dependencies'], *p['optional-dependencies']['quantum']])"
../OxfordQ-submission-env/Scripts/python -B -m orchestrator.composition --style all --require-audio --out ../output-submission-pieces
```

Python, installed pip packages and generated compositions are not shipped in the
folder. `-B` avoids creating bytecode files there. There are no sample downloads after
building. The acoustic receipt uses portable paths relative to `assets/acoustic`.
The default six instruments are flute, clarinet, violin, cello, double bass and piano.
Other instrument APIs remain, but their acoustic samples are absent in this compact
edition and selecting them produces an explicit missing-patch error.

This is not a Qollab/Pyodide browser deployment: its Windows native renderer requires
a local compatible runtime. Existing component source paths are preserved, while
separate browser deployment builders/platform verification remain outside this copy.
Quantum inference uses the current local Statevector models, with replaceable
instrument generators. No paid API is required. Text prompts and an exact duration
in seconds remain future work; this packaging change does not implement them.
