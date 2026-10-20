import copy
import json
import wave

import mido
import numpy as np
import pytest
from qiskit.providers.basic_provider import BasicSimulator

from experiments.qcbm_composition.composition import (
    ROOT, ASSETS, SEED, sample_motifs, decode, raw_events, compose, harmonize, canonical, digest)
from experiments.qcbm_composition.__main__ import run
from experiments.qcbm_composition.render import export
from experiments.qcbm_composition.compare import comparisons


@pytest.fixture(scope='module')
def raw():
    return sample_motifs()


def test_exact_sample_and_bit_order_reproducible(raw):
    assert raw == sample_motifs(SEED)
    assert len(raw['motifs']) == raw['candidate_draws'] == 16
    assert raw['rejected_draws'] == raw['backend_jobs'] == raw['training_steps'] == 0
    assert decode(1 + (2 << 3) + (3 << 6) + (7 << 9)) == [1, 2, 3, 7]
    for motif in raw['motifs']:
        assert motif['basis_index'] == int(motif['bitstring'], 2)
        assert motif['tokens'] == decode(motif['basis_index'])
        assert 0 < motif['exact_probability'] <= 1
    assert raw['checkpoint_file_sha256'] == digest((ASSETS / 'melody_angles.json').read_bytes())
    assert raw['original_checkpoint_sha256'] == 'ecd7faaa232a15c261a5e3daf8047e0b4d71be9f4eb4bb597e70acb671c5b8a4'


def test_composition_determinism_and_immutable_raw(raw):
    before = canonical(raw)
    a, b = compose(raw), compose(copy.deepcopy(raw))
    assert a == b
    assert before == canonical(raw)
    assert len(a['events']) == 64 and len(a['unused_sampled_positions']) == 20
    assert {e['source_event_id'].split(':')[0] for e in a['events']} == {f'm{i:02}' for i in range(16)}


def test_every_event_resolves_to_sample_and_changes_are_explicit(raw):
    sources = {e['source_event_id']: e for e in raw_events(raw)}
    events = compose(raw)['events']
    for e in events:
        source = sources[e['source_event_id']]
        assert source['pitch'] == e['sampled_pitch'] and source['sampled_token'] == e['sampled_token']
        assert e['rest'] == (e['pitch'] is None) == source['rest']
        assert e['origin'] == 'classically_developed_from_qcbm_sample'
        if e['pitch'] != source['pitch']:
            assert any(t['rule'] in ('classical_octave_placement', 'classical_phrase_ending') for t in e['transformations'])
        assert 0 < e['duration'] <= e['slot_beats']
        assert 0 <= e['onset'] < e['onset'] + e['duration'] <= 64
        assert e['pitch'] is None or 60 <= e['pitch'] <= 83
        assert 1 <= e['velocity'] <= 127
    assert len([e for e in events if any(t['rule'] == 'classical_theme_repetition' for t in e['transformations'])]) == 20
    for bar in range(16):
        notes = [e for e in events if e['bar'] == bar]
        assert sum(e['slot_beats'] for e in notes) == 4
        assert notes[0]['onset'] == bar * 4 and notes[-1]['onset'] + notes[-1]['slot_beats'] == bar * 4 + 4


def test_all_rest_motifs_stay_rests_and_no_cadence_invention(raw):
    silent = copy.deepcopy(raw)
    for motif in silent['motifs']:
        motif['tokens'] = [0] * 4
    assert all(e['pitch'] is None for e in compose(silent)['events'])


def test_harmony_deterministic_no_melody_repair(raw):
    events = compose(raw)['events']; before = copy.deepcopy(events)
    assert harmonize(events) == harmonize(events)
    assert events == before
    harmony, bass, chords = harmonize(events)
    assert len(harmony) == 16 and len(bass) == 32 and len(chords) == 48
    assert [harmony[i]['chord'] for i in (3, 7, 11, 15)] == ['V', 'V', 'V', 'I']


