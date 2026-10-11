"""Compile plans with octave-only source placement, then validate every occurrence."""
from collections import Counter, defaultdict
from statistics import mean
from bisect import bisect_right

from orchestrator.instruments import profile
from orchestrator.models import NoteEvent, Part
from orchestrator.performance import performance_for
from .models import ComposedScore


def validate_plan(plan, bank, request):
    if plan.source_bank_sha256 != bank.digest or plan.style != request.style:
        raise ValueError("Plan does not match source bank/style")
    if len(plan.timeline.bars) != request.bars:
        raise ValueError("Plan must keep the requested bar count")
    cursor = 0
    for section in plan.sections:
        if section.start_bar != cursor or section.end_bar <= cursor:
            raise ValueError("Sections must cover the score exactly once")
        cursor = section.end_bar
    if cursor != request.bars or not any(s.function == "develop" for s in plan.sections) or plan.sections[-1].function != "return":
        raise ValueError("Require development and thematic return")
    introduced = {o.motif_id for o in plan.motifs if o.target_part == request.lead_track and
                  o.start_tick < plan.timeline.bar_starts[plan.sections[0].end_bar]}
    returned = {o.motif_id for o in plan.motifs if o.target_part == request.lead_track and
                o.start_tick >= plan.timeline.bar_starts[plan.sections[-1].start_bar]}
    if plan.sections[0].function != "introduce" or not introduced.intersection(returned):
        raise ValueError("The lead must return to an introduced source motif")
    motifs = {m.id: m for m in bank.motifs}
    chords = {c.id: c for c in bank.chords}
    ids = [o.id for o in [*plan.motifs, *plan.harmony]]
    if len(ids) != len(set(ids)):
        raise ValueError("Occurrence IDs must be unique")
    for occurrence in plan.motifs:
        motif = motifs.get(occurrence.motif_id)
        if motif is None or occurrence.target_part not in request.instruments:
            raise ValueError("Unknown motif/target part")
        if len(occurrence.steps_ticks) != len(motif.events) or any(n <= 0 for n in occurrence.steps_ticks):
            raise ValueError("Positive rhythmic step required for each source event")
        if occurrence.start_tick + sum(occurrence.steps_ticks) > plan.timeline.end_tick:
            raise ValueError("Motif exceeds timeline")
    for occurrence in plan.harmony:
        if occurrence.chord_id not in chords or len(set(occurrence.target_parts)) != len(occurrence.target_parts):
            raise ValueError("Unknown chord or duplicate harmony targets")
        if any(i not in request.instruments or i == request.lead_track for i in occurrence.target_parts):
            raise ValueError("Harmony requires supplied non-lead targets")
        if occurrence.start_tick + occurrence.span_ticks > plan.timeline.end_tick:
            raise ValueError("Harmony exceeds timeline")


def _place(pitch, instrument, target, previous=None):
    pr = profile(instrument)
    candidates = [p for p in range(pr.low, pr.high + 1) if p % 12 == pitch % 12]
    if not candidates:
        raise ValueError(f"No octave placement in {instrument}")
    return min(candidates, key=lambda p: abs(p - target) + (.25 * abs(p - previous) if previous is not None else 0))


