import json
from pathlib import Path

import mido
import pytest

from orchestrator import OrchestrationConfig, PartSpec, load_manifest, orchestrate
from orchestrator.baseline import arrange_baseline
from orchestrator.midi_io import export_midi, import_parts
from orchestrator.models import ArrangementPlan, EditProposal
from orchestrator.theory import baseline_plan, musical_metrics
from orchestrator.validation import apply_proposal, validate_plan, validate_score


def parts(bars=4):
    return [
        PartSpec(id="lead", instrument="flute", tempo_bpm=100, notes=[
            {"pitch": p, "onset_beats": bar * 4 + i, "duration_beats": 1, "velocity": 90}
            for bar in range(bars) for i, p in enumerate([76, 79, 81, 79])]),
        PartSpec(id="strings", instrument="viola", tempo_bpm=80, notes=[
            {"pitch": 62, "onset_beats": bar * 4, "duration_beats": 4, "velocity": 100}
            for bar in range(bars)]),
        PartSpec(id="bass", instrument="double_bass", notes=[
            {"pitch": 36, "onset_beats": bar * 4, "duration_beats": 4, "velocity": 80}
            for bar in range(bars)]),
    ]


def state(bars=4, **kwargs):
    cfg = OrchestrationConfig(bars=bars, key="C major", chords=["C"], render_audio=False, **kwargs)
    original, _ = import_parts(parts(bars), "lead", cfg)
    plan = baseline_plan(original, cfg)
    arranged = arrange_baseline(original, plan, cfg)
    return cfg, original, plan, arranged


def test_rules_pipeline_preserves_lead_and_complete_lineage(tmp_path):
    cfg = OrchestrationConfig(bars=4, backend="rules", render_audio=False, key="C major", chords=["C"], output_dir=tmp_path)
    result = orchestrate(parts(), "lead", cfg)
    lead = result.score.part("lead")
    assert [n.pitch for n in lead.notes] == [76, 79, 81, 79] * 4
    assert [n.onset_tick for n in lead.notes] == list(range(0, 16*480, 480))
    assert result.report["lead_preserved"] is True
    assert len(result.report["note_lineage"]) == 24
    assert any("mapped source tempo" in w for w in result.report["warnings"])
    for name in ("original.mid", "baseline.mid", "arrangement.mid", "report.json", "arrangement.json"):
        assert (tmp_path / name).is_file()
    assert len(mido.MidiFile(tmp_path / "arrangement.mid").tracks) == 4


def test_independent_key_offset_is_corrected_as_phrase_transform():
    cfg, original, plan, score = state()
    assert all(n.pitch % 12 in {0, 4, 7} for n in score.part("strings").notes)
    assert validate_score(score, original, cfg) == []
    assert musical_metrics(score, plan, original)["harmonic_fit_with_ornaments"] > 0.9


@pytest.mark.parametrize("edit", [
    {"op": "edit_note", "target": "lead:n0", "pitch": 77},
    {"op": "mute_phrase", "target": "lead:p0"},
    {"op": "shift_phrase", "target": "lead:p0", "ticks": 480},
    {"op": "transpose_phrase", "target": "lead:p0", "semitones": 12},
])
def test_lead_note_edits_rejected_atomically(edit):
    cfg, original, _, score = state()
    before = score.model_dump()
    with pytest.raises(ValueError, match="lead"):
        apply_proposal(score, EditProposal(edits=[edit]), original, cfg, 0, cfg.end_tick)
    assert score.model_dump() == before


def test_uniform_lead_octave_shift_preserves_contour():
    source = parts()
    source[0].notes = [n.model_copy(update={"pitch": n.pitch-12}) for n in source[0].notes]
    source[0].instrument = "piccolo"
    result = orchestrate(source, "lead", {"bars": 4, "backend": "rules", "render_audio": False})
    lead = result.score.part("lead")
    assert len({n.transpose for n in lead.notes}) == 1
    assert all(n.transpose % 12 == 0 for n in lead.notes)


def test_unplayable_lead_rejected():
    source = parts()
    source[0].notes[0].pitch = 20
    source[0].notes[-1].pitch = 120
    with pytest.raises(ValueError, match="lead cannot fit"):
        orchestrate(source, "lead", {"bars": 4, "backend": "rules", "render_audio": False})


