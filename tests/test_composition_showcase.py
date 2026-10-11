"""Freeze, opt-in packaging and lossless export isolation acceptance."""
import ast
import base64
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import wave

import mido
import pytest
from quantum_duet.composition_showcase import load_showcase

ROOT=Path(__file__).resolve().parents[1]
COMPONENT=ROOT/'components/quantum_duet'
ASSETS=COMPONENT/'composition'
spec=importlib.util.spec_from_file_location('composition_exports',COMPONENT/'tools/extract_composition_exports.py')
decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)


@pytest.fixture(scope='module')
def builds(tmp_path_factory):
    p=tmp_path_factory.mktemp('composition-packages')
    for name,extra in [('default',[]),('optional',['--with-composition'])]:
        subprocess.run([sys.executable,str(COMPONENT/'tools/build_qollab.py'),'--out',str(p/name),*extra],check=True,capture_output=True)
    return p


def test_default_package_and_experiment_are_unchanged(builds):
    default=builds/'default'; optional=builds/'optional'
    assert (default/'main.js').read_bytes()==(COMPONENT/'web/main.js').read_bytes()
    assert (default/'index.html').read_bytes()==(COMPONENT/'web/index.html').read_bytes()
    assert not list(default.rglob('*composition*'))
    for path in default.rglob('*'):
        if path.is_file() and path.name not in ('main.js','index.html','manifest.json'):
            assert path.read_bytes()==(optional/path.relative_to(default)).read_bytes()
    assert (optional/'index.html').read_bytes().endswith((default/'index.html').read_bytes())
    files=[p for p in optional.rglob('*') if p.is_file()]
    assert len(files)<=100 and all(p.stat().st_size<=2_000_000 for p in files)


def test_literal_paths_and_no_new_runtime_dependencies(builds):
    source=(COMPONENT/'src/quantum_duet/composition_showcase.py').read_text()
    strings={n.value for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Constant) and isinstance(n.value,str)}
    shipped=json.loads((ASSETS/'freeze.json').read_bytes())['files']
    for name in [*shipped, 'freeze.json']:
        assert 'data/composition/'+name in strings
    assert (builds/'optional/requirements.txt').read_bytes()==(COMPONENT/'requirements.txt').read_bytes()
    assert not (builds/'optional/quantum_duet/orchestration_adapter.py').exists()


def test_bridge_frozen_bytes_duration_source_and_zero_jobs(builds,monkeypatch):
    monkeypatch.chdir(builds/'optional')
    with patch('qiskit.providers.basic_provider.BasicSimulator.run',side_effect=AssertionError('Forbidden backend job')):
        bundle=json.loads(load_showcase())
    assert bundle['backend_jobs_this_playback']==0
    trace=json.loads(bundle['trace_text']); raw=json.loads(bundle['raw_samples_text'])
    assert bundle['trace_text'].encode()==(ASSETS/'trace.json').read_bytes()
    assert bundle['raw_samples_text'].encode()==(ASSETS/'raw-samples.json').read_bytes()
    assert len(raw['motifs'])==16 and sum(map(len,(m['tokens'] for m in raw['motifs'])))==64
    assert trace['source']['raw_samples_sha256']==sha256((ASSETS/'raw-samples.json').read_bytes()).hexdigest()
    for name,encoded in bundle['media'].items():
        contents=base64.b64decode(encoded,validate=True)
        assert contents==(ASSETS/name).read_bytes()
        if name.endswith('.mid'):
            assert mido.MidiFile(file=io.BytesIO(contents)).length==32
        else:
            with wave.open(io.BytesIO(contents)) as w:
                assert w.getnframes()/w.getframerate()==32


def test_loader_rejects_changed_media_without_fallback(builds,monkeypatch):
    monkeypatch.chdir(builds/'optional')
    target=Path('data/composition/improved-melody.mid'); original=target.read_bytes()
    try:
        target.write_bytes(original+b' ')
        with pytest.raises(ValueError,match='asset changed'): load_showcase()
    finally:
        target.write_bytes(original)


def test_both_midi_and_provenance_console_exports_roundtrip(builds,monkeypatch,tmp_path):
    monkeypatch.chdir(builds/'optional');bundle=json.loads(load_showcase())
    records=[dict(event='composition-export',filename=f'oxfordq-composition-{t}.mid',encoding='base64',payload=bundle['media'][f'improved-{t}.mid']) for t in ('melody','arranged')]
    provenance=dict(schema='oxfordq.composition-provenance.v1',raw_samples_text=bundle['raw_samples_text'],trace_text=bundle['trace_text'])
    records.append(dict(event='composition-export',filename='oxfordq-composition-provenance.json',encoding='utf-8',payload=json.dumps(provenance)))
    assert set(decoder.extract('\n'.join(json.dumps(r,separators=(',',':')) for r in records),tmp_path))==set(decoder.FILENAMES)
    for texture in ('melody','arranged'):
        assert (tmp_path/f'oxfordq-composition-{texture}.mid').read_bytes()==(ASSETS/f'improved-{texture}.mid').read_bytes()
    assert json.loads((tmp_path/'oxfordq-composition-provenance.json').read_bytes())==provenance


@pytest.mark.parametrize('filename',['../oxfordq-composition-melody.mid','quantum-duet-raw-quantum.mid'])
def test_export_names_remain_separate(filename,tmp_path):
    text=json.dumps(dict(event='composition-export',filename=filename,encoding='base64',payload='TWhkZA=='),separators=(',',':'))
    with pytest.raises(ValueError,match='Unexpected'):decoder.extract(text,tmp_path)
    assert not list(tmp_path.iterdir())
