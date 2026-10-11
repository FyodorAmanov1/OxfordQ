"""Independent media/provenance invariants for the two-version comparison."""
from datetime import datetime,timezone
from pathlib import Path
import json
import wave
import mido
import numpy as np
from experiments.qcbm_composition.composition import compose,canonical
from .__main__ import load_samples,digest
from .refine import refine


def notes(path,track):
    active={};clock=0;result=[]
    for m in mido.MidiFile(path).tracks[track]:
        clock+=m.time
        if m.type=='note_on' and m.velocity:
            key=(m.channel,m.note)
            assert key not in active,'Overlapping same-pitch MIDI voice'
            active[key]=(clock,m.velocity)
        elif m.type=='note_off' or m.type=='note_on' and not m.velocity:
            start,velocity=active.pop((m.channel,m.note))
            assert start<clock
            result.append((m.note,start,clock-start,velocity))
    assert not active,'Unclosed MIDI notes'
    return sorted(result)


def expected(events):
    return sorted((e['pitch'],round(e['onset']*480),round((e['onset']+e['duration'])*480)-round(e['onset']*480),e['velocity'])
                  for e in events if e['pitch'] is not None)


def verify(out):
    out=Path(out)
    raw,source,reference=load_samples()
    trace=json.loads((out/'trace.json').read_bytes())
    assert (out/'raw-samples.json').read_bytes()==source
    assert trace['source']['raw_samples_sha256']==digest(source)
    assert trace['original']['events']==compose(raw)['events']
    assert canonical(trace['improved'])==canonical(refine(raw))
    assert trace['backend_jobs']==trace['sampling_calls']==trace['statevector_evaluations']==trace['training_steps']==0
    assert trace['data_status']=='PRE-GENERATED' and 'statistics' not in trace
    improved=trace['improved']
    sources={f'{m["motif_id"]}:n{j}':token for m in raw['motifs'] for j,token in enumerate(m['tokens'])}
    assert len(sources)==64 and len(improved['events'])==64
    assert len(set(improved['cadence_event_ids']))==4
    assert {e['source_event_id'].split(':')[0] for e in improved['events']}=={m['motif_id'] for m in raw['motifs']}
    changed_pcs=[]
    for before,e in zip(trace['original']['events'],improved['events']):
        assert e['reference_event_id']==before['event_id']
        assert e['source_event_id']==before['source_event_id']
        assert e['sampled_token']==sources[e['source_event_id']]
        assert e['rest']==before['rest']==(e['pitch'] is None)
        assert 4*e['bar']<=e['onset']<e['onset']+e['duration']<=e['onset']+e['slot_beats']<=4*(e['bar']+1)
        for t in e['transformations']:
            assert t['rule'].startswith('classical_') and t['source_event_ids']==[e['source_event_id']]
        if not e['rest'] and e['pitch']%12!=e['sampled_pitch']%12:
            changed_pcs.append(e['event_id'])
    assert set(changed_pcs)<=set(improved['cadence_event_ids'])
    assert improved['unused_sampled_positions']==trace['original']['unused_sampled_positions']
    for e in improved['bass']+improved['chords']:
        assert 0<=e['pitch']<=127 and 1<=e['velocity']<=127
        assert 4*e['bar']<=e['onset']<e['onset']+e['duration']<=4*(e['bar']+1)
        assert e['origin'].startswith('classical_') and e['source_event_ids']
        for t in e['transformations']:
            assert t['rule'].startswith('classical_') and set(t['source_event_ids'])<=sources.keys()
    files=[]
    for version in ('original','improved'):
        for texture in ('melody','arranged'):
            stem=f'{version}-{texture}'
            path=out/f'{stem}.mid'
            midi=mido.MidiFile(path)
            assert midi.length==32 and midi.ticks_per_beat==480
            assert len(midi.tracks)==(2 if texture=='melody' else 4)
            assert all(sum(m.time for m in t)==30720 for t in midi.tracks)
            assert [next(m.program for m in t if m.type=='program_change') for t in midi.tracks[1:]]==([73] if texture=='melody' else [73,32,0])
            for i in range(1,len(midi.tracks)):
                decoded=notes(path,i)
                assert all(0<=p<=127 and 0<=on<on+duration<=30720 and 1<=v<=127 for p,on,duration,v in decoded)
                if version=='improved':
                    assert decoded==expected(improved[('events','bass','chords')[i-1]])
            with wave.open(str(path.with_suffix('.wav'))) as stream:
                assert stream.getframerate()==22050 and stream.getsampwidth()==2 and stream.getnchannels()==1
                assert stream.getnframes()==705600
                audio=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2')/32768
                rms=float(np.sqrt(np.mean(audio**2)))
                peak=float(np.abs(audio).max())
                assert .001<rms<.7 and peak<=.951
            files.append(dict(name=stem,seconds=32,midi_sha256=digest(path.read_bytes()),
                wav_sha256=digest(path.with_suffix('.wav').read_bytes()),rms=rms,peak=peak))
    assert notes(out/'improved-melody.mid',1)==notes(out/'improved-arranged.mid',1)
    for name,h in reference['reference_files'].items():
        assert digest((out/f'original-{name}').read_bytes())==h
    for texture in ('melody','arranged'):
        a,b=[next(f['rms'] for f in files if f['name']==f'{v}-{texture}') for v in ('original','improved')]
        assert abs(20*np.log10(a/b))<.01
    manifest=json.loads((out/'manifest.json').read_bytes())
    for name,meta in manifest['files'].items():
        assert digest((out/name).read_bytes())==meta['sha256'] and (out/name).stat().st_size==meta['bytes']
    from html.parser import HTMLParser
    class Links(HTMLParser):
        def handle_starttag(self,tag,attrs):
            for k,v in attrs:
                if k in ('href','src'):assert (out/v).is_file(),v
    Links().feed((out/'listen.html').read_text(encoding='utf-8'))
    report=dict(verified_utc=datetime.now(timezone.utc).isoformat(),status='passed',files=files,
        preserved_raw_sha256=digest(source),original_outputs_unchanged=True,source_lineage_passed=True,
        pitch_class_changes=changed_pcs,melody_unchanged_by_accompaniment=True,
        loudness_delta_db_less_than=.01,browser='Separate actual browser checks required',subjective_listening='Pending user assessment')
    (out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    import sys
    verify(sys.argv[1])
