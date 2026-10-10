"""Local orchestration: register placement, restrained repairs, and dynamics."""
from collections import defaultdict
from math import floor

from .instruments import profile
from .models import ArrangementPlan, OrchestrationConfig, Score
from .theory import pcs_at
from .validation import apply_directives, validate_score


def arrange_baseline(original: Score, plan: ArrangementPlan, config: OrchestrationConfig) -> Score:
    result = apply_directives(original, plan)
    for part in result.parts:
        pr = profile(part.instrument)
        if part.id == result.lead_track:
            offsets = [shift for shift in range(-48, 49, 12)
                       if all(pr.low <= n.pitch + shift <= pr.high for n in part.notes)]
            if not offsets:
                raise ValueError(f"{part.id}: lead cannot fit {part.instrument} with one uniform octave shift; choose a suitable lead instrument or regenerate")
            offset = min(offsets, key=abs)
            for n in part.notes:
                n.pitch += offset
                n.transpose = offset
        elif pr.family != "drums":
            phrases = defaultdict(list)
            for n in part.notes:
                phrases[n.phrase_id].append(n)
            for notes in phrases.values():
                active = [n for n in notes if not n.muted]
                if not active:
                    continue
                offsets = [shift for shift in range(-24, 25)
                           if all(pr.low <= n.pitch + shift <= pr.high for n in active)
                           and all(0 <= n.pitch + shift <= 127 for n in notes)]
                if not offsets:
                    for n in notes:
                        n.muted = True
                    continue
                def placement(shift):
                    consonance = sum(n.duration_ticks for n in active if (n.pitch + shift) % 12 in pcs_at(plan, n.onset_tick))
                    return consonance - abs(shift) * result.ppq * 0.015
                offset = max(offsets, key=placement)
                for n in notes:
                    n.pitch += offset
                    n.transpose = offset
                budget = floor(len(notes) * config.edit_budget + 1e-9)
                repairs = []
                for n in active:
                    if n.duration_ticks < result.ppq or n.onset_tick % result.ppq:
                        continue  # allow weak-beat and short decorative notes
                    pcs = pcs_at(plan, n.onset_tick)
                    if n.pitch % 12 in pcs:
                        continue
                    candidates = [pitch for pitch in range(max(pr.low, n.pitch - 2), min(pr.high, n.pitch + 2) + 1) if pitch % 12 in pcs]
                    if candidates:
                        chosen = min(candidates, key=lambda pitch: abs(pitch - n.pitch))
                        repairs.append((n.duration_ticks, n, chosen))
                for _, n, pitch in sorted(repairs, key=lambda item: item[0], reverse=True)[:budget]:
                    n.pitch = pitch
        # Resolve section capacity by muting quiet overlaps, never by dropping IDs.
        if part.id != result.lead_track:
            accepted = []
            for n in sorted((n for n in part.notes if not n.muted), key=lambda n: (n.onset_tick, -n.velocity)):
                overlapping = [a for a in accepted if a.end_tick > n.onset_tick]
                if len(overlapping) >= pr.polyphony:
                    n.muted = True
                elif not pr.low <= n.pitch <= pr.high:
                    n.muted = True
                else:
                    accepted.append(n)
    errors = validate_score(result, original, config)
    if errors:
        raise ValueError("Baseline cannot produce a valid arrangement: " + "; ".join(errors[:12]))
    return result
