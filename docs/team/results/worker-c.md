# Worker C — browser experience verification

Date: 2026-10-10. All times below are UTC (London BST = UTC + 1 hour).
Started on the existing clean `codex/duet-interface-20261010` checkout, with HEAD
exactly `3eb26f205f9b68c9e7f01cff9ca26f74315882a1`. No extra worktree or clone.
Fetched main at `bff4c0e0ff1d67f73503724b5d3e303eaf696103` (merged PR #1).
Per the human override, the draft PR targets main. The final commit SHA and PR URL
are supplied in the completion message and GitHub PR head, avoiding a self-hash
inside the committed report. No merge, publication or hackathon submission.

## Changed canonical paths

- `components/quantum_duet/web/index.html`
- `components/quantum_duet/web/main.js`
- `components/quantum_duet/web/main.css`
- `components/quantum_duet/web/ui.mjs`
- `components/quantum_duet/web/run-contract.mjs`
- `components/quantum_duet/dev/server.py`
- `components/quantum_duet/dev/main.mjs`
- `components/quantum_duet/tests/ui_c/contract_checks.mjs`
- `docs/team/results/worker-c.md`

All writes are within C's exact allowlist. Existing tests, Python inference,
orchestrator/adapter, checkpoints, scientific evidence, shared fixture/contract,
dependencies/locks, build tool and deployment notes remain unchanged. Installation,
test outputs, screenshot and generated upload ZIP are ignored local artifacts.

## Behavior and contract mapping

Local development serves the unchanged shared fixture at the fixed `/api/fixture`
endpoint. Loading it displays RECORDED Qollab built-in simulator, its stable run ID,
4096 historical CHSH shots, original one backend call and zero replay calls. It
does not invoke inference. The original asynchronous Qollab Python bridge remains
active until pagehide/Stop, and permits at most one explicit live request per page.
Failures have visible errors; there is no automatic retry or simulator substitution.

The UI helper validates qm.run-result.v1, run/round/event identity, both 32-event
comparators including rests, integer named-setting histograms matched by name,
CHSH shot denominator/estimate, conditional interval, checkpoint/source hashes,
classical precommitted strategy, MIDI pitches/velocities and four-bar beat timing.
Unknown schemas and failed envelopes disable playback and clear stale evidence.
Supplied metadata is displayed as supplied; validation is not hardware certification.

Raw replay uses the frozen events directly and bypasses central arrangement.
Play/repeat/Stop, mutes, comparison and tempo reuse measurements; both methods use
the same flute/cello WebAudio waves, levels, velocity scaling and controls. Loading,
switching and tempo changes stop old scheduling; generation guards cancel stale
AudioContext resumes. A pending load cannot race an inference request.

Arranged null stays unavailable. Optional supplied `arranged.events.quantum` and
`arranged.events.classical` are a UI-only playback projection, not a replacement
shared schema or a claim that B's production adapter is integrated. Both comparators
must be supplied, with requested/actual backend, errors/fallback report,
`raw_source_sha256`, `transformation_ids` and each event's original
`source_event_ids`, run/round/voice lineage. Unsupported/erroneous arranged output
stays unavailable while valid raw playback remains usable. Metadata is inspectable
even without a playable projection. A test-only transposition proves switching
does not mutate raw events; it is not scientific evidence or a production arranger.

JSON export retains the exact original envelope text and unchanged parsed result
inside `raw_envelope_text`/`run_result`, with separate export_view controls. Reimport
supports this wrapper and rejects contradictions. MIDI type 1 uses 480 ppq, actual
velocities, 192 ticks for 0.4 beats, flute/cello programs, run/round/raw-source and
active event/source metadata with pitch, velocity and start/end ticks. Bob's legacy
MIDI bass program was corrected to cello (GM zero-based 41); Alice stays flute
(73). Rests remain in JSON; MIDI's conductor retains all
round identities. MIDI exports reject tempo values outside the 24-bit MIDI tempo
representation and sub-tick durations explicitly. Mutes affect listening only.
Visible JSON/base64 and console envelopes remain; a download attempt is not proof
of Qollab download support.

## Executed verification

| Check | Timestamp and actual result | Scope |
|---|---|---|
| `python -m venv .venv-worker`; dependency install | Initial ensurepip/cache attempt failed with sandbox access denied. Workspace-local cache then failed network access. Authorized escalated `uv --cache-dir .venv-worker/uv-cache pip install --python .venv-worker/Scripts/python.exe '.[dev]' './components/quantum_duet[dev]'` succeeded before 15:49 | Local test environment only; root configs unchanged |
| `.venv-worker/Scripts/python.exe -m pytest -q tests components/quantum_duet/tests --basetemp .test-worker-c-final` | 15:57:04–15:57:22; **32 passed in 15.53s** | Existing root and component tests, including offline/intercepted provider checks |
| `node components/quantum_duet/tests/ui_checks.mjs` | Final UI review rerun 15:59:29.025; **passed** | Existing mocked AudioContext race/repeat/Stop/mute and MIDI checks |
| `node components/quantum_duet/tests/ui_c/contract_checks.mjs` | Final UI review rerun 15:59:29.281; **passed** | New Node contract, MIDI parser (including flute/cello programs), mocked DOM/audio, raw/arranged lineage and single-request lifecycle; not a browser claim |
| `.venv-worker/Scripts/python.exe -m orchestrator --manifest examples/note_events.json --backend rules --bars 4 --no-audio --out output-worker-c-events` | Executed 15:49–15:50; **passed**, provider disabled, audio not_requested | Rules-only existing event-manifest CLI |
| `.venv-worker/Scripts/python.exe -m orchestrator --generation-manifest examples/generation.json --backend rules --bars 4 --no-audio --out output-worker-c-generators` | Executed 15:49–15:50; **passed**, provider disabled, audio not_requested | Rules-only existing synthetic-generator CLI |
| `.venv-worker/Scripts/python.exe components/quantum_duet/tools/build_qollab.py --out components/quantum_duet/build/worker-c-reviewed` | 15:59:29–15:59:30; **passed**; ZIP SHA-256 `49397b7f063d87011c18b876888f33b346487a2622d2b497d457e9985a34c03f` | Fresh ignored upload build, not uploaded/published |
| Original fixture identity comparison | 15:54–15:55; bytes SHA-256 `3f1901a7b132111752c35b4b62fba5cf1bee57a2811f28930199a420088d3e1a`; canonical SHA-256 matched `9dc550b1227b7854cbf91ee2c1b9ca8b7cb3b437fca3ffc7252e681edc438624` | Original raw asset preserved |
| `git diff --check` / allowlist audit | 15:57:24 and final precommit review; **passed** | Only the nine canonical paths above |

Real Chrome checks at `http://127.0.0.1:8767`, observed 15:52–15:57: the fixture
loaded with recorded/zero-call labels and disabled arranged option; repeat Play
reported 30 scheduled notes; comparator/Stop reported zero; mute state persisted;
90 BPM and keyboard Enter on Play/Stop worked. JSON exposed the actual paired run
and 4096 historical shots; MIDI base64 began `TVRoZAAAAAYA`. Export reimport retained
original text and enabled raw playback. Unknown schema failed visibly and disabled
Play. The local legacy live route completed one five-circuit BasicSimulator job,
16 shots per circuit / **64 CHSH shots**, job
`1589676e-7cab-453e-8c5e-654807c50e2d`; Generate stayed disabled afterwards. No browser
console errors were observed. Browser checks verify UI/WebAudio scheduling states,
not subjective audible quality or physical speaker output.

At a 375x812 viewport, document scrollWidth/clientWidth were both 360 (15px scrollbar),
with no horizontal overflow. Controls and recorded provenance wrapped visibly.
Ignored screenshot: `.test-worker-c/browser-375.jpg`. Viewport override was reset.
An attempted full-page screenshot timed out; the normal viewport capture succeeded.
Initial browser/server checks timed out/refused under sandbox/process constraints;
the escalated live terminal server resolved this. Native Qollab download/toolbars
were not checked. Local download attempts do not remove the visible export route.

## Unresolved problems and coordinator dependencies

1. **Qollab fixture packaging:** `build_qollab.py` copies canonical web/Python/data,
   but not the shared docs fixture. Coordinator must explicitly bundle the unchanged
   fixture and provide a supported asset/bridge loader for mountDuet's loadFixture
   option. Current Qollab entry reports this missing integration and supports pasted
   envelope JSON, with no unsupported private-file fetch. C did not edit packaging.
2. **B production arrangement hookup:** coordinator must review B's output and map
   its score/parts into paired UI event playback with source lineage and matching
   comparator conditions. No registry/backend/arranger calls were introduced here.
3. **Live envelope integration:** A's existing generate_take API remains compatible;
   its legacy live results truthfully lack shared run/round envelope IDs. Coordinator
   must connect B's pure conversion at the single-completed-take boundary. Current
   live JSON retains legacy provenance without inventing stable run IDs.
4. **Real platform checks:** new Qollab/Pyodide playback, fixture loading, toolbar
   downloads and IonQ checks remain unexecuted by C. Historical fixture evidence is
   labelled recorded. No paid APIs, physical QPU, credentials, native FluidSynth,
   retraining, held-out motifs or scientific-quality/speedup claims were used.

All implemented local and mocked checks pass. The dependencies above are explicit
integration boundaries, not permission to edit another owner's files.