def validate_score(score, bank, request):
    if score.source_bank_sha256 != bank.digest or score.lead_track != request.lead_track:
        raise ValueError("Score source/lead identity mismatch")
    if [p.id for p in score.parts] != request.instruments:
        raise ValueError("Score instrument identity/order mismatch")
    if any(part not in request.instruments for part in score.performance):
        raise ValueError("Unknown instrument in performance envelope")
    sources = {event.id: event for event in bank.events}
    ids = [n.id for part in score.parts for n in part.notes]
    if len(ids) != len(set(ids)):
        raise ValueError("Output occurrence IDs must be unique")
    for part in score.parts:
        if part.instrument != part.id:
            raise ValueError("Composition track instrument mismatch")
        pr = profile(part.instrument)
        capacity, unisons = [], defaultdict(list)
        for note in part.notes:
            source = sources.get(note.source_id)
            if source is None or source.pitch is None or note.pitch % 12 != source.pitch % 12:
                raise ValueError("Output note must preserve a sounding source pitch class")
            if not pr.low <= note.pitch <= pr.high or note.end_tick > score.end_tick:
                raise ValueError("Note violates range/timeline")
            if note.muted or note.transpose != note.pitch - source.pitch:
                raise ValueError("Composition retains sounding occurrences with truthful octave shifts")
            capacity.extend([(note.onset_tick, 1), (note.end_tick, -1)])
            unisons[note.pitch].append(note)
        alive = 0
        for _, delta in sorted(capacity):
            alive += delta
            if alive > pr.polyphony:
                raise ValueError(f"{part.id}: section capacity exceeded")
        for notes in unisons.values():
            notes.sort(key=lambda n: n.onset_tick)
            if any(a.end_tick > b.onset_tick for a, b in zip(notes, notes[1:])):
                raise ValueError("Overlapping unisons would lose occurrence identity in MIDI")
        if any(not 0 <= tick < score.end_tick or not 0 <= value <= 127 for tick, value in part.expression):
            raise ValueError("Invalid expression envelope")
    if not next(p for p in score.parts if p.id == score.lead_track).notes:
        raise ValueError("The composition needs a sounding lead")
    output = {n.id: n for p in score.parts for n in p.notes}
    references = []
    groups = {m.id: m.events for m in bank.motifs}
    chord_groups = {c.id: c.events for c in bank.chords}
    occurrence_ids = [o["id"] for o in score.occurrences]
    if len(set(occurrence_ids)) != len(occurrence_ids):
        raise ValueError("Occurrence lineage IDs must be unique")
    for occurrence in score.occurrences:
        kind, group = occurrence["kind"], occurrence["source_group"]
        expected = groups.get(group) if kind == "motif" else chord_groups.get(group) if kind == "harmony" else [group] if kind == "source" else None
        if expected is None or any(slot["source_id"] not in expected for slot in occurrence["events"]):
            raise ValueError("Occurrence references unknown source group")
        if kind == "motif" and [slot["source_id"] for slot in occurrence["events"]] != expected:
            raise ValueError("Motif occurrence must preserve source ordering and rests")
        for slot in occurrence["events"]:
            event = sources.get(slot["source_id"])
            if event is None or slot["rest"] != (event.pitch is None):
                raise ValueError("Broken rest/source lineage")
            if not occurrence["start_tick"] <= slot["onset_tick"] < score.end_tick or not 0 < slot["duration_ticks"] <= score.end_tick - slot["onset_tick"]:
                raise ValueError("Invalid source/rest occurrence timing")
            if slot["rest"] and slot["output_id"] is not None:
                raise ValueError("A source rest cannot have an output note")
            if not slot["rest"]:
                note = output.get(slot["output_id"])
                if note is None or note.source_id != event.id or note.phrase_id != occurrence["id"]:
                    raise ValueError("Broken occurrence lineage")
                if note.onset_tick < occurrence["start_tick"]:
                    raise ValueError("Output precedes its occurrence")
                if (note.onset_tick, note.duration_ticks) != (slot["onset_tick"], slot["duration_ticks"]):
                    raise ValueError("Occurrence timing differs from its output note")
                references.append(note.id)
    if Counter(references) != Counter(output.keys()):
        raise ValueError("Every output note needs exactly one occurrence reference")


