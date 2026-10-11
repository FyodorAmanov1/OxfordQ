import json
import math
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.providers.basic_provider import BasicSimulator
from qiskit.quantum_info import Statevector

from quantum_duet import joint_cue as j
from quantum_duet.duet_quantum import REFERENCE_ANGLES, exact_outcomes

ASSETS = Path(__file__).resolve().parents[1]/'src/quantum_duet/data'
FROZEN = json.loads((ASSETS/'selected_angles.json').read_text())['parameters_radians']


@pytest.mark.parametrize('name,sha', [
    ('diagnostic-32', 'c8eda2bfff5c77fd6db6f6d290714fc92bce374c40f14d1bd580ffc9d627e871'),
    ('application-32', 'f25708db79a0d9301b019a6a9562736a488b1cadef146342d365580fccc1cfaa'),
])
def test_recorded_actual_ionq_result_reconstructs_without_jobs(name, sha, monkeypatch):
    import hashlib
    def denied(*args, **kwargs):
        raise AssertionError('Evidence replay must not submit a backend job')
    monkeypatch.setattr(BasicSimulator, 'run', denied)
    original = (ASSETS.parents[2]/'evidence/joint-cue'/f'{name}.json').read_bytes()
    assert hashlib.sha256(original).hexdigest() == sha
    take = json.loads(original)
    restored = j.assemble_joint(take['joint_histogram_yxba'], take['execution'],
                               *j.load_assets(ASSETS),
                               j.prepare_presentation(int(take['randomness']['presentation_master_seed'])))
    for key in ['rounds', 'events', 'statistics', 'cue_sequence', 'excerpt']:
        assert restored[key] == take[key]
    assert take['execution']['backend_run_calls'] == 1
    assert take['execution']['circuit_count'] == 1
    assert sum(take['joint_histogram_yxba'].values()) == 32


@pytest.mark.parametrize('angles', [REFERENCE_ANGLES, FROZEN, [.23,-1.7,2.4,.9]])
def test_exact_conditional_equivalence_and_cues(angles):
    p = Statevector.from_instruction(j.build_joint_circuit(angles, measure=False)).probabilities()
    for x, y in j.SETTINGS:
        group = p[4*x+8*y:4*x+8*y+4]
        assert group.sum() == pytest.approx(.25, abs=1e-14)
        assert group*4 == pytest.approx(exact_outcomes(angles,x,y), abs=1e-14)
        assert (group[[0,2]].sum(), group[[0,1]].sum()) == pytest.approx((.125,.125))
    if tuple(angles)==REFERENCE_ANGLES:
        assert j.exact_metrics(angles)['expected_success'] == pytest.approx(np.cos(np.pi/8)**2)


def test_own_cue_only_wiring_and_compilation():
    source=j.build_joint_circuit(FROZEN)
    controls=[tuple(source.find_bit(q).index for q in inst.qubits) for inst in source.data if inst.operation.name=='cry']
    assert controls==[(2,0),(3,1)]
    measured=[(source.find_bit(i.qubits[0]).index,source.find_bit(i.clbits[0]).index) for i in source.data if i.operation.name=='measure']
    assert measured==[(i,i) for i in range(4)]
    compiled=j.compile_joint(FROZEN)
    assert set(compiled.count_ops()) <= set(j.QIS)|{'measure'}
    assert Statevector.from_instruction(source.remove_final_measurements(inplace=False)).equiv(Statevector.from_instruction(compiled.remove_final_measurements(inplace=False)))


@pytest.mark.parametrize('n',range(16))
def test_yxba_bit_order(n):
    assert j.decode_joint(f'{n:04b}') == ((n>>2)&1,(n>>3)&1,n&1,(n>>1)&1)


def test_real_sdk_serialization_no_network(monkeypatch):
    def denied(*args,**kwargs): raise AssertionError('Network forbidden')
    monkeypatch.setattr('requests.sessions.Session.request',denied)
    from qiskit_ionq.helpers import qiskit_to_ionq,decompress_metadata_string
    from qiskit.providers import Options
    backend=SimpleNamespace(name='ionq_simulator',gateset=lambda:'qis',options=Options(noise_model='aria-1',sampler_seed=None))
    payload=json.loads(qiskit_to_ionq(j.compile_joint(FROZEN),backend,{'shots':32}))
    assert payload['type']=='ionq.circuit.v1' and payload['shots']==32
    assert payload['input']['qubits']==4 and 'circuit' in payload['input']
    assert decompress_metadata_string(payload['metadata']['qiskit_header'])['meas_mapped']==[0,1,2,3]