def test_cumulative_budget_and_small_phrases():
    cfg, original, _, score = state()
    # Four accompaniment notes have a floor(4 * .2) = 0 individual edit budget.
    with pytest.raises(ValueError, match="budget"):
        apply_proposal(score, EditProposal(edits=[{"op": "edit_note", "target": "strings:n0", "pitch": score.part("strings").notes[0].pitch+1}]),
                       original, cfg, 0, cfg.end_tick)


def test_unknown_ids_and_context_edits_rejected():
    cfg, original, _, score = state(bars=8)
    with pytest.raises(ValueError, match="Unknown"):
        apply_proposal(score, EditProposal(edits=[{"op": "mute_note", "target": "invented"}]), original, cfg, 0, cfg.end_tick)
    with pytest.raises(ValueError, match="outside"):
        apply_proposal(score, EditProposal(edits=[{"op": "mute_note", "target": "strings:n0"}]), original, cfg, cfg.bar_ticks*4, cfg.end_tick)


def test_phrase_shift_cannot_rewrite_a_previous_window():
    cfg, original, _, score = state(bars=8)
    with pytest.raises(ValueError, match="read-only context"):
        apply_proposal(score, EditProposal(edits=[{"op": "shift_phrase", "target": "strings:p1", "ticks": -480}]),
                       original, cfg, cfg.bar_ticks*4, cfg.end_tick)


def test_cli_strict_flags_expose_fallback(tmp_path, monkeypatch):
    from orchestrator.cli import main
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    manifest = tmp_path / "parts.json"
    manifest.write_text(json.dumps({"lead_track": "lead", "parts": [p.model_dump(mode="json", exclude_none=True) for p in parts()]}))
    assert main(["--manifest", str(manifest), "--out", str(tmp_path / "out"), "--bars", "4",
                 "--no-audio", "--require-gemini"]) == 2
    assert (tmp_path / "out" / "report.json").is_file()


def test_boundary_clipping_has_source_warning():
    source = parts(bars=1)
    source[0].notes[-1].duration_beats = 2
    cfg = OrchestrationConfig(bars=1, backend="rules", render_audio=False)
    original, warnings = import_parts(source, "lead", cfg)
    assert original.part("lead").notes[-1].end_tick == cfg.end_tick
    assert any("clipped" in warning for warning in warnings)


def test_payload_fields_and_bounds_rejected():
    cfg, original, _, score = state()
    with pytest.raises(ValueError, match="unexpected"):
        apply_proposal(score, EditProposal(edits=[{"op": "mute_note", "target": "strings:n0", "pitch": 60}]), original, cfg, 0, cfg.end_tick)
    with pytest.raises(ValueError):
        apply_proposal(score, EditProposal(edits=[{"op": "transpose_phrase", "target": "strings:p0", "semitones": 48}]), original, cfg, 0, cfg.end_tick)
    with pytest.raises(ValueError):
        apply_proposal(score, EditProposal(edits=[{"op": "shift_phrase", "target": "strings:p0", "ticks": -480}]), original, cfg, 0, cfg.end_tick)


def test_note_identity_and_transform_tampering_rejected():
    cfg, original, _, score = state()
    score.part("strings").notes[0].source_id = "wrong"
    assert any("source reference" in e for e in validate_score(score, original, cfg))
    cfg, original, _, score = state()
    score.part("strings").notes.pop()
    assert any("invented" in e for e in validate_score(score, original, cfg))
    cfg, original, _, score = state()
    score.part("strings").notes[0].transpose += 1
    assert any("every source note" in e for e in validate_score(score, original, cfg))


def test_polyphony_repaired_and_muting_exposed():
    source = parts()
    source[1].instrument = "double_bass"
    source[1].notes = [{"pitch": 48 + i, "onset_beats": 0, "duration_beats": 4, "velocity": 60} for i in range(4)]
    result = orchestrate(source, "lead", {"bars": 4, "backend": "rules", "render_audio": False})
    assert sum(not n.muted for n in result.score.part("strings").notes) == 1
    assert any("muted" in w for w in result.report["warnings"])


def test_empty_lead_and_duplicate_parts_rejected():
    source = parts()
    source[0].notes = []
    with pytest.raises(ValueError, match="lead has no notes"):
        orchestrate(source, "lead", {"backend": "rules"})
    with pytest.raises(ValueError, match="unique"):
        orchestrate([parts()[0], parts()[0]], "lead", {"backend": "rules"})


