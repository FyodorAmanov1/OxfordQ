"""Browser export names remain lossless through the Qollab console decoder."""
import base64
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys

import mido
import pytest
from quantum_duet.browser_projection import arrange_browser

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'components/quantum_duet/tools/extract_duet_exports.py'
spec = importlib.util.spec_from_file_location('duet_exports', TOOL)
exports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exports)

@pytest.fixture(scope='module')
def browser_records():
    raw = (ROOT / 'docs/fixtures/run-result.v1.json').read_bytes()
    bundle = arrange_browser(raw)
    code = """
import {midiBytes} from './components/quantum_duet/web/ui.mjs';
import fs from 'node:fs';
const bundle=JSON.parse(fs.readFileSync(0,'utf8'));
for(const method of ['quantum','classical']) for(const mode of ['raw','arranged']) {
 const events=mode==='raw'?bundle.run_result.events[method]:bundle.playback_projection.policies[method].events;
 console.log(JSON.stringify({event:'duet-export',filename:`quantum-duet-${mode}-${method}.mid`,encoding:'base64',payload:Buffer.from(midiBytes(events,120)).toString('base64')}));
}
"""
    return subprocess.run(['node', '--input-type=module', '-e', code], cwd=ROOT,
                          input=json.dumps(bundle), text=True, capture_output=True, check=True).stdout

def test_actual_browser_raw_and_arranged_console_roundtrip(browser_records, tmp_path):
    names = exports.extract(browser_records, tmp_path)
    assert len(names) == 4
    for line in browser_records.splitlines():
        record = json.loads(line)
        data = (tmp_path / record['filename']).read_bytes()
        assert data == base64.b64decode(record['payload'])
        midi = mido.MidiFile(file=io.BytesIO(data))
        assert midi.ticks_per_beat == 480 and len(midi.tracks) == 3

def test_copied_new_name_cli(browser_records, tmp_path):
    record = json.loads(browser_records.splitlines()[0])
    source = tmp_path / 'payload.txt'
    source.write_text(record['payload'], encoding='utf-8')
    subprocess.run([sys.executable, str(TOOL), str(source), '--filename', record['filename'],
                    '--output-dir', str(tmp_path / 'decoded')], check=True, capture_output=True)
    assert (tmp_path / 'decoded' / record['filename']).read_bytes() == base64.b64decode(record['payload'])

def test_legacy_names_remain_supported(browser_records, tmp_path):
    record = json.loads(browser_records.splitlines()[0])
    lines = []
    for name in ('quantum-duet-quantum.mid', 'quantum-duet-classical.mid'):
        lines.append(json.dumps(dict(record, filename=name), separators=(',', ':')))
    lines.append(json.dumps(dict(event='duet-export', filename='quantum-duet-run.json',
                                encoding='utf-8', payload='{"recorded":true}'), separators=(',', ':')))
    assert exports.extract('\n'.join(lines), tmp_path) == sorted(exports.EXPORT_FILENAMES[:3])

@pytest.mark.parametrize('name', ['../quantum-duet-raw-quantum.mid', 'quantum-duet-arranged-other.mid'])
def test_unexpected_paths_still_rejected(browser_records, tmp_path, name):
    record = dict(json.loads(browser_records.splitlines()[0]), filename=name)
    with pytest.raises(ValueError, match='Unexpected export filename'):
        exports.extract(json.dumps(record, separators=(',', ':')), tmp_path)
    assert not list(tmp_path.iterdir())
