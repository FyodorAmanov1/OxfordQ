from orchestrator import orchestrate


def test_register_placement_avoids_feasible_boundary_octave_jump():
    result = orchestrate([
        {"id": "lead", "instrument": "flute", "notes": [
            {"pitch": 72, "onset_beats": 0, "duration_beats": .5},
            {"pitch": 72, "onset_beats": 16, "duration_beats": .5}]},
        {"id": "strings", "instrument": "violin_1", "notes": [
            {"pitch": 79, "onset_beats": 0, "duration_beats": .5},
            {"pitch": 52, "onset_beats": 16, "duration_beats": .5}]},
    ], "lead", {"bars": 8, "backend": "rules", "key": "C major",
                 "chords": ["C"], "render_audio": False})
    a, b = result.score.part("strings").notes
    assert abs(b.pitch - a.pitch) <= 12
    assert result.report["hard_validation_errors"] == []
    assert result.report["warnings"] == []


def test_drum_sound_changes_do_not_trigger_melodic_leap_warning():
    result = orchestrate([
        {"id": "lead", "instrument": "flute", "notes": [
            {"pitch": 72, "onset_beats": 0, "duration_beats": .5}]},
        {"id": "drums", "instrument": "percussion", "notes": [
            {"pitch": 36, "onset_beats": 0, "duration_beats": .5},
            {"pitch": 51, "onset_beats": 16, "duration_beats": .5}]},
    ], "lead", {"bars": 8, "backend": "rules", "key": "C major",
                 "chords": ["C"], "render_audio": False})
    assert result.report["warnings"] == []


def test_monophonic_section_motion_is_measured_despite_divisi_capacity():
    result = orchestrate([
        {"id": "lead", "instrument": "flute", "notes": [
            {"pitch": 72, "onset_beats": 0, "duration_beats": .5},
            {"pitch": 79, "onset_beats": 1, "duration_beats": .5}]},
    ], "lead", {"bars": 1, "backend": "rules", "key": "C major",
                 "chords": ["C"], "render_audio": False})
    assert result.report["metrics"]["original"]["mean_monophonic_motion_semitones"] == 7
