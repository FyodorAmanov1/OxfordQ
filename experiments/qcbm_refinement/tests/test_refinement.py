from copy import deepcopy
import json
from pathlib import Path
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen

import pytest
from qiskit.quantum_info import Statevector
from qiskit.providers.basic_provider import BasicSimulator
from experiments.qcbm_composition import composition as reference
from experiments.qcbm_composition.composition import canonical
from experiments.qcbm_refinement.__main__ import run,load_samples
from experiments.qcbm_refinement.refine import refine,CHORDS,safe_intervals
from experiments.qcbm_refinement.verify import verify,notes
from experiments.qcbm_refinement.preview import Handler


@pytest.fixture(scope='module')
def raw():return load_samples()[0]

def test_preserved_samples_and_no_mutation(raw):
    before=canonical(raw)
    a=refine(raw);b=refine(deepcopy(raw))
    assert canonical(raw)==before and a==b
    assert len(raw['motifs'])==16 and sum(len(m['tokens']) for m in raw['motifs'])==64
    assert len(a['events'])==64 and len(a['unused_sampled_positions'])==20
    assert {e['source_event_id'].split(':')[0] for e in a['events']}=={f'm{i:02}' for i in range(16)}

def test_only_four_eligible_phrase_endings_can_change_pc(raw):
    a=refine(raw)
    old=reference.compose(raw)['events']
    source={f'{m["motif_id"]}:n{j}':reference.base_pitch(t) for m in raw['motifs'] for j,t in enumerate(m['tokens'])}
    cadence=set(a['cadence_event_ids'])
    assert len(cadence)==4
    for before,e in zip(old,a['events']):
        assert e['reference_event_id']==before['event_id'] and e['source_event_id']==before['source_event_id']
        assert e['rest']==before['rest']==(e['pitch'] is None)
        if not e['rest'] and e['pitch']%12!=source[e['source_event_id']]%12:
            assert e['event_id'] in cadence
        if e['event_id'] in cadence:
            assert e==[x for x in a['events'] if x['bar']==e['bar'] and not x['rest']][-1]
    assert a['events'][-1]['pitch']%12==0
    silent=deepcopy(raw)
    for m in silent['motifs']:m['tokens']=[0]*4
    assert all(e['pitch'] is None for e in refine(silent)['events'])

def test_melody_phrase_timing_expression_and_provenance(raw):
    a=refine(raw)
    assert len({e['velocity'] for e in a['events'] if not e['rest']})>1
    assert len({tuple(e['slot_beats'] for e in a['events'] if e['bar']==b) for b in range(16)})>4
    for bar in range(16):
        events=[e for e in a['events'] if e['bar']==bar]
        assert sum(e['slot_beats'] for e in events)==4
        assert events[0]['onset']==4*bar and events[-1]['onset']+events[-1]['slot_beats']==4*(bar+1)
        for e in events:
            assert 0<e['duration']<=e['slot_beats'] and 1<=e['velocity']<=127
            assert e['reference_transformations']
            assert all(t['rule'].startswith('classical_') and t['source_event_ids']==[e['source_event_id']] for t in e['transformations'])

def test_harmony_voicings_functional_cadence_and_lead_protection(raw):
    a=refine(raw)
    assert [a['harmony'][b]['function'] for b in (3,7,11,14,15)]==['dominant']*4+['tonic']
    assert a['harmony'][-2]['chord']=='V7' and a['harmony'][-1]['chord']=='I'
    assert any(len(h['pitch_classes'])==4 for h in a['harmony'])
    assert any(h['inversion']>0 for h in a['harmony'])
    for h in a['harmony']:
        assert set(p%12 for p in h['voicing'])==set(CHORDS[h['chord']])
    assert all(e['origin'].startswith('classical_') and e['source_event_ids'] for e in a['bass']+a['chords'])
    assert all(4*e['bar']<=e['onset']<e['onset']+e['duration']<=4*(e['bar']+1) for e in a['bass']+a['chords'])

def test_accompaniment_shortens_clashes_without_mutating_lead():
    lead=[dict(rest=False,pitch=65,onset=0,duration=1.2,event_id='test-note',source_event_id='m00:n0')]
    snapshot=deepcopy(lead)
    spans,blocked=safe_intervals(0,2,64,(0,4,7),lead)
    assert spans==[(1.2,2)] and blocked[0]['source_event_id']=='m00:n0'
    assert lead==snapshot

def test_whole_generation_no_quantum_execution_and_reproducible_files(tmp_path,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('No sampling or quantum execution allowed')
    monkeypatch.setattr(reference,'sample_motifs',forbidden)
    monkeypatch.setattr(Statevector,'from_instruction',forbidden)
    monkeypatch.setattr(BasicSimulator,'run',forbidden)
    first,second=tmp_path/'one',tmp_path/'two'
    run(first);run(second)
    report=verify(first)
    assert report['status']=='passed'
    for p in first.iterdir():
        if p.suffix in ('.wav','.mid') or p.name in ('raw-samples.json','analysis.json','harmonic-analysis.json'):
            assert p.read_bytes()==(second/p.name).read_bytes()
    assert notes(first/'improved-melody.mid',1)==notes(first/'improved-arranged.mid',1)
    assert json.loads((first/'analysis.json').read_bytes())['subjective_listening']['winner'] is None
    with pytest.raises(ValueError,match='already exists'):run(first)

def test_protected_weights_and_duet_contract_unchanged(tmp_path):
    root=Path(__file__).resolve().parents[3]
    paths=list((root/'components/quantum_duet/src/quantum_duet/data').glob('*.json'))
    paths += [root/'docs/fixtures/run-result.v1.json',root/'components/quantum_duet/tests/fixtures/qollab-local-run.json']
    before={p:p.read_bytes() for p in paths}
    run(tmp_path/'safe')
    assert before=={p:p.read_bytes() for p in paths}

def test_preview_byte_ranges_and_invalid_ranges(tmp_path):
    (tmp_path/'test.wav').write_bytes(b'0123456789')
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(tmp_path)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        request=Request(f'http://127.0.0.1:{server.server_port}/test.wav',headers={'Range':'bytes=2-5'})
        with urlopen(request,timeout=5) as response:
            assert response.status==206 and response.read()==b'2345'
            assert response.headers['Accept-Ranges']=='bytes' and response.headers['Content-Range']=='bytes 2-5/10'
        from urllib.error import HTTPError
        with pytest.raises(HTTPError) as error:
            urlopen(Request(request.full_url,headers={'Range':'bytes=20-'}),timeout=5)
        assert error.value.code==416
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
