# Paired Quantum Duet integration

From the repository root after installing both projects in the same environment:

```powershell
.venv/Scripts/python.exe -m quantum_duet.orchestration_adapter --result docs/fixtures/run-result.v1.json --out output-b-duet --arrange
```

The output directory must be new. `raw-result.json` retains the complete frozen
contract (all rests and rounds); `manifest.json` contains Alice flute/melody and
Bob cello/bass with string source metadata. `raw.mid` uses the original mapping
without central arrangement. The optional `arranged-result.json` and `arranged.mid`
are explicitly labelled rules outputs. No native audio or external API is used.
The creative rules demo explicitly selects C major and C/F/G/C, recorded in its
report; Python callers may pass `key` and `chords` to `arrange_result`. This avoids
the existing orchestrator's flat-symbol inference incompatibility without changing
its source or adding a retry/fallback.
An arrangement failure produces structured errors and exit status 1 while retaining
the usable raw exports. Omit `--arrange` for raw playback/export alone.
Use `--policy classical` to export the same run's precommitted classical comparator.

In Python, the caller assigns a run UUID **before** executing `generate_take` once.
Pass that returned JSON directly to the pure converter:

```python
from uuid import uuid4
from quantum_duet.integration import generate_take
from quantum_duet.orchestration_adapter import from_take, to_manifest, arrange_result

run_id = str(uuid4())
# backend is explicitly selected by the caller; no paid provider or hardware.
take_json = generate_take(backend, asset_dir=asset_dir)
completed = from_take(take_json, run_id=run_id, data_status="live",
                      source_asset="raw-take.json")
manifest = to_manifest(completed)  # both voices; zero further submissions
# Save completed.raw_bytes as raw-take.json and completed.to_dict() as raw-result.json.
arranged = arrange_result(completed)  # optional rules, render_audio=False
```

For historical take files use `data_status="recorded"`; for mocked evidence use
`"mock"`. Four-recorded melody mode additionally requires `recorded_melody_asset`.
`freeze_result(contract_dict, raw_bytes=optional_original_take_bytes)` consumes the
shared fixture or another contract snapshot without executing a backend. It checks
the raw canonical digest if source bytes are provided. Byte digests in historical
fixtures may refer to original LF bytes while checkout files contain CRLF; the
canonical JSON digest disambiguates this without editing historical evidence.

`CompletedResult` retains immutable JSON bytes and exposes only fresh dictionaries.
Every `to_manifest` call returns new models. Source metadata carries run/checkpoint
and raw hashes, sidecar reference/hash, `round_index_map` (active note index to
round ID), and `source_event_map` (`alice:nN`/`bob:nN` to event ID). This agrees with
`midi_io.import_parts`; 0.4 quarter-note beats equals 192 ticks at 480 PPQ. Rests
stay in the sidecar, including a fully silent raw take. A silent lead is an explicit
arrangement failure. Arrangement output includes per-note transformation IDs and
original run/round/event/source-ID lineage, including muted notes.

Use this paired-manifest path directly. Independent registered generators are
unnecessary and would risk resampling the voices. Do not allow registry/job source
metadata to overwrite the provenance; `to_manifest(source=...)` rejects conflicts.
The coordinator owns any root CLI entrypoint, packaging inclusion and UI hookup.

CHSH statistics retain the four full histograms and their original denominator;
replays and QCBM shots are not new CHSH trials. Arranged music is not unchanged
musical coordination evidence, musical-quality advantage or quantum speedup.
