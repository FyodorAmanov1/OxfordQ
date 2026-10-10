"""Hard invariants and atomic application of bounded model edits."""
from __future__ import annotations

from collections import Counter, defaultdict
from math import floor

from .instruments import profile
from .models import ArrangementPlan, EditProposal, OrchestrationConfig, Score
from .theory import chord_pcs, parse_key


def validate_plan(plan: ArrangementPlan, score: Score, config: OrchestrationConfig) -> list[str]:
    errors = []
    try:
        parse_key(plan.key)
    except Exception as exc:
        errors.append(f"Invalid key: {exc}")
    if config.key and plan.key != str(parse_key(config.key)):
        errors.append("The configured key override must be retained")
    cursor = 0
    for span in plan.chords:
        if span.start_tick != cursor:
            errors.append("Chord spans must be ordered and cover the excerpt without gaps or overlaps")
        cursor = span.start_tick + span.duration_ticks
        try:
            chord_pcs(span.symbol)
        except ValueError as exc:
            errors.append(str(exc))
    if cursor != score.end_tick:
        errors.append("Chord spans must end exactly at the excerpt boundary")
    if config.chords:
        expected = [config.chords[i % len(config.chords)] for i in range(score.bars)]
        if len(plan.chords) != score.bars or any(
            span.symbol != expected[i] or span.start_tick != i * score.ppq * 4 or span.duration_ticks != score.ppq * 4
            for i, span in enumerate(plan.chords)):
            errors.append("The configured chord override must be retained")
    directives = defaultdict(list)
    for directive in plan.directives:
        if directive.track_id not in {p.id for p in score.parts}:
            errors.append(f"Unknown directive track: {directive.track_id}")
            continue
        if directive.end_bar <= directive.start_bar or directive.end_bar > score.bars:
            errors.append(f"{directive.track_id}: invalid directive interval")
        if directive.track_id == score.lead_track:
            if directive.silent or directive.role != "melody" or directive.expression < 1:
                errors.append("The lead must remain active, audible and in the melody role")
        directives[directive.track_id].append(directive)
    for part in score.parts:
        cursor = 0
        for directive in sorted(directives[part.id], key=lambda d: d.start_bar):
            if directive.start_bar != cursor:
                errors.append(f"{part.id}: directives must cover every bar once")
            cursor = directive.end_bar
        if cursor != score.bars:
            errors.append(f"{part.id}: directives do not cover the entire excerpt")
    return errors


def validate_score(score: Score, original: Score, config: OrchestrationConfig) -> list[str]:
    errors = []
    if (score.lead_track, score.ppq, score.bars, score.tempo_bpm, score.window_bars) != (
        original.lead_track, original.ppq, original.bars, original.tempo_bpm, original.window_bars):
        errors.append("Score timing and anchor metadata must not change")
    if [p.id for p in score.parts] != [p.id for p in original.parts]:
        return errors + ["Track identities and order must not change"]
    if sum(profile(p.instrument).family != "drums" for p in score.parts) > 15:
        errors.append("A standard MIDI file supports at most 15 independently controlled pitched parts")
    if sum(profile(p.instrument).family == "drums" for p in score.parts) > 1:
        errors.append("Combine unpitched percussion into a single part")
    for part in score.parts:
        source_part = original.part(part.id)
        if part.instrument != source_part.instrument:
            errors.append(f"{part.id}: instrument identity must not change")
        source = {n.id: n for n in source_part.notes}
        if Counter(n.id for n in part.notes) != Counter(source.keys()):
            errors.append(f"{part.id}: notes cannot be invented, duplicated or deleted; use muting")
            continue
        pr = profile(part.instrument)
        phrases = defaultdict(list)
        active_events = []
        lead_offsets = set()
        for n in part.notes:
            ref = source[n.id]
            phrases[ref.phrase_id].append((n, ref))
            if n.source_id != ref.source_id or n.phrase_id != ref.phrase_id:
                errors.append(f"{n.id}: broken source reference")
            if n.end_tick > score.end_tick:
                errors.append(f"{n.id}: note exceeds excerpt boundary")
            if abs(n.transpose) > 48 or abs(n.phrase_shift) > score.ppq * 4:
                errors.append(f"{n.id}: phrase transform exceeds the permitted bounds")
            if n.onset_tick != ref.onset_tick + n.phrase_shift:
                errors.append(f"{n.id}: only whole-phrase timing shifts are allowed")
            if abs(n.pitch - (ref.pitch + n.transpose)) > 2:
                errors.append(f"{n.id}: an individual pitch repair may move at most two semitones")
            if not 0.5 * ref.duration_ticks <= n.duration_ticks <= 2 * ref.duration_ticks:
                errors.append(f"{n.id}: duration repair must stay within half to twice the original")
            if part.id == score.lead_track:
                lead_offsets.add(n.transpose)
                if n.muted or n.phrase_shift or n.onset_tick != ref.onset_tick or n.duration_ticks != ref.duration_ticks or n.pitch != ref.pitch + n.transpose or n.transpose % 12:
                    errors.append(f"{n.id}: lead melody pitches and timing must be preserved, except a uniform octave shift")
            if not n.muted:
                if not pr.low <= n.pitch <= pr.high:
                    errors.append(f"{n.id}: pitch {n.pitch} is outside {part.instrument} range {pr.low}..{pr.high}")
                active_events.extend([(n.onset_tick, 1), (n.end_tick, -1)])
        if part.id == score.lead_track and len(lead_offsets) != 1:
            errors.append("The lead may only receive one uniform octave shift across the excerpt")
        for phrase_id, pairs in phrases.items():
            if len({n.transpose for n, _ in pairs}) > 1 or len({n.phrase_shift for n, _ in pairs}) > 1:
                errors.append(f"{phrase_id}: whole-phrase transforms must affect every source note equally")
            if part.id != score.lead_track:
                changes = sum(n.pitch != ref.pitch + n.transpose or n.duration_ticks != ref.duration_ticks for n, ref in pairs)
                if changes > floor(len(pairs) * config.edit_budget + 1e-9):
                    errors.append(f"{phrase_id}: individual edits exceed the {config.edit_budget:.0%} budget")
        count = 0
        for _, delta in sorted(active_events):
            count += delta
            if count > pr.polyphony:
                errors.append(f"{part.id}: exceeds configured section polyphony {pr.polyphony}")
                break
        if any(tick < 0 or tick > score.end_tick or not 0 <= value <= 127 for tick, value in part.expression):
            errors.append(f"{part.id}: invalid expression controller envelope")
    return errors


