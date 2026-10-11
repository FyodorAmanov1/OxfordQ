"""Editable instrument amplitude envelopes; defaults describe ordinary articulation."""
from pydantic import Field
import numpy as np
from .models import Schema


class InstrumentPerformance(Schema):
    volume: float = Field(default=.8, ge=0, le=1, allow_inf_nan=False)
    attack_seconds: float = Field(default=.02, gt=0, le=2, allow_inf_nan=False)
    decay_seconds: float = Field(default=.08, gt=0, le=4, allow_inf_nan=False)
    sustain: float = Field(default=.85, ge=0, le=1, allow_inf_nan=False)
    release_seconds: float = Field(default=.1, gt=0, le=4, allow_inf_nan=False)
    swell: float = Field(default=.1, ge=0, le=.5, allow_inf_nan=False)
    tremolo_depth: float = Field(default=.015, ge=0, le=.1, allow_inf_nan=False)
    struck: bool = False


def performance_for(instrument):
    from .instruments import profile
    family = profile(instrument).family
    values = {
        "woodwind": dict(attack_seconds=.045, decay_seconds=.09, sustain=.84, release_seconds=.08, swell=.16),
        "brass": dict(attack_seconds=.028, decay_seconds=.09, sustain=.88, release_seconds=.10, swell=.12),
        "strings": dict(volume=.75, attack_seconds=.015, decay_seconds=.08, sustain=.88, release_seconds=.12, swell=.10),
        "keyboard": dict(volume=.9, attack_seconds=.004, decay_seconds=.65, sustain=0, release_seconds=.13, swell=0, tremolo_depth=0, struck=True),
        "percussion": dict(attack_seconds=.002, decay_seconds=.24, sustain=0, release_seconds=.08, swell=0, tremolo_depth=0, struck=True),
        "drums": dict(attack_seconds=.002, decay_seconds=.15, sustain=0, release_seconds=.05, swell=0, tremolo_depth=0, struck=True),
    }[family].copy()
    values.update({
        "flute": dict(attack_seconds=.075, release_seconds=.075, swell=.20),
        "piccolo": dict(attack_seconds=.045, release_seconds=.055),
        "clarinet": dict(attack_seconds=.035, swell=.13),
        "oboe": dict(attack_seconds=.022, swell=.10),
        "bassoon": dict(attack_seconds=.035, release_seconds=.10),
        "cello": dict(attack_seconds=.024, release_seconds=.15, swell=.14),
        "double_bass": dict(attack_seconds=.035, release_seconds=.18, volume=.85),
        "horns": dict(attack_seconds=.06, swell=.16),
        "tuba": dict(attack_seconds=.06, release_seconds=.14),
        "timpani": dict(decay_seconds=.55, release_seconds=.16),
    }.get(instrument, {}))
    return InstrumentPerformance(**values)


def envelope(spec, duration, rate, pitch=60):
    """Held-note seconds exclude release. Smooth attack/release prevent hard cuts."""
    if duration <= 0 or rate <= 0:
        raise ValueError("Envelope needs a positive duration/sample rate")
    attack = min(spec.attack_seconds, duration * .22)
    release = min(spec.release_seconds, max(.008, duration * .4))
    count = max(2, round((duration + release) * rate))
    time = np.arange(count, dtype=np.float64) / rate
    if spec.struck:
        # Lower piano/percussion pitches can ring longer; the strike never stays flat.
        decay = spec.decay_seconds * 2 ** ((60 - pitch) / 48)
        gain = np.exp(-np.maximum(0, time - attack) / decay)
    else:
        decay = min(spec.decay_seconds, duration * .22)
        settle = np.clip((time - attack) / decay, 0, 1)
        gain = 1 - (1 - spec.sustain) * settle
        phase = np.clip((time - attack - decay) / max(.001, duration - attack - decay), 0, 1)
        gain *= 1 + spec.swell * np.sin(np.pi * phase)
        gain *= 1 - .22 * phase ** 3  # breath/bow easing before release
        gain *= 1 + spec.tremolo_depth * np.sin(2 * np.pi * 5.2 * time) * np.minimum(1, time / .3)
    rising = time < attack
    gain[rising] = .5 - .5 * np.cos(np.pi * time[rising] / attack)
    falling = time >= duration
    gain[falling] *= .5 + .5 * np.cos(np.pi * np.clip((time[falling] - duration) / release, 0, 1))
    gain[0] = gain[-1] = 0
    return gain.astype(np.float32)
