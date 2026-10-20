"""One unfiltered QCBM sample followed by deterministic, traceable classical rules."""
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import qiskit
from qiskit.quantum_info import Statevector
from quantum_duet.circuit import build_circuit, bind_parameters

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'components/quantum_duet/src/quantum_duet/data'
SEED = 20261011  # declared before sampling; no search, auditions or rejection sampling
SCALE = (0, 2, 4, 5, 7, 9, 11)
RHYTHMS = ((1, 1, 1, 1), (1.5, .5, 1, 1), (.5, .5, 1, 2), (1, .5, .5, 2))
SECTIONS = ('A', "A'", 'B', "A''")
CHORDS = {'I': (0, 4, 7), 'ii': (2, 5, 9), 'iii': (4, 7, 11),
          'IV': (5, 9, 0), 'V': (7, 11, 2), 'vi': (9, 0, 4)}
OPTIONS = (('I',), ('IV', 'ii'), ('vi', 'I'), ('V',),
           ('I',), ('IV', 'ii'), ('ii', 'IV'), ('V',),
           ('vi',), ('iii', 'I'), ('IV', 'ii'), ('V',),
           ('I',), ('IV', 'ii'), ('V',), ('I',))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def decode(index):
    """Basis integer q11..q0; four little-endian three-qubit registers."""
    return [(int(index) >> (3 * i)) & 7 for i in range(4)]


def sample_motifs(seed=SEED):
    checkpoint = ASSETS / 'melody_angles.json'
    contents = checkpoint.read_bytes()
    model = json.loads(contents)
    circuit = bind_parameters(build_circuit(), model['parameters_radians'])
    probabilities = Statevector.from_instruction(circuit).probabilities()
    total = float(probabilities.sum())
    if len(probabilities) != 4096 or not np.isfinite(probabilities).all() or abs(total - 1) > 1e-10:
        raise ValueError('Invalid exact frozen-model distribution')
    probabilities = probabilities / total  # only floating-point mass correction
    rng = np.random.Generator(np.random.PCG64(seed))
    draws = rng.choice(4096, size=16, replace=True, p=probabilities)
    motifs = [dict(motif_id=f'm{i:02}', draw_index=i, basis_index=int(value),
                   bitstring=format(int(value), '012b'), tokens=decode(value),
                   exact_probability=float(probabilities[value])) for i, value in enumerate(draws)]
    raw = dict(schema='oxfordq.qcbm-motif-sample.v1', seed=seed, rng='NumPy PCG64',
               numpy_version=np.__version__, qiskit_version=qiskit.__version__,
               python_version=platform.python_version(), qubits=12, parameters=84,
               checkpoint_file='components/quantum_duet/src/quantum_duet/data/melody_angles.json',
               checkpoint_file_sha256=digest(contents), checkpoint_canonical_sha256=digest(canonical(model)),
               original_checkpoint_sha256=model['source_checkpoint_sha256'],
               circuit_source_sha256=digest((ASSETS.parent / 'circuit.py').read_bytes()),
               distribution_sha256=digest(np.asarray(probabilities, dtype='<f8').tobytes()),
               probability_mass_before_normalization=total,
               bit_order='Displayed q11..q0; motif token i = (basis_index >> (3*i)) & 7',
               token_mapping='0 rest; 1..7 C4 D4 E4 F4 G4 A4 B4 before classical transformations',
               execution='OFFLINE exact local statevector; 16 independent categorical draws with replacement',
               backend_jobs=0, training_steps=0, candidate_draws=16, rejected_draws=0,
               selection='All draws saved in original order; no quality filtering or resampling', motifs=motifs)
    return raw


def base_pitch(token):
    return None if token == 0 else 60 + SCALE[token - 1]


def raw_events(raw):
    """Independent compositional reference; NOT Quantum Duet raw evidence."""
    return [dict(event_id=f'raw:{m["motif_id"]}:n{j}', source_event_id=f'{m["motif_id"]}:n{j}',
                 pitch=base_pitch(token), onset=m['draw_index'] * 4 + j, duration=1., velocity=82,
                 rest=token == 0, sampled_token=token, origin='sampled_pitch_mapping', transformations=[])
            for m in raw['motifs'] for j, token in enumerate(m['tokens'])]


