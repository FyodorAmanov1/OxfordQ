"""Verify generated upload identity, limits, literal assets and LOCAL inference."""
import argparse, hashlib, importlib, json, sys, zipfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('build',type=Path);a=p.parse_args()
    out=a.build.resolve();root=Path(__file__).resolve().parents[1]
    files=[f for f in out.rglob('*') if f.is_file()]
    assert len(files)<=100 and max(f.stat().st_size for f in files)<=2_000_000
    manifest=json.loads((out/'manifest.json').read_bytes())
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    with zipfile.ZipFile(out.with_suffix('.zip')) as z:
        assert set(z.namelist())=={f.relative_to(out).as_posix() for f in files}
        for f in files:assert z.read(f.relative_to(out).as_posix())==f.read_bytes()
    assert (out/'data/run-result.v1.json').read_bytes()==(root/'docs/team/fixtures/run-result.v1.json').read_bytes()
    assert (out/'data/qollab-local-run.json').read_bytes()==(root/'components/quantum_duet/tests/fixtures/qollab-local-run.json').read_bytes()
    assert not (out/'quantum_duet/orchestration_adapter.py').exists()
    assert not (out/'quantum_duet/browser_projection.py').exists()
    assert (out/'requirements.txt').read_text().strip().splitlines()==['qiskit==2.5.2','numpy>=2.1,<3']
    # Generated namespace, not the editable source install. Path isolation is explicit.
    import os
    os.chdir(out);sys.path.insert(0,str(out))
    for source in (out/'quantum_duet').glob('*.py'):
        m=importlib.import_module('quantum_duet.'+source.stem) if source.stem!='__init__' else importlib.import_module('quantum_duet')
        assert Path(m.__file__).resolve().is_relative_to(out)
    from quantum_duet.recorded_fixture import load_fixture
    from quantum_duet.probe import probe_json
    from quantum_duet.integration import generate_take
    from qiskit.providers.basic_provider import BasicSimulator
    recorded=json.loads(load_fixture());assert recorded['run_result']['execution']['data_status']=='recorded'
    local=BasicSimulator();local.set_options(seed_simulator=32004)
    probe=json.loads(probe_json(local,32))
    take=json.loads(generate_take(local,32,'five-live','ideal-local-development',32005))
    assert take['execution']['backend_run_calls']==1 and take['statistics']['total_independent_shots']==128
    assert len(take['events']['quantum'])==len(take['events']['classical'])==32
    print(json.dumps(dict(status='passed',scope='LOCAL CPython generated namespace; NOT Qollab/Pyodide',
        files=len(files),bytes=sum(f.stat().st_size for f in files),largest_file_bytes=max(f.stat().st_size for f in files),
        fixture_byte_identity=True,probe=probe,live_job_id=take['execution']['job_id'],chsh_shots=128)))

if __name__=='__main__':main()