def test_short_parts_trail_with_rests_and_excerpt_is_explicit():
    source = parts(bars=1)
    result = orchestrate(source, "lead", {"bars": 4, "backend": "rules", "render_audio": False})
    assert result.score.end_tick == 16*480
    assert max(n.end_tick for n in result.score.part("lead").notes) == 4*480
    source = parts(bars=8)
    result = orchestrate(source, "lead", {"bars": 4, "start_bar": 4, "backend": "rules", "render_audio": False})
    assert result.score.part("lead").notes[0].source_id == "lead:n16"
    assert result.score.part("lead").notes[0].onset_tick == 0
    assert result.report["excerpt"]["start_bar"] == 4


def test_plan_gaps_muted_lead_and_override_changes_rejected():
    cfg, original, plan, _ = state()
    plan.chords[0].start_tick = 1
    plan.directives[0].silent = True
    plan.key = "G major"
    errors = validate_plan(plan, original, cfg)
    assert any("gaps" in e for e in errors)
    assert any("lead" in e.lower() for e in errors)
    assert any("override" in e for e in errors)


class EchoProvider:
    def __init__(self):
        self.feedback = []
    def request(self, schema, payload, feedback):
        self.feedback.append(feedback)
        if schema is ArrangementPlan:
            return payload["baseline_plan"]
        return {"edits": [], "rationale": "Retain the validated baseline"}


def test_gemini_integration_with_schema_provider():
    provider = EchoProvider()
    result = orchestrate(parts(bars=8), "lead", {"bars": 8, "backend": "gemini", "render_audio": False}, provider=provider)
    assert result.report["provider_status"] == "active"
    assert len(result.report["windows"]) == 2
    assert len(result.report["requests"]) == 3


class BadEditProvider(EchoProvider):
    def request(self, schema, payload, feedback):
        if schema is ArrangementPlan:
            return payload["baseline_plan"]
        return {"edits": [{"op": "mute_note", "target": "lead:n0"}]}


def test_failed_model_edits_fall_back_with_bounded_corrections():
    result = orchestrate(parts(), "lead", {"bars": 4, "render_audio": False}, provider=BadEditProvider())
    assert result.report["provider_status"] == "degraded"
    assert result.report["windows"][0]["status"] == "unrepaired"
    assert len(result.report["requests"]) == 4  # one global plus three bounded window attempts
    assert not any(n.muted for n in result.score.part("lead").notes)


def test_missing_key_returns_explicit_baseline(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    result = orchestrate(parts(), "lead", {"bars": 4, "render_audio": False})
    assert result.report["provider_status"] == "unavailable"
    assert any("GEMINI_API_KEY" in w for w in result.report["warnings"])


class RepairProvider(EchoProvider):
    def request(self, schema, payload, feedback):
        self.feedback.append(feedback)
        if schema is ArrangementPlan:
            data = payload["baseline_plan"]
            if len(self.feedback) == 1:
                return dict(data, chords=[])
            return data
        return {"edits": []}


def test_schema_error_is_sent_back_for_correction():
    provider = RepairProvider()
    result = orchestrate(parts(), "lead", {"bars": 4, "render_audio": False}, provider=provider)
    assert provider.feedback[1]
    assert result.report["provider_status"] == "active"


def _midi(path, messages, ticks_per_beat=960, metre=(4,4)):
    midi = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage("time_signature", numerator=metre[0], denominator=metre[1]))
    track.extend(messages)
    midi.save(path)


def test_midi_sustain_channels_and_ppq(tmp_path):
    path = tmp_path / "pedal.mid"
    _midi(path, [
        mido.Message("note_on", note=76, velocity=90, channel=0),
        mido.Message("control_change", control=64, value=127, channel=0),
        mido.Message("note_off", note=76, channel=0, time=960),
        mido.Message("control_change", control=64, value=0, channel=0, time=960),
    ])
    score, _ = import_parts([PartSpec(id="lead", instrument="flute", path=path)], "lead", OrchestrationConfig(bars=1))
    assert score.part("lead").notes[0].duration_ticks == 960
    exported = tmp_path / "exported.mid"
    export_midi(score, exported)
    assert mido.MidiFile(exported).ticks_per_beat == 480


