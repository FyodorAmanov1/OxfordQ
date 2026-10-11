import json

import pytest

from orchestrator import GenerationJob, GenerationRegistry
from orchestrator.generation import GenerationRequest
from orchestrator.instruments import PROFILES
from quantum_models import QCBMInstrumentGenerator
from quantum_models.orchestra import main


@pytest.mark.parametrize("instrument", list(PROFILES))
def test_instrument_decoder_is_reproducible_and_in_range(instrument):
    pr = PROFILES[instrument]
    request = GenerationRequest(part_id="part", instrument=instrument, bars=4, tempo_bpm=96,
        pitch_low=pr.low, pitch_high=pr.high, max_polyphony=pr.polyphony, seed=42)
    model = QCBMInstrumentGenerator(instrument)
    output = model.generate(request)
    assert output == model.generate(request)
    assert output.notes and all(pr.low <= n.pitch <= pr.high for n in output.notes)
    assert all(n.onset_beats + n.duration_beats <= 16 for n in output.notes)
    assert output.source["backend_submissions"] == "0"
    tokens = json.loads(output.source["raw_token_sequence"])
    links = json.loads(output.source["decoded_token_map"])
    assert [tokens[link["token_index"]] for link in links] == [link["token"] for link in links]
    assert len(links) == len(output.notes)


def test_shared_checkpoint_with_distinct_decoders():
    registry = GenerationRegistry()
    for instrument in ["flute", "cello"]:
        registry.register(instrument, QCBMInstrumentGenerator(instrument), instruments=[instrument])
    manifest = registry.generate_parts(
        [GenerationJob(id=i, instrument=i, seed=42) for i in ["flute", "cello"]], "flute", bars=4)
    flute, cello = manifest.parts
    assert flute.source["checkpoint_payload_sha256"] == cello.source["checkpoint_payload_sha256"]
    assert flute.source["decoder_instrument"] != cello.source["decoder_instrument"]
    assert flute.notes[0].pitch != cello.notes[0].pitch
    assert flute.notes[0].duration_beats != cello.notes[0].duration_beats


def test_complete_model_orchestra_cli(tmp_path):
    assert main(["--bars", "4", "--no-audio", "--out", str(tmp_path)]) == 0
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["lead_preserved"]
    assert report["provider_status"] == "disabled"
    assert len(report["sources"]) == 5
    assert report["quantum_harmony"]["source"]["checkpoint_payload_sha256"]
    assert (tmp_path / "generated_parts.json").is_file()
