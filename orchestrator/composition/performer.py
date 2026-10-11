"""Score-conditioned performance; logical notes and generator lineage stay immutable."""
from bisect import bisect_right
import hashlib
import math
import random
from typing import Literal, Protocol
from pydantic import Field, model_validator
from orchestrator.models import Schema
from orchestrator.instruments import profile
from .models import MusicalTimeline, TempoEvent, PhraseMark


class PlayedNote(Schema):
    note_id: str
    source_id: str
    part_id: str
    phrase_id: str
    pitch: int = Field(ge=0, le=127)
    onset_tick: int = Field(ge=0)
    duration_ticks: int = Field(gt=0)
    velocity: int = Field(ge=1, le=127)
    articulation: Literal["sustained", "connected", "detached", "accented", "pizzicato"]


class Control(Schema):
    tick: int = Field(ge=0)
    controller: Literal[11, 64]
    value: int = Field(ge=0, le=127)


class PerformancePlan(Schema):
    schema_version: Literal["qm.performance.v1"] = "qm.performance.v1"
    score_sha256: str
    source_bank_sha256: str
    adapter: str
    seed: int
    strength: float = Field(ge=0, le=1, allow_inf_nan=False)
    timeline: MusicalTimeline
    notes: list[PlayedNote]
    controls: dict[str, list[Control]]
    phrases: list[PhraseMark]
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def timing_valid(self):
        if len({n.note_id for n in self.notes}) != len(self.notes):
            raise ValueError("Performance note IDs must be unique")
        if any(n.onset_tick + n.duration_ticks > self.timeline.end_tick for n in self.notes):
            raise ValueError("Performance exceeds the musical timeline")
        if any(c.tick > self.timeline.end_tick for controls in self.controls.values() for c in controls):
            raise ValueError("Control exceeds the musical timeline")
        for phrase in self.phrases:
            if not phrase.start_tick <= phrase.peak_tick < phrase.end_tick <= self.timeline.end_tick:
                raise ValueError("Invalid performance phrase")
        return self


class PerformanceAdapter(Protocol):
    def perform(self, score, *, style: str, seed: int, strength: float) -> PerformancePlan: ...


def score_digest(score):
    return hashlib.sha256(score.model_dump_json().encode("utf-8")).hexdigest()


def default_phrases(score):
    marks = []
    starts = score.timeline.bar_starts + [score.end_tick]
    for part in score.parts:
        for index in range(0, len(starts) - 1, 4):
            end = starts[min(index + 4, len(starts) - 1)]
            start = starts[index]
            marks.append(PhraseMark(id=f"phrase/{part.id}/{index}", part_id=part.id,
                start_tick=start, end_tick=end, peak_tick=start + round((end-start)*.65),
                function="arrival" if end == score.end_tick else "answer" if index % 8 else "question"))
    return marks


def _arc(phrase, tick):
    if tick <= phrase.peak_tick:
        phase = (tick - phrase.start_tick) / max(1, phrase.peak_tick - phrase.start_tick)
        return math.sin(max(0, phase) * math.pi / 2)
    phase = (tick - phrase.peak_tick) / max(1, phrase.end_tick - phrase.peak_tick)
    return max(0, math.cos(phase * math.pi / 2))