def compose(raw):
    """Every output points to immutable raw tokens; unused positions are reported.

    A = m0..3. A' first two notes repeat A; final two use m4..7.
    B = m8..11. A'' first three repeat A; final note uses m12..15.
    This deterministic source schedule uses all 16 sampled motifs, not all 64 tokens.
    """
    result = []
    previous = 67
    for bar in range(16):
        section, local = divmod(bar, 4)
        onset = bar * 4.
        for j, slot in enumerate(RHYTHMS[section]):
            repeated = section == 1 and j < 2 or section == 3 and j < 3
            source_bar = local if repeated else bar
            token = raw['motifs'][source_bar]['tokens'][j]
            initial = base_pitch(token)
            changes = []
            if repeated:
                changes.append(dict(rule='classical_theme_repetition', from_bar=local, source_note=j))
            pitch = initial
            if pitch is not None:
                target = (65, 72, 69, 65)[section]
                choices = [pitch, pitch + 12]
                # Same sampled pitch class; deterministic nearest register with a section target.
                pitch = min(choices, key=lambda p: (abs(p - previous) + .45 * abs(p - target), p))
                if pitch != initial:
                    changes.append(dict(rule='classical_octave_placement', semitones=pitch - initial))
                previous = pitch
            duration = slot * (.90 if j < 3 else 1.)
            changes.append(dict(rule='classical_rhythm_and_gate', onset_in_bar=onset - 4 * bar,
                                slot_beats=slot, sounding_beats=duration, reference_duration=1.))
            result.append(dict(event_id=f'composition:b{bar:02}:n{j}', bar=bar, section=SECTIONS[section],
                               source_event_id=f'm{source_bar:02}:n{j}', assigned_motif=f'm{bar:02}',
                               sampled_token=token, sampled_pitch=initial, pitch=pitch, rest=token == 0,
                               onset=onset, duration=duration, slot_beats=slot, velocity=82,
                               origin='classically_developed_from_qcbm_sample', transformations=changes))
            onset += slot
    # Cadences are explicitly imposed, only on an already sounding phrase-final event.
    for bar, target_pc in ((3, 7), (7, 7), (11, 11), (15, 0)):
        sounding = [e for e in result if e['bar'] == bar and not e['rest']]
        if not sounding:
            continue
        event = sounding[-1]
        old_pitch, old_duration = event['pitch'], event['duration']
        event['pitch'] = min((60 + target_pc, 72 + target_pc), key=lambda p: (abs(p - old_pitch), p))
        # Never overwrite an explicit following sampled rest.
        event['duration'] = event['slot_beats']
        event['transformations'].append(dict(rule='classical_phrase_ending',
            previous_pitch=old_pitch, pitch=event['pitch'], previous_duration=old_duration,
            duration=event['duration'], target_pitch_class=target_pc))
    used = {e['source_event_id'] for e in result}
    unused = [e['source_event_id'] for e in raw_events(raw) if e['source_event_id'] not in used]
    return dict(events=result, unused_sampled_positions=unused,
                unused_reason='Fixed A-prime/A-double-prime repetition schedule replaces positions, never sample-quality selection',
                source_schedule='A all m00..03; A-prime first 2 from A, last 2 m04..07; B all m08..11; A-double-prime first 3 from A, last m12..15')


def harmonize(events):
    """Constrained functional harmony, duration-weighted overlap, deterministic ties."""
    harmony, bass, chords = [], [], []
    for bar, options in enumerate(OPTIONS):
        notes = [e for e in events if e.get('bar') == bar and not e['rest']]
        scores = {name: sum(e['duration'] for e in notes if e['pitch'] % 12 in CHORDS[name]) for name in options}
        name = max(options, key=lambda item: scores[item])  # fixed declared order wins ties
        pcs = CHORDS[name]
        harmony.append(dict(bar=bar, chord=name, pitch_classes=list(pcs), candidates=scores,
                            origin='classical_functional_harmony'))
        for beat, offset in ((0, pcs[0]), (2, (pcs[0] + 7) % 12)):
            bass.append(dict(pitch=36 + offset, onset=4 * bar + beat, duration=1.85, velocity=54))
        for pc in pcs:
            chords.append(dict(pitch=48 + pc, onset=4 * bar, duration=3.8, velocity=34))
    return harmony, bass, chords
