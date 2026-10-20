"""Verify the actual generated artifacts, immutable source and repeatable output bytes."""
from datetime import datetime, timezone
import json
from pathlib import Path
import wave
import mido
import numpy as np
from .composition import sample_motifs, compose, harmonize, canonical, digest, ROOT
from .render import export


def midi_notes(path, track=1):
    clock = 0; active = {}; notes = []
    for message in mido.MidiFile(path).tracks[track]:
        clock += message.time
        if message.type == 'note_on' and message.velocity:
            assert message.note not in active
            active[message.note] = (clock, message.velocity)
        elif message.type == 'note_off' or message.type == 'note_on' and not message.velocity:
            start, velocity = active.pop(message.note)
            notes.append((message.note, start, clock - start, velocity))
    assert not active
    return sorted(notes)


def verify(out):
    out = Path(out)
    raw_bytes = (out / 'raw-samples.json').read_bytes()
    raw = json.loads(raw_bytes)
    trace = json.loads((out / 'trace.json').read_bytes())
    assert raw == sample_motifs(raw['seed'])
    assert digest(raw_bytes) == trace['raw_samples_sha256']
    assert digest(canonical(raw)) == trace['raw_samples_canonical_sha256']
    developed = compose(raw)
    assert trace['events'] == developed['events']
    harmony, bass, chords = harmonize(developed['events'])
    assert trace['harmony'] == harmony and trace['bass'] == bass and trace['chords'] == chords
    replica = out / 'reproduction'
    for name, tracks in [('melody', [('Classically developed QCBM melody', developed['events'])]),
                         ('arranged', [('Classically developed QCBM melody', developed['events']), ('Classical bass', bass), ('Classical chords', chords)])]:
        export(replica, name, tracks)
        for ext in ('mid', 'wav'):
            assert (out / f'{name}.{ext}').read_bytes() == (replica / f'{name}.{ext}').read_bytes()
    expected = sorted((e['pitch'], round(e['onset']*480), round((e['onset']+e['duration'])*480)-round(e['onset']*480), e['velocity'])
                      for e in developed['events'] if e['pitch'] is not None)
    assert midi_notes(out/'melody.mid') == midi_notes(out/'arranged.mid') == expected
    comparison = json.loads((out/'comparison.json').read_bytes())
    recorded = comparison['sources'][0]
    fixture = (ROOT/recorded['path']).read_bytes()
    assert digest(fixture) == recorded['sha256']
    assert json.loads(fixture)['statistics'] == recorded['original_statistics']
    files = []
    for path in sorted(out.glob('*.mid')):
        length = 8 if path.name.startswith('original-four-bar') else 32
        midi = mido.MidiFile(path)
        assert abs(midi.length-length) < 1e-9
        assert all(sum(m.time for m in t) == length*2*480 for t in midi.tracks)
        for i in range(1, len(midi.tracks)):
            assert all(0 <= pitch <= 127 and duration > 0 and 1 <= velocity <= 127
                       for pitch, start, duration, velocity in midi_notes(path, i))
        with wave.open(str(path.with_suffix('.wav'))) as stream:
            assert stream.getframerate() == 22050 and stream.getsampwidth() == 2 and stream.getnchannels() == 1
            assert stream.getnframes()/stream.getframerate() == length
            audio = np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2') / 32768
            rms = float(np.sqrt(np.mean(audio**2)))
            assert .001 < rms < .7 and np.abs(audio).max() < .951
        for artifact in (path, path.with_suffix('.wav')):
            files.append(dict(file=artifact.name, seconds=length, sha256=digest(artifact.read_bytes()),
                              bytes=artifact.stat().st_size, wav_rms=rms if artifact.suffix=='.wav' else None))
    # Validate local page links without requiring a browser or uploading any artifacts.
    from html.parser import HTMLParser
    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key in ('href', 'src'):
                    assert (out / value).is_file(), value
    Links().feed((out/'listen.html').read_text(encoding='utf-8'))
    report = dict(verified_utc=datetime.now(timezone.utc).isoformat(), status='passed',
                  identical_regenerated_midi_wav=True, preserved_raw_sha256=digest(raw_bytes),
                  protected_recorded_statistics_unchanged=True, backend_jobs=0, files=files,
                  browser_check='Not executed: browser tool rejected file URLs; local links checked with HTML parser',
                  subjective_listening='Pending human audition; no listening verdict fabricated')
    (out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return report


if __name__ == '__main__':
    import sys
    verify(sys.argv[1] if len(sys.argv)>1 else Path(__file__).parent/'artifacts')