def compile_plan(plan, bank, request, *, planner="local"):
    validate_plan(plan, bank, request)
    source = {e.id: e for e in bank.events}
    motifs = {m.id: m for m in bank.motifs}
    chords = {c.id: c for c in bank.chords}
    parts = {instrument: Part(id=instrument, instrument=instrument, notes=[],
             role="melody" if instrument == request.lead_track else "harmony",
             pan=profile(instrument).pan, source={"source_bank_sha256": bank.digest})
             for instrument in request.instruments}
    lineage, previous = [], {}
    starts = plan.timeline.bar_starts

    def accent(tick):
        bar_index = bisect_right(starts, tick) - 1
        bar = plan.timeline.bars[bar_index]
        offset = tick - starts[bar_index]
        if offset == 0:
            return 5
        boundaries, cursor = [], 0
        for group in bar.groups:
            cursor += group
            boundaries.append(round(cursor * plan.timeline.ppq * 4 / bar.denominator))
        return 3 if offset in boundaries else 0

    def emit(occurrence_id, index, event_id, instrument, tick, duration, target, velocity):
        event = source[event_id]
        pitch = _place(event.pitch, instrument, target, previous.get(instrument))
        previous[instrument] = pitch
        note = NoteEvent(id=f"{occurrence_id}/{index}", source_id=event.id, phrase_id=occurrence_id,
                         pitch=pitch, onset_tick=tick, duration_ticks=max(1, duration),
                         velocity=min(127, velocity + accent(tick)), transpose=pitch - event.pitch)
        parts[instrument].notes.append(note)
        return {"source_id": event.id, "rest": False, "output_id": note.id,
                "onset_tick": tick, "duration_ticks": note.duration_ticks}

    actions = [(o.start_tick, 0, o) for o in plan.motifs] + [(o.start_tick, 1, o) for o in plan.harmony]
    for _, kind, occurrence in sorted(actions, key=lambda item: (item[0], item[1], item[2].id)):
        slots = []
        if kind == 0:
            motif = motifs[occurrence.motif_id]
            tick = occurrence.start_tick
            # Prefer a uniform octave displacement to preserve each motif's contour.
            pitches = [source[e].pitch for e in motif.events if source[e].pitch is not None]
            pr = profile(occurrence.target_part)
            shifts = [shift for shift in range(-120, 121, 12)
                      if pitches and all(pr.low <= pitch + shift <= pr.high for pitch in pitches)]
            shift = min(shifts, key=lambda s: abs(mean(pitches) + s - occurrence.register_target)) if shifts else None
            for index, (event_id, step) in enumerate(zip(motif.events, occurrence.steps_ticks)):
                event = source[event_id]
                if event.pitch is None:
                    slots.append({"source_id": event.id, "rest": True, "output_id": None,
                                  "onset_tick": tick, "duration_ticks": step})
                else:
                    target = event.pitch + shift if shift is not None else occurrence.register_target
                    velocity = round(occurrence.velocity_start + (occurrence.velocity_end - occurrence.velocity_start)
                                     * index / max(1, len(motif.events) - 1))
                    slots.append(emit(occurrence.id, index, event.id, occurrence.target_part,
                                      tick, round(step * occurrence.gate), target, velocity))
                tick += step
        else:
            chord = chords[occurrence.chord_id]
            if occurrence.texture in ("sustained", "pedal"):
                # Establish the chord root in the lowest available supporting voice.
                targets = sorted(occurrence.target_parts, key=lambda i:
                    (i not in ("double_bass", "tuba"), i not in ("cello", "bassoon")))
                for index, instrument in enumerate(targets):
                    event_id = chord.events[index % len(chord.events)]
                    target = occurrence.register_target - (24 if instrument in ("double_bass", "tuba") else 12 if instrument == "cello" else 0)
                    slots.append(emit(occurrence.id, index, event_id, instrument, occurrence.start_tick,
                        round(occurrence.span_ticks * .96), target, occurrence.velocity))
            else:
                pulse = occurrence.pulse_ticks
                for index, tick in enumerate(range(occurrence.start_tick,
                        occurrence.start_tick + occurrence.span_ticks, pulse)):
                    # Bass root plus moving upper chord tones, each retaining its model source.
                    for voice, instrument in enumerate(occurrence.target_parts):
                        bass = instrument in ("double_bass", "tuba")
                        event_id = chord.events[0] if bass else chord.events[(index + voice) % len(chord.events)]
                        target = occurrence.register_target - (24 if bass else 12 if instrument == "cello" else 0)
                        duration = round(min(pulse, occurrence.start_tick + occurrence.span_ticks - tick) * .83)
                        velocity = max(1, occurrence.velocity - (4 if index % 3 else 0))
                        slots.append(emit(occurrence.id, f"{index}/{voice}", event_id, instrument,
                                          tick, duration, target, velocity))
        lineage.append({"id": occurrence.id, "kind": "motif" if kind == 0 else "harmony",
                        "source_group": occurrence.motif_id if kind == 0 else occurrence.chord_id,
                        "start_tick": occurrence.start_tick, "events": slots})
    for part in parts.values():
        part.notes.sort(key=lambda n: (n.onset_tick, n.pitch))
        part.expression = [(start, 65 + (20 if request.bars // 3 <= bar < 2 * request.bars // 3 else 0)
                            + (bar % 4) * 3) for bar, start in enumerate(plan.timeline.bar_starts)]
    score = ComposedScore(title=request.style + " study", parts=list(parts.values()),
        lead_track=request.lead_track, timeline=plan.timeline,
        source_bank_sha256=bank.digest, planner=planner, occurrences=lineage,
        performance={p.id: performance_for(p.instrument) for p in parts.values()})
    for instrument, volume in request.part_volumes.items():
        score.performance[instrument].volume = volume
    validate_score(score, bank, request)
    return score
