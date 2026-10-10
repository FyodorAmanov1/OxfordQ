# Shared run/result contract — qm.run-result.v1

Coordinator owns this specification and docs/team/fixtures/run-result.v1.json.
The fixture is a design/example projection of the retained historical run, not an
implemented production adapter. Do not change its schema in worker branches.
Reuse orchestrator.models.InputNote, PartSpec, Manifest, ArrangementResult and
generation.GeneratedSequence. Their source dictionaries accept string values only;
store run_id, model/checkpoint IDs, round-index map and raw-sidecar hash/reference as
strings. Rich paired evidence belongs in this envelope, not invented PartSpec fields.

| Field | Required meaning |
|---|---|
| contract_version | Literal qm.run-result.v1; reject unknown versions |
| run_id | Nonempty stable ID assigned once to a completed execution; historical fixture uses actual job UUID prefixed qm3b-qollab-; live caller assigns UUID before execution; never infer identity from seed alone |
| mode/status | raw or arranged; completed or failed. Failed result has errors and no invented counts/events |
| models | Bell and QCBM checkpoint SHA-256 IDs, exact Bell angles, 84 parameters / 12 qubits; identify recorded melody asset for four-recorded mode |
| execution | Actual backend name/class/version, job_id if accepted, five-live/four-recorded choice, data_status live/recorded/mock, simulator declaration and its verification status, historical calls/shots and backend_run_calls_this_replay; record SDK/platform versions if available, unknown explicitly otherwise |
| raw_source | Immutable raw take/sidecar asset plus bytes SHA-256 and canonical JSON SHA-256 (sorted keys, UTF-8, compact separators); preserve original contents. Git text line endings can change bytes hash; canonical digest disambiguates |
| rounds | Exactly 16 indexed rounds including rests/losses; unique run_id/r00..r15 IDs. Own cues x/y, token, paired a/b, ba string, wins, classical precommitted shared strategy and measurement provenance |
| events | quantum and classical arrays retain all 32 events, 16 per voice; stable event_id, run_id, round_id, voice, base_token/local_output, rest, nullable pitch_midi, velocity, onset_beats/duration_beats |
| tempo/metre/ppq | Finite positive tempo <=400 (initial 120 BPM), quarter-note beats, 4/4, initial ppq=480. MIDI pitch integer 0..127, sounding concert pitch; velocity integer 1..127, initial 80; onset >=0 and duration >0. No milliseconds mistaken for beats |
| statistics | Four named-setting integer histograms and allocated shots, full-count expected_success and conditional interval/assumptions. QCBM shots and 16-round excerpt excluded from CHSH denominator. Counts order reconstructed, never labelled chronological memory |
| errors/fallback | Structured stage/code/redacted message errors. fallback explicitly requested/used/reason; never silently switch backend or recorded/live mode. Null accepted job_id on rejection; no fabricated successful run |
| arranged | Null for raw; otherwise arranger requested/actual backend (rules/Gemini), transformation IDs, immutable source hash, output parts and original source-ID/round-ID lineage, errors/fallback report. Source remains unchanged |

The fixture labels historical execution recorded and replay calls zero, while retaining
one original backend call and 4096 CHSH shots. Do not aggregate replays as new trials.
All original execution experiment histograms are retained inside execution.

## Smallest integration boundary

B creates a pure conversion from one already completed raw take to this envelope,
then a paired manifest from the envelope. Choose the paired-run path: the caller
executes Quantum Duet once, freezes the result, and calls to_manifest(result).
Do not register independent Alice/Bob generators that each call generate_take().
If a registry adapter is necessary, inject one immutable completed result into both
adapter instances; two generate(request) calls must cause zero backend submissions.
No hidden module globals or caches; preserve source and ownership explicitly.

Use Alice as flute/melody and Bob as cello/bass, IDs alice and bob; PartSpec permits
these IDs. Omit rest events from InputNote lists but keep every rest in the envelope.
InputNote = pitch_midi, onset_beats, duration_beats, velocity, unchanged. Both parts
share tempo and run_id; map each active note index to round_id in a sidecar before
midi_io.import_parts assigns alice:nN / bob:nN source IDs. Keep the association after
conversion to ticks (round(beat*ppq)); 0.4 beats is 192 ticks at ppq 480.

Raw playback/export comes directly from frozen local mapping and bypasses
pipeline.orchestrate and baseline.arrange_baseline. They centrally transpose, repair,
mute and reconcile notes even in rule mode. Optional creative arrangement may call
orchestrate with backend=rules and render_audio=False. It must copy input, preserve
raw envelope byte/canonical identity, and return arranged output with transformation
lineage. Never call arranged music unchanged CHSH evidence. Handle a fully silent
lead as an explicit arrangement error while raw replay remains usable.

C consumes this same fixture/envelope, preserving the existing UI where possible.
It can implement fixture playback while B works; real adapter hookup is coordinated
after B's boundary lands. A preserves generate_take's existing bridge API. Contract,
dependency and generated-packaging changes are coordinator work, not shared edits.

Exact coordination probability is about 85.3553%; local classical bound 75%, central
reference 100%. Central simulation is classically simulatable. CHSH success does not
establish musical quality, hardware certification or speedup. Validation-selected
QCBM still loses the classical melody likelihood comparison. No held-out evaluation.
