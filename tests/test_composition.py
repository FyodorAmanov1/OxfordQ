"""Composition contract, frozen inference, and offline AI comparison checks."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import mido
import pytest
from pydantic import ValidationError
from orchestrator import GenerationRegistry, GeneratedSequence, InputNote
from orchestrator.composition.models import (CompositionRequest, SourceBank, SourceEvent,
    SourceMotif, SourceChord, MusicalTimeline, BarSignature, TempoEvent, CompositionPlan)
from orchestrator.composition.planner import local_plan
from orchestrator.composition.compiler import compile_plan, validate_plan, validate_score
from orchestrator.composition.sources import generate_source_bank
from orchestrator.composition.pipeline import compose, _check_round_trip
from orchestrator.composition.midi import export_composed_midi, read_composed_midi
from orchestrator.composition.cli import main


@pytest.fixture
def bank():
    events, motifs = [], []
    for instrument, base in [("flute", 72), ("clarinet", 60), ("violin_1", 60), ("cello", 48), ("double_bass", 36)]:
        for variant, pitches in enumerate([[base, base + 2, None, base + 7],
                                           [base + 4, base + 7, base + 2, base]]):
            ids = []
            for i, pitch in enumerate(pitches):
                event_id = f"{instrument}/{variant}/{i}"
                events.append(SourceEvent(id=event_id, pitch=pitch, source_part=instrument, model="external"))
                ids.append(event_id)
            motifs.append(SourceMotif(id=f"{instrument}/motif/{variant}", source_part=instrument, events=ids))
        motifs.append(SourceMotif(id=instrument + "/arrival", source_part=instrument, events=[instrument + "/0/0"]))
    chords = []
    for name, pitches in [("I", [48, 52, 55]), ("V", [55, 59, 62]), ("vi", [57, 60, 64])]:
        ids = []
        for i, pitch in enumerate(pitches):
            event_id = f"chord/{name}/{i}"
            events.append(SourceEvent(id=event_id, pitch=pitch, source_part="harmony", model="external"))
            ids.append(event_id)
        chords.append(SourceChord(id=name, symbol=name, events=ids))
    return SourceBank(key="C major", events=events, motifs=motifs, chords=chords, provenance={"execution": "mock fixture"})


@pytest.mark.parametrize("style", ["bach", "mozart", "debussy", "rachmaninoff"])
def test_styles_develop_and_preserve_sources(bank, style):
    request = CompositionRequest(style=style, bars=24)
    before = bank.model_dump_json()
    plan = local_plan(request, bank)
    assert plan == local_plan(request, bank)
    score = compile_plan(plan, bank, request)
    assert bank.model_dump_json() == before
    validate_score(score, bank, request)
    lead = next(p for p in score.parts if p.id == request.lead_track)
    assert len({n.duration_ticks for n in lead.notes}) > 3
    assert max(n.pitch for n in lead.notes) - min(n.pitch for n in lead.notes) >= 24
    assert len({n.velocity for n in lead.notes}) > 5
    development = plan.timeline.bar_starts[plan.sections[1].start_bar]
    end_break = development + plan.timeline.bar_ticks(plan.sections[1].start_bar)
    assert not any(development <= n.onset_tick < end_break for n in lead.notes)
    assert score.occurrences and any(e["rest"] for o in score.occurrences for e in o["events"])
    assert len(set(t.bpm for t in plan.timeline.tempos)) > 3
    assert any(o.texture == "sustained" for o in plan.harmony)
    if style == "debussy":
        assert {(b.numerator, b.denominator) for b in plan.timeline.bars} == {(6, 8), (5, 4), (3, 4)}


@pytest.mark.parametrize("mutation,match", [
    (lambda p: setattr(p, "source_bank_sha256", "wrong"), "source bank"),
    (lambda p: setattr(p.motifs[0], "motif_id", "invented"), "Unknown motif"),
    (lambda p: setattr(p.motifs[0], "steps_ticks", [-1, 480, 480, 480]), "Positive rhythmic"),
    (lambda p: setattr(p.motifs[0], "start_tick", p.timeline.end_tick), "exceeds timeline"),
    (lambda p: setattr(p.motifs[1], "id", p.motifs[0].id), "unique"),
    (lambda p: setattr(p.harmony[0], "target_parts", ["flute"]), "non-lead"),
])
def test_reject_bad_plans(bank, mutation, match):
    request = CompositionRequest()
    plan = local_plan(request, bank)
    mutation(plan)
    with pytest.raises(ValueError, match=match):
        validate_plan(plan, bank, request)


def test_return_needs_actual_theme(bank):
    request = CompositionRequest()
    plan = local_plan(request, bank)
    end = plan.timeline.bar_starts[plan.sections[-1].start_bar]
    for o in plan.motifs:
        if o.start_tick >= end and o.target_part == "flute":
            o.motif_id = "flute/motif/1" if o.motif_id != "flute/motif/1" else "flute/motif/0"
    with pytest.raises(ValueError, match="introduced source motif"):
        validate_plan(plan, bank, request)


@pytest.mark.parametrize("mutation,match", [
    (lambda s: setattr(s.parts[0].notes[0], "pitch", s.parts[0].notes[0].pitch + 1), "pitch class"),
    (lambda s: setattr(s.parts[0].notes[0], "source_id", "invented"), "pitch class"),
    (lambda s: setattr(s.parts[0].notes[0], "transpose", 1), "truthful"),
    (lambda s: setattr(s.parts[0].notes[0], "pitch", 0), "range"),
    (lambda s: s.occurrences[0]["events"].pop(), "ordering and rests"),
    (lambda s: s.parts[0].notes.append(s.parts[0].notes[0].model_copy(update={"id": "extra"})), "Overlapping unisons"),
])
def test_reject_bad_scores(bank, mutation, match):
    request = CompositionRequest()
    score = compile_plan(local_plan(request, bank), bank, request)
    mutation(score)
    with pytest.raises(ValueError, match=match):
        validate_score(score, bank, request)


def test_mixed_meter_tempo_tuplet_roundtrip(bank, tmp_path):
    request = CompositionRequest(style="debussy", bars=12)
    plan = local_plan(request, bank)
    # 3:2 eighth-note tuplet values are exactly representable at PPQ 480.
    plan.motifs[0].steps_ticks = [160, 160, 160, 840]
    score = compile_plan(plan, bank, request)
    midi_path = tmp_path / "expressive.mid"
    export_composed_midi(score, midi_path)
    _check_round_trip(score, midi_path)
    data = read_composed_midi(midi_path)
    assert data["metres"] == [(0, 6, 8), (5760, 5, 4), (15360, 3, 4)]
    assert data["tempos"] == [(t.tick, mido.bpm2tempo(t.bpm)) for t in score.timeline.tempos]
    assert mido.MidiFile(midi_path).length == pytest.approx(score.timeline.seconds_at(score.end_tick), abs=.0001)
    for part in score.parts:
        assert data["parts"][part.id]["expression"][1:] == part.expression


@pytest.mark.parametrize("tempos", [[], [{"tick": 10, "bpm": 80}],
    [{"tick": 0, "bpm": 80}, {"tick": 0, "bpm": 90}],
    [{"tick": 0, "bpm": float("nan")}], [{"tick": 1920, "bpm": 80}]])
def test_invalid_timeline(tempos):
    with pytest.raises(ValidationError):
        MusicalTimeline(bars=[BarSignature(numerator=4)], tempos=tempos)


def test_tempo_integration():
    timeline = MusicalTimeline(bars=[BarSignature(numerator=4), BarSignature(numerator=3)],
                               tempos=[TempoEvent(tick=0, bpm=120), TempoEvent(tick=960, bpm=60)])
    assert timeline.bar_starts == [0, 1920]
    assert timeline.seconds_at(timeline.end_tick) == 6
    with pytest.raises(ValueError):
        timeline.seconds_at(timeline.end_tick + 1)


class OfflinePlanner:
    def __init__(self, bad_first=False):
        self.payloads, self.feedback, self.bad_first = [], [], bad_first

    def request(self, schema, payload, feedback):
        self.payloads.append(payload)
        self.feedback.append(list(feedback))
        result = schema.model_validate(payload["reference_plan"])
        if self.bad_first and len(self.payloads) == 1:
            result.motifs[0].motif_id = "invented"
        return result


def test_ai_comparison_same_bank_and_validation_retry(bank, tmp_path):
    request = CompositionRequest(compare=True)
    provider = OfflinePlanner(bad_first=True)
    result = compose(request, bank=bank, provider=provider, output_dir=tmp_path / "study")
    assert result.report["gemini"]["status"] == "completed"
    assert result.report["gemini"]["execution"] == "injected_provider"
    assert result.report["gemini"]["calls"] == 2
    assert provider.feedback[1] and not provider.feedback[0]
    assert all(s.source_bank_sha256 == bank.digest for s in result.scores.values())
    assert result.scores["local"].parts == result.scores["gemini"].parts
    assert len(result.report["files_sha256"]) >= 10
    assert (tmp_path / "study/index.html").is_file()
    with pytest.raises(ValueError, match="fresh"):
        compose(request, bank=bank, output_dir=tmp_path / "study")


def test_no_live_api_without_optin(bank, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Live provider must never initialize")
    monkeypatch.setattr("orchestrator.composition.pipeline.GeminiProvider", forbidden)
    result = compose(CompositionRequest(planner="gemini", compare=True), bank=bank)
    assert result.report["status"] == "requested_planner_unavailable"
    assert result.report["actual_planner"] is None
    assert result.report["gemini"]["calls"] == 0
    assert result.report["gemini"]["execution"] == "not_executed"
    assert set(result.scores) == {"local", "raw"}


def test_invalid_ai_never_accepted(bank):
    class Invalid:
        def request(self, schema, payload, feedback):
            return {"pitches": [66]}
    result = compose(CompositionRequest(planner="gemini"), bank=bank, provider=Invalid())
    assert result.report["gemini"]["calls"] == 3
    assert result.report["gemini"]["status"] == "failed_validation_or_provider"
    assert "gemini" not in result.scores


def test_source_bank_rejects_rest_chord(bank):
    content = bank.model_dump()
    content["chords"][0]["events"][0] = "flute/0/2"
    with pytest.raises(ValidationError, match="sounding chord"):
        SourceBank.model_validate(content)


def test_distinct_small_models_remain_pluggable():
    class SmallModel:
        def __init__(self, pitches):
            self.pitches, self.calls = pitches, []
        def generate(self, request):
            self.calls.append(request)
            return GeneratedSequence(notes=[InputNote(pitch=p, onset_beats=i, duration_beats=.7)
                    for i, p in enumerate(self.pitches)], source={"checkpoint": "mock-small"})
    flute, cello = SmallModel([72, 74, 79, 72]), SmallModel([48, 52, 55, 48])
    registry = GenerationRegistry().register("flute-small", flute, instruments=["flute"])
    registry.register("cello-small", cello, instruments=["cello"])
    request = CompositionRequest(instruments=["flute", "cello"], bars=12)
    bank = generate_source_bank(request, registry=registry)
    result = compose(request, bank=bank)
    assert len(flute.calls) == len(cello.calls) == 1
    assert all(e.model == "external" for e in bank.events if e.source_part in request.instruments)
    assert result.report["status"] == "completed"
    assert "Caller-owned" in bank.provenance["execution"]
    assert "no physical hardware" not in bank.provenance["execution"]


@pytest.mark.parametrize("style", ["bach", "mozart", "debussy", "rachmaninoff"])
def test_actual_frozen_models_and_hash_preservation(style):
    root = Path(__file__).parents[1] / "quantum_models/data"
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob("*.json")}
    request = CompositionRequest(style=style, bars=12)
    bank = generate_source_bank(request)
    again = generate_source_bank(request)
    assert bank.digest == again.digest
    assert any(e.pitch is None for e in bank.events)
    assert {e.model for e in bank.events} == {"qcbm", "pop909"}
    result = compose(request, bank=bank)
    assert result.report["status"] == "completed"
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob("*.json")}


def test_cli_explicit_missing_ai_and_no_false_fallback(bank, tmp_path, monkeypatch):
    bank_path = tmp_path / "bank.json"
    bank_path.write_text(bank.model_dump_json(), encoding="utf-8")
    status = main(["--source-bank", str(bank_path), "--planner", "gemini", "--no-audio", "--out", str(tmp_path / "missing")])
    assert status == 2
    report = json.loads((tmp_path / "missing/report.json").read_text())
    assert report["actual_planner"] is None
    assert not (tmp_path / "missing/gemini.mid").exists()


def test_gemini_composition_prompt_is_separate(monkeypatch, bank):
    from orchestrator.gemini import GeminiProvider, SYSTEM_INSTRUCTIONS
    from orchestrator.composition.planner import COMPOSITION_INSTRUCTIONS
    from orchestrator.models import OrchestrationConfig
    provider = object.__new__(GeminiProvider)
    provider.config = OrchestrationConfig()
    provider.instructions = COMPOSITION_INSTRUCTIONS
    provider.calls = 0
    inputs = []
    plan = local_plan(CompositionRequest(), bank)
    def create(**kwargs):
        inputs.append(kwargs)
        return SimpleNamespace(status="completed", output_text=plan.model_dump_json())
    provider.client = SimpleNamespace(interactions=SimpleNamespace(create=create))
    assert provider.request(CompositionPlan, {}, []) == plan
    assert COMPOSITION_INSTRUCTIONS in inputs[0]["input"]
    assert SYSTEM_INSTRUCTIONS not in inputs[0]["input"]


def test_section_capacity_violation(bank):
    request = CompositionRequest()
    score = compile_plan(local_plan(request, bank), bank, request)
    first = score.parts[0].notes[0]
    score.parts[0].notes.extend([first.model_copy(update={"id": "extra1"}), first.model_copy(update={"id": "extra2"})])
    with pytest.raises(ValueError, match="capacity exceeded"):
        validate_score(score, bank, request)


def test_source_rest_timing_cannot_be_corrupted(bank):
    request = CompositionRequest()
    score = compile_plan(local_plan(request, bank), bank, request)
    slot = next(e for o in score.occurrences for e in o["events"] if e["rest"])
    slot["onset_tick"] = score.end_tick
    with pytest.raises(ValueError, match="occurrence timing"):
        validate_score(score, bank, request)


def test_bank_key_mismatch_and_ambiguous_inputs(bank):
    with pytest.raises(ValueError, match="key differs"):
        compose(CompositionRequest(key="D minor"), bank=bank)
    with pytest.raises(ValueError, match="either"):
        compose(CompositionRequest(), bank=bank, registry=GenerationRegistry())
    with pytest.raises(ValueError, match="output directory"):
        compose(CompositionRequest(), bank=bank, render_audio=True)


def test_cli_does_not_silently_accept_zero_bars(bank, tmp_path):
    path = tmp_path / "bank.json"
    path.write_text(bank.model_dump_json())
    assert main(["--bars", "0", "--source-bank", str(path), "--no-audio", "--out", str(tmp_path / "bad")]) == 1
    assert not (tmp_path / "bad").exists()


def test_sustained_bass_uses_source_chord_root(bank):
    request = CompositionRequest(style="bach")
    plan = local_plan(request, bank)
    score = compile_plan(plan, bank, request)
    bass = next(p for p in score.parts if p.id == "double_bass")
    chord = next(c for c in bank.chords if c.id == plan.harmony[0].chord_id)
    note = next(n for n in bass.notes if n.phrase_id == plan.harmony[0].id)
    assert note.source_id == chord.events[0]


def test_missing_instrument_source_has_clear_error(bank):
    request = CompositionRequest(instruments=["flute", "oboe"])
    with pytest.raises(ValueError, match="No sounding source motif.*oboe"):
        compose(request, bank=bank)


def test_saved_artifact_verifier_detects_corruption(bank, tmp_path):
    from scripts.verify_composition_artifacts import verify
    output = tmp_path / "study"
    compose(CompositionRequest(), bank=bank, output_dir=output)
    assert verify(output)["status"] == "passed"
    with (output / "local.mid").open("ab") as stream:
        stream.write(b"corrupt")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify(output)
