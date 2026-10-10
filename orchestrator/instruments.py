"""Conservative concert-pitch profiles; MIDI programs are zero-based.

Ranges guide a listening demo, not certification of a score for human performance.
Section polyphony denotes explicit divisi or multiple wind/brass players.
References: https://www.vsl.co.at/academy/ and Philharmonia instrument resources.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentProfile:
    low: int
    high: int
    program: int
    family: str
    polyphony: int
    pan: int = 64


PROFILES = {
    "piccolo": InstrumentProfile(74, 108, 72, "woodwind", 1, 60),
    "flute": InstrumentProfile(60, 96, 73, "woodwind", 2, 56),
    "oboe": InstrumentProfile(58, 91, 68, "woodwind", 2, 68),
    "clarinet": InstrumentProfile(50, 94, 71, "woodwind", 2, 60),
    "bassoon": InstrumentProfile(34, 75, 70, "woodwind", 2, 72),
    "horns": InstrumentProfile(41, 77, 60, "brass", 4, 46),
    "trumpets": InstrumentProfile(54, 86, 56, "brass", 3, 76),
    "trombones": InstrumentProfile(40, 72, 57, "brass", 3, 80),
    "tuba": InstrumentProfile(28, 65, 58, "brass", 1, 84),
    "violin_1": InstrumentProfile(55, 100, 48, "strings", 2, 30),
    "violin_2": InstrumentProfile(55, 96, 48, "strings", 2, 42),
    "viola": InstrumentProfile(48, 88, 48, "strings", 2, 54),
    "cello": InstrumentProfile(36, 81, 48, "strings", 2, 78),
    "double_bass": InstrumentProfile(28, 67, 43, "strings", 1, 90),
    "timpani": InstrumentProfile(40, 57, 47, "percussion", 2, 74),
    "percussion": InstrumentProfile(35, 81, 0, "drums", 8, 70),
}


def profile(instrument: str) -> InstrumentProfile:
    try:
        return PROFILES[instrument]
    except KeyError:
        raise ValueError(f"Unknown instrument {instrument!r}. Choose: {', '.join(PROFILES)}") from None