def read_notes(path, track=1):
    clock = 0; active = {}; notes = []
    midi = mido.MidiFile(path)
    for msg in midi.tracks[track]:
        clock += msg.time
        if msg.type == 'note_on' and msg.velocity:
            assert msg.note not in active
            active[msg.note] = (clock, msg.velocity)
        elif msg.type == 'note_off' or msg.type == 'note_on' and not msg.velocity:
            start, velocity = active.pop(msg.note)
            notes.append((msg.note, start, clock - start, velocity))
    assert not active
    return sorted(notes)


def test_full_export_no_jobs_and_protected_sources_unchanged(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Experiment must never call a backend')
    monkeypatch.setattr(BasicSimulator, 'run', forbidden)
    protected = list(ASSETS.glob('*.json')) + [ROOT / 'components/quantum_duet/tests/fixtures/qollab-local-run.json',
                                             ROOT / 'docs/fixtures/run-result.v1.json']
    before = {str(p): p.read_bytes() for p in protected}
    trace = run(tmp_path)
    assert before == {str(p): p.read_bytes() for p in protected}
    assert digest((tmp_path / 'raw-samples.json').read_bytes()) == trace['raw_samples_sha256']
    assert trace['backend_jobs'] == 0 and 'statistics' not in trace
    expected = sorted((e['pitch'], round(e['onset'] * 480), round(e['duration'] * 480), e['velocity'])
                      for e in trace['events'] if e['pitch'] is not None)
    for name in ('melody', 'arranged', 'sampled-reference'):
        midi = mido.MidiFile(tmp_path / f'{name}.mid')
        assert midi.length == 32 and midi.ticks_per_beat == 480
        assert all(sum(m.time for m in t) == 30720 for t in midi.tracks)
        assert all(0 <= m.note <= 127 and 0 < m.velocity <= 127 for t in midi.tracks for m in t if m.type == 'note_on')
        with wave.open(str(tmp_path / f'{name}.wav')) as wav:
            assert wav.getnframes() / wav.getframerate() == 32
            samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2') / 32768
            assert .001 < np.sqrt(np.mean(samples**2)) < .7
            assert np.abs(samples).max() < .951
        if name != 'sampled-reference':
            assert read_notes(tmp_path / f'{name}.mid') == expected
    # Original evidence comparison faithfully retains the recorded Alice MIDI events.
    original = json.loads(protected[-2].read_bytes())
    expected_original = sorted((e['pitch_midi'], round(e['onset_beats']*480), round(e['duration_beats']*480), 80)
                              for e in original['events']['quantum'] if e['voice'] == 'alice' and not e['rest'])
    assert read_notes(tmp_path / 'original-four-bar-melody.mid') == expected_original
    comp = json.loads((tmp_path / 'comparison.json').read_bytes())
    assert comp['sources'][0]['original_statistics'] == original['statistics']
    assert comp['qnn_availability']['free'].startswith('unavailable')


def test_export_reproducibility(raw, tmp_path):
    events = compose(raw)['events']
    for name in ('one', 'two'):
        export(tmp_path, name, [('melody', events)])
    for extension in ('wav', 'mid'):
        assert (tmp_path / f'one.{extension}').read_bytes() == (tmp_path / f'two.{extension}').read_bytes()


def test_qnn_comparison_decodes_unchanged_events(tmp_path, raw):
    source = tmp_path / 'source'
    for name in ('free', 'structured'):
        (source / name).mkdir(parents=True)
        (source / name / 'generation.json').write_text(json.dumps(dict(model_version='longform-qnn-v1',
            duration_beats=64, checkpoint_sha256='synthetic-test-only', seed=1,
            events=[dict(event=dict(pitch=1 if i % 2 else 0, units=8, onset=i*8)) for i in range(16)])))
    result = comparisons(tmp_path, compose(raw)['events'], raw_events(raw), source)
    assert result['qnn_availability']['free'].startswith('included')
    assert len(read_notes(tmp_path / 'qnn-free-melody.mid')) == 8
