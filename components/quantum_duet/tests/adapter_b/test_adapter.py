"""Paired boundary acceptance tests; no remote backend or native audio."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import mido
import pytest

from quantum_duet.orchestration_adapter import (
    arrange_result, freeze_result, from_take, raw_score, to_manifest,
)

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "docs/team/fixtures/run-result.v1.json"
TAKE = ROOT / "components/quantum_duet/tests/fixtures/qollab-local-run.json"


@pytest.fixture
def fixture():
    return json.loads(FIXTURE.read_bytes())


def test_frozen_fixture_zero_submissions_and_lineage(fixture, monkeypatch):
    from quantum_duet import integration
    from orchestrator.midi_io import import_parts
    from orchestrator.models import OrchestrationConfig

    def forbidden(*args, **kwargs):
        pytest.fail("Frozen conversion must not execute or arrange")

    monkeypatch.setattr(integration, "generate_take", forbidden)
    import orchestrator.pipeline
    import orchestrator.baseline
    monkeypatch.setattr(orchestrator.pipeline, "orchestrate", forbidden)
    monkeypatch.setattr(orchestrator.baseline, "arrange_baseline", forbidden)
    completed = freeze_result(fixture)
    for policy in ("quantum", "classical"):
        manifest = to_manifest(completed, policy=policy)
        assert [p.id for p in manifest.parts] == ["alice", "bob"]
        score, _ = import_parts(manifest.parts, "alice", OrchestrationConfig(bars=4, backend="rules"))
        direct = raw_score(completed, policy=policy)
        for part, spec, raw in zip(score.parts, manifest.parts, direct.parts):
            assert spec.source["run_id"] == fixture["run_id"]
            assert all(isinstance(v, str) for v in spec.source.values())
            mapping = json.loads(spec.source["round_index_map"])
            events = json.loads(spec.source["source_event_map"])
            assert len(spec.notes) == sum(not e["rest"] for e in fixture["events"][policy] if e["voice"] == spec.id)
            assert [n.model_dump() for n in part.notes] == [n.model_dump() for n in raw.notes]
            for i, n in enumerate(part.notes):
                assert n.duration_ticks == 192  # 0.4 quarter-note beats * 480 PPQ
                assert mapping[str(i)] == fixture["run_id"] + "/r" + events[n.source_id].split("/r")[-1]
        assert len(completed.to_dict()["events"][policy]) == 32
    assert completed.to_dict() == fixture


def test_take_exact_bytes_and_fixed_outputs(fixture):
    data = TAKE.read_bytes()
    converted = from_take(data, run_id=fixture["run_id"], data_status="recorded", source_asset="retained.json")
    result = converted.to_dict()
    assert converted.raw_bytes == data
    assert result["raw_source"]["sha256"] == sha256(data).hexdigest()
    assert result["raw_source"]["canonical_json_sha256"] == fixture["raw_source"]["canonical_json_sha256"]
    for key in ("events", "models", "statistics"):
        assert result[key] == fixture[key]
    assert all(
            {k: v for k, v in a.items() if k != "measurement_provenance"} ==
            {k: v for k, v in b.items() if k != "measurement_provenance"}
            for a, b in zip(result["rounds"], fixture["rounds"]))
    # Real local outputs modify both pitch and onset, independently in both voices.
    notes = to_manifest(converted).parts
    for voice, spec in zip(("alice", "bob"), notes):
        active = [e for e in result["events"]["quantum"] if e["voice"] == voice and not e["rest"]]
        assert {e["local_output"] for e in active} == {0, 1}
        for note, event in zip(spec.notes, active):
            assert note.pitch == event["pitch_midi"]
            assert note.onset_beats == event["round"] + event["local_output"] * 0.5


def test_one_local_execution_then_both_voices(monkeypatch):
    from qiskit.providers.basic_provider import BasicSimulator
    from quantum_duet.integration import generate_take
    backend = BasicSimulator()
    calls = []
    original = backend.run

    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(backend, "run", counted)
    run_id = "local-assigned-before-execution"
    raw = generate_take(backend, shots=16, presentation_seed=7,
                        execution_mode="ideal-local-development",
                        asset_dir=ROOT / "components/quantum_duet/src/quantum_duet/data")
    completed = from_take(raw, run_id=run_id, data_status="live", source_asset="retained-live.json")
    for _ in range(2):
        assert len(to_manifest(completed).parts) == 2
        assert len(to_manifest(completed, policy="classical").parts) == 2
    assert len(calls) == 1
    assert completed.to_dict()["statistics"]["total_independent_shots"] == 64
    assert completed.to_dict()["execution"]["backend_run_calls_this_replay"] == 0


def test_rules_arrangement_preserves_raw_and_links_sources(fixture):
    completed = freeze_result(fixture, raw_bytes=TAKE.read_bytes())
    before = completed._json, completed.raw_bytes, completed.canonical_sha256
    arranged = arrange_result(completed).to_dict()
    assert arranged["mode"] == "arranged" and arranged["status"] == "completed"
    assert before == (completed._json, completed.raw_bytes, completed.canonical_sha256)
    for key in ("rounds", "events", "models", "execution", "statistics", "raw_source"):
        assert arranged[key] == fixture[key]
    output = arranged["arranged"]
    assert output["backend_requested"] == output["backend_actual"] == "rules"
    assert output["report"]["audio"]["status"] == "not_requested"
    assert output["report"]["provider_status"] == "disabled"
    assert len(output["lineage"]) == sum(len(p.notes) for p in to_manifest(completed).parts)
    active_ids = {e["event_id"] for e in fixture["events"]["quantum"] if not e["rest"]}
    assert {line["event_id"] for line in output["lineage"]} == active_ids
    assert all(line["round_id"].startswith(fixture["run_id"] + "/r") for line in output["lineage"])
    assert output["raw_result_canonical_json_sha256"] == before[2]
    assert any(p["source"] for p in output["output_parts"])
    assert not arranged["fallback"]["used"]


def silent_fixture(fixture):
    from quantum_duet.music import musical_event
    for row in fixture["rounds"]:
        row["base_token"] = 0
    for policy in ("quantum", "classical"):
        for event in fixture["events"][policy]:
            row = fixture["rounds"][event["round"]]
            event.update(musical_event(0, row[policy][event["voice"]], event["voice"], event["round"]))
    return freeze_result(fixture)


def test_silent_raw_is_usable_arrangement_fails(fixture):
    completed = silent_fixture(fixture)
    assert all(not p.notes for p in raw_score(completed).parts)
    arranged = arrange_result(completed).to_dict()
    assert arranged["status"] == "failed" and arranged["mode"] == "arranged"
    assert arranged["errors"][0]["code"] == "silent_lead"
    assert not arranged["arranged"]["output_parts"]
    assert not arranged["fallback"]["used"]
    assert completed.to_dict()["mode"] == "raw"


def test_arrangement_exception_is_redacted_and_no_fallback(fixture, monkeypatch):
    import orchestrator.pipeline

    def broken(*args, **kwargs):
        raise RuntimeError("secret-token-private-path")

    monkeypatch.setattr(orchestrator.pipeline, "orchestrate", broken)
    arranged = arrange_result(freeze_result(fixture)).to_dict()
    assert arranged["status"] == "failed"
    assert arranged["errors"][0]["code"] == "rules_arrangement_failed"
    assert "secret-token" not in json.dumps(arranged)
    assert not arranged["arranged"]["fallback"]["used"]


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(contract_version="unknown"),
    lambda d: d.update(run_id=""),
    lambda d: d.update(tempo_bpm=float("nan")),
    lambda d: d.update(ppq=0),
    lambda d: d["models"].update(qcbm_parameters=83),
    lambda d: d["execution"].update(data_status="guessed"),
    lambda d: d["execution"].update(backend_run_calls=2),
    lambda d: d["execution"].update(backend_run_calls_this_replay=1),
    lambda d: d["execution"]["experiments"][0].update(name="duet_xy_01"),
    lambda d: d["execution"]["experiments"][0]["counts"].update({"00": 0.5}),
    lambda d: d["statistics"].update(total_independent_shots=5120),
    lambda d: d["statistics"].update(expected_success=0.9),
    lambda d: d["rounds"][0].update(round_id="different/r00"),
    lambda d: d["rounds"][0]["quantum"].update(displayed_ba="01"),
    lambda d: d["rounds"][0]["classical"].update(shared_strategy=[1, 1, 0, 0]),
    lambda d: d["events"]["quantum"][0].update(pitch_midi=75),
    lambda d: d["events"]["quantum"][0].update(onset_beats=1000),
    lambda d: d["events"]["quantum"][0].update(velocity=0),
    lambda d: d["events"]["quantum"].pop(),
    lambda d: d["fallback"].update(used=True),
    lambda d: d.update(mode="arranged"),
])
def test_contradictory_contract_rejected(fixture, mutation):
    mutation(fixture)
    with pytest.raises(ValueError):
        freeze_result(fixture)


def test_snapshot_and_metadata_ownership(fixture):
    original = deepcopy(fixture)
    completed = freeze_result(fixture)
    fixture["events"]["quantum"].clear()
    copy = completed.to_dict()
    copy["models"].clear()
    manifest = to_manifest(completed)
    manifest.parts[0].notes.clear()
    assert completed.to_dict() == original
    with pytest.raises(FrozenInstanceError):
        completed.raw_bytes = b"changed"
    for key in ("run_id", "qcbm_checkpoint_sha256", "raw_source_sha256"):
        with pytest.raises(ValueError, match="Contradictory source"):
            to_manifest(completed, source={key: "wrong"})
    with pytest.raises(ValueError, match="Source metadata"):
        to_manifest(completed, source={"integer": 1})


def test_raw_hash_verification(fixture):
    with pytest.raises(ValueError, match="canonical digest"):
        freeze_result(fixture, raw_bytes=b'{}')
    fixture["models"]["bell_checkpoint_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Checkpoint metadata"):
        freeze_result(fixture, raw_bytes=TAKE.read_bytes())


def test_velocity_cannot_change_from_raw_source(fixture):
    fixture["events"]["quantum"][0]["velocity"] = 81
    with pytest.raises(ValueError, match="Velocity changed"):
        freeze_result(fixture, raw_bytes=TAKE.read_bytes())


def test_changed_local_output_changes_only_its_voice():
    from quantum_duet.music import events_from_outputs
    take = json.loads(TAKE.read_bytes())
    kwargs = dict(run_id="paired-change", data_status="mock", source_asset="mock.json")
    original = to_manifest(from_take(take, **kwargs))
    row = take["rounds"]["quantum"][0]
    row["a"] = 1 - row["a"]
    row["displayed_ba"] = f"{row['b']}{row['a']}"
    row["win"] = (row["a"] ^ row["b"]) == (row["x"] & row["y"])
    take["events"]["quantum"] = events_from_outputs(take["base_melody"]["tokens"],
        [r["a"] for r in take["rounds"]["quantum"]], [r["b"] for r in take["rounds"]["quantum"]])
    changed = to_manifest(from_take(take, **kwargs))
    assert changed.parts[0].notes[0].pitch == original.parts[0].notes[0].pitch + 2
    assert changed.parts[0].notes[0].onset_beats == original.parts[0].notes[0].onset_beats + 0.5
    assert changed.parts[1].notes == original.parts[1].notes


def test_failed_execution_has_no_music_and_cannot_be_replayed(fixture):
    fixture.update(status="failed", rounds=[], events={"quantum": [], "classical": []}, statistics={},
                   errors=[dict(stage="submission", code="rejected", message="Backend rejected request")])
    fixture["execution"].update(job_id=None, backend_run_calls=0, experiments=[])
    failed = freeze_result(fixture)
    with pytest.raises(ValueError, match="completed raw"):
        to_manifest(failed)
    fixture["execution"]["experiments"] = [{"counts": {"00": 1024}}]
    with pytest.raises(ValueError, match="successful counts/events"):
        freeze_result(fixture)


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(run_id="wrong"),
    lambda d: d.update(status="failed"),
    lambda d: d["execution"].update(data_status="live"),
    lambda d: d["events"]["quantum"][0].update(run_id="wrong"),
    lambda d: d["rounds"]["quantum"].pop(),
])
def test_contradictory_raw_take_rejected(mutation):
    take = json.loads(TAKE.read_bytes())
    mutation(take)
    with pytest.raises(ValueError):
        from_take(take, run_id="mock", data_status="recorded", source_asset="retained.json")


def test_four_recorded_requires_asset_and_excludes_melody_shots():
    take = json.loads(TAKE.read_bytes())
    take["execution"].update(mode="four-recorded", circuit_count=4)
    take["execution"]["experiments"].pop()
    take["base_melody"]["generated_now"] = False
    with pytest.raises(ValueError, match="recorded melody asset"):
        from_take(take, run_id="four", data_status="mock", source_asset="mock.json")
    completed = from_take(take, run_id="four", data_status="mock", source_asset="mock.json",
                          recorded_melody_asset="data/recorded_melody.json")
    assert completed.to_dict()["statistics"]["total_independent_shots"] == 4096


def test_cli_raw_arranged_and_existing_output_protection(tmp_path):
    command = [sys.executable, "-m", "quantum_duet.orchestration_adapter", "--result", str(FIXTURE),
               "--arrange", "--out", str(tmp_path / "demo")]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '"backend_submissions": 0' in result.stdout
    raw = json.loads((tmp_path / "demo/raw-result.json").read_bytes())
    arranged = json.loads((tmp_path / "demo/arranged-result.json").read_bytes())
    assert raw["mode"] == "raw" and arranged["mode"] == "arranged"
    midi = mido.MidiFile(tmp_path / "demo/raw.mid")
    assert midi.ticks_per_beat == 480 and len(midi.tracks) == 3
    assert any(m.type == "note_off" and m.time == 192 for track in midi.tracks for m in track)
    assert subprocess.run(command, cwd=ROOT, capture_output=True).returncode != 0
