import json
from pathlib import Path
from unittest.mock import patch

from orchestrator.models import ArrangementPlan, EditProposal
from quantum_duet.orchestration_adapter import freeze_result, arrange_result
from quantum_duet.browser_projection import arrange_browser

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "docs/fixtures/run-result.v1.json").read_bytes()


class EchoProvider:
    """Offline typed model response; never evidence of a live Gemini call."""
    def request(self, schema, payload, feedback):
        if schema is ArrangementPlan:
            return ArrangementPlan.model_validate(payload["baseline_plan"])
        return EditProposal(edits=[])


def test_paired_model_arrangement_preserves_raw_and_lineage():
    frozen = freeze_result(json.loads(RAW))
    before = frozen._json
    with patch("quantum_duet.integration.generate_take", side_effect=AssertionError("Resampled")):
        result = arrange_result(frozen, backend="gemini", provider=EchoProvider()).to_dict()
        bundle = arrange_browser(RAW, backend="gemini", provider=EchoProvider())
    assert result["status"] == "completed"
    assert result["arranged"]["backend_actual"] == "gemini"
    assert all("/arranged/gemini/" in t for t in result["arranged"]["transformation_ids"])
    assert frozen._json == before
    assert bundle["run_result"]["mode"] == "raw"
    assert bundle["playback_projection"]["available"]
    assert all(p["actual_backend"] == "gemini" for p in bundle["playback_projection"]["policies"].values())


def test_missing_gemini_key_keeps_raw_and_does_not_label_rules_as_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    bundle = arrange_browser(RAW, backend="gemini")
    assert bundle["run_result"]["status"] == "completed"
    assert bundle["playback_projection"]["available"] is False
    for policy in bundle["playback_projection"]["policies"].values():
        assert policy["status"] == "failed"
        assert not policy["events"]
        assert policy["actual_backend"] is None
