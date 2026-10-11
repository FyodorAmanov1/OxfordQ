"""Harmonic analysis, a transparent baseline, and diagnostic musical metrics."""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from itertools import combinations
from statistics import mean

from music21 import chord, harmony, key as m21key, note as m21note, stream

from .instruments import profile
from .models import ArrangementPlan, ChordSpan, OrchestrationConfig, Score, TrackDirective


def parse_key(value: str) -> m21key.Key:
    words = value.strip().split()
    if len(words) == 1:
        return m21key.Key(words[0])
    if len(words) == 2 and words[1].lower() in {"major", "minor"}:
        return m21key.Key(words[0], words[1].lower())
    raise ValueError("Key must be a tonic and optional mode, e.g. 'C major' or 'A minor'")


@lru_cache(maxsize=512)
def chord_pcs(symbol: str) -> frozenset[int]:
    try:
        cs = harmony.ChordSymbol(symbol)
        pcs = frozenset(p.pitchClass for p in cs.pitches)
    except Exception as exc:
        raise ValueError(f"Invalid chord symbol {symbol!r}: {exc}") from exc
    if not pcs:
        raise ValueError(f"Empty chord symbol: {symbol!r}")
    return pcs


def pcs_at(plan: ArrangementPlan, tick: int) -> frozenset[int]:
    for span in plan.chords:
        if span.start_tick <= tick < span.start_tick + span.duration_ticks:
            return chord_pcs(span.symbol)
    return frozenset()


def infer_key(score: Score, override: str | None = None) -> str:
    if override:
        return str(parse_key(override))
    melody = stream.Stream()
    for event in score.part(score.lead_track).notes:
        n = m21note.Note(event.pitch)
        n.duration.quarterLength = event.duration_ticks / score.ppq
        melody.insert(event.onset_tick / score.ppq, n)
    try:
        result = melody.analyze("key")
    except Exception:
        result = m21key.Key(m21note.Note(score.part(score.lead_track).notes[-1].pitch).pitch.name)
    return str(result)


def _diatonic_chords(tonality: str) -> list[str]:
    k = parse_key(tonality)
    scale = k.getScale()
    result = []
    for degree in range(1, 8):
        triad = chord.Chord([scale.pitchFromDegree(d) for d in (degree, degree + 2, degree + 4)])
        suffix = {"major": "", "minor": "m", "diminished": "dim", "augmented": "+"}[triad.quality]
        # music21 uses '-' for flats in chord roots; converting to 'b' makes
        # symbols such as Bb parse as a B chord with an invalid suffix.
        result.append(triad.root().name + suffix)
    return result


def baseline_plan(score: Score, config: OrchestrationConfig) -> ArrangementPlan:
    tonality = infer_key(score, config.key)
    symbols = _diatonic_chords(tonality)
    spans = []
    previous = frozenset()
    lead = score.part(score.lead_track)
    bar_ticks = score.ppq * 4
    for bar in range(score.bars):
        left, right = bar * bar_ticks, (bar + 1) * bar_ticks
        if config.chords:
            symbol = config.chords[bar % len(config.chords)]
            chord_pcs(symbol)
        else:
            weights = defaultdict(float)
            for event in lead.notes:
                overlap = max(0, min(right, event.end_tick) - max(left, event.onset_tick))
                accent = 1.4 if event.onset_tick % bar_ticks in {0, 2 * score.ppq} else 1.0
                weights[event.pitch % 12] += overlap * accent
            def preference(symbol):
                pcs = chord_pcs(symbol)
                coverage = sum(weight for pc, weight in weights.items() if pc in pcs)
                continuity = len(pcs & previous) * score.ppq * 0.04
                return coverage + continuity
            symbol = max(symbols, key=preference)
        previous = chord_pcs(symbol)
        spans.append(ChordSpan(start_tick=left, duration_ticks=bar_ticks, symbol=symbol))
    directives = []
    for part in score.parts:
        pr = profile(part.instrument)
        for start in range(0, score.bars, config.window_bars):
            end = min(score.bars, start + config.window_bars)
            fraction = (start + end) / (2 * score.bars)
            arc = 0.78 + 0.25 * fraction
            lead_part = part.id == score.lead_track
            base = 94 if lead_part else (48 if pr.family == "brass" else 61)
            directives.append(TrackDirective(
                track_id=part.id, start_bar=start, end_bar=end, role=part.role,
                silent=(not lead_part and pr.family == "brass" and start == 0 and score.bars >= 8),
                velocity=max(1, min(127, round(base * arc))),
                expression=min(120, round(88 + 24 * fraction)), pan=part.pan))
    return ArrangementPlan(key=tonality, chords=spans, directives=directives,
                           rationale="Lead-weighted diatonic harmony with section dynamics and a restrained brass entrance.")


def _ornaments(part, ppq: int) -> set[str]:
    notes = sorted((n for n in part.notes if not n.muted), key=lambda n: (n.onset_tick, n.pitch))
    result = set()
    for i in range(1, len(notes) - 1):
        prev, current, following = notes[i - 1:i + 2]
        if current.duration_ticks > ppq:
            continue
        before, after = current.pitch - prev.pitch, following.pitch - current.pitch
        neighbour = prev.pitch == following.pitch and 0 < abs(before) <= 2
        passing = 0 < abs(before) <= 2 and 0 < abs(after) <= 2 and before * after > 0
        if prev.end_tick >= current.onset_tick - ppq // 4 and following.onset_tick <= current.end_tick + ppq // 4:
            if neighbour or passing:
                result.add(current.id)
    return result


