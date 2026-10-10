"""Typed input, musical state and model proposals. Times are sounding MIDI ticks."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


Role = Literal["melody", "countermelody", "harmony", "bass", "rhythm", "texture"]


class InputNote(Schema):
    pitch: int = Field(ge=0, le=127)
    onset_beats: float = Field(ge=0, allow_inf_nan=False)
    duration_beats: float = Field(gt=0, allow_inf_nan=False)
    velocity: int = Field(default=80, ge=1, le=127)


class PartSpec(Schema):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    instrument: str
    path: Path | None = None
    midi_track: int | None = Field(default=None, ge=0)
    channel: int | None = Field(default=None, ge=0, le=15)
    notes: list[InputNote] | None = None
    tempo_bpm: float | None = Field(default=None, gt=0, le=400, allow_inf_nan=False)
    role: Role | None = None
    source: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def one_source(self):
        if (self.path is None) == (self.notes is None):
            raise ValueError("Supply exactly one of path (MIDI) or notes (beat-based events)")
        return self


class Manifest(Schema):
    parts: list[PartSpec] = Field(min_length=1)
    lead_track: str


class OrchestrationConfig(Schema):
    bars: int = Field(default=16, ge=1, le=128)
    start_bar: int = Field(default=0, ge=0)
    window_bars: int = Field(default=4, ge=1, le=16)
    ppq: int = Field(default=480, ge=24, le=9600)
    tempo_bpm: float | None = Field(default=None, gt=0, le=400, allow_inf_nan=False)
    key: str | None = None
    chords: list[str] | None = Field(default=None, min_length=1)
    backend: Literal["gemini", "rules"] = "gemini"
    model: str = "gemini-3.8-flash"
    edit_budget: float = Field(default=0.2, ge=0, le=1)
    max_corrections: int = Field(default=2, ge=0, le=2)
    api_timeout_seconds: int = Field(default=60, ge=1, le=300)
    max_api_calls: int = Field(default=18, ge=0, le=100)
    render_audio: bool = True
    fluidsynth: str | None = None
    soundfont: Path | None = None
    sample_rate: int = Field(default=44100, ge=8000, le=96000)
    output_dir: Path | None = None

    @property
    def bar_ticks(self) -> int:
        return self.ppq * 4

    @property
    def end_tick(self) -> int:
        return self.bars * self.bar_ticks


class NoteEvent(Schema):
    id: str
    source_id: str
    phrase_id: str
    pitch: int = Field(ge=0, le=127)
    onset_tick: int = Field(ge=0)
    duration_ticks: int = Field(gt=0)
    velocity: int = Field(ge=1, le=127)
    muted: bool = False
    transpose: int = 0
    phrase_shift: int = 0

    @property
    def end_tick(self) -> int:
        return self.onset_tick + self.duration_ticks


class Part(Schema):
    id: str
    instrument: str
    notes: list[NoteEvent]
    role: Role
    source: dict[str, str] = Field(default_factory=dict)
    source_tempo_bpm: float | None = None
    pan: int = Field(default=64, ge=0, le=127)
    expression: list[tuple[int, int]] = Field(default_factory=list)


class Score(Schema):
    parts: list[Part]
    lead_track: str
    tempo_bpm: float
    ppq: int
    bars: int
    window_bars: int

    @property
    def end_tick(self) -> int:
        return self.bars * 4 * self.ppq

    def part(self, track_id: str) -> Part:
        for part in self.parts:
            if part.id == track_id:
                return part
        raise ValueError(f"Unknown track: {track_id}")


class ChordSpan(Schema):
    start_tick: int = Field(ge=0)
    duration_ticks: int = Field(gt=0)
    symbol: str = Field(min_length=1, max_length=24)


class TrackDirective(Schema):
    track_id: str
    start_bar: int = Field(ge=0)
    end_bar: int = Field(gt=0)
    role: Role
    silent: bool = False
    velocity: int = Field(ge=1, le=127)
    expression: int = Field(default=100, ge=0, le=127)
    pan: int = Field(default=64, ge=0, le=127)


class ArrangementPlan(Schema):
    key: str
    chords: list[ChordSpan] = Field(min_length=1)
    directives: list[TrackDirective]
    rationale: str = Field(default="", max_length=4000)


class Edit(Schema):
    op: Literal["transpose_phrase", "shift_phrase", "mute_phrase", "mute_note", "edit_note", "set_velocity", "set_pan"]
    target: str
    semitones: int | None = Field(default=None, ge=-48, le=48)
    ticks: int | None = None
    pitch: int | None = Field(default=None, ge=0, le=127)
    duration_ticks: int | None = Field(default=None, gt=0)
    value: int | None = Field(default=None, ge=0, le=127)
    reason: str = Field(default="", max_length=1000)


class EditProposal(Schema):
    edits: list[Edit] = Field(max_length=256)
    rationale: str = Field(default="", max_length=4000)


class ArrangementResult(Schema):
    score: Score
    plan: ArrangementPlan
    report: dict
    artifacts: dict[str, str] = Field(default_factory=dict)
