import pytest

from orchestrator import OrchestrationConfig, PartSpec, orchestrate
from orchestrator.theory import _diatonic_chords, chord_pcs


@pytest.mark.parametrize("tonality", [
    "C major", "F major", "B- major", "E- major", "A- major",
    "D- major", "G- major", "D minor", "G minor", "C minor", "F minor",
])
def test_diatonic_chords_parse_and_pipeline_runs(tonality):
    symbols = _diatonic_chords(tonality)
    assert len(symbols) == 7
    assert all(chord_pcs(symbol) for symbol in symbols)
    parts = [
        PartSpec(id="theme", instrument="flute", notes=[
            dict(pitch=p, onset_beats=i, duration_beats=0.8)
            for i, p in enumerate([72, 74, 76, 77])]),
        PartSpec(id="bass", instrument="cello", notes=[
            dict(pitch=48, onset_beats=0, duration_beats=4)]),
    ]
    result = orchestrate(parts, "theme", OrchestrationConfig(
        bars=1, backend="rules", key=tonality, render_audio=False))
    assert result.report["lead_preserved"]
    assert not result.report["hard_validation_errors"]


def test_flat_root_spelling_preserved():
    assert "B-" in _diatonic_chords("F major")
    assert chord_pcs("B-") == frozenset({10, 2, 5})
