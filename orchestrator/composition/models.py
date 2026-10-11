"""Composition contracts. Time is integer ticks; pitch identity comes from sources."""
from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import Field, model_validator
from orchestrator.models import Schema, Part

Style = Literal["bach", "mozart", "debussy", "rachmaninoff"]


class CompositionRequest(Schema):
    style: Style = "mozart"
    seed: int = Field(default=42, ge=0)
    bars: int = Field(default=24, ge=12, le=96)
    instruments: list[str] = Field(default_factory=lambda: [
        "flute", "clarinet", "violin_1", "cello", "double_bass"], min_length=2, max_length=15)
    lead_track: str = "flute"
    key: str | None = None
    planner: Literal["local", "gemini"] = "local"
    compare: bool = False
    model: str = "gemini-3.8-flash"

    @model_validator(mode="after")
    def instruments_valid(self):
        from orchestrator.instruments import profile
        if len(set(self.instruments)) != len(self.instruments) or self.lead_track not in self.instruments:
            raise ValueError("Require unique instruments and a selected lead")
        if any(profile(i).family == "drums" for i in self.instruments):
            raise ValueError("Composition v1 uses pitched instrument sources")
        return self


class BarSignature(Schema):
    numerator: int = Field(ge=1, le=16)
    denominator: Literal[2, 4, 8, 16] = 4
    groups: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def grouping_valid(self):
        if self.groups and (any(type(n) is not int or n < 1 for n in self.groups) or sum(self.groups) != self.numerator):
            raise ValueError("Accent groups must sum to the numerator")
        return self


class TempoEvent(Schema):
    tick: int = Field(ge=0)
    bpm: float = Field(gt=0, le=400, allow_inf_nan=False)


class MusicalTimeline(Schema):
    ppq: int = Field(default=480, ge=24, le=9600)
    bars: list[BarSignature] = Field(min_length=1, max_length=96)
    tempos: list[TempoEvent] = Field(min_length=1, max_length=2000)

    @property
    def bar_starts(self):
        starts, cursor = [], 0
        for bar in self.bars:
            starts.append(cursor)
            value = self.ppq * bar.numerator * 4
            if value % bar.denominator:
                raise ValueError("PPQ cannot exactly represent this metre")
            cursor += value // bar.denominator
        return starts

    @property
    def end_tick(self):
        bar = self.bars[-1]
        return self.bar_starts[-1] + self.ppq * bar.numerator * 4 // bar.denominator

    def bar_ticks(self, index):
        bar = self.bars[index]
        return self.ppq * bar.numerator * 4 // bar.denominator

    def seconds_at(self, tick):
        if not 0 <= tick <= self.end_tick:
            raise ValueError("Tick outside timeline")
        cursor, bpm, seconds = 0, self.tempos[0].bpm, 0.0
        for event in self.tempos[1:]:
            if event.tick >= tick:
                break
            seconds += (event.tick - cursor) * 60 / (self.ppq * bpm)
            cursor, bpm = event.tick, event.bpm
        return seconds + (tick - cursor) * 60 / (self.ppq * bpm)

    @model_validator(mode="after")
    def valid_tempos(self):
        ticks = [event.tick for event in self.tempos]
        if ticks[0] != 0 or ticks != sorted(set(ticks)) or ticks[-1] >= self.end_tick:
            raise ValueError("Tempo map starts at zero with unique ascending in-range ticks")
        return self


class SourceEvent(Schema):
    id: str
    pitch: int | None = Field(default=None, ge=0, le=127)
    source_part: str
    model: Literal["qcbm", "pop909", "external"]
    token_index: int | None = Field(default=None, ge=0)


class SourceMotif(Schema):
    id: str
    source_part: str
    events: list[str] = Field(min_length=1, max_length=16)


class SourceChord(Schema):
    id: str
    symbol: str
    events: list[str] = Field(min_length=1, max_length=8)


class SourceBank(Schema):
    key: str
    events: list[SourceEvent]
    motifs: list[SourceMotif]
    chords: list[SourceChord]
    provenance: dict

    @property
    def digest(self):
        return hashlib.sha256(self.model_dump_json().encode("utf-8")).hexdigest()

    @model_validator(mode="after")
    def references_valid(self):
        ids = [event.id for event in self.events]
        if len(ids) != len(set(ids)):
            raise ValueError("Source event IDs must be unique")
        available = set(ids)
        pitches = {event.id: event.pitch for event in self.events}
        for group in [*self.motifs, *self.chords]:
            if any(event not in available for event in group.events):
                raise ValueError("Unknown event in source group")
        for groups in (self.motifs, self.chords):
            if len({group.id for group in groups}) != len(groups):
                raise ValueError("Source group IDs must be unique")
        if not self.motifs or not self.chords or any(pitches[e] is None for c in self.chords for e in c.events):
            raise ValueError("Require motifs and sounding chord sources")
        return self


class Section(Schema):
    name: str = Field(min_length=1, max_length=80)
    start_bar: int = Field(ge=0)
    end_bar: int = Field(gt=0)
    function: Literal["introduce", "develop", "return"]


class MotifOccurrence(Schema):
    id: str
    motif_id: str
    target_part: str
    start_tick: int = Field(ge=0)
    steps_ticks: list[int] = Field(min_length=1, max_length=16)
    register_target: int = Field(ge=0, le=127)
    velocity_start: int = Field(ge=1, le=127)
    velocity_end: int = Field(ge=1, le=127)
    gate: float = Field(default=.9, ge=.2, le=1, allow_inf_nan=False)


class HarmonyOccurrence(Schema):
    id: str
    chord_id: str
    target_parts: list[str] = Field(min_length=1, max_length=15)
    start_tick: int = Field(ge=0)
    span_ticks: int = Field(gt=0)
    texture: Literal["sustained", "broken", "arpeggio", "pedal"]
    pulse_ticks: int = Field(gt=0)
    register_target: int = Field(ge=0, le=127)
    velocity: int = Field(ge=1, le=127)


class CompositionPlan(Schema):
    style: Style
    source_bank_sha256: str
    timeline: MusicalTimeline
    sections: list[Section] = Field(min_length=3, max_length=16)
    motifs: list[MotifOccurrence] = Field(min_length=1, max_length=2000)
    harmony: list[HarmonyOccurrence] = Field(default_factory=list, max_length=2000)
    rationale: str = Field(default="", max_length=4000)


class ComposedScore(Schema):
    title: str
    parts: list[Part]
    lead_track: str
    timeline: MusicalTimeline
    source_bank_sha256: str
    planner: Literal["raw", "local", "gemini"]
    # Includes silent source tokens and deliberate phrase gaps.
    occurrences: list[dict] = Field(default_factory=list)

    @property
    def ppq(self):
        return self.timeline.ppq

    @property
    def end_tick(self):
        return self.timeline.end_tick

    @property
    def tempo_bpm(self):
        return self.timeline.tempos[0].bpm

    @property
    def bars(self):
        return len(self.timeline.bars)
