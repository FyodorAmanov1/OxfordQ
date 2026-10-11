"""Source-preserving composition with explicit local/AI comparison status."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import wave
from pathlib import Path
from orchestrator.audio import render_comparisons
from orchestrator.gemini import GeminiProvider, safe_error
from orchestrator.models import OrchestrationConfig
from .models import CompositionPlan, ComposedScore, SourceBank
from .sources import generate_source_bank
from .planner import local_plan, COMPOSITION_INSTRUCTIONS
from .compiler import compile_plan
from .reference import raw_reference
from .assessment import assess
from .midi import export_composed_midi, read_composed_midi


@dataclass
class CompositionResult:
    bank: SourceBank
    plans: dict[str, CompositionPlan]
    scores: dict[str, ComposedScore]
    report: dict
    artifacts: dict[str, str]


def compose(request, *, bank=None, registry=None, provider=None, output_dir=None,
            render_audio=False, audio_config=None, allow_live_api=False):
    """Injected providers support offline checks; live credentials are never persisted."""
    if bank is not None and registry is not None:
        raise ValueError("Supply either a source bank or a generation registry")
    if render_audio and output_dir is None:
        raise ValueError("Rendering audio requires an output directory")
    out = Path(output_dir).resolve() if output_dir is not None else None
    if out is not None:
        if out.exists():
            raise ValueError("Choose a fresh output directory; existing pieces are preserved")
        out.mkdir(parents=True)
    bank = bank.model_copy(deep=True) if bank is not None else generate_source_bank(request, registry=registry)
    if request.key is not None:
        from orchestrator.theory import parse_key
        expected, supplied = parse_key(request.key), parse_key(bank.key)
        if (expected.tonic.pitchClass, expected.mode) != (supplied.tonic.pitchClass, supplied.mode):
            raise ValueError("Source bank key differs from the requested key")
    digest = bank.digest
    plan = local_plan(request, bank)
    plans = {"local": plan}
    scores = {"raw": raw_reference(request, bank, plan.timeline), "local": compile_plan(plan, bank, request)}
    ai = {"status": "not_requested", "execution": "none", "calls": 0, "errors": []}
    if request.compare or request.planner == "gemini":
        owned = provider is None
        ai["execution"] = "live_api" if owned else "injected_provider"
        try:
            if owned:
                if not allow_live_api:
                    raise ValueError("Live Gemini disabled: explicitly enable allow_live_api/--live-gemini to send the source bank to a potentially paid API")
                provider = GeminiProvider(OrchestrationConfig(model=request.model, max_api_calls=3,
                    render_audio=False), instructions=COMPOSITION_INSTRUCTIONS)
            payload = {"request": request.model_dump(), "source_bank": bank.model_dump(),
                       "reference_plan": plan.model_dump(),
                       "instrument_constraints": _constraints(request)}
            feedback = []
            for attempt in range(3):
                ai["calls"] += 1
                try:
                    response = provider.request(CompositionPlan, payload, feedback)
                    candidate = CompositionPlan.model_validate(response)
                    compiled = compile_plan(candidate, bank, request, planner="gemini")
                    plans["gemini"], scores["gemini"] = candidate, compiled
                    ai["status"] = "completed"
                    break
                except Exception as exc:
                    message = safe_error(exc)
                    ai["errors"].append(message)
                    feedback = [message]
            else:
                ai["status"] = "failed_validation_or_provider"
        except Exception as exc:
            ai.update(status="unavailable", execution="not_executed")
            ai["errors"].append(safe_error(exc))
        finally:
            if owned and provider is not None:
                try:
                    provider.close()
                except Exception as exc:
                    ai["errors"].append(safe_error(exc))
    if bank.digest != digest:
        raise RuntimeError("Source bank was mutated")
    actual = request.planner if request.planner in scores else None
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "requested_planner": request.planner, "actual_planner": actual,
        "status": "completed" if actual else "requested_planner_unavailable",
        "source_bank_sha256": digest, "source_execution": bank.provenance,
        "gemini": ai, "styles": "Procedural or AI-directed inspiration, not trained composer imitation",
        "pitch_policy": "Every sounding note preserves its source pitch class; octave shifts only",
        "reference_policy": "Independent fixed-grid instrument-source playback; POP909 is used by composition. Raw shares the local tempo/metre map.",
        "variants": {name: assess(score, plans.get(name)) for name, score in scores.items()},
        "audio": {"status": "not_requested"},
    }
    artifacts = {}
    if out is not None:
        def write(name, value):
            path = out / name
            text = value.model_dump_json(indent=2) if hasattr(value, "model_dump_json") else json.dumps(value, indent=2)
            path.write_text(text, encoding="utf-8")
            artifacts[name] = str(path)
        write("request.json", request)
        write("source-bank.json", bank)
        midis = {}
        for name, score in scores.items():
            write(name + ".score.json", score)
            if name in plans:
                write(name + ".plan.json", plans[name])
            midi = out / (name + ".mid")
            export_composed_midi(score, midi)
            _check_round_trip(score, midi)
            artifacts[name + "_midi"] = str(midi)
            midis[name] = midi
        if render_audio:
            audio, report["audio"] = render_comparisons(midis, audio_config or OrchestrationConfig(), scores=scores)
            artifacts.update(audio)
            if report["audio"]["status"] == "rendered":
                durations = {}
                for name, score in scores.items():
                    with wave.open(str(midis[name].with_suffix(".wav")), "rb") as wav:
                        seconds = wav.getnframes() / wav.getframerate()
                    expected = score.timeline.seconds_at(score.end_tick)
                    if seconds + .05 < expected:
                        raise ValueError("Rendered audio truncates the tempo timeline")
                    durations[name] = {"wav_seconds": round(seconds, 3), "timeline_seconds": round(expected, 3),
                                       "release_tail_seconds": round(seconds - expected, 3)}
                report["audio"]["durations"] = durations
        from .listening import write_study_page
        write_study_page(out, request, report)
        artifacts["listening_page"] = str(out / "index.html")
        report["files_sha256"] = {Path(path).name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                  for path in artifacts.values()}
        write("report.json", report)
    return CompositionResult(bank, plans, scores, report, artifacts)


def _constraints(request):
    from orchestrator.instruments import profile
    return {i: {"low": profile(i).low, "high": profile(i).high,
                "polyphony": profile(i).polyphony} for i in request.instruments}


def _check_round_trip(score, path):
    import mido
    midi = read_composed_midi(path)
    if midi["ppq"] != score.ppq or midi["end_tick"] != score.end_tick:
        raise ValueError("MIDI changed the composition timeline")
    for part in score.parts:
        expected = sorted((n.pitch, n.onset_tick, n.duration_ticks, n.velocity) for n in part.notes)
        if midi["parts"][part.id]["notes"] != expected:
            raise ValueError("MIDI changed sounding occurrences")
        if midi["parts"][part.id]["expression"][1:] != sorted(part.expression):
            raise ValueError("MIDI changed expression events")
    expected_tempos = [(t.tick, mido.bpm2tempo(t.bpm)) for t in score.timeline.tempos]
    expected_metres, previous = [], None
    for tick, bar in zip(score.timeline.bar_starts, score.timeline.bars):
        signature = (bar.numerator, bar.denominator)
        if signature != previous:
            expected_metres.append((tick, *signature))
            previous = signature
    if midi["tempos"] != expected_tempos or midi["metres"] != expected_metres:
        raise ValueError("MIDI changed metre or tempo events")
