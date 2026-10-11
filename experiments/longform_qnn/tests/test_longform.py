import json
import time
import wave
from pathlib import Path
import numpy as np
import pytest
import torch
import mido
from experiments.longform_qnn.encoding import (Event, FEATURES, AGGREGATION, OUTPUT_TOKENS,
    context, teacher_examples, event_from_token)
from experiments.longform_qnn.quantum import (QuantumModel, build_circuit, bind_parameters,
    qiskit_probabilities, verify_equivalence, normalize_legal)
from experiments.longform_qnn.data import source_groups, half_units, Reject, load_examples
from experiments.longform_qnn.train import inputs, save_checkpoint, load_checkpoint, train_one
from experiments.longform_qnn.generate import sample, structured, write_midi, write_wav

torch.set_num_threads(1)

def history():
    return [Event(1+(i//2)%14,2,i) for i in range(0,64,2)]

def test_qiskit_dimensions_parameter_binding_and_order():
    qc,theta,data=build_circuit(measure=True)
    assert qc.num_qubits==8 and qc.num_clbits==7 and len(theta)==len(data)==48
    assert [p.index for p in theta]==list(range(48))
    bound=bind_parameters(np.arange(48)*.01,np.zeros(FEATURES))
    assert bound.num_parameters==0
    assert [bound.data[i].operation.name for i in range(8)]==['h']*8

@pytest.mark.parametrize('index,pitch,units',[(0,0,1),(8,0,1),(1,1,1),(9,8,1),(127,14,8),(112,0,8)])
def test_little_endian_encoding(index,pitch,units):
    e=event_from_token(OUTPUT_TOKENS[index],0)
    assert (e.pitch,e.units)==(pitch,units)
    assert e.midi is None if pitch==0 else 60 <= e.midi <= 83

def test_ancilla_marginalization_and_rest_aggregation():
    model=QuantumModel(3); x=torch.zeros(1,FEATURES,dtype=torch.float64)
    state=model.statevector(x)
    measured=state.abs().square().reshape(1,2,128).sum(1)
    semantic=model.joint(x)
    assert torch.allclose(semantic[0,0],measured[0,0]+measured[0,8])
    assert torch.allclose(semantic.sum(1),torch.ones(1,dtype=torch.float64))
    assert np.allclose(AGGREGATION.sum(axis=1),1)
    assert AGGREGATION[:,0].sum()==2 and AGGREGATION[:,8].sum()==1

@pytest.mark.parametrize('remaining',[1,2,3,4,5,6,7,8])
def test_legal_normalization(remaining):
    p=normalize_legal(torch.zeros(2,120,dtype=torch.float64),torch.tensor([remaining,remaining]))
    assert torch.allclose(p.sum(1),torch.ones(2,dtype=torch.float64))
    assert torch.all(p[:,torch.arange(120)%8+1>remaining]==0)
    assert torch.all(p[:,torch.arange(120)%8+1<=remaining]>0)

def test_qiskit_training_equivalence():
    assert verify_equivalence()['max_absolute_error']<1e-10

def test_gradients_finite_difference_and_no_dead_final_phase():
    model=QuantumModel(11); x=torch.tensor(np.random.default_rng(4).normal(0,.2,(3,FEATURES)))
    r=torch.tensor([8,4,2]); y=torch.tensor([10,26,48])
    def loss():return -torch.log(model(x,r)[torch.arange(3),y]).mean()
    loss().backward(); analytic=model.theta.grad.clone(); epsilon=1e-5
    for index in (0,7,17,32,47):
        original=float(model.theta[index].detach())
        with torch.no_grad():model.theta[index]=original+epsilon
        plus=float(loss().detach())
        with torch.no_grad():model.theta[index]=original-epsilon
        minus=float(loss().detach())
        with torch.no_grad():model.theta[index]=original
        assert np.isclose(float(analytic[index]),(plus-minus)/(2*epsilon),atol=1e-7,rtol=1e-5)
    assert abs(float(analytic[47]))>1e-7

def test_causal_prefix_future_mutation_and_long_history():
    events=history(); xs,_,_=teacher_examples(events)
    altered=events[:20]+[Event(14,e.units,e.onset) for e in events[20:]]
    assert np.array_equal(xs[:21],teacher_examples(altered)[0][:21])
    with pytest.raises(ValueError,match='Future'):context(events,events[3].onset)
    assert np.any(context(events,64)[40:])
    assert np.all(context(events,64,'short')[40:]==0)
    assert np.array_equal(context(events,64)[:40],context(events,64,'short')[:40])

def test_grouped_source_isolation_and_duplicate_editions():
    rows=[dict(source='a',bwv='1.1',title='Hymn A',riemenschneider=1),
          dict(source='b',bwv='1.2',title='Other',riemenschneider=2),
          dict(source='c',bwv='2',title='Hymn A',riemenschneider=3)]
    grouped=source_groups(rows)
    assert len({r['group'] for r in grouped})==len({r['split'] for r in grouped})==1
    assert grouped==source_groups(rows)

def test_no_test_content_access_and_no_silent_quantization(tmp_path):
    with pytest.raises(ValueError,match='Test'):load_examples(tmp_path,'test')
    with pytest.raises(Reject):half_units(.25)
    assert half_units(1.5)==3

def test_preprocessing_preserves_rests_and_explicit_tied_bar_segments(monkeypatch):
    from music21 import stream,note,meter,key,tie
    from experiments.longform_qnn.data import preprocess
    score=stream.Score();part=stream.Part();score.append(part)
    for i in range(4):
        bar=stream.Measure(number=i+1)
        if i==0:bar.append(meter.TimeSignature('4/4'))
        n=note.Rest(quarterLength=4) if i==2 else note.Note('C4',quarterLength=4)
        if i<2:n.tie=tie.Tie('start' if i==0 else 'stop')
        bar.append(n);part.append(bar)
    monkeypatch.setattr(score,'analyze',lambda method:key.Key('C'))
    events,report=preprocess(score)
    assert [(e.pitch,e.units,e.onset) for e in events]==[(1,8,0),(1,8,8),(0,8,16),(1,8,24)]
    assert events[1].continuation and report['split_at_barlines']==1

def test_reserved_sources_are_not_parsed(monkeypatch,tmp_path):
    from music21 import corpus
    from experiments.longform_qnn import data
    rows=[dict(source=f'{s}-{i}',split=s,group=f'{s}-{i}',bwv=str(i),title=s,riemenschneider=i)
          for s in ('train','validation','test') for i in range(2)]
    seen=[]
    monkeypatch.setattr(data,'metadata',lambda:rows)
    def parse(name,**kwargs):
        assert not name.startswith('test');seen.append(name);return name
    monkeypatch.setattr(corpus,'parse',parse)
    monkeypatch.setattr(data,'preprocess',lambda name:([Event(1 if name.startswith('train') else 2,8,i*8) for i in range(4)],{}))
    report=data.prepare(tmp_path)
    assert len(seen)==4 and report['test_scores_opened']==0 and not (tmp_path/'test.json').exists()

def test_reproducible_sampling_and_exact_length():
    model=QuantumModel(2)
    a,ta=sample(model,919);b,tb=sample(model,919)
    assert a==b and ta['events']==tb['events']
    assert sum(e.units for e in a)==128 and a[-1].onset+a[-1].units==128
    assert all(e.onset%8+e.units<=8 for e in a)

def test_checkpoint_reproduction_and_training(tmp_path):
    arrays=teacher_examples(history()[:12]); reports=[];weights=[]
    for label in ('a','b'):
        out=tmp_path/label;out.mkdir()
        model,report,_=train_one('qnn_full',9,arrays,arrays,out,3,8,time.perf_counter()+90)
        reports.append(report);weights.append(model.theta.detach().numpy())
        restored,_=load_checkpoint(out/'qnn_full-9.json')
        assert torch.equal(model.theta,restored.theta)
    assert np.array_equal(*weights)
    assert reports[0]['checkpoint_sha256']==reports[1]['checkpoint_sha256']

def test_history_ablation_preserves_short_features_targets_and_allocation():
    arrays=teacher_examples(history());full=inputs(arrays);short=inputs(arrays,'short');permuted=inputs(arrays,permute_seed=9)
    assert torch.equal(full[0][:,:40],short[0][:,:40]) and torch.equal(full[0][:,:40],permuted[0][:,:40])
    assert torch.equal(full[1],short[1]) and torch.equal(full[2],permuted[2])
    assert torch.count_nonzero(short[0][:,40:])==0

def test_midi_wav_validity_and_classical_labelled_form(tmp_path):
    model=QuantumModel(4);events,trace=structured(model,51)
    assert len({r['origin'] for r in trace['events']})==3
    assert all(r['probabilities'] is None for r in trace['events'] if r['origin']=='classical_phrase_transform')
    for arranged in (False,True):
        path=tmp_path/f'{arranged}.mid';write_midi(events,path,arranged)
        midi=mido.MidiFile(path)
        assert midi.ticks_per_beat==480 and abs(midi.length-32)<1e-8
        assert all(sum(m.time for m in t)==64*480 for t in midi.tracks)
        assert all(0<=m.note<=127 and 0<m.velocity<=127 for t in midi.tracks for m in t if m.type=='note_on')
        wav=tmp_path/f'{arranged}.wav';stats=write_wav(events,wav,arranged)
        with wave.open(str(wav)) as audio:assert audio.getnframes()/audio.getframerate()==32
        assert .001<stats['rms']<.7 and stats['peak']<=.951
    notes=lambda p:[(m.note,m.velocity,m.time) for m in mido.MidiFile(p).tracks[1] if m.type in ('note_on','note_off')]
    assert notes(tmp_path/'False.mid')==notes(tmp_path/'True.mid')