class RulePerformer:
    """Subtle phrase-correlated shaping, not an independently trained ML performer."""
    def perform(self, score, *, style="mozart", seed=42, strength=.6):
        if not math.isfinite(strength) or not 0 <= strength <= 1:
            raise ValueError("Expression strength must be finite and from zero to one")
        rng = random.Random(seed)
        phrases = score.phrases or default_phrases(score)
        by_part = {part.id: sorted([p for p in phrases if p.part_id == part.id], key=lambda p: p.start_tick)
                   for part in score.parts}
        for part in score.parts:
            if not by_part[part.id]:
                raise ValueError("Each part needs performance phrases")
        def phrase_at(part_id, tick):
            candidates = by_part[part_id]
            return candidates[max(0, bisect_right([p.start_tick for p in candidates], tick) - 1)]
        base = score.timeline
        tempo_ticks = [t.tick for t in base.tempos]
        def bpm_at(tick):
            return base.tempos[bisect_right(tempo_ticks, tick) - 1].bpm
        amount = {"bach": .02, "mozart": .04, "debussy": .08, "rachmaninoff": .075}.get(style, .04)
        tempos = []
        budget = max(0,2000-len(tempo_ticks))
        grid = max(base.ppq // 4, math.ceil(base.end_tick / max(1,budget)))
        extra = set(range(0,base.end_tick,grid)) if budget else set()
        for tick in sorted(extra | set(tempo_ticks)):
            phrase = phrase_at(score.lead_track, tick)
            progress = (tick - phrase.start_tick) / max(1, phrase.end_tick - phrase.start_tick)
            departure = .25 * _arc(phrase, tick) - max(0, (progress - .72) / .28)
            bpm = min(400,bpm_at(tick) * (1 + amount * strength * departure))
            tempos.append(TempoEvent(tick=tick, bpm=round(bpm, 5)))
        timeline = MusicalTimeline(ppq=base.ppq,bars=base.bars,tempos=tempos)
        notes, controls = [], {}
        for part in score.parts:
            family = profile(part.instrument).family
            playing = sorted([n for n in part.notes if not n.muted], key=lambda n: (n.onset_tick, n.pitch))
            played = []
            drift = 0.0
            onset_ticks = sorted({n.onset_tick for n in playing})
            onset_offsets = {}
            for index, note in enumerate(playing):
                phrase = phrase_at(part.id, note.onset_tick)
                arc = _arc(phrase, note.onset_tick)
                nxt = playing[index+1] if index+1 < len(playing) else None
                gap = nxt.onset_tick - note.end_tick if nxt else score.end_tick - note.end_tick
                connected = (phrase.articulation == "connected" and nxt is not None
                             and nxt.onset_tick < phrase.end_tick and gap < base.ppq * .4)
                art = "connected" if connected else "sustained"
                if phrase.articulation == "pizzicato" and family == "strings":
                    art = "pizzicato"
                elif phrase.articulation == "detached" or (style == "mozart" and note.duration_ticks < base.ppq*.65):
                    art = "detached"
                elif art=="sustained" and note.onset_tick in base.bar_starts and arc>.7:
                    art = "accented"
                # Structural attacks stay aligned; other deviations are correlated, bounded.
                structural = note.onset_tick in base.bar_starts or note.onset_tick == phrase.start_tick
                drift = .65 * drift + .35 * rng.uniform(-.012, .012)
                jitter = 0 if structural else round(drift * strength * base.ppq * bpm_at(note.onset_tick) / 60)
                onset = max(0, min(score.end_tick - 1, note.onset_tick + jitter))
                if note.onset_tick not in onset_offsets:
                    position = bisect_right(onset_ticks,note.onset_tick)-1
                    before = onset_ticks[position-1] if position else -1
                    after = onset_ticks[position+1] if position+1<len(onset_ticks) else score.end_tick
                    lower = note.onset_tick-max(0,(note.onset_tick-before-1)//2)
                    upper = note.onset_tick+max(0,(after-note.onset_tick-1)//2)
                    onset_offsets[note.onset_tick] = max(lower,min(upper,onset))
                onset = onset_offsets[note.onset_tick]
                duration = note.duration_ticks
                if strength:
                    if art == "detached":
                        duration = round(duration * (1 - .22 * strength))
                    elif connected:
                        duration = round(duration + strength * max(0, gap))
                    if family in ("woodwind", "brass") and (nxt is None or nxt.onset_tick >= phrase.end_tick):
                        duration -= round(min(base.ppq*.3, duration*.12) * strength)
                velocity = max(1, min(127, round(note.velocity + strength * (10*arc - 4))))
                played.append(PlayedNote(note_id=note.id, source_id=note.source_id, part_id=part.id,
                    phrase_id=phrase.id, pitch=note.pitch, onset_tick=onset,
                    duration_ticks=max(1, min(duration, score.end_tick-onset)), velocity=velocity,
                    articulation=art if strength else "sustained"))
            # Retriggered pitches must release before the next onset in all MIDI players.
            for index, note in enumerate(played):
                next_same = next((n for n in played[index+1:] if n.pitch == note.pitch), None)
                if next_same is not None:
                    note.duration_ticks = max(1, min(note.duration_ticks, next_same.onset_tick - note.onset_tick))
                if profile(part.instrument).polyphony==1 and index+1<len(played):
                    note.duration_ticks = max(1,min(note.duration_ticks,played[index+1].onset_tick-note.onset_tick))
            notes.extend(played)
            cc = []
            for tick in range(0, score.end_tick, max(1, base.ppq // 8)):
                phrase = phrase_at(part.id, tick)
                # Piano dynamics come from the strike; no expression swell on ringing notes.
                value = 100 if family in ("keyboard", "percussion", "drums") else round(100 + strength * (18*_arc(phrase,tick) - 10))
                cc.append(Control(tick=tick, controller=11, value=value))
            if family == "keyboard" and strength:
                for phrase in by_part[part.id]:
                    boundaries = sorted({phrase.start_tick} | {o["start_tick"] for o in score.occurrences
                        if o["kind"]=="harmony" and phrase.start_tick<=o["start_tick"]<phrase.end_tick})
                    for tick in boundaries:
                        cc.append(Control(tick=tick, controller=64, value=0))
                        cc.append(Control(tick=min(tick+max(1, base.ppq//16), phrase.end_tick-1), controller=64, value=90))
                    cc.append(Control(tick=phrase.end_tick, controller=64, value=0))
            controls[part.id] = sorted(cc, key=lambda c:(c.tick,c.controller,c.value))
        plan = PerformancePlan(score_sha256=score_digest(score), source_bank_sha256=score.source_bank_sha256,
            adapter="local phrase performer", seed=seed, strength=strength, timeline=timeline,
            notes=notes, controls=controls, phrases=phrases,
            warnings=["Connected sustain approximates legato; VSCO has no recorded interval transitions."])
        validate_performance(score, plan)
        return plan


def validate_performance(score, plan):
    MusicalTimeline.model_validate(plan.timeline.model_dump())
    if plan.score_sha256 != score_digest(score) or plan.source_bank_sha256 != score.source_bank_sha256:
        raise ValueError("Performance references a different logical score")
    original = {n.id:(part.id,n.source_id,n.pitch) for part in score.parts for n in part.notes if not n.muted}
    actual = {n.note_id:(n.part_id,n.source_id,n.pitch) for n in plan.notes}
    if original != actual or len(plan.notes) != len(original):
        raise ValueError("Performance must preserve every sounding note and source identity")
    if set(plan.controls) != {p.id for p in score.parts}:
        raise ValueError("Unknown/missing performance control part")
    if plan.timeline.bars != score.timeline.bars or plan.timeline.ppq != score.ppq:
        raise ValueError("Performance must preserve metre and PPQ")
    for part in score.parts:
        notes = [n for n in plan.notes if n.part_id==part.id]
        edges = sorted([(n.onset_tick,1) for n in notes]+[(n.onset_tick+n.duration_ticks,-1) for n in notes])
        alive = 0
        for _,delta in edges:
            alive += delta
            if alive>profile(part.instrument).polyphony:
                raise ValueError("Performance exceeds part capacity: " + part.id)
        for pitch in {n.pitch for n in notes}:
            unisons = sorted([n for n in notes if n.pitch==pitch],key=lambda n:n.onset_tick)
            if any(a.onset_tick+a.duration_ticks>b.onset_tick for a,b in zip(unisons,unisons[1:])):
                raise ValueError("Performance overlaps same-pitch occurrences")
