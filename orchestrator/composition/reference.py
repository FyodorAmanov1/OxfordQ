"""Fixed-grid source playback, kept separate from expressive composition."""
from orchestrator.instruments import profile
from orchestrator.models import Part, NoteEvent
from orchestrator.performance import performance_for
from .models import ComposedScore
from .compiler import validate_score


def raw_reference(request, bank, timeline):
    parts, occurrences = [], []
    for instrument in request.instruments:
        events = [e for e in bank.events if e.source_part == instrument and e.model != "pop909"]
        if not events or not any(e.pitch is not None for e in events):
            raise ValueError("Each instrument needs sounding source material")
        part = Part(id=instrument, instrument=instrument, notes=[], pan=profile(instrument).pan,
                    role="melody" if instrument == request.lead_track else "harmony",
                    source={"source_bank_sha256": bank.digest})
        step = timeline.ppq * (2 if instrument in ("cello", "double_bass", "tuba") else 1)
        for index, tick in enumerate(range(0, timeline.end_tick, step)):
            event = events[index % len(events)]
            occurrence_id = f"raw/{instrument}/{index}"
            duration = min(step, timeline.end_tick - tick)
            slot = {"source_id": event.id, "rest": event.pitch is None, "output_id": None,
                    "onset_tick": tick, "duration_ticks": duration}
            if event.pitch is not None:
                pr = profile(instrument)
                if not pr.low <= event.pitch <= pr.high:
                    raise ValueError("Raw source register outside instrument range")
                note = NoteEvent(id=occurrence_id + "/0", source_id=event.id, phrase_id=occurrence_id,
                    pitch=event.pitch, onset_tick=tick,
                    duration_ticks=min(round(step * .85), timeline.end_tick - tick), velocity=70)
                part.notes.append(note)
                slot["output_id"] = note.id
                slot["duration_ticks"] = note.duration_ticks
            occurrences.append({"id": occurrence_id, "kind": "source", "source_group": event.id,
                                "start_tick": tick, "events": [slot]})
        parts.append(part)
    score = ComposedScore(title="Fixed-grid source reference", parts=parts, lead_track=request.lead_track,
        timeline=timeline.model_copy(deep=True), source_bank_sha256=bank.digest,
        planner="raw", occurrences=occurrences,
        performance={p.id: performance_for(p.instrument) for p in parts})
    for instrument, volume in request.part_volumes.items():
        score.performance[instrument].volume = volume
    validate_score(score, bank, request)
    return score
