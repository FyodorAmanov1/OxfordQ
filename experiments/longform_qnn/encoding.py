"""Half-beat integer time; 120 semantic tokens; deterministic causal context."""
from dataclasses import dataclass, asdict
import numpy as np

SCALE = (0, 2, 4, 5, 7, 9, 11)
DURATIONS = tuple((i + 1) / 2 for i in range(8))
FEATURES = 80
LONG = slice(40, 80)

@dataclass(frozen=True)
class Event:
    pitch: int  # 0=rest; 1..7=C4..B4; 8..14=C5..B5
    units: int  # half beats, 1..8
    onset: int
    continuation: bool = False  # corpus segmentation provenance only

    def __post_init__(self):
        if not (0 <= self.pitch <= 14 and 1 <= self.units <= 8 and self.onset >= 0):
            raise ValueError('Invalid musical event')
        if self.onset % 8 + self.units > 8:
            raise ValueError('Event crosses a bar')

    @property
    def token(self):
        return self.pitch * 8 + self.units - 1

    @property
    def midi(self):
        return None if self.pitch == 0 else 60 + SCALE[(self.pitch - 1) % 7] + 12 * ((self.pitch - 1) // 7)

def event_from_token(token, onset):
    if not 0 <= int(token) < 120:
        raise ValueError('Invalid semantic token')
    return Event(int(token) // 8, int(token) % 8 + 1, int(onset))

def output_token(index):
    """Qiskit index bits q6..q0 = duration(3), register(1), degree(3)."""
    degree, register, duration = index & 7, (index >> 3) & 1, (index >> 4) & 7
    pitch = 0 if degree == 0 else degree + register * 7
    return pitch * 8 + duration

OUTPUT_TOKENS = np.array([output_token(i) for i in range(128)])
AGGREGATION = np.eye(120)[OUTPUT_TOKENS]

def context(history, onset, mode='full'):
    """Caller supplies only the prefix; reject any overlapping/future events.

    0:32 last 8 (pitch, duration, sounding, interval); 32:40 clock/BoP;
    40:80 previous four complete bars, ten summary values per bar, newest first.
    The clock is deterministic scheduling information shared by all models.
    """
    if mode not in ('full', 'short'):
        raise ValueError('Unknown context mode')
    if any(e.onset + e.units > onset for e in history):
        raise ValueError('Future or overlapping event in causal prefix')
    x = np.zeros(FEATURES, dtype=np.float64)
    recent = history[-8:]
    for i, e in enumerate(reversed(recent)):
        idx = len(history) - 1 - i
        prior = history[idx - 1] if idx else None
        interval = (e.midi - prior.midi) / 24 if prior and e.midi is not None and prior.midi is not None else 0
        x[4*i:4*i+4] = (e.pitch / 14, e.units / 8, float(e.pitch != 0), interval)
    beat = onset % 8 / 8
    bar = (onset // 8) % 16
    x[32:40] = (np.sin(2*np.pi*beat), np.cos(2*np.pi*beat), beat,
                np.sin(2*np.pi*bar/16), np.cos(2*np.pi*bar/16), bar/15,
                float(onset == 0), min(len(history), 8)/8)
    if mode == 'short':
        return x
    for lag in range(1, 5):
        start = (onset // 8 - lag) * 8
        events = [e for e in history if start <= e.onset < start + 8] if start >= 0 else []
        if not events:
            continue
        pitches = [e.pitch / 14 for e in events if e.pitch]
        durations = np.array([e.units / 8 for e in events])
        values = (1, np.mean(pitches) if pitches else 0, np.std(pitches) if pitches else 0,
                  pitches[0] if pitches else 0, pitches[-1] if pitches else 0,
                  sum(e.units for e in events if not e.pitch)/8, len(events)/8,
                  durations.mean(), durations.std(), sum(e.units == 1 for e in events)/len(events))
        x[40+(lag-1)*10:50+(lag-1)*10] = values
    return x

def teacher_examples(events):
    """No target/future event is passed to context()."""
    history, xs, ys, remaining = [], [], [], []
    for e in events:
        xs.append(context(history, e.onset)); ys.append(e.token)
        remaining.append(8-e.onset % 8); history.append(e)
    return np.array(xs), np.array(ys), np.array(remaining)

def dump_events(events):
    return [asdict(e) for e in events]
