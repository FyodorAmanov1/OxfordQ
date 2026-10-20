"""Independently read exported MIDI/WAV and trace; never execute a quantum job."""
import hashlib
import json
from pathlib import Path
import wave
import numpy as np
import mido
from .encoding import Event,context

def verify(root):
    root=Path(root);report=[]
    for example in ('free','structured'):
        directory=root/'examples'/example
        trace=json.loads((directory/'generation.json').read_text())
        history=[];probability_errors=[]
        for record in trace['events']:
            e=Event(**record['event'])
            assert e.onset==sum(p.units for p in history)
            assert np.array_equal(context(history,e.onset),record['context'])
            if record['probabilities'] is not None:
                p=np.array(record['probabilities'])
                assert np.isfinite(p).all() and np.all(p>=0) and abs(p.sum()-1)<1e-12
                assert np.all(p[np.arange(120)%8+1>8-e.onset%8]==0)
                assert p[e.token]==record['sample_probability']
                assert record['qiskit_max_error']<1e-10
                probability_errors.append(record['qiskit_max_error'])
            else:
                assert record['origin']=='classical_phrase_transform'
                original=history[record['source_event_index']]
                assert original.units==e.units and bool(original.pitch)==bool(e.pitch)
            history.append(e)
        assert sum(e.units for e in history)==128
        files=[]
        for label in ('melody','arranged'):
            midi_path=directory/f'{label}.mid';midi=mido.MidiFile(midi_path)
            assert abs(midi.length-32)<1e-9 and midi.ticks_per_beat==480
            assert all(sum(m.time for m in track)==30720 for track in midi.tracks)
            active={};parsed=[];tick=0
            for m in midi.tracks[1]:
                tick+=m.time
                if m.type=='note_on' and m.velocity:active[m.note]=(tick,m.velocity)
                elif m.type=='note_off' or m.type=='note_on' and not m.velocity:
                    start,velocity=active.pop(m.note);parsed.append((m.note,start,tick-start,velocity))
            expected=[(e.midi,e.onset*240,e.units*240,84) for e in history if e.pitch]
            assert sorted(parsed)==sorted(expected) and not active
            wav_path=directory/f'{label}.wav'
            with wave.open(str(wav_path)) as wav:
                assert wav.getnchannels()==1 and wav.getsampwidth()==2
                assert wav.getnframes()/wav.getframerate()==32
                audio=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(float)/32768
                rms=float(np.sqrt(np.mean(audio**2)));assert rms>.001
            files.extend(dict(file=p.relative_to(root).as_posix(),bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (midi_path,wav_path))
        report.append(dict(example=example,event_count=len(history),seconds=32,
            qnn_sampled_events=len(probability_errors),max_qiskit_error=max(probability_errors),files=files))
    (root/'artifact_verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2));return report

if __name__=='__main__':
    import sys
    verify(sys.argv[1] if len(sys.argv)>1 else Path(__file__).parent/'artifacts')