def musical_metrics(score: Score, plan: ArrangementPlan, original: Score) -> dict:
    """Heuristics for comparisons, not an objective judgement of musical quality."""
    chord_weight = matched_weight = 0.0
    retained = total_accompaniment = edited = 0
    voice_movements = []
    total_velocity = []
    original_map = {n.id: n for p in original.parts for n in p.notes}
    timeline = defaultdict(list)
    for part in score.parts:
        pr = profile(part.instrument)
        ornament_ids = _ornaments(part, score.ppq)
        active = sorted((n for n in part.notes if not n.muted), key=lambda n: (n.onset_tick, n.pitch))
        if pr.family != "drums" and all(a.end_tick <= b.onset_tick for a, b in zip(active, active[1:])):
            # A section capable of divisi may still carry one melodic line.
            voice_movements.extend(abs(b.pitch - a.pitch) for a, b in zip(active, active[1:]))
        for n in part.notes:
            source = original_map[n.id]
            if part.id != score.lead_track:
                total_accompaniment += 1
                retained += not n.muted
            edited += n.pitch != source.pitch + n.transpose or n.duration_ticks != source.duration_ticks
            if n.muted:
                continue
            timeline[n.onset_tick].append((True, n.id, n.pitch, pr.family == "drums"))
            timeline[n.end_tick].append((False, n.id, n.pitch, pr.family == "drums"))
            if part.id != score.lead_track:
                total_velocity.append(n.velocity)
            if pr.family == "drums":
                continue
            for span in plan.chords:
                duration = max(0, min(n.end_tick, span.start_tick + span.duration_ticks) - max(n.onset_tick, span.start_tick))
                if duration:
                    weight = duration * (1.4 if n.onset_tick % (score.ppq * 4) in {0, 2 * score.ppq} else 1)
                    chord_weight += weight
                    if n.pitch % 12 in chord_pcs(span.symbol) or n.id in ornament_ids:
                        matched_weight += weight
    active = {}
    maximum = 0
    density = rough = pair_duration = 0.0
    times = sorted(set(timeline) | {0, score.end_tick})
    for tick, following in zip(times, times[1:]):
        for on, note_id, pitch, drum in sorted(timeline[tick], key=lambda x: x[0]):
            if on:
                active[note_id] = (pitch, drum)
            else:
                active.pop(note_id, None)
        duration = following - tick
        maximum = max(maximum, len(active))
        density += len(active) * duration
        pitches = [p for p, drum in active.values() if not drum]
        for a, b in combinations(pitches, 2):
            pair_duration += duration
            interval = abs(a - b) % 12
            if interval in {1, 6, 11}:
                rough += duration * (1.5 if min(a, b) < 48 else 1.0)
    fit = matched_weight / chord_weight if chord_weight else 1.0
    retention = retained / total_accompaniment if total_accompaniment else 1.0
    movement = mean(voice_movements) if voice_movements else 0.0
    smoothness = max(0.0, 1 - movement / 12)
    roughness = min(1.0, rough / pair_duration) if pair_duration else 0.0
    edit_fraction = edited / max(1, len(original_map))
    lead_velocity = mean(n.velocity for n in score.part(score.lead_track).notes if not n.muted)
    accompaniment_velocity = mean(total_velocity) if total_velocity else 0
    balance = min(1.0, lead_velocity / max(1, accompaniment_velocity * 1.3))
    quality = 0.40 * fit + 0.15 * smoothness + 0.20 * retention + 0.15 * balance + 0.10 * (1-roughness) - 0.20 * edit_fraction
    return {
        "heuristic_score": round(quality, 5), "harmonic_fit_with_ornaments": round(fit, 5),
        "accompaniment_note_retention": round(retention, 5), "individual_edit_fraction": round(edit_fraction, 5),
        "mean_monophonic_motion_semitones": round(movement, 3), "rough_interval_ratio": round(roughness, 5),
        "mean_simultaneous_notes": round(density / max(1, score.end_tick), 3),
        "max_simultaneous_notes": maximum, "velocity_balance_proxy": round(balance, 5),
        "interpretation": "Symbolic heuristics; velocity is not measured loudness. Confirm quality by listening.",
    }


def musical_warnings(score: Score, original: Score) -> list[str]:
    warnings = []
    for part in score.parts:
        origin = original.part(part.id)
        total = len(origin.notes)
        alive = sorted((n for n in part.notes if not n.muted), key=lambda n: n.onset_tick)
        if total and len(alive) / total < 0.5:
            warnings.append(f"{part.id}: {total-len(alive)}/{total} notes muted; review loss of source material")
        if profile(part.instrument).family == "drums":
            continue  # Unpitched MIDI numbers identify drum sounds, not melodic intervals.
        boundaries = range(score.window_bars * score.ppq * 4, score.end_tick, score.window_bars * score.ppq * 4)
        for boundary in boundaries:
            before = [n for n in alive if n.onset_tick < boundary]
            after = [n for n in alive if n.onset_tick >= boundary]
            if before and after and abs(after[0].pitch - before[-1].pitch) > 12:
                warnings.append(f"{part.id}: leap over an octave at bar {boundary // (score.ppq*4)+1}")
    return warnings