def test_metre_and_tempo_changes_rejected(tmp_path):
    path = tmp_path / "bad.mid"
    _midi(path, [mido.Message("note_on", note=76, velocity=90),
                 mido.Message("note_off", note=76, time=960)], metre=(3,4))
    with pytest.raises(ValueError, match="4/4"):
        import_parts([PartSpec(id="lead", instrument="flute", path=path)], "lead", OrchestrationConfig())
    _midi(path, [mido.MetaMessage("set_tempo", tempo=500000),
                 mido.Message("note_on", note=76, velocity=90),
                 mido.MetaMessage("set_tempo", tempo=600000, time=960),
                 mido.Message("note_off", note=76)])
    with pytest.raises(ValueError, match="tempo changes"):
        import_parts([PartSpec(id="lead", instrument="flute", path=path)], "lead", OrchestrationConfig())


def test_multitrack_selection_and_relative_paths(tmp_path):
    path = tmp_path / "multi.mid"
    midi = mido.MidiFile()
    for pitch in (76, 79):
        tr = mido.MidiTrack()
        tr.extend([mido.Message("note_on", note=pitch, velocity=90),
                   mido.Message("note_off", note=pitch, time=480)])
        midi.tracks.append(tr)
    midi.save(path)
    spec = PartSpec(id="lead", instrument="flute", path=path)
    with pytest.raises(ValueError, match="select midi_track"):
        import_parts([spec], "lead", OrchestrationConfig())
    manifest_path = tmp_path / "parts.json"
    manifest_path.write_text(json.dumps({"lead_track": "lead", "parts": [
        {"id": "lead", "instrument": "flute", "path": "multi.mid", "midi_track": 1}]}))
    manifest = load_manifest(manifest_path)
    score, _ = import_parts(manifest.parts, "lead", OrchestrationConfig())
    assert score.part("lead").notes[0].pitch == 79


def test_audio_unavailable_reports_problem_but_keeps_midi(tmp_path):
    result = orchestrate(parts(), "lead", {"bars": 4, "backend": "rules", "output_dir": tmp_path,
                                          "soundfont": tmp_path / "missing.sf2"})
    assert result.report["audio"]["status"] == "unavailable"
    assert (tmp_path / "arrangement.mid").is_file()


def test_sdk_adapter_uses_structured_response_without_real_network(monkeypatch):
    import orchestrator.gemini as module
    provider = object.__new__(module.GeminiProvider)
    provider.config = OrchestrationConfig()
    provider.calls = 0
    captured = {}
    class Response:
        output_text = '{"edits":[],"rationale":"test"}'
    class Interactions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return Response()
    class Client:
        interactions = Interactions()
    provider.client = Client()
    assert provider.request(EditProposal, {"note": 60}, []).edits == []
    assert captured["response_format"]["mime_type"] == "application/json"
    assert "schema" in captured["response_format"]
    provider.config.max_api_calls = 1
    with pytest.raises(RuntimeError, match="budget"):
        provider.request(EditProposal, {}, [])


def test_installed_sdk_request_and_response_contract(monkeypatch):
    """Exercise the real SDK's normalisation/serialization, intercepting HTTP send."""
    import httpx
    from orchestrator.gemini import GeminiProvider
    monkeypatch.setenv("GEMINI_API_KEY", "local-sdk-contract-test")
    captured = {}
    def intercept(self, request, **kwargs):
        captured.update(json.loads(request.content))
        return httpx.Response(200, request=request, json={
            "id": "offline-test", "model": "gemini-3.8-flash", "status": "completed",
            "steps": [{"type": "model_output", "content": [
                {"type": "text", "text": '{"edits":[],"rationale":"SDK contract"}'}]}]})
    monkeypatch.setattr(httpx.Client, "send", intercept)
    provider = GeminiProvider(OrchestrationConfig())
    try:
        proposal = provider.request(EditProposal, {"note": 60}, [])
        assert proposal.rationale == "SDK contract"
        assert captured["response_format"]["mime_type"] == "application/json"
        assert captured["response_format"]["schema"]["type"] == "object"
        assert captured["model"] == "gemini-3.8-flash"
    finally:
        provider.close()
