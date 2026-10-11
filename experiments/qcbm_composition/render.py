"""Small deterministic MIDI and additive WAV renderer; no native/audio dependencies."""
from pathlib import Path
import wave
import mido
import numpy as np


def midi(tracks, path, beats):
    output = mido.MidiFile(ticks_per_beat=480)
    conductor = mido.MidiTrack()
    output.tracks.append(conductor)
    conductor.extend([mido.MetaMessage('set_tempo', tempo=500000),
                      mido.MetaMessage('time_signature', numerator=4, denominator=4),
                      mido.MetaMessage('text', text='Offline QCBM composition experiment; classical development labelled in trace'),
                      mido.MetaMessage('end_of_track', time=round(beats * 480))])
    for channel, (name, events) in enumerate(tracks):
        track = mido.MidiTrack()
        output.tracks.append(track)
        track.append(mido.MetaMessage('track_name', name=name))
        track.append(mido.Message('program_change', channel=channel, program=(73, 32, 0)[channel]))
        schedule = []
        for event in events:
            if event['pitch'] is None:
                continue
            start, end = round(event['onset'] * 480), round((event['onset'] + event['duration']) * 480)
            if not 0 <= start < end <= round(beats * 480):
                raise ValueError('Invalid note timing')
            schedule.extend([(start, 1, event['pitch'], event['velocity']), (end, 0, event['pitch'], 0)])
        tick = 0
        for at, on, pitch, velocity in sorted(schedule):
            track.append(mido.Message('note_on' if on else 'note_off', channel=channel,
                                      note=pitch, velocity=velocity, time=at - tick))
            tick = at
        track.append(mido.MetaMessage('end_of_track', time=round(beats * 480) - tick))
    output.save(str(path))


def wav(tracks, path, beats):
    rate = 22050
    audio = np.zeros(round(beats * .5 * rate))
    for channel, (_, events) in enumerate(tracks):
        for event in events:
            if event['pitch'] is None:
                continue
            start = round(event['onset'] * .5 * rate)
            end = round((event['onset'] + event['duration']) * .5 * rate)
            t = np.arange(end - start) / rate
            frequency = 440 * 2 ** ((event['pitch'] - 69) / 12)
            tone = sum(np.sin(2 * np.pi * frequency * k * t) / k**2 for k in (1, 2, 3))
            envelope = np.minimum(1, t / .012) * np.minimum(1, ((end-start) / rate - t) / .035)
            audio[start:end] += tone * envelope * event['velocity'] / 127 * (.32 if channel == 0 else .16)
    peak = float(np.abs(audio).max())
    if peak > .95:
        audio *= .95 / peak
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes((audio * 32767).astype('<i2').tobytes())
    return dict(seconds=len(audio) / rate, sample_rate=rate,
                rms=float(np.sqrt(np.mean(audio**2))), peak=float(np.abs(audio).max()),
                renderer='Same additive 3-harmonic synth for every comparison; no listening-quality score')


def export(directory, name, tracks, beats=64):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    midi(tracks, directory / f'{name}.mid', beats)
    return wav(tracks, directory / f'{name}.wav', beats)