def test_unequal_empty_and_all_shots():
    counts={'0000':2,'0010':1,'0100':7,'1000':4,'1110':2}
    stats=j.joint_statistics(counts)
    assert [r['shots'] for r in stats['allocation']]==[3,4,7,2]
    p=(2/3+1+1+1)/4
    assert stats['expected_success']==pytest.approx(p)
    assert stats['chsh']==pytest.approx(8*p-4)
    assert stats['pooled_success']==pytest.approx(15/16)
    radius=math.sqrt(math.log(40)/2*sum(1/(16*n) for n in [3,4,7,2]))
    assert stats['hoeffding_radius']==pytest.approx(radius)
    assert stats['success_interval']==pytest.approx([max(0,p-radius),min(1,p+radius)])
    empty=j.joint_statistics({'0000':32})
    assert empty['expected_success'] is None and empty['chsh'] is None and empty['success_interval'] is None
    assert empty['pooled_success']==1 and empty['total_independent_shots']==32


@pytest.mark.parametrize('counts',[{'0000':.5},{'0000':True},{'0000':-1},{'00':32},{'0000':0}])
def test_invalid_counts(counts):
    with pytest.raises(ValueError): j.validate_counts(counts)


class RecordingSimulator(BasicSimulator):
    def __init__(self,fail=False):
        super().__init__(); self.calls=[];self.fail=fail
    def run(self,circuit,**kwargs):
        assert isinstance(circuit,QuantumCircuit) and circuit.num_qubits==4
        self.calls.append((circuit,kwargs))
        if self.fail: raise RuntimeError('Deliberate provider failure')
        return super().run(circuit,seed_simulator=32003,**kwargs)


def test_single_call_precommitment_provenance_and_no_redraw(monkeypatch,tmp_path):
    backend=RecordingSimulator()
    original=j.prepare_presentation;preparations=[]
    def prepare(seed):
        assert not backend.calls
        p=original(seed);preparations.append(p);return p
    monkeypatch.setattr(j,'prepare_presentation',prepare)
    take=json.loads(j.generate_joint(backend,32,20261011,asset_dir=ASSETS))
    assert len(backend.calls)==1 and take['execution']['returned_shots']==32
    assert take['execution']['circuit_count']==1 and take['contract_version']==j.CONTRACT
    assert take['randomness']['cue_redraws']==0 and take['base_melody']['generated_now'] is False
    assert take['base_melody']['tokens']==json.loads((ASSETS/'recorded_melody.json').read_text())['tokens']
    used=Counter(r['source_measurement']['displayed_yxba'] for r in take['rounds']['quantum'])
    assert all(n<=take['joint_histogram_yxba'][bits] for bits,n in used.items())
    for q,c in zip(take['rounds']['quantum'],take['rounds']['classical']):
        assert (q['x'],q['y'],q['a'],q['b'])==j.decode_joint(q['source_measurement']['displayed_yxba'])
        assert (q['x'],q['y'],q['round_id'],q['base_token'])==(c['x'],c['y'],c['round_id'],c['base_token'])
        assert c['a']==c['shared_strategy'][c['x']] and c['b']==c['shared_strategy'][2+c['y']]
    for policy in ('quantum','classical'):
        assert len(take['events'][policy])==32
        assert len({e['event_id'] for e in take['events'][policy]})==32
        assert [e['rest'] for e in take['events'][policy]].count(True)==2
    # Replaying/converting/exporting the completed object submits no further job.
    j.joint_statistics(take['joint_histogram_yxba']); json.dumps(take)
    assert len(backend.calls)==1
    (tmp_path/'joint.json').write_text(json.dumps(take))


def test_classical_commitment_independent_of_returned_counts():
    angles,melody,recorded=j.load_assets(ASSETS)
    e={'job_id':'mock','backend_run_calls':1}
    a=j.assemble_joint({'0000':32},e,angles,melody,recorded,j.prepare_presentation(9))
    b=j.assemble_joint({'1111':32},e,angles,melody,recorded,j.prepare_presentation(9))
    assert a['randomness']==b['randomness']
    assert [r['shared_strategy'] for r in a['rounds']['classical']]==[r['shared_strategy'] for r in b['rounds']['classical']]


def test_failure_no_retry_or_fallback():
    backend=RecordingSimulator(fail=True)
    with pytest.raises(RuntimeError,match='submit'):
        j.generate_joint(backend,32,asset_dir=ASSETS)
    assert len(backend.calls)==1


def test_unknown_or_physical_backend_no_submission():
    for simulator in [None,False]:
        b=SimpleNamespace(options=SimpleNamespace(shots=32),name='unknown',configuration=lambda:SimpleNamespace(simulator=simulator))
        with pytest.raises(RuntimeError): j.simulator_identity(b,32)


def test_legacy_ionq_disabled_before_any_job(monkeypatch):
    monkeypatch.setattr(j,'simulator_identity',lambda b,s:({},True))
    with pytest.raises(RuntimeError,match='disabled on IonQ'): j.run_selected(object(),32,'five-live')


def test_returned_allocation_mismatch_not_retried(monkeypatch):
    b=RecordingSimulator()
    original=b.run
    def wrong(c,**kwargs): return original(c,shots=16)
    monkeypatch.setattr(b,'run',wrong)
    with pytest.raises(RuntimeError,match='validate_result'): j.generate_joint(b,32,asset_dir=ASSETS)
    assert len(b.calls)==1
