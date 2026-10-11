"""Pure paired-take conversion; raw replay never invokes a central arranger.

Execute generate_take once in the caller, assign run_id before execution, then
freeze with from_take. This module has no backend, registry, cache or credentials.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path

from orchestrator.models import InputNote, Manifest, PartSpec
from .music import musical_event

VERSION = "qm.run-result.v1"
VOICES = {"alice": ("flute", "melody"), "bob": ("cello", "bass")}
POLICIES = ("quantum", "classical")


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def validate_result(result: dict) -> None:
    """Reject inconsistent identity, fixed mapping, allocation and evidence labels."""
    canonical_json(result)
    _require(result["contract_version"] == VERSION, "Unknown contract version")
    run_id = result["run_id"]
    _require(isinstance(run_id, str) and bool(run_id.strip()), "Missing stable run_id")
    _require(result["mode"] in ("raw", "arranged"), "Unknown playback mode")
    _require(result["status"] in ("completed", "failed"), "Unknown status")
    _require(type(result["tempo_bpm"]) in (int, float) and
             0 < result["tempo_bpm"] <= 400, "Invalid quarter-beat tempo")
    _require(result["beats_per_bar"] == 4 and _integer(result["ppq"], 24, 9600),
             "Require 4/4 and valid PPQ")
    fallback = result["fallback"]
    _require(type(fallback["requested"]) is bool and type(fallback["used"]) is bool,
             "Invalid fallback flags")
    _require(not fallback["used"] or (fallback["requested"] and fallback["reason"]),
             "Fallback must be explicitly requested with a reason")
    for error in result["errors"]:
        _require(all(isinstance(error.get(k), str) and error[k] for k in
                     ("stage", "code", "message")), "Structured errors required")
    if result["status"] == "failed":
        _require(bool(result["errors"]), "Failure requires explicit errors")
        if result["mode"] == "raw":
            _require(not result["rounds"] and not any(result["events"].values()) and
                     not result["statistics"] and not result["execution"].get("experiments"),
                     "Failed execution cannot supply successful counts/events")
            return
    models = result["models"]
    for field in ("bell_checkpoint_sha256", "qcbm_checkpoint_sha256"):
        _require(isinstance(models[field], str) and len(models[field]) == 64 and
                 all(c in "0123456789abcdef" for c in models[field]), "Invalid checkpoint digest")
    _require(len(models["bell_angles_radians"]) == 4 and
             all(type(a) in (int, float) and math.isfinite(a) for a in models["bell_angles_radians"])
             and models["qcbm_parameters"] == 84 and models["qcbm_qubits"] == 12,
             "Invalid frozen-model dimensions")
    source = result["raw_source"]
    _require(isinstance(source["asset"], str) and bool(source["asset"]), "Missing raw source reference")
    for field in ("sha256", "canonical_json_sha256"):
        _require(isinstance(source[field], str) and len(source[field]) == 64 and
                 all(c in "0123456789abcdef" for c in source[field]), "Invalid raw source digest")
    execution = result["execution"]
    _require(execution["data_status"] in ("live", "recorded", "mock"), "Explicit data_status required")
    _require(execution["mode"] in ("five-live", "four-recorded"), "Explicit melody mode required")
    _require(type(execution["backend_run_calls"]) is int and execution["backend_run_calls"] == 1 and
             execution["circuit_count"] == (5 if execution["mode"] == "five-live" else 4),
             "Require one original paired execution")
    _require(type(execution["backend_run_calls_this_replay"]) is int and
             execution["backend_run_calls_this_replay"] == 0, "Conversion submits zero jobs")
    _require(type(execution["execution_mode_verified"]) is bool and
             execution["hardware_executed"] is False, "Invalid simulator evidence")
    for field in ("backend_name", "backend_class", "backend_version", "execution_mode",
                  "execution_mode_source"):
        _require(isinstance(execution[field], str) and bool(execution[field]), "Missing backend provenance")
    _require(execution["job_id"] is None or isinstance(execution["job_id"], str), "Invalid job identity")
    if execution["mode"] == "four-recorded":
        _require(bool(models.get("recorded_melody_asset")), "Identify recorded melody asset")
    experiments = execution["experiments"]
    _require(len(experiments) == execution["circuit_count"], "Incomplete experiments")
    _require(len({e["name"] for e in experiments}) == len(experiments), "Duplicate experiment names")
    for experiment in experiments:
        _require(_integer(experiment["shots"], 1, 4096) and
                 all(type(n) is int and n >= 0 for n in experiment["counts"].values()) and
                 sum(experiment["counts"].values()) == experiment["shots"], "Invalid experiment shots/counts")
    if execution["mode"] == "five-live":
        melody_rows = [e for e in experiments if e["name"] == "duet_live_melody"]
        _require(len(melody_rows) == 1 and melody_rows[0]["role"] == "live_base_melody" and
                 all(len(k) == 12 and set(k) <= {"0", "1"} for k in melody_rows[0]["counts"]),
                 "Invalid QCBM experiment")
    settings = [(0, 0), (0, 1), (1, 0), (1, 1)]
    counts = []
    for setting in settings:
        rows = [e for e in experiments if e.get("name") == f"duet_xy_{setting[0]}{setting[1]}"]
        _require(len(rows) == 1, "Missing or duplicate named setting")
        row = rows[0]
        _require(row["role"] == "coordination" and tuple(row["setting"]) == setting,
                 "Contradictory setting label")
        count = row["counts"]
        _require(bool(count) and not set(count) - {"00", "01", "10", "11"} and
                 all(type(n) is int and n >= 0 for n in count.values()), "Invalid integer counts")
        _require(sum(count.values()) == row["shots"] == execution["shots_per_circuit"] > 0,
                 "Contradictory shot allocation")
        counts.append(count)
    # Recompute only for validation; never replace supplied scientific evidence.
    from .duet_referee import sampled_metrics
    measured = sampled_metrics(counts)
    stats = result["statistics"]
    for key, value in measured.items():
        if key == "independence_assumption":
            _require(bool(stats[key]), "Missing interval assumptions")
        else:
            _require(stats[key] == value, f"Statistics disagree with counts: {key}")
    _require(stats["allocation"] == [dict(x=x, y=y, shots=sum(c.values()))
                                     for (x, y), c in zip(settings, counts)] and
             stats["hardware_certified"] is False, "Invalid statistical provenance")
    rounds = result["rounds"]
    _require(len(rounds) == 16, "Retain all sixteen rounds")
    for i, row in enumerate(rounds):
        _require(row["index"] == i and row["round_id"] == f"{run_id}/r{i:02}", "Broken round identity")
        _require(_integer(row["base_token"], 0, 7), "Invalid base token")
        x, y = row["cues"]["alice"], row["cues"]["bob"]
        _require(_integer(x, 0, 1) and _integer(y, 0, 1), "Invalid own cues")
        _require(bool(row["measurement_provenance"]), "Missing reconstructed measurement provenance")
        for policy in POLICIES:
            output = row[policy]
            a, b = output["alice"], output["bob"]
            _require(_integer(a, 0, 1) and _integer(b, 0, 1), "Invalid paired outputs")
            _require(type(output["win"]) is bool and output["win"] == ((a ^ b) == (x & y)),
                     "Contradictory win flag")
            if policy == "quantum":
                _require(output["displayed_ba"] == f"{b}{a}", "Contradictory displayed ba")
            else:
                strategy = output["shared_strategy"]
                _require(len(strategy) == 4 and all(_integer(v, 0, 1) for v in strategy) and
                         (a, b) == (strategy[x], strategy[2+y]), "Contradictory precommitted strategy")
    for policy in POLICIES:
        events = result["events"][policy]
        _require(len(events) == 32, "Retain all 32 events including rests")
        seen = set()
        for event in events:
            i, voice = event["round"], event["voice"]
            _require(_integer(i, 0, 15) and voice in VOICES and (i, voice) not in seen,
                     "Invalid/duplicate voice-round event")
            seen.add((i, voice))
            row = rounds[i]
            expected = musical_event(row["base_token"], row[policy][voice], voice, i)
            _require(all(type(event[k]) is type(v) and event[k] == v for k, v in expected.items()
                         if k not in ("onset_beats", "duration_beats")), "Event differs from fixed local mapping")
            _require(event["onset_beats"] == expected["onset_beats"] and
                     event["duration_beats"] == expected["duration_beats"] and
                     type(event["onset_beats"]) in (int, float) and
                     type(event["duration_beats"]) in (int, float), "Event timing differs from mapping")
            _require(event["run_id"] == run_id and event["round_id"] == row["round_id"] and
                     event["event_id"] == f"{run_id}/{policy}/{voice}/r{i:02}", "Broken event identity")
            _require(_integer(event["velocity"], 1, 127), "Invalid velocity")
    _require((result["mode"] == "raw" and result["arranged"] is None) or
             (result["mode"] == "arranged" and isinstance(result["arranged"], dict)),
             "Contradictory arrangement label")
    if result["mode"] == "arranged":
        arranged = result["arranged"]
        _require(arranged["backend_requested"] in ("rules", "gemini") and
                 arranged["immutable_source_sha256"] == source["sha256"] and
                 arranged["immutable_source_canonical_json_sha256"] == source["canonical_json_sha256"],
                 "Arrangement changed raw identity")
        if result["status"] == "completed":
            _require(arranged["backend_actual"] == arranged["backend_requested"], "Unknown actual arrangement backend")
            event_lookup = {e["event_id"]: e for e in result["events"][arranged["policy"]] if not e["rest"]}
            lines = {line["output_id"]: line for line in arranged["lineage"]}
            _require(len(lines) == len(event_lookup), "Incomplete output lineage")
            for part in arranged["output_parts"]:
                for note in part["notes"]:
                    line = lines[note["id"]]
                    event = event_lookup[line["event_id"]]
                    _require(line["run_id"] == run_id and line["round_id"] == event["round_id"] and
                             line["source_id"] == note["source_id"] and part["id"] == event["voice"],
                             "Broken arranged source lineage")


@dataclass(frozen=True)
class CompletedResult:
    """Immutable JSON snapshot; every exposed dict is a fresh copy.

    raw_bytes retains the exact take bytes when supplied, including line endings.
    Contract fixtures can be frozen without resolving their external asset paths.
    """
    _json: bytes
    raw_bytes: bytes | None = None

    def __post_init__(self):
        _require(type(self._json) is bytes and
                 (self.raw_bytes is None or type(self.raw_bytes) is bytes), "Immutable bytes required")
        value = self.to_dict()
        validate_result(value)
        if self.raw_bytes is not None:
            raw = json.loads(self.raw_bytes)
            _require(sha256(canonical_json(raw)).hexdigest() ==
                     value["raw_source"]["canonical_json_sha256"], "Raw canonical digest mismatch")
            if raw.get("schema_version") == 1:
                _require(all(value["models"][k] == v for k, v in raw["models"].items()),
                         "Checkpoint metadata disagrees with raw source")
                for policy in POLICIES:
                    for i, row in enumerate(value["rounds"]):
                        original = raw["rounds"][policy][i]
                        _require(row["base_token"] == original["base_token"] and
                                 row["cues"] == dict(alice=original["x"], bob=original["y"]) and
                                 (row[policy]["alice"], row[policy]["bob"]) == (original["a"], original["b"]),
                                 "Rounds disagree with raw source")
                _require(value["statistics"] == raw["statistics"], "Statistics changed from raw source")
                for policy in POLICIES:
                    original_events = {(e["voice"], e["round"]): e for e in raw["events"][policy]}
                    for event in value["events"][policy]:
                        original_event = original_events[(event["voice"], event["round"])]
                        _require(event["velocity"] == original_event.get("velocity", 80),
                                 "Velocity changed from raw source")
                for key, item in raw["execution"].items():
                    _require(value["execution"][key] == item, "Execution metadata changed from raw source")

    def to_dict(self) -> dict:
        return json.loads(self._json)

    @property
    def canonical_sha256(self) -> str:
        return sha256(canonical_json(self.to_dict())).hexdigest()


def freeze_result(result: dict, *, raw_bytes: bytes | None = None) -> CompletedResult:
    return CompletedResult(canonical_json(result), raw_bytes)


def from_take(take: dict | str | bytes, *, run_id: str, data_status: str,
              source_asset: str, recorded_melody_asset: str | None = None) -> CompletedResult:
    """Convert an already completed unchanged generate_take bridge result.

    run_id must be assigned by the caller before execution; never derived from a
    presentation seed. data_status is mandatory: loading a historical take is recorded.
    Dict input is frozen as canonical bytes; text/bytes input retains original bytes.
    """
    raw_bytes = canonical_json(take) if isinstance(take, dict) else (
        take.encode("utf-8") if isinstance(take, str) else take)
    raw = json.loads(raw_bytes)
    _require(raw["schema_version"] == 1, "Unknown raw take version")
    _require(raw.get("status", "completed") == "completed", "Only completed raw takes can be converted")
    if "run_id" in raw:
        _require(raw["run_id"] == run_id, "Contradictory take run_id")
    execution = deepcopy(raw["execution"])
    if "data_status" in execution:
        _require(execution["data_status"] == data_status, "Contradictory data_status")
    execution.update(data_status=data_status, replayed_now=data_status == "recorded",
                     backend_run_calls_this_replay=0)
    execution.setdefault("sdk_versions", {"qiskit": "unknown", "platform": "unknown"})
    if data_status == "recorded":
        execution["recorded_at_utc"] = raw["created_utc"]
    models = deepcopy(raw["models"])
    if execution["mode"] == "four-recorded":
        _require(recorded_melody_asset, "Identify recorded melody asset")
        models["recorded_melody_asset"] = recorded_melody_asset
    _require(raw["base_melody"]["generated_now"] == (execution["mode"] == "five-live"),
             "Recorded/current melody mismatch")
    rounds = []
    _require(all(len(raw["rounds"][p]) == 16 for p in POLICIES) and
             len(raw["base_melody"]["tokens"]) == len(raw["cue_sequence"]) == 16, "Invalid round count")
    for i in range(16):
        q, c = (raw["rounds"][policy][i] for policy in POLICIES)
        _require(all(q[k] == c[k] for k in ("round", "x", "y", "base_token")), "Unpaired raw rounds")
        _require(q["round"] == i and raw["cue_sequence"][i] == [q["x"], q["y"]] and
                 raw["base_melody"]["tokens"][i] == q["base_token"], "Contradictory raw cue/token")
        _require(q["required_parity"] == c["required_parity"] == (q["x"] & q["y"]),
                 "Contradictory required parity")
        rounds.append(dict(round_id=f"{run_id}/r{i:02}", index=i,
            cues={"alice": q["x"], "bob": q["y"]}, base_token=q["base_token"],
            quantum=dict(alice=q["a"], bob=q["b"], displayed_ba=q["displayed_ba"], win=q["win"]),
            classical=dict(alice=c["a"], bob=c["b"], win=c["win"], shared_strategy=c["shared_strategy"]),
            measurement_provenance=raw["playback_ordering"]))
    events = deepcopy(raw["events"])
    for policy in POLICIES:
        for event in events[policy]:
            i, voice = event["round"], event["voice"]
            for field, expected in dict(run_id=run_id, round_id=f"{run_id}/r{i:02}",
                                       event_id=f"{run_id}/{policy}/{voice}/r{i:02}").items():
                _require(field not in event or event[field] == expected, f"Contradictory event {field}")
            event.update(event_id=f"{run_id}/{policy}/{voice}/r{i:02}", run_id=run_id,
                         round_id=f"{run_id}/r{i:02}", velocity=event.get("velocity", 80))
    result = dict(contract_version=VERSION, run_id=run_id, mode="raw", status="completed",
        tempo_bpm=120, beats_per_bar=4, ppq=480, models=models, execution=execution,
        raw_source=dict(asset=source_asset, sha256=sha256(raw_bytes).hexdigest(),
                        canonical_json_sha256=sha256(canonical_json(raw)).hexdigest(),
                        scope=f"{data_status} supplied completed take; no adapter submissions"),
        rounds=rounds, events=events, statistics=deepcopy(raw["statistics"]),
        references=deepcopy(raw["references"]), errors=deepcopy(raw.get("errors", [])),
        fallback=deepcopy(raw.get("fallback", dict(requested=False, used=False, reason=None))),
        arranged=None, limitations=deepcopy(raw["limitations"]))
    return freeze_result(result, raw_bytes=raw_bytes)


def _raw(completed_result: CompletedResult) -> dict:
    result = completed_result.to_dict()
    _require(result["mode"] == "raw" and result["status"] == "completed", "Require a completed raw result")
    return result


def to_manifest(completed_result: CompletedResult, *, policy: str = "quantum",
                source: dict[str, str] | None = None) -> Manifest:
    """Return both voices together; source maps keep rests outside InputNote lists."""
    result = _raw(completed_result)
    _require(policy in POLICIES, "Unknown policy")
    parts = []
    for voice, (instrument, role) in VOICES.items():
        active = sorted((e for e in result["events"][policy] if e["voice"] == voice and not e["rest"]),
                        key=lambda e: e["round"])
        metadata = dict(run_id=result["run_id"], policy=policy,
            bell_checkpoint_sha256=result["models"]["bell_checkpoint_sha256"],
            qcbm_checkpoint_sha256=result["models"]["qcbm_checkpoint_sha256"],
            raw_source_sha256=result["raw_source"]["sha256"],
            raw_source_canonical_json_sha256=result["raw_source"]["canonical_json_sha256"],
            raw_sidecar_sha256=completed_result.canonical_sha256,
            raw_sidecar_reference="raw-result.json", data_status=result["execution"]["data_status"],
            round_index_map=json.dumps({str(i): e["round_id"] for i, e in enumerate(active)}, sort_keys=True),
            source_event_map=json.dumps({f"{voice}:n{i}": e["event_id"] for i, e in enumerate(active)}, sort_keys=True))
        for key, value in (source or {}).items():
            _require(isinstance(key, str) and isinstance(value, str), "Source metadata must be strings")
            _require(key not in metadata or metadata[key] == value, f"Contradictory source metadata: {key}")
            metadata[key] = value
        parts.append(PartSpec(id=voice, instrument=instrument, role=role,
            tempo_bpm=result["tempo_bpm"], source=metadata,
            notes=[InputNote(pitch=e["pitch_midi"], onset_beats=e["onset_beats"],
                             duration_beats=e["duration_beats"], velocity=e["velocity"]) for e in active]))
    return Manifest(parts=parts, lead_track="alice")


def raw_score(completed_result: CompletedResult, *, policy: str = "quantum"):
    """Direct tick projection, including a silent lead; no central repairs."""
    from orchestrator.models import NoteEvent, Part, Score
    result = _raw(completed_result)
    manifest = to_manifest(completed_result, policy=policy)
    ppq = result["ppq"]
    parts = [Part(id=p.id, instrument=p.instrument, role=p.role, source=dict(p.source),
        source_tempo_bpm=p.tempo_bpm, notes=[NoteEvent(id=f"{p.id}:n{i}", source_id=f"{p.id}:n{i}",
            phrase_id=f"{p.id}:p0", pitch=n.pitch, onset_tick=round(n.onset_beats*ppq),
            duration_ticks=max(1, round(n.duration_beats*ppq)), velocity=n.velocity)
            for i, n in enumerate(p.notes)]) for p in manifest.parts]
    return Score(parts=parts, lead_track="alice", tempo_bpm=result["tempo_bpm"], ppq=ppq,
                 bars=4, window_bars=4)


def arrange_result(completed_result: CompletedResult, *, policy: str = "quantum",
                   key: str = "C major", chords: tuple[str, ...] = ("C", "F", "G", "C"),
                   backend: str = "rules", model: str | None = None, provider=None) -> CompletedResult:
    """Optional arrangement; Gemini must complete or raw replay remains available."""
    from orchestrator.models import OrchestrationConfig
    from orchestrator.pipeline import orchestrate
    raw = _raw(completed_result)
    manifest = to_manifest(completed_result, policy=policy)
    result = deepcopy(raw)
    result["mode"] = "arranged"
    _require(backend in ("rules", "gemini"), "Unknown arrangement backend")
    arranged = dict(backend_requested=backend, backend_actual=None, policy=policy,
        raw_result_canonical_json_sha256=completed_result.canonical_sha256,
        immutable_source_sha256=raw["raw_source"]["sha256"],
        immutable_source_canonical_json_sha256=raw["raw_source"]["canonical_json_sha256"],
        transformation_ids=[], output_parts=[], lineage=[], errors=[],
        fallback=dict(requested=False, used=False, reason=None))
    result["arranged"] = arranged
    try:
        _require(bool(manifest.parts[0].notes), "Silent lead")
        output = orchestrate([p.model_copy(deep=True) for p in manifest.parts], "alice",
            OrchestrationConfig(bars=4, window_bars=4, ppq=raw["ppq"], tempo_bpm=raw["tempo_bpm"],
                                backend=backend, render_audio=False, key=key, chords=list(chords),
                                **({"model": model} if model else {})), provider=provider)
        if backend == "gemini" and output.report["provider_status"] != "active":
            raise ValueError("Gemini did not complete all stages; no fallback arrangement accepted")
        arranged["backend_actual"] = backend
        arranged["output_parts"] = [p.model_dump(mode="json") for p in output.score.parts]
        arranged["report"] = output.report
        for part in output.score.parts:
            spec = next(p for p in manifest.parts if p.id == part.id)
            round_map = json.loads(spec.source["round_index_map"])
            event_map = json.loads(spec.source["source_event_map"])
            for note in part.notes:
                transform_id = f"{raw['run_id']}/arranged/{backend}/{policy}/{note.id}"
                arranged["transformation_ids"].append(transform_id)
                arranged["lineage"].append(dict(output_id=note.id, source_id=note.source_id,
                    event_id=event_map[note.source_id], round_id=round_map[note.source_id.split(":n")[1]],
                    run_id=raw["run_id"], transformation_id=transform_id, muted=note.muted))
    except Exception as exc:
        # Provider errors and local paths may contain secrets. Export only a safe class/code.
        code = "silent_lead" if not manifest.parts[0].notes else f"{backend}_arrangement_failed"
        error = dict(stage="arrangement", code=code, message=f"{backend} arrangement failed ({type(exc).__name__})")
        result["status"] = "failed"
        result["errors"].append(error)
        arranged["errors"].append(error)
    return freeze_result(result, raw_bytes=completed_result.raw_bytes)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=Path, help="Frozen qm.run-result.v1 JSON")
    parser.add_argument("--out", required=True, type=Path, help="New output directory")
    parser.add_argument("--policy", choices=POLICIES, default="quantum")
    parser.add_argument("--arrange", action="store_true", help="Also produce a labelled arrangement")
    parser.add_argument("--backend", choices=("rules", "gemini"), default="rules")
    parser.add_argument("--model")
    args = parser.parse_args(argv)
    completed = freeze_result(json.loads(args.result.read_bytes()))
    manifest = to_manifest(completed, policy=args.policy)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "raw-result.json").write_bytes(completed._json)
    (args.out / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    from orchestrator.midi_io import export_midi
    export_midi(raw_score(completed, policy=args.policy), args.out / "raw.mid")
    if args.arrange:
        arranged = arrange_result(completed, policy=args.policy, backend=args.backend, model=args.model).to_dict()
        (args.out / "arranged-result.json").write_bytes(canonical_json(arranged))
        if arranged["status"] == "failed":
            print(json.dumps(arranged["errors"]))
            return 1
        from orchestrator.models import Part
        score = raw_score(completed, policy=args.policy)
        score.parts = [Part.model_validate(p) for p in arranged["arranged"]["output_parts"]]
        export_midi(score, args.out / "arranged.mid")
    print(json.dumps(dict(run_id=completed.to_dict()["run_id"], data_status=completed.to_dict()["execution"]["data_status"],
                         backend_submissions=0, output=str(args.out))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
