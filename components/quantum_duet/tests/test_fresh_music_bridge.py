import base64
import hashlib
import io
import json
from pathlib import Path
import mido
from qiskit.providers.basic_provider import BasicSimulator
from quantum_duet.fresh_qcbm import generate_fresh
from quantum_duet.fresh_music_bridge import compose_result


def test_complete_source_compose_export_without_additional_jobs(monkeypatch):
    assets=Path(__file__).resolve().parents[1]/'src/quantum_duet/data'
    source=generate_fresh(BasicSimulator(),32,20261011,asset_dir=assets)
    def denied(*args,**kwargs):raise AssertionError('Composition/export must not submit a job')
    monkeypatch.setattr(BasicSimulator,'run',denied)
    result=json.loads(compose_result(source))
    assert result['source_json_text']==source
    assert result['source_json_sha256']==hashlib.sha256(source.encode()).hexdigest()
    assert len(result['source']['source_occurrences'])==32
    assert len(result['source']['unused_occurrence_ids'])==12
    midi=base64.b64decode(result['export']['midi_base64'],validate=True)
    assert hashlib.sha256(midi).hexdigest()==result['export']['midi_sha256']
    parsed=mido.MidiFile(file=io.BytesIO(midi))
    assert len(parsed.tracks)==6 and parsed.ticks_per_beat==480
    assert abs(parsed.length-32)<1e-9
    assert [next(m.program for m in track if m.type=='program_change') for track in parsed.tracks[1:]]==[73,71,40,42,0]
    assert json.loads(compose_result(source))==result


def test_actual_ionq_capture_reproduces_losslessly_without_jobs(monkeypatch):
    evidence=Path(__file__).resolve().parents[1]/'evidence/fresh-music'
    raw=(evidence/'ionq-32-source.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='020d4abd5b87b0ce3a6bf6a83a16d2fbcc6713bb7c7920e5d60be173433c3cad'
    def denied(*args,**kwargs):raise AssertionError('Actual evidence replay must not submit a job')
    monkeypatch.setattr(BasicSimulator,'run',denied)
    actual=json.loads((evidence/'ionq-32-composition.json').read_bytes())
    assert actual==json.loads(compose_result(raw.decode()))
    exported=(evidence/'ionq-32-composition.mid').read_bytes()
    assert exported==base64.b64decode(actual['export']['midi_base64'],validate=True)
    assert actual['execution']['job_id']=='01a12d1e-0398-78eb-a4ae-16e82466b52b'
    assert actual['execution']['backend_run_calls']==1
    assert actual['execution']['returned_shots']==32
