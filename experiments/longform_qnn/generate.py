"""Unrepaired autoregressive melody; separately labelled classical accompaniment."""
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time
import wave
import numpy as np
import torch
import mido
from .encoding import Event, context, event_from_token, dump_events
from .quantum import QuantumModel, qiskit_probabilities, normalize_legal, EPS
from .train import load_checkpoint

def next_event(model,history,onset,rng,mode='full',reference=False):
    x=context(history,onset,mode); remaining=8-onset%8
    with torch.no_grad():
        probabilities=model(torch.tensor(x[None,:]),torch.tensor([remaining])).numpy()[0]
    error=None
    if reference and isinstance(model,QuantumModel):
        reference_p=qiskit_probabilities(model.theta.detach().numpy(),x)
        reference_p=normalize_legal(torch.tensor(reference_p[None,:]),torch.tensor([remaining])).numpy()[0]
        error=float(np.max(np.abs(reference_p-probabilities)))
        if error > 1e-10: raise AssertionError('Generation Qiskit mismatch')
        probabilities=reference_p
    token=int(rng.choice(120,p=probabilities))
    event=event_from_token(token,onset)
    trace=dict(index=len(history),event=asdict(event),token=token,context=x.tolist(),
        probabilities=probabilities.tolist(),sample_probability=float(probabilities[token]),
        probability_semantics='exact, legal-duration-normalized 120-token distribution; q7 and rest register marginalized',
        origin='qnn_sample' if isinstance(model,QuantumModel) else 'classical_sample',qiskit_max_error=error)
    return event,trace

def sample(model,seed,bars=16,mode='full',reference=False):
    history=[]; trace=[]; onset=0; rng=np.random.default_rng(seed)
    start=time.perf_counter()
    while onset < bars*8:
        e,record=next_event(model,history,onset,rng,mode,reference)
        history.append(e); trace.append(record); onset+=e.units
    return history,dict(seed=seed,bars=bars,tempo_bpm=120,beginning='empty prefix; no prompt',
        duration_beats=bars*4,seconds=bars*2,events=trace,inference_seconds=time.perf_counter()-start,
        simulator='offline exact statevector' if isinstance(model,QuantumModel) else 'classical CPU',
        quantum_hardware_jobs=0,post_sampling_note_repair=False)

def structured(model,seed):
    history=[]; trace=[]; rng=np.random.default_rng(seed); onset=0
    start=time.perf_counter()
    for section in range(4):
        if section in (0,2):
            while onset < (section+1)*32:
                e,record=next_event(model,history,onset,rng,reference=True)
                record['section']='A' if section==0 else 'B'
                if section==2: record['origin']='qnn_conditioned_after_classical_A_prime'
                history.append(e); trace.append(record); onset+=e.units
        else:
            # Classical phrase operation, explicitly not learned repetition.
            source=[(i,e) for i,e in enumerate(history) if e.onset<32]
            shift=1 if section==1 else -1
            for idx,original in source:
                pitch=0 if not original.pitch else 1+(original.pitch-1+shift)%14
                e=Event(pitch,original.units,section*32+original.onset)
                trace.append(dict(index=len(history),event=asdict(e),token=e.token,
                    context=context(history,e.onset).tolist(),probabilities=None,sample_probability=None,
                    source_event_index=idx,origin='classical_phrase_transform',
                    section="A'" if section==1 else "A''",
                    transformation=f'diatonic shift {shift:+d}, wrap within 14 pitches; duration/rest preserved'))
                history.append(e); onset=e.onset+e.units
    return history,dict(seed=seed,bars=16,tempo_bpm=120,duration_beats=64,seconds=32,events=trace,
        form="A-A'-B-A''",inference_seconds=time.perf_counter()-start,
        quantum_hardware_jobs=0,limitation='A prime and A double-prime are documented classical transformations, not learned QNN dependencies')

def accompaniment():
    # Explicit deterministic C-major I-vi-IV-V progression, ending I.
    roots=[0,9,5,7,0,9,5,7,0,9,5,7,0,5,7,0]
    bass=[]; chords=[]
    for bar,root in enumerate(roots):
        bass.append((36+root,bar*4,4,50))
        third=3 if root==9 else 4
        chords.extend((48+(root+step)%12,bar*4,4,32) for step in (0,third,7))
    return bass,chords

def note_tracks(events,arranged=False):
    melody=[(e.midi,e.onset/2,e.units/2,84) for e in events if e.pitch]
    return [melody,*accompaniment()] if arranged else [melody]

def write_midi(events,path,arranged=False,bars=16):
    midi=mido.MidiFile(ticks_per_beat=480); conductor=mido.MidiTrack(); midi.tracks.append(conductor)
    conductor.extend([mido.MetaMessage('set_tempo',tempo=500000,time=0),
                      mido.MetaMessage('time_signature',numerator=4,denominator=4,time=0),
                      mido.MetaMessage('text',text='Offline long-form QNN melody; accompaniment/phrase transformations classical where declared',time=0),
                      mido.MetaMessage('end_of_track',time=bars*4*480)])
    for channel,notes in enumerate(note_tracks(events,arranged)):
        track=mido.MidiTrack(); midi.tracks.append(track)
        track.append(mido.MetaMessage('track_name',name=['QNN melody (see trace for form transforms)','Classical bass','Classical chords'][channel],time=0))
        track.append(mido.Message('program_change',program=[73,32,0][channel],channel=channel,time=0))
        schedule=[]
        for pitch,onset,duration,velocity in notes:
            schedule.extend([(round(onset*480),1,pitch,velocity),(round((onset+duration)*480),0,pitch,0)])
        previous=0
        for tick,on,pitch,velocity in sorted(schedule):
            track.append(mido.Message('note_on' if on else 'note_off',note=pitch,velocity=velocity,channel=channel,time=tick-previous));previous=tick
        track.append(mido.MetaMessage('end_of_track',time=bars*4*480-previous))
    midi.save(str(path))

