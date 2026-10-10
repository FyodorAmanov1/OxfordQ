import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_inference_regressions_in_isolated_runtime():
    subprocess.run([sys.executable, str(ROOT/'tests/inference_checks.py')],
                   cwd=ROOT/'src/quantum_duet', check=True)

def test_installed_assets_from_unrelated_directory(tmp_path):
    output=tmp_path/'run.json'
    subprocess.run([sys.executable,'-m','quantum_duet','--out',str(output),'--shots','32'],
                   cwd=tmp_path, check=True)
    import json
    take=json.loads(output.read_text())
    assert take['execution']['backend_run_calls']==1
    assert take['statistics']['total_independent_shots']==128
