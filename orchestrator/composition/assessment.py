"""Descriptive musical diagnostics. These numbers do not measure beauty."""
from collections import Counter


def assess(score, plan=None):
    parts = {}
    for part in score.parts:
        notes = sorted(part.notes, key=lambda n: n.onset_tick)
        pitches = [n.pitch for n in notes]
        cursor, silence = 0, 0
        for note in notes:
            silence += max(0, note.onset_tick - cursor)
            cursor = max(cursor, note.end_tick)
        silence += score.end_tick - cursor
        parts[part.id] = {
            "notes": len(notes), "pitch_min": min(pitches) if pitches else None,
            "pitch_max": max(pitches) if pitches else None,
            "register_span_semitones": max(pitches) - min(pitches) if pitches else 0,
            "duration_classes_ticks": sorted({n.duration_ticks for n in notes}),
            "velocity_range": [min(n.velocity for n in notes), max(n.velocity for n in notes)] if notes else [],
            "silence_fraction": round(silence / score.end_tick, 4),
            "expression_values": sorted({value for _, value in part.expression}),
        }
    pitches = [n.pitch for p in score.parts for n in p.notes]
    motif_counts = Counter(o["source_group"] for o in score.occurrences if o["kind"] == "motif")
    return {"meaning": "Descriptive structure, not a musical-quality score",
            "seconds": round(score.timeline.seconds_at(score.end_tick), 3),
            "ensemble_span_semitones": max(pitches) - min(pitches),
            "metres": sorted({f"{b.numerator}/{b.denominator}" for b in score.timeline.bars}),
            "tempo_range_bpm": [min(t.bpm for t in score.timeline.tempos), max(t.bpm for t in score.timeline.tempos)],
            "repeated_motif_occurrences": {key: count for key, count in motif_counts.items() if count > 1},
            "textures": sorted({o.texture for o in plan.harmony}) if plan else [],
            "sections": [s.model_dump() for s in plan.sections] if plan else [], "parts": parts}