def write_wav(events,path,arranged=False,bars=16,rate=22050):
    """Deterministic additive audition synth, not a sampled instrument or quality claim."""
    audio=np.zeros(round(bars*2*rate),dtype=np.float64)
    for channel,notes in enumerate(note_tracks(events,arranged)):
        for pitch,onset,duration,velocity in notes:
            start=round(onset*.5*rate); count=round(duration*.5*rate)
            t=np.arange(count)/rate; frequency=440*2**((pitch-69)/12)
            tone=sum(np.sin(2*np.pi*frequency*k*t)/k**2 for k in (1,2,3))
            envelope=np.minimum(1,t/.012)*np.minimum(1,(count/rate-t)/.035)
            audio[start:start+count]+=tone*envelope*(velocity/127)*(.32 if channel==0 else .16)
    peak=float(np.max(np.abs(audio)))
    if peak > .95: audio*=.95/peak
    pcm=(audio*32767).astype('<i2')
    with wave.open(str(path),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(pcm.tobytes())
    return dict(sample_rate=rate,seconds=len(audio)/rate,rms=float(np.sqrt(np.mean(audio**2))),peak=float(np.max(np.abs(audio))),synthesis='deterministic additive 3-harmonic CPU synth')

def diagnostics(events,training_pieces):
    tokens=[e.token for e in events]; pitches=[e.pitch for e in events if e.pitch]
    train_sequences=[[e['pitch']*8+e['units']-1 for e in p['events']] for p in training_pieces]
    def grams(seq,n): return {tuple(seq[i:i+n]) for i in range(len(seq)-n+1)}
    training8=set().union(*(grams(s,8) for s in train_sequences)); generated8=grams(tokens,8)
    max_match=0
    for seq in train_sequences:
        previous=np.zeros(len(seq)+1,dtype=int)
        for token in tokens:
            current=np.zeros(len(seq)+1,dtype=int)
            for j,value in enumerate(seq):
                if token==value:current[j+1]=previous[j]+1
            max_match=max(max_match,int(current.max()));previous=current
    bar_means=np.array([np.mean([e.pitch for e in events if e.pitch and e.onset//8==bar]) if any(e.pitch and e.onset//8==bar for e in events) else 0 for bar in range(16)])
    lag=float(np.corrcoef(bar_means[:-4],bar_means[4:])[0,1]) if np.std(bar_means[:-4]) and np.std(bar_means[4:]) else None
    generated=np.bincount([e.units-1 for e in events],minlength=8).astype(float);generated/=generated.sum()
    empirical=np.bincount([e['units']-1 for p in training_pieces for e in p['events']],minlength=8).astype(float);empirical/=empirical.sum()
    mixture=(generated+empirical)/2
    def kl(p,q):return float(np.sum(p[p>0]*np.log(p[p>0]/q[p>0])))
    return dict(events=len(events),distinct_pitches=len(set(pitches)),distinct_durations=len({e.units for e in events}),
        pitch_distribution=dict(Counter(e.pitch for e in events)),duration_units_distribution=dict(Counter(e.units for e in events)),
        unique_token_fraction=len(set(tokens))/len(tokens),training_8gram_match_fraction=len(generated8&training8)/max(1,len(generated8)),
        longest_training_token_match=max_match,rhythm_js_divergence=.5*(kl(generated,mixture)+kl(empirical,mixture)),
        repeated_4gram_fraction=1-len(grams(tokens,4))/max(1,len(tokens)-3),
        mean_absolute_diatonic_interval=float(np.mean(np.abs(np.diff(pitches)))) if len(pitches)>1 else 0,
        previous_four_bar_mean_pitch_correlation=lag,last_sounding_pitch=pitches[-1] if pitches else None,
        ends_on_tonic=bool(pitches and (pitches[-1]-1)%7==0),
        limitations='Single generated sample diagnostics; no listener evaluation, learned phrase/cadence or originality guarantee')

def export_example(model,checkpoint,seed,out,training_pieces,form=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    events,trace=structured(model,seed) if form else sample(model,seed,reference=True)
    trace.update(model_version='longform-qnn-v1',checkpoint_sha256=hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest(),
                 probability_stabilization_epsilon=EPS,simulator='offline exact statevector, every sampled QNN event checked against Qiskit',
                 context_features=80,trainable_angles=48,qubits=8,measured_qubits=7,
                 accompaniment='Classical deterministic I-vi-IV-V / I-IV-V-I, no melody repair',diagnostics=diagnostics(events,training_pieces))
    audio={}
    for arranged in (False,True):
        label='arranged' if arranged else 'melody'
        write_midi(events,out/f'{label}.mid',arranged)
        audio[label]=write_wav(events,out/f'{label}.wav',arranged)
    trace['audio']=audio
    (out/'generation.json').write_text(json.dumps(trace,indent=2))
    return trace