def apply_directives(score: Score, plan: ArrangementPlan) -> Score:
    result = score.model_copy(deep=True)
    for part in result.parts:
        instructions = sorted((d for d in plan.directives if d.track_id == part.id), key=lambda d: d.start_bar)
        for directive in instructions:
            left, right = directive.start_bar * score.ppq * 4, directive.end_bar * score.ppq * 4
            part.expression.append((left, directive.expression))
            for n in part.notes:
                if left <= n.onset_tick < right:
                    n.velocity = directive.velocity
                    if directive.silent:
                        n.muted = True
            part.role = directive.role
        if instructions:
            part.pan = instructions[0].pan
        part.expression = sorted(set(part.expression))
    return result


def apply_proposal(score: Score, proposal: EditProposal, original: Score, config: OrchestrationConfig,
                   window_start: int, window_end: int) -> Score:
    """Validate the complete candidate; callers retain their existing score on failure."""
    result = score.model_copy(deep=True)
    original_notes = {n.id: (p.id, n) for p in original.parts for n in p.notes}
    notes = {n.id: (p.id, n) for p in result.parts for n in p.notes}
    phrases = defaultdict(list)
    for p in result.parts:
        for n in p.notes:
            phrases[n.phrase_id].append((p.id, n))
    allowed = {
        "transpose_phrase": {"semitones"}, "shift_phrase": {"ticks"}, "mute_phrase": set(),
        "mute_note": set(), "edit_note": {"pitch", "duration_ticks"}, "set_velocity": {"value"},
        "set_pan": {"value"},
    }
    for edit in proposal.edits:
        payload = {name for name in ("semitones", "ticks", "pitch", "duration_ticks", "value") if getattr(edit, name) is not None}
        if payload - allowed[edit.op]:
            raise ValueError(f"{edit.op}: unexpected payload fields {sorted(payload - allowed[edit.op])}")
        if edit.op in {"transpose_phrase", "shift_phrase", "set_velocity", "set_pan"} and payload != allowed[edit.op]:
            raise ValueError(f"{edit.op}: required payload is missing")
        if edit.op == "edit_note" and not payload:
            raise ValueError("edit_note requires a pitch or duration_ticks")
        if edit.op in {"set_pan", "set_velocity"}:
            part = result.part(edit.target)
            if edit.op == "set_pan":
                part.pan = edit.value
                continue
            if edit.value < 1:
                raise ValueError("Use explicit muting; note velocity must be at least 1")
            affected = [(part.id, n) for n in part.notes if window_start <= original_notes[n.id][1].onset_tick < window_end]
        elif edit.op.endswith("_phrase"):
            if edit.target not in phrases:
                raise ValueError(f"Unknown phrase: {edit.target}")
            affected = phrases[edit.target]
        else:
            if edit.target not in notes:
                raise ValueError(f"Unknown note: {edit.target}")
            affected = [notes[edit.target]]
        for part_id, n in affected:
            ref = original_notes[n.id][1]
            if not window_start <= ref.onset_tick < window_end:
                raise ValueError(f"{n.id}: edit lies outside this window; preceding context is read-only")
            if part_id == score.lead_track and edit.op != "set_velocity":
                raise ValueError("The lead is protected; model edits may only change its dynamics or pan")
            if edit.op == "transpose_phrase":
                n.pitch += edit.semitones
                n.transpose += edit.semitones
            elif edit.op == "shift_phrase":
                if n.onset_tick + edit.ticks < window_start:
                    raise ValueError("A phrase shift cannot move notes into the preceding read-only context")
                n.onset_tick += edit.ticks
                n.phrase_shift += edit.ticks
            elif edit.op in {"mute_phrase", "mute_note"}:
                n.muted = True
            elif edit.op == "edit_note":
                if edit.pitch is not None:
                    n.pitch = edit.pitch
                if edit.duration_ticks is not None:
                    n.duration_ticks = edit.duration_ticks
            elif edit.op == "set_velocity":
                n.velocity = edit.value
    errors = validate_score(result, original, config)
    if errors:
        raise ValueError("; ".join(errors[:12]))
    return result
